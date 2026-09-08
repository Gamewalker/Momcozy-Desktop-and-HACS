"""UI configuration for one camera endpoint per entry."""

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import DEFAULT_PATH, DEFAULT_PORT, DOMAIN
from .rtsp import (
    CannotConnect,
    InvalidAuth,
    async_validate_endpoint,
    endpoint_id,
    normalize_config,
)

SCHEMA = vol.Schema(
    {
        vol.Required("name", default="Momcozy BM04"): cv.string,
        vol.Required("host"): cv.string,
        vol.Required("port", default=DEFAULT_PORT): cv.port,
        vol.Required("path", default=DEFAULT_PATH): cv.string,
        vol.Optional("username", default=""): cv.string,
        vol.Optional("password", default=""): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        ),
    }
)


class MomcozyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Configure a local RTSP bridge, not a Momcozy cloud account."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Create a camera entry."""
        return await self._async_configure("user", user_input)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change connection details while preserving the camera entity ID."""
        return await self._async_configure("reconfigure", user_input)

    async def _async_configure(
        self, step: str, user_input: dict[str, Any] | None
    ) -> ConfigFlowResult:
        errors = {}
        entry = self._get_reconfigure_entry() if step == "reconfigure" else None
        if user_input is not None:
            try:
                data = normalize_config(user_input)
                identity = endpoint_id(data)
                if any(
                    endpoint_id(other.data) == identity
                    and (entry is None or other.entry_id != entry.entry_id)
                    for other in self._async_current_entries()
                ):
                    return self.async_abort(reason="already_configured")
                await async_validate_endpoint(data)
            except ValueError:
                errors["base"] = "invalid_config"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            else:
                if entry is not None:
                    return self.async_update_reload_and_abort(
                        entry,
                        unique_id=identity,
                        title=data["name"],
                        data=data,
                        reason="reconfigure_successful",
                    )
                await self.async_set_unique_id(identity)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=data["name"], data=data)
        return self.async_show_form(
            step_id=step,
            data_schema=self.add_suggested_values_to_schema(
                SCHEMA,
                user_input
                if user_input is not None
                else (entry.data if entry else None),
            ),
            errors=errors,
        )
