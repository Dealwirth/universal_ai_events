"""Config flow for Universal AI Event Finder (Gemini Only)."""
from __future__ import annotations

import logging
from yarl import URL
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)
DOMAIN = "universal_ai_events"

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Universal AI Event Finder."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Säubere den Key strikt von allen unsichtbaren Zeichen/Leerschritten
            clean_key = str(user_input.get("api_key", "")).strip()

            # API Key Test-Aufruf
            session = async_get_clientsession(self.hass)
            test_url = URL("[https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent](https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent)").with_query({"key": clean_key})
            
            try:
                async with session.post(test_url, json={"contents": [{"parts": [{"text": "Ping"}]}]}, timeout=10) as resp:
                    if resp.status == 200:
                        user_input["api_key"] = clean_key
                        return self.async_create_entry(
                            title=f"Events {user_input.get('location', 'Gerolzhofen')}",
                            data=user_input
                        )
                    else:
                        _LOGGER.error("API Key Validierung fehlgeschlagen: HTTP %s", resp.status)
                        errors["base"] = "invalid_api_key"
            except Exception as e:
                _LOGGER.error("Verbindungsfehler bei Key-Prüfung: %s", e)
                errors["base"] = "cannot_connect"

        data_schema = vol.Schema({
            vol.Required("api_key"): str,
            vol.Required("location", default="Gerolzhofen"): str,
            vol.Optional("country", default="Germany"): str,
            vol.Optional("radius_km", default=30): int,
            vol.Optional("criteria", default="Festival, Konzert, Markt, Kirchweih, Weinfest"): str,
            vol.Optional("language", default="Deutsch"): str,
        })

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )
