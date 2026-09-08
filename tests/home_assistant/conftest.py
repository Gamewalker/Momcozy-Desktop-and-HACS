"""Enable custom integration loading in Home Assistant's test harness."""

from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def custom_integrations(enable_custom_integrations):
    with patch(
        "homeassistant.components.ffmpeg.FFmpegManager.async_get_version",
        return_value="6.0",
    ):
        yield
