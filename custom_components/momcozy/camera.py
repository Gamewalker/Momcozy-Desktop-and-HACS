"""Camera entity using Home Assistant's stream and FFmpeg components."""

from __future__ import annotations

import asyncio
import shlex

from homeassistant.components.camera import Camera, CameraEntityFeature
from homeassistant.components.ffmpeg import async_get_image
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .rtsp import stream_url


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Add the configured camera."""
    async_add_entities([MomcozyCamera(entry)])


class MomcozyCamera(Camera):
    """Expose a bridge stream without repeated cloud-triggering RTSP probes."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_supported_features = CameraEntityFeature.STREAM
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry) -> None:
        super().__init__()
        self._data = entry.data
        self._attr_unique_id = entry.entry_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Momcozy",
            model="BM04 via RTSP bridge",
        )
        self.stream_options["rtsp_transport"] = "tcp"
        self._image_lock = asyncio.Lock()

    async def stream_source(self) -> str:
        """Let Home Assistant manage the RTSP stream lifecycle."""
        return stream_url(self._data)

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Decode a JPEG using HA's FFmpeg helper, with TCP input transport."""
        async with self._image_lock:
            # haffmpeg parses the input using shlex; quote the entire URL.
            source = "-rtsp_transport tcp -i " + shlex.quote(stream_url(self._data))
            return await async_get_image(self.hass, source, width=width, height=height)
