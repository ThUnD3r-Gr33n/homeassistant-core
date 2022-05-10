"""Config flow for Overkiz (by Somfy) integration."""
from __future__ import annotations

from collections.abc import Mapping
from dis import disco
from typing import Any, cast

from aiohttp import ClientError
from pyoverkiz.client import OverkizClient
from pyoverkiz.const import SUPPORTED_SERVERS
from pyoverkiz.exceptions import (
    BadCredentialsException,
    CozyTouchBadCredentialsException,
    MaintenanceException,
    TooManyAttemptsBannedException,
    TooManyRequestsException,
    UnknownUserException,
)
from pyoverkiz.models import OverkizServer, obfuscate_id
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import dhcp, zeroconf
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_TOKEN, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .const import CONF_HUB, CONF_TOKEN_UUID, DEFAULT_HOST, DEFAULT_HUB, DOMAIN, LOGGER

LOCAL = "local"
LOCAL_HUB = {
    LOCAL: OverkizServer(
        name="Somfy TaHoma Developer Mode (local API)",
        endpoint="",
        manufacturer="Somfy",
        configuration_url=None,
    )
}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Overkiz (by Somfy)."""

    VERSION = 1

    _config_entry: ConfigEntry | None
    _default_user: None | str
    _default_hub: str
    _default_host: str

    def __init__(self) -> None:
        """Initialize Overkiz Config Flow."""
        super().__init__()

        self._config_entry = None
        self._default_user = None
        self._default_hub = DEFAULT_HUB
        self._default_host = DEFAULT_HOST

    async def async_validate_input(self, user_input: dict[str, Any]) -> dict[str, Any]:
        """Validate user credentials."""
        username = user_input[CONF_USERNAME]
        password = user_input[CONF_PASSWORD]

        if user_input[CONF_HUB] == LOCAL:
            session = async_create_clientsession(self.hass)
            server = SUPPORTED_SERVERS["somfy_europe"]
            client = OverkizClient(
                username=username, password=password, server=server, session=session
            )

            await client.login(register_event_listener=False)

            gateways = await client.get_gateways()

            for gateway in gateways:
                # Generate tokens
                # TODO check if gateway is in the right format (thermostat not supported)
                token = await client.generate_local_token(gateway.id)
                uuid = await client.activate_local_token(
                    gateway_id=gateway.id, token=token, label="Home Assistant/local"
                )

            host = user_input[CONF_HOST]
            user_input[CONF_TOKEN] = token
            user_input[CONF_TOKEN_UUID] = uuid

            session = async_create_clientsession(self.hass, verify_ssl=False)

            # TODO try if we can access the .local, otherwise remove the token
            client = OverkizClient(
                username="",
                password="",
                token=token,
                session=session,
                server=OverkizServer(
                    name="Somfy TaHoma Developer Mode (local API)",
                    endpoint=f"https://{host}/enduser-mobile-web/1/enduserAPI/",
                    manufacturer="Somfy",
                    configuration_url=None,
                ),
            )
        else:
            server = SUPPORTED_SERVERS[user_input[CONF_HUB]]

            session = async_create_clientsession(self.hass)
            client = OverkizClient(
                username=username, password=password, server=server, session=session
            )

            await client.login(register_event_listener=False)

        # Set first gateway id as unique id
        if gateways := await client.get_gateways():
            gateway_id = gateways[0].id
            await self.async_set_unique_id(gateway_id)

        return user_input

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step via config flow."""
        errors = {}
        description_placeholders = {}

        if user_input:
            self._default_hub = user_input[CONF_HUB]

            if self._default_hub == LOCAL:
                return await self.async_step_local()
            return await self.async_step_cloud()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HUB, default=self._default_hub): vol.In(
                        {
                            key: hub.name
                            for key, hub in {**SUPPORTED_SERVERS, **LOCAL_HUB}.items()
                        }
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_cloud(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the cloud authentication step via config flow."""
        errors = {}

        if user_input:
            self._default_user = user_input[CONF_USERNAME]
            user_input[CONF_HUB] = self._default_hub

            try:
                await self.async_validate_input(user_input)
            except TooManyRequestsException:
                errors["base"] = "too_many_requests"
            except BadCredentialsException as exception:
                # If authentication with CozyTouch auth server is valid, but token is invalid
                # for Overkiz API server, the hardware is not supported.
                if user_input[CONF_HUB] == "atlantic_cozytouch" and not isinstance(
                    exception, CozyTouchBadCredentialsException
                ):
                    description_placeholders["unsupported_device"] = "CozyTouch"
                    errors["base"] = "unsupported_hardware"
                else:
                    errors["base"] = "invalid_auth"
            except (TimeoutError, ClientError):
                errors["base"] = "cannot_connect"
            except MaintenanceException:
                errors["base"] = "server_in_maintenance"
            except TooManyAttemptsBannedException:
                errors["base"] = "too_many_attempts"
            except UnknownUserException:
                # Somfy Protect accounts are not supported since they don't use
                # the Overkiz API server. Login will return unknown user.
                description_placeholders["unsupported_device"] = "Somfy Protect"
                errors["base"] = "unsupported_hardware"
            except Exception as exception:  # pylint: disable=broad-except
                errors["base"] = "unknown"
                LOGGER.exception(exception)
            else:
                if self._config_entry:
                    if self._config_entry.unique_id != self.unique_id:
                        return self.async_abort(reason="reauth_wrong_account")

                    # Update existing entry during reauth
                    self.hass.config_entries.async_update_entry(
                        self._config_entry,
                        data={
                            **self._config_entry.data,
                            **user_input,
                        },
                    )

                    self.hass.async_create_task(
                        self.hass.config_entries.async_reload(
                            self._config_entry.entry_id
                        )
                    )

                    return self.async_abort(reason="reauth_successful")

                # Create new entry
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=user_input[CONF_USERNAME], data=user_input
                )

        return self.async_show_form(
            step_id="cloud",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME, default=self._default_user): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_local(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the local authentication step via config flow."""
        errors = {}

        if user_input:
            self._default_user = user_input[CONF_USERNAME]
            user_input[CONF_HUB] = self._default_hub

            try:
                user_input = await self.async_validate_input(user_input)

            except TooManyRequestsException:
                errors["base"] = "too_many_requests"
            except BadCredentialsException:
                errors["base"] = "invalid_auth"
            except (TimeoutError, ClientError):
                errors["base"] = "cannot_connect"
            except MaintenanceException:
                errors["base"] = "server_in_maintenance"
            except TooManyAttemptsBannedException:
                errors["base"] = "too_many_attempts"
            except Exception as exception:  # pylint: disable=broad-except
                errors["base"] = "unknown"
                LOGGER.exception(exception)
            else:
                if self._config_entry:
                    if self._config_entry.unique_id != self.unique_id:
                        return self.async_abort(reason="reauth_wrong_account")

                    # Update existing entry during reauth
                    self.hass.config_entries.async_update_entry(
                        self._config_entry,
                        data={
                            **self._config_entry.data,
                            **user_input,
                        },
                    )

                    self.hass.async_create_task(
                        self.hass.config_entries.async_reload(
                            self._config_entry.entry_id
                        )
                    )

                    return self.async_abort(reason="reauth_successful")

                # Create new entry
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=user_input[CONF_HOST], data=user_input
                )

        return self.async_show_form(
            step_id="local",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HOST, default="gateway-xxxx-xxxx-xxxx.local:8443"
                    ): str,
                    vol.Required(CONF_USERNAME, default=self._default_user): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            description_placeholders=description_placeholders,
            errors=errors,
        )

    async def async_step_dhcp(self, discovery_info: dhcp.DhcpServiceInfo) -> FlowResult:
        """Handle DHCP discovery."""
        hostname = discovery_info.hostname
        gateway_id = hostname[8:22]

        LOGGER.debug("DHCP discovery detected gateway %s", obfuscate_id(gateway_id))
        return await self._process_discovery(gateway_id)

    async def async_step_zeroconf(
        self, discovery_info: zeroconf.ZeroconfServiceInfo
    ) -> FlowResult:
        """Handle ZeroConf discovery."""
        properties = discovery_info.properties
        gateway_id = properties["gateway_pin"]
        hostname = discovery_info.hostname
        self._default_host = hostname

        LOGGER.debug(
            "ZeroConf discovery detected gateway %s on %s",
            obfuscate_id(gateway_id),
            hostname,
        )

        # await self.async_set_unique_id(gateway_id)
        # self._abort_if_unique_id_configured()
        self.context["title_placeholders"] = {"gateway_id": gateway_id}

        if discovery_info.type == "_kizbox._tcp.local.":
            return await self.async_step_cloud()
        if discovery_info.type == "_kizboxdev._tcp.local.":
            return await self.async_step_local()

        return await self.async_step_cloud()

    async def _process_discovery(self, gateway_id: str) -> FlowResult:
        """Handle discovery of a gateway."""
        await self.async_set_unique_id(gateway_id)
        self._abort_if_unique_id_configured()
        self.context["title_placeholders"] = {"gateway_id": gateway_id}

        return await self.async_step_user()

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> FlowResult:
        """Handle reauth."""
        self._config_entry = cast(
            ConfigEntry,
            self.hass.config_entries.async_get_entry(self.context["entry_id"]),
        )

        self.context["title_placeholders"] = {
            "gateway_id": self._config_entry.unique_id
        }

        self._default_user = self._config_entry.data[CONF_USERNAME]
        self._default_hub = self._config_entry.data[CONF_HUB]

        return await self.async_step_user(dict(entry_data))
