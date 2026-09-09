"""Connect Home Assistant to the local app or an external Momcozy RTSP bridge."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .rtsp import CannotConnect, async_validate_endpoint

PLATFORMS = [Platform.CAMERA]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Validate the bridge, retry unavailable endpoints and set up the camera."""
    try:
        await async_validate_endpoint(entry.data)
    except CannotConnect as err:
        raise ConfigEntryNotReady(
            "Bridge unavailable or credentials rejected; use Reconfigure"
        ) from err
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload camera streams through the platform lifecycle."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
