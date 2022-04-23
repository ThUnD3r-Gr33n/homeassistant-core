"""Config flow for IntelliFire integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aiohttp import ClientConnectionError
from intellifire4py import (
    AsyncUDPFireplaceFinder,
    IntellifireAsync,
    IntellifireControlAsync,
)
from intellifire4py.exceptions import LoginException
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.dhcp import DhcpServiceInfo
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, LOGGER

STEP_USER_DATA_SCHEMA = vol.Schema({vol.Required(CONF_HOST): str})

MANUAL_ENTRY_STRING = "IP Address"  # Simplified so it does not have to be translated


@dataclass
class DiscoveredHostInfo:
    """Host info for discovery."""

    ip: str
    serial: str | None


async def validate_host_input(host: str) -> str:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    api = IntellifireAsync(host)
    await api.poll()
    serial = api.data.serial
    LOGGER.debug("Found a fireplace: %s", serial)
    # Return the serial number which will be used to calculate a unique ID for the device/sensors
    return serial


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for IntelliFire."""

    VERSION = 1

    def __init__(self):
        """Initialize the Config Flow Handler."""
        self._host: str = ""
        self._serial: str = ""
        self._not_configured_hosts: list[DiscoveredHostInfo] = []
        self._discovered_host: DiscoveredHostInfo
        self._reauth_needed: DiscoveredHostInfo

    async def _find_fireplaces(self):
        """Perform UDP discovery."""
        fireplace_finder = AsyncUDPFireplaceFinder()
        discovered_hosts = await fireplace_finder.search_fireplace(timeout=1)
        configured_hosts = {
            entry.data[CONF_HOST]
            for entry in self._async_current_entries(include_ignore=False)
            if CONF_HOST in entry.data  # CONF_HOST will be missing for ignored entries
        }

        self._not_configured_hosts = [
            DiscoveredHostInfo(ip, None)
            for ip in discovered_hosts
            if ip not in configured_hosts
        ]
        LOGGER.debug("Discovered Hosts: %s", discovered_hosts)
        LOGGER.debug("Configured Hosts: %s", configured_hosts)
        LOGGER.debug("Not Configured Hosts: %s", self._not_configured_hosts)

    async def validate_api_access_and_create_or_update(
        self, *, host: str, username: str, password: str, serial: str
    ):
        """Validate username/password against api."""
        ift_control = IntellifireControlAsync(fireplace_ip=host)

        LOGGER.debug("Attempting login to iftapi with: %s", username)
        # This can throw an error which will be handled above
        try:
            await ift_control.login(username=username, password=password)
            await ift_control.get_username()
        finally:
            await ift_control.close()

        data = {CONF_HOST: host, CONF_PASSWORD: password, CONF_USERNAME: username}

        # Update or Create
        existing_entry = await self.async_set_unique_id(serial)
        if existing_entry:
            self.hass.config_entries.async_update_entry(existing_entry, data=data)
            await self.hass.config_entries.async_reload(existing_entry.entry_id)
            return self.async_abort(reason="reauth_successful")
        return self.async_create_entry(title=f"Fireplace {serial}", data=data)

    async def async_step_api_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure API access."""

        errors = {}
        control_schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )

        if user_input is not None:

            control_schema = vol.Schema(
                {
                    vol.Required(
                        CONF_USERNAME, default=user_input.get(CONF_USERNAME, "")
                    ): str,
                    vol.Required(
                        CONF_PASSWORD, default=user_input.get(CONF_PASSWORD, "")
                    ): str,
                }
            )

            if user_input[CONF_USERNAME] != "":
                try:
                    return await self.validate_api_access_and_create_or_update(
                        host=self._host,
                        username=user_input[CONF_USERNAME],
                        password=user_input[CONF_PASSWORD],
                        serial=self._serial,
                    )

                except (ConnectionError, ClientConnectionError):
                    errors["base"] = "iftapi_connect"
                    LOGGER.error("ERROR: iftapi_connect")
                except LoginException:
                    errors["base"] = "api_error"
                    LOGGER.error("ERROR: api_error")

        return self.async_show_form(
            step_id="api_config", errors=errors, data_schema=control_schema
        )

    async def _async_validate_ip_and_continue(self, host: str) -> FlowResult:
        """Validate local config and continue."""
        self._async_abort_entries_match({CONF_HOST: host})
        self._serial = await validate_host_input(host)
        await self.async_set_unique_id(self._serial, raise_on_progress=False)
        self._abort_if_unique_id_configured(updates={CONF_HOST: host})
        # Store current data and jump to next stage
        self._host = host

        return await self.async_step_api_config()

    async def async_step_manual_device_entry(self, user_input=None):
        """Handle manual input of local IP configuration."""
        LOGGER.debug("STEP: manual_device_entry")
        errors = {}
        self._host = user_input.get(CONF_HOST) if user_input else None
        if user_input is not None:
            try:
                return await self._async_validate_ip_and_continue(self._host)
            except (ConnectionError, ClientConnectionError):
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="manual_device_entry",
            errors=errors,
            data_schema=vol.Schema({vol.Required(CONF_HOST, default=self._host): str}),
        )

    async def async_step_pick_device(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Pick which device to configure."""
        errors = {}
        LOGGER.debug("STEP: pick_device")

        if user_input is not None:
            if user_input[CONF_HOST] == MANUAL_ENTRY_STRING:
                return await self.async_step_manual_device_entry()

            try:
                return await self._async_validate_ip_and_continue(user_input[CONF_HOST])
            except (ConnectionError, ClientConnectionError):
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="pick_device",
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): vol.In(
                        [host.ip for host in self._not_configured_hosts]
                        + [MANUAL_ENTRY_STRING]
                    )
                }
            ),
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Start the user flow."""

        # Launch fireplaces discovery
        await self._find_fireplaces()
        LOGGER.debug("STEP: user")
        if self._not_configured_hosts:
            LOGGER.debug("Running Step: pick_device")
            return await self.async_step_pick_device()
        LOGGER.debug("Running Step: manual_device_entry")
        return await self.async_step_manual_device_entry()

    async def async_step_reauth(self, user_input=None):
        """Perform reauth upon an API authentication error."""
        LOGGER.debug("STEP: reauth")
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])

        # populate the expected vars
        self._serial = entry.unique_id
        self._host = entry.data[CONF_HOST]

        placeholders = {CONF_HOST: self._host, "serial": self._serial}
        self.context["title_placeholders"] = placeholders
        return await self.async_step_api_config()

    async def async_step_dhcp(self, discovery_info: DhcpServiceInfo) -> FlowResult:
        """Handle DHCP Discovery."""

        LOGGER.debug("STEP: dhcp")
        # Run validation logic on ip
        host = discovery_info.ip

        self._async_abort_entries_match({CONF_HOST: host})
        try:
            self._serial = await validate_host_input(host)
        except (ConnectionError, ClientConnectionError):
            return self.async_abort(reason="not_intellifire_device")

        await self.async_set_unique_id(self._serial)
        self._abort_if_unique_id_configured(updates={CONF_HOST: host})
        self._discovered_host = DiscoveredHostInfo(ip=host, serial=self._serial)

        placeholders = {CONF_HOST: host, "serial": self._serial}
        self.context["title_placeholders"] = placeholders
        self._set_confirm_only()

        return await self.async_step_dhcp_confirm()

    async def async_step_dhcp_confirm(self, user_input=None):
        """Attempt to confirm."""

        LOGGER.debug("STEP: dhcp_confirm")
        # Add the hosts one by one
        host = self._discovered_host.ip
        serial = self._discovered_host.serial

        if user_input is None:
            # Show the confirmation dialog
            return self.async_show_form(
                step_id="dhcp_confirm",
                description_placeholders={CONF_HOST: host, "serial": serial},
            )

        return self.async_create_entry(
            title=f"Fireplace {serial}",
            data={CONF_HOST: host},
        )
