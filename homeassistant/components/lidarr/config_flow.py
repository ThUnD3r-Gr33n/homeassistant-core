"""Config flow for Lidarr."""
from __future__ import annotations

from typing import Any

from aiohttp import ClientConnectorError
from aiopyarr import SystemStatus, exceptions
from aiopyarr.lidarr_client import LidarrClient
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import CONF_API_KEY, CONF_URL, CONF_VERIFY_SSL
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_MAX_RECORDS,
    CONF_UPCOMING_DAYS,
    DEFAULT_MAX_RECORDS,
    DEFAULT_NAME,
    DEFAULT_UPCOMING_DAYS,
    DEFAULT_URL,
    DOMAIN,
)


class LidarrConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Lidarr."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the flow."""
        self.entry: ConfigEntry | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
        return LidarrOptionsFlowHandler(config_entry)

    async def async_step_reauth(self, _: dict[str, Any]) -> FlowResult:
        """Handle configuration by re-auth."""
        self.entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])

        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Confirm reauth dialog."""
        if user_input is not None:
            return await self.async_step_user()

        self._set_confirm_only()
        return self.async_show_form(step_id="reauth_confirm")

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle a flow initiated by the user."""
        placeholders = {CONF_URL: self.entry.data[CONF_URL]} if self.entry else None
        errors = {}

        if user_input is None:
            user_input = dict(self.entry.data) if self.entry else None

        else:
            try:
                result = await validate_input(self.hass, user_input)
                if isinstance(result, tuple):
                    user_input[CONF_API_KEY] = result[1]
                elif isinstance(result, str):
                    errors = {"base": result}
            except exceptions.ArrAuthenticationException:
                errors = {"base": "invalid_auth"}
            except (ClientConnectorError, exceptions.ArrConnectionException):
                errors = {"base": "cannot_connect"}
            except exceptions.ArrException:
                errors = {"base": "unknown"}
            if not errors:
                if self.entry:
                    self.hass.config_entries.async_update_entry(
                        self.entry, data=user_input
                    )
                    await self.hass.config_entries.async_reload(self.entry.entry_id)

                    return self.async_abort(reason="reauth_successful")

                return self.async_create_entry(title=DEFAULT_NAME, data=user_input)

        user_input = user_input or {}
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_URL, default=user_input.get(CONF_URL, DEFAULT_URL)
                    ): str,
                    vol.Optional(CONF_API_KEY): str,
                    vol.Optional(
                        CONF_VERIFY_SSL,
                        default=user_input.get(CONF_VERIFY_SSL, False),
                    ): bool,
                }
            ),
            errors=errors,
            description_placeholders=placeholders,
        )


async def validate_input(
    hass: HomeAssistant, data: dict[str, Any]
) -> tuple[str, str, str] | str | SystemStatus:
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """
    lidarr = LidarrClient(
        api_token=data.get(CONF_API_KEY, ""),
        url=data[CONF_URL],
        session=async_get_clientsession(hass),
        verify_ssl=data[CONF_VERIFY_SSL],
    )
    if CONF_API_KEY not in data:
        return await lidarr.async_try_zeroconf()
    return await lidarr.async_get_system_status()


class LidarrOptionsFlowHandler(OptionsFlow):
    """Handle Lidarr client options."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, int] | None = None
    ) -> FlowResult:
        """Manage Lidarr options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = {
            vol.Optional(
                CONF_UPCOMING_DAYS,
                default=self.config_entry.options.get(
                    CONF_UPCOMING_DAYS, DEFAULT_UPCOMING_DAYS
                ),
            ): int,
            vol.Optional(
                CONF_MAX_RECORDS,
                default=self.config_entry.options.get(
                    CONF_MAX_RECORDS, DEFAULT_MAX_RECORDS
                ),
            ): int,
        }

        return self.async_show_form(step_id="init", data_schema=vol.Schema(options))
