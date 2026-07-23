"""Config flow for Universal AI Event Finder (Gemini Only)."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

DOMAIN = "universal_ai_events"

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Universal AI Event Finder."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Bereinige den API-Key von versehentlichen Zeichen
            clean_key = user_input.get("api_key", "").strip()
            if not clean_key:
                errors["base"] = "invalid_api_key"
            else:
                user_input["api_key"] = clean_key
                return self.async_create_entry(
                    title=f"Events {user_input.get('location', 'Local')}",
                    data=user_input
                )

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
