"""Config flow for simplepush integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME, CONF_PASSWORD
from homeassistant.data_entry_flow import FlowResult

from .const import ATTR_ENCRYPTED, CONF_DEVICE_KEY, CONF_SALT, DEFAULT_NAME, DOMAIN


class SimplePushFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for simplepush."""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle a flow initiated by the user."""
        if user_input is not None:

            await self.async_set_unique_id(user_input[CONF_DEVICE_KEY])
            self._abort_if_unique_id_configured()

            self._async_abort_entries_match(
                {
                    CONF_NAME: user_input[CONF_NAME],
                }
            )
            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data=user_input,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEVICE_KEY): str,
                    vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                    vol.Inclusive(CONF_PASSWORD, ATTR_ENCRYPTED): str,
                    vol.Inclusive(CONF_SALT, ATTR_ENCRYPTED): str,
                }
            ),
        )
