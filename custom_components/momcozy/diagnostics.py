"""Minimal diagnostics: no host, path, stream URL, credentials or entry data."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict:
    """Return only non-identifying implementation details."""
    return {
        "entry_version": entry.version,
        "transport": "tcp",
        "authentication_configured": bool(entry.data.get("username")),
    }
