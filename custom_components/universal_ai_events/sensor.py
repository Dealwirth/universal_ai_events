"""Support for Universal AI Events sensor powered strictly by Google Gemini."""
from __future__ import annotations

from datetime import timedelta
import json
import logging
import re

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
    """Representation of the Gemini AI Events Sensor."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, config: dict):
        self.hass = hass
        self._entry = entry
        self._config = config
        
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
            "provider_used": "Google Gemini (Live Search)",
        }

    async def async_update(self) -> None:
        """Fetch events dynamically via Google Gemini with Web Grounding."""
        _LOGGER.info("Gezielte KI-Event-Suche via Google Gemini wird gestartet...")
        
        raw_key = str(self._config.get("api_key", ""))
        
        # Extremer Schutz-Filter: Falls die URL oder Markdown im Key gelandet ist, schneiden wir sie ab
        # Ein echter Gemini API Key besteht nur aus Alphanumerischen Zeichen, Bindestrichen und Unterstrichen (beginnt meist mit AIzaSy...)
        cleaned_key = re.sub(r"https?://\S+", "", raw_key) # Entfernt URLs
        cleaned_key = re.sub(r"[\[\]\(\)\"'\s=]", "", cleaned_key) # Entfernt Klammern, Anführungszeichen, Gleichheitszeichen
        
        # Falls der Key durch falsches Einfügen mit "key=" getrennt war:
        if "key=" in raw_key:
            cleaned_key = raw_key.split("key=")[-1]
            cleaned_key = re.sub(r"[\[\]\(\)\"'\s]", "", cleaned_key)

        location = self._config.get("location", "Gerolzhofen")
        country = self._config.get("country", "Germany")
        radius = self._config.get("radius_km", 30)
        criteria = self._config.get("criteria", "Festival, Konzert, Markt, Kirchweih, Weinfest")
        lang = self._config.get("language", "Deutsch")

        if not cleaned_key or len(cleaned_key) < 10:
            _LOGGER.error("Universal AI Event Finder: Ungültiger oder beschädigter Gemini API-Key! Extrahierter Key war: '%s'", cleaned_key)
            return

        prompt = (
            f"Durchsuche das Internet nach aktuellen öffentlichen Veranstaltungen und Events in den nächsten 7 Tagen "
            f"im Umkreis von {radius} km um {location} ({country}).\n"
            f"Kriterien/Kategorien: {criteria}.\n"
            f"Antworte ausschließlich auf {lang}.\n"
            "Gib NUR ein valides JSON-Array von Objekten zurück. Verwende keinerlei Markdown-Formatierung wie ```json.\n"
            "Jedes Objekt MUSS folgende Felder haben:\n"
            "id, title, date, time, location_name, city, category, description, price, url."
        )

        session = async_get_clientsession(self.hass)

        try:
            # Feste Basis-URL ohne dynamische Manipulation
            endpoint = "[https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent](https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent)"
            params = {"key": cleaned_key}
            
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "tools": [{"google_search_retrieval": {}}]
            }
            
            # Wir übergeben den Key sauber als URL-Parameter 'params', um URL-Formatierungsfehler zu vermeiden
            async with session.post(endpoint, params=params, json=payload, timeout=45) as r:
                _LOGGER.info("Gemini HTTP Status-Code: %s", r.status)
                res_json = await r.json()
                
                if r.status != 200:
                    _LOGGER.error("Gemini API Fehler (Status %s): %s", r.status, res_json)
                    return
                
                candidates = res_json.get("candidates", [])
                if not candidates:
                    _LOGGER.warning("Gemini hat keine Treffer/Antworten geliefert.")
                    return
                    
                raw_response = candidates[0]["content"]["parts"][0]["text"]

        except Exception as err:
            _LOGGER.error("Netzwerk- oder API-Fehler bei Gemini: %s", err)
            return

        # JSON aus der KI-Antwort extrahieren
        try:
            start = raw_response.find("[")
            end = raw_response.rfind("]") + 1
            if start != -1 and end > start:
                clean_json = raw_response[start:end]
                self._events_list = json.loads(clean_json)
                self._attr_native_value = len(self._events_list)
                _LOGGER.info("Erfolgreich %s Events für %s geladen!", len(self._events_list), location)
            else:
                _LOGGER.error("Kein JSON-Array in der Gemini-Antwort gefunden: %s", raw_response[:200])
        except Exception as e:
            _LOGGER.error("JSON-Parse-Fehler: %s", e)
