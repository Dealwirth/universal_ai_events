"""Config flow for Universal AI Event Finder."""
import voluptuous as vol
from homeassistant import config_entries

DOMAIN = "universal_ai_events"

class UniversalEventsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            return self.async_create_entry(
                title=f"Events: {user_input['location']} ({user_input['radius_km']}km)", 
                data=user_input
            )

        data_schema = vol.Schema({
            vol.Required("api_provider", default="groq"): vol.In({
                "groq": "Groq API (Kostenlos & extrem schnell)",
                "gemini": "Google Gemini API (Kostenloser Tier)",
                "perplexity": "Perplexity API (Kostenpflichtig / Hohe Präzision)"
            }),
            vol.Required("api_key"): str,
            vol.Required("location", default="Gerolzhofen"): str,
            vol.Required("country", default="Germany"): str,
            vol.Required("radius_km", default=30): int,
            vol.Required("update_hours", default=24): int,
            vol.Required(
                "criteria", 
                default="Weinfest, Kirchweih, Kerwa, Open Air, Rock-Konzert, Märkte, Fest, Festival"
            ): str,
            vol.Optional("language", default="Deutsch"): str,
        })

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )
