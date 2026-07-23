"""Support for Universal AI Events sensor with Google Gemini."""
from __future__ import annotations

from datetime import timedelta
import json
import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

DOMAIN = "universal_ai_events"
SCAN_INTERVAL = timedelta(hours=12)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Set up the event sensor from a config entry."""
    config = entry.data
    sensor = UniversalEventSensor(hass, entry, config)
    async_add_entities([sensor], True)


class UniversalEventSensor(SensorEntity):
    """Representation of the AI Events Sensor."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, config: dict):
        self.hass = hass
        self._entry = entry
        self._config = config
        
        # Generiert einen festen Slug als Entity Name
        loc_slug = config.get("location", "gerolzhofen").lower().replace(" ", "_")
        self.entity_id = f"sensor.events_{loc_slug}"
        self._attr_name = f"Events {config.get('location', 'Gerolzhofen')}"
        self._attr_unique_id = f"ai_events_{entry.entry_id}"
        self._attr_icon = "mdi:calendar-search"
        self._attr_native_value = 0
        self._events_list = []

    @property
    def extra_state_attributes(self) -> dict:
        """Return state attributes."""
        return {
            "total_events": len(self._events_list),
            "events": self._events_list,
            "location": self._config.get("location"),
            "radius_km": self._config.get("radius_km"),
            "provider_used": self._config.get("api_provider"),
        }

    async def async_update(self) -> None:
        """Fetch events dynamically via Google Gemini with Web Grounding."""
        _LOGGER.info("Starting AI Event search...")
        
        provider = self._config.get("api_provider", "gemini")
        api_key = str(self._config.get("api_key", "")).strip()
        location = self._config.get("location", "Gerolzhofen")
        country = self._config.get("country", "Germany")
        radius = self._config.get("radius_km", 30)
        criteria = self._config.get("criteria", "Festival, Konzert, Markt, Kirchweih, Weinfest")
        lang = self._config.get("language", "Deutsch")

        if not api_key:
            _LOGGER.error("AI Event Finder: Kein API Key hinterlegt!")
            return

        prompt = (
            f"Durchsuche das Internet nach öffentlichen Veranstaltungen und Events in den nächsten 7 Tagen "
            f"im Umkreis von {radius} km um {location} ({country}).\n"
            f"Kriterien/Kategorien: {criteria}.\n"
            f"Antworte ausschließlich auf {lang}.\n"
            "Gib NUR ein valides JSON-Array von Objekten zurück. Kein Markdown (keine ```json Tags).\n"
            "Jedes Objekt MUSS folgende Felder enthalten:\n"
            "id, title, date, time, location_name, city, category, description, price, url."
        )

        session = async_get_clientsession(self.hass)
        raw_response = None

        try:
            if provider == "gemini":
                # Saubere API-URL ohne Klammern oder Anführungszeichen-Salat
                clean_key = api_key.replace("[", "").replace("]", "").replace("(", "").replace(")", "").strip()
                endpoint = f"[https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=](https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=){clean_key}"
                
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    # Aktiviert die Live-Google-Suche
                    "tools": [{"google_search_retrieval": {}}]
                }
                
                async with session.post(endpoint, json=payload, timeout=45) as r:
                    _LOGGER.info("Gemini HTTP Status: %s", r.status)
                    res_json = await r.json()
                    
                    if r.status != 200:
                        _LOGGER.error("Gemini API Fehler (Status %s): %s", r.status, res_json)
                        return
                    
                    # Antwort extrahieren
                    raw_response = res_json["candidates"][0]["content"]["parts"][0]["text"]

        except Exception as err:
            _LOGGER.error("Netzwerk-/API-Fehler bei %s: %s", provider, err)
            return

        if not raw_response:
            _LOGGER.warning("Keine Antwort von Gemini erhalten.")
            return

        try:
            start = raw_response.find("[")
            end = raw_response.rfind("]") + 1
            if start != -1 and end > start:
                clean_json = raw_response[start:end]
                self._events_list = json.loads(clean_json)
                self._attr_native_value = len(self._events_list)
                _LOGGER.info("Erfolgreich %s Events geladen!", len(self._events_list))
            else:
                _LOGGER.error("Kein gültiges JSON-Array in Antwort gefunden: %s", raw_response[:200])
        except Exception as e:
            _LOGGER.error("JSON Parse Fehler: %s", e)
