"""Support for Geolocation entities for Local Events worldwide."""
from __future__ import annotations

from datetime import timedelta
import json
import logging
import math

import aiohttp

# Offizieller, robuster Import für GeolocationEntity in Home Assistant
from homeassistant.components.geo_location import GeolocationEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

DOMAIN = "universal_ai_events"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Set up the event entities from a config entry."""
    config = entry.data
    updater = UniversalEventDataUpdater(hass, async_add_entities, config)
    
    # Erstes Update ausführen
    await updater.async_update()


class UniversalEventDataUpdater:
    """Class to manage fetching event data globally."""

    def __init__(self, hass: HomeAssistant, async_add_entities, config: dict):
        self.hass = hass
        self.async_add_entities = async_add_entities
        self.config = config
        self.entities: dict[str, UniversalEventEntity] = {}
        self.center_lat = 52.5200
        self.center_lon = 13.4050

    async def _geocode_location(self, session: aiohttp.ClientSession, location: str, country: str):
        """Find center coordinates globally using Nominatim/OpenStreetMap."""
        try:
            url = f"https://nominatim.openstreetmap.org/search?q={location},{country}&format=json&limit=1"
            headers = {"User-Agent": "HomeAssistantUniversalEventFinder/1.0"}
            async with session.get(url, headers=headers, timeout=10) as resp:
                data = await resp.json()
                if data:
                    return float(data[0]["lat"]), float(data[0]["lon"])
        except Exception as e:
            _LOGGER.warning("Geocoding failed, falling back to defaults: %s", e)
        return 52.5200, 13.4050

    async def async_update(self, _=None) -> None:
        """Fetch events dynamically via chosen AI provider."""
        _LOGGER.info("Fetching events globally via AI...")
        
        provider = self.config.get("api_provider", "groq")
        api_key = self.config.get("api_key")
        location = self.config.get("location", "Berlin")
        country = self.config.get("country", "Germany")
        radius = self.config.get("radius_km", 30)
        criteria = self.config.get("criteria", "Festival, Concert, Market, Open Air")
        lang = self.config.get("language", "Deutsch")

        prompt = (
            f"Search for public upcoming events in the next 7 days within a {radius} km radius "
            f"around {location} in {country}.\n"
            f"Filter Criteria / Keywords: {criteria}.\n"
            f"Respond in language: {lang}.\n"
            "Return ONLY a raw JSON array of objects. Do NOT wrap in markdown tags like ```json.\n"
            "Each object must have these fields:\n"
            "id (unique string), title, date, time, location_name, city, latitude (float), longitude (float), "
            "category, description, price, url."
        )

        session = async_get_clientsession(self.hass)
        self.center_lat, self.center_lon = await self._geocode_location(session, location, country)

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
                events = json.loads(clean_json)

                new_entities = []
                for ev in events:
                    event_id = str(ev.get("id", ev.get("title")))
                    
                    lat = ev.get("latitude")
                    lon = ev.get("longitude")
                    if not lat or not lon:
                        loc_str = f"{ev.get('location_name', '')} {ev.get('city', location)}"
                        lat, lon = await self._geocode_location(session, loc_str, country)

                    ev["latitude"] = lat
                    ev["longitude"] = lon

                    if event_id not in self.entities:
                        entity = UniversalEventEntity(event_id, ev, self.center_lat, self.center_lon)
                        self.entities[event_id] = entity
                        new_entities.append(entity)
                    else:
                        self.entities[event_id].update_data(ev)

                if new_entities:
                    self.async_add_entities(new_entities)

        except Exception as e:
            _LOGGER.error("Failed to parse AI response JSON: %s", e)


class UniversalEventEntity(GeolocationEntity):
    """Representation of a global event entity."""

    def __init__(self, event_id: str, data: dict, center_lat: float, center_lon: float):
        self._event_id = event_id
        self.center_lat = center_lat
        self.center_lon = center_lon
        self.update_data(data)

    @property
    def unique_id(self) -> str:
        """Return a unique ID for this entity."""
        return f"universal_event_{self._event_id}"

    def update_data(self, data: dict):
        self._attr_name = f"{data.get('title')} ({data.get('date')})"
        self._attr_latitude = float(data.get("latitude", self.center_lat))
        self._attr_longitude = float(data.get("longitude", self.center_lon))
        self._attr_distance = self._calc_distance(self._attr_latitude, self._attr_longitude)
        self._attr_source = "universal_ai_events"
        self._attr_icon = self._get_icon(data.get("category", "") + " " + data.get("title", ""))
        
        self._attr_extra_state_attributes = {
            "Datum": data.get("date"),
            "Uhrzeit": data.get("time"),
            "Ort": f"{data.get('location_name', '')}, {data.get('city', '')}",
            "Kategorie": data.get("category"),
            "Eintritt": data.get("price", "K.A."),
            "Beschreibung": data.get("description"),
            "Link": data.get("url", ""),
            "Entfernung_km": self._attr_distance,
        }

    def _get_icon(self, text: str) -> str:
        t = text.lower()
        if any(w in t for w in ["wein", "wine"]): return "mdi:wine"
        if any(w in t for w in ["rock", "konzert", "concert", "music"]): return "mdi:guitar-electric"
        if any(w in t for w in ["kerwa", "kirchweih", "fair", "fest"]): return "mdi:ferris-wheel"
        if any(w in t for w in ["market", "markt"]): return "mdi:store"
        return "mdi:calendar-star"

    def _calc_distance(self, lat: float, lon: float) -> float:
        dlat = math.radians(lat - self.center_lat)
        dlon = math.radians(lon - self.center_lon)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(self.center_lat)) * math.cos(math.radians(lat)) * math.sin(dlon/2)**2
        return round(6371 * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a)), 1)
