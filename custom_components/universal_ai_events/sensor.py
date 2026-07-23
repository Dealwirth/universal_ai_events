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
        
        # 1. API Key strikt bereinigen (entfernt Klammern [], (), Leerzeichen, Anführungszeichen)
        raw_key = str(self._config.get("api_key", ""))
        api_key = re.sub(r"[\[\]\(\)\"'\s]", "", raw_key).strip()

        location = self._config.get("location", "Gerolzhofen")
        country = self._config.get("country", "Germany")
        radius = self._config.get("radius_km", 30)
        criteria = self._config.get("criteria", "Festival, Konzert, Markt, Kirchweih, Weinfest")
        lang = self._config.get("language", "Deutsch")

        if not api_key:
            _LOGGER.error("Universal AI Event Finder: Kein gültiger Gemini API-Key hinterlegt!")
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
            # Reiner Endpoint ohne Klammern-Gefahr
            endpoint = f"[https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=](https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=){api_key}"
            
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                # Google Search Retrieval aktiviert den Zugriff auf das Live-Web
                "tools": [{"google_search_retrieval": {}}]
            }
            
            async with session.post(endpoint, json=payload, timeout=45) as r:
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

        # 2. JSON-Array aus dem Antworttext filtern
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
