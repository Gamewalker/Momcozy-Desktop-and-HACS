"""Real Home Assistant flow/entity lifecycle with network and FFmpeg mocked."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import ConfigEntryNotReady
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.momcozy import async_setup_entry, async_unload_entry
from custom_components.momcozy.camera import MomcozyCamera
from custom_components.momcozy.diagnostics import async_get_config_entry_diagnostics
from custom_components.momcozy.rtsp import CannotConnect, InvalidAuth

DATA = {
    "host": "bridge.local",
    "port": 18554,
    "path": "bm04_1",
    "name": "Nursery",
    "username": "viewer",
    "password": "test-password-123456",
}


@pytest.fixture
def entry(hass):
    result = MockConfigEntry(
        domain="momcozy",
        data=DATA,
        title="Nursery",
        unique_id="bridge.local:18554/bm04_1",
    )
    result.add_to_hass(hass)
    return result


@pytest.mark.asyncio
async def test_user_flow(hass):
    with (
        patch(
            "custom_components.momcozy.config_flow.async_validate_endpoint",
            new_callable=AsyncMock,
        ),
        patch("custom_components.momcozy.async_setup_entry", return_value=True),
    ):
        result = await hass.config_entries.flow.async_init(
            "momcozy", context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] is FlowResultType.FORM
        result = await hass.config_entries.flow.async_configure(result["flow_id"], DATA)
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"] == DATA
        await hass.async_block_till_done()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "expected"),
    [(CannotConnect, "cannot_connect"), (InvalidAuth, "invalid_auth")],
)
async def test_connection_errors(hass, error, expected):
    with patch(
        "custom_components.momcozy.config_flow.async_validate_endpoint",
        side_effect=error,
    ):
        result = await hass.config_entries.flow.async_init(
            "momcozy", context={"source": config_entries.SOURCE_USER}, data=DATA
        )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": expected}


@pytest.mark.asyncio
async def test_duplicate(hass, entry):
    result = await hass.config_entries.flow.async_init(
        "momcozy", context={"source": config_entries.SOURCE_USER}, data=DATA
    )
    assert result["reason"] == "already_configured"


@pytest.mark.asyncio
async def test_reconfigure_preserves_entity_identity(hass, entry):
    identity = MomcozyCamera(entry).unique_id
    with (
        patch(
            "custom_components.momcozy.config_flow.async_validate_endpoint",
            new_callable=AsyncMock,
        ),
        patch.object(hass.config_entries, "async_schedule_reload"),
    ):
        result = await hass.config_entries.flow.async_init(
            "momcozy",
            context={
                "source": config_entries.SOURCE_RECONFIGURE,
                "entry_id": entry.entry_id,
            },
            data={**DATA, "host": "new-bridge.local"},
        )
    assert result["reason"] == "reconfigure_successful"
    assert entry.data["host"] == "new-bridge.local"
    assert MomcozyCamera(entry).unique_id == identity


@pytest.mark.asyncio
async def test_setup_and_unload(hass, entry):
    with (
        patch(
            "custom_components.momcozy.async_validate_endpoint", new_callable=AsyncMock
        ),
        patch.object(
            hass.config_entries, "async_forward_entry_setups", new_callable=AsyncMock
        ) as setup,
        patch.object(
            hass.config_entries, "async_unload_platforms", return_value=True
        ) as unload,
    ):
        assert await async_setup_entry(hass, entry)
        setup.assert_awaited_once()
        assert await async_unload_entry(hass, entry)
        unload.assert_awaited_once()


@pytest.mark.asyncio
async def test_setup_offline_retries(hass, entry):
    with (
        patch(
            "custom_components.momcozy.async_validate_endpoint",
            side_effect=CannotConnect,
        ),
        pytest.raises(ConfigEntryNotReady),
    ):
        await async_setup_entry(hass, entry)


@pytest.mark.asyncio
async def test_camera_and_diagnostics(hass, entry):
    camera = MomcozyCamera(entry)
    camera.hass = hass
    assert camera.stream_options["rtsp_transport"] == "tcp"
    assert (
        await camera.stream_source()
        == "rtsp://viewer:test-password-123456@bridge.local:18554/bm04_1"
    )
    with patch(
        "custom_components.momcozy.camera.async_get_image", return_value=b"jpeg"
    ) as image:
        assert await camera.async_camera_image(320, 180) == b"jpeg"
        assert image.call_args.args[1].startswith("-rtsp_transport tcp -i ")
        assert image.call_args.kwargs == {"width": 320, "height": 180}
    assert not camera.should_poll
    diagnostics = await async_get_config_entry_diagnostics(hass, entry)
    assert diagnostics == {
        "entry_version": 1,
        "transport": "tcp",
        "authentication_configured": True,
    }
