"""The Universal AI Event Finder integration."""
import logging

_LOGGER = logging.getLogger(__name__)

DOMAIN = "universal_ai_events"
PLATFORMS = ["geo_location"]

async def async_setup_entry(hass, entry):
    """Set up Universal AI Event Finder from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass, entry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_forward_entry_unload(entry, "geo_location")
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
