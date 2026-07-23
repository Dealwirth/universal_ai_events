"""Support for Universal AI Events sensor."""
from __future__ import annotations

from datetime import timedelta
import json
import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval

_LOGGER = logging.getLogger(__name__)

DOMAIN = "universal_ai_events"


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
        self._attr_name = f"Events {config.get('location', 'Local')}"
        self._attr_unique_id = f"ai_events_{entry.entry_id}"
        self._attr_icon = "mdi:calendar-search"
        self._attr_native_value = 0
        self._events_list = []
        self._extra_attributes = {}

    @property
    def extra_state_attributes(self) -> dict:
        """Return state attributes."""
        return {
            "total_events": len(self._events_list),
            "events": self._events_list,
            "location": self._config.get("location"),
            "radius_km": self._config.get("radius_km"),
        }

    async def async_update(self) -> None:
        """Fetch events dynamically via chosen AI provider."""
        _LOGGER.info("Updating AI Events sensor...")
        
        provider = self._config.get("api_provider", "groq")
        api_key = self._config.get("api_key")
        location = self._config.get("location", "Berlin")
        country = self._config.get("country", "Germany")
        radius = self._config.get("radius_km", 30)
        criteria = self._config.get("criteria", "Festival, Concert, Market, Open Air")
        lang = self._config.get("language", "Deutsch")

        prompt = (
            f"Search for public upcoming events in the next 7 days within a {radius} km radius "
            f"around {location} in {country}.\n"
            f"Filter Criteria / Keywords: {criteria}.\n"
            f"Respond in language: {lang}.\n"
            "Return ONLY a raw JSON array of objects. Do NOT wrap in markdown tags like ```json.\n"
            "Each object must have these fields:\n"
            "id (unique string), title, date, time, location_name, city, category, description, price, url."
        )

        session = async_get_clientsession(self.hass)

        raw_response = None
        try:
            if provider == "groq":
                endpoint = "[https://api.groq.com/openai/v1/chat/completions](https://api.groq.com/openai/v1/chat/completions)"
                headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                payload = {
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": prompt}]
                }
                async with session.post(endpoint, json=payload, headers=headers, timeout=30) as r:
                    res_json = await r.json()
                    raw_response = res_json["choices"][0]["message"]["content"]
            
            elif provider == "gemini":
                endpoint = f"[https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=](https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=){api_key}"
                payload = {"contents": [{"parts": [{"text": prompt}]}]}
                async with session.post(endpoint, json=payload, timeout=30) as r:
                    res_json = await r.json()
                    raw_response = res_json["candidates"][0]["content"]["parts"][0]["text"]
                    
            elif provider == "perplexity":
                endpoint = "[https://api.perplexity.ai/chat/completions](https://api.perplexity.ai/chat/completions)"
                headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                payload = {
                    "model": "sonar",
                    "messages": [{"role": "user", "content": prompt}]
                }
                async with session.post(endpoint, json=payload, headers=headers, timeout=30) as r:
                    res_json = await r.json()
                    raw_response = res_json["choices"][0]["message"]["content"]
        except Exception as err:
            _LOGGER.error("API error for provider %s: %s", provider, err)
            return

        if not raw_response:
            return

        try:
            start = raw_response.find("[")
            end = raw_response.rfind("]") + 1
            if start != -1 and end != 0:
                clean_json = raw_response[start:end]
                self._events_list = json.loads(clean_json)
                self._attr_native_value = len(self._events_list)
        except Exception as e:
            _LOGGER.error("Failed to parse AI response JSON: %s", e)
