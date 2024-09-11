"""Config flow for solarlog integration."""

from collections.abc import Mapping
import logging
from typing import TYPE_CHECKING, Any
from urllib.parse import ParseResult, urlparse

from solarlog_cli.solarlog_connector import SolarLogConnector
from solarlog_cli.solarlog_exceptions import (
    SolarLogAuthenticationError,
    SolarLogConnectionError,
    SolarLogError,
)
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PASSWORD
from homeassistant.util import slugify

from . import SolarlogConfigEntry
from .const import DEFAULT_HOST, DEFAULT_NAME, DOMAIN

_LOGGER = logging.getLogger(__name__)


class SolarLogConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for solarlog."""

    _entry: SolarlogConfigEntry | None = None
    VERSION = 1
    MINOR_VERSION = 2

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._errors: dict = {}
        self._user_input: dict = {}

    def _parse_url(self, host: str) -> str:
        """Return parsed host url."""
        url = urlparse(host, "http")
        netloc = url.netloc or url.path
        path = url.path if url.netloc else ""
        url = ParseResult("http", netloc, path, *url[3:])
        return url.geturl()

    async def _test_connection(self, host: str) -> bool:
        """Check if we can connect to the Solar-Log device."""
        solarlog = SolarLogConnector(host)
        try:
            await solarlog.test_connection()
        except SolarLogConnectionError:
            self._errors = {CONF_HOST: "cannot_connect"}
            return False
        except SolarLogError:
            self._errors = {CONF_HOST: "unknown"}
            return False
        finally:
            await solarlog.client.close()

        return True

    async def _test_extended_data(self, host: str, pwd: str = "") -> bool:
        """Check if we get extended data from Solar-Log device."""
        response: bool = False
        solarlog = SolarLogConnector(host, password=pwd)
        try:
            response = await solarlog.test_extended_data_available()
        except SolarLogAuthenticationError:
            self._errors = {CONF_HOST: "password_error"}
            response = False
        except SolarLogError:
            self._errors = {CONF_HOST: "unknown"}
            response = False
        finally:
            await solarlog.client.close()

        return response

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step when user initializes a integration."""
        self._errors = {}
        if user_input is not None:
            user_input[CONF_HOST] = self._parse_url(user_input[CONF_HOST])

            self._async_abort_entries_match({CONF_HOST: user_input[CONF_HOST]})

            user_input[CONF_NAME] = slugify(user_input[CONF_NAME])

            if await self._test_connection(user_input[CONF_HOST]):
                if user_input["has_password"]:
                    self._user_input = user_input
                    return await self.async_step_password()

                user_input["extended_data"] = await self._test_extended_data(
                    user_input[CONF_HOST]
                )

                return self.async_create_entry(
                    title=user_input[CONF_NAME], data=user_input
                )
        else:
            user_input = {CONF_NAME: DEFAULT_NAME, CONF_HOST: DEFAULT_HOST}

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=user_input[CONF_NAME]): str,
                    vol.Required(CONF_HOST, default=user_input[CONF_HOST]): str,
                    vol.Required("has_password", default=False): bool,
                }
            ),
            errors=self._errors,
        )

    async def async_step_password(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step when user sets password ."""
        self._errors = {}
        if user_input is not None:
            if await self._test_extended_data(
                self._user_input[CONF_HOST], user_input[CONF_PASSWORD]
            ):
                self._user_input |= user_input
                self._user_input |= {"extended_data": True}
                return self.async_create_entry(
                    title=self._user_input[CONF_NAME], data=self._user_input
                )
        else:
            user_input = {CONF_PASSWORD: ""}

        return self.async_show_form(
            step_id="password",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=self._errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a reconfiguration flow initialized by the user."""

        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])

        if TYPE_CHECKING:
            assert entry is not None

        if user_input is not None:
            if not user_input["has_password"] or user_input[CONF_PASSWORD] == "":
                user_input[CONF_PASSWORD] = ""
                user_input["has_password"] = False
                return self.async_update_reload_and_abort(
                    entry,
                    reason="reconfigure_successful",
                    data={**entry.data, **user_input},
                )

            if await self._test_extended_data(
                entry.data[CONF_HOST], user_input[CONF_PASSWORD]
            ):
                # if password has been provided, only save if extended data is available
                return self.async_update_reload_and_abort(
                    entry,
                    reason="reconfigure_successful",
                    data={**entry.data, **user_input},
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "has_password", default=entry.data["has_password"]
                    ): bool,
                    vol.Optional(CONF_PASSWORD): str,
                }
            ),
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle flow upon an API authentication error."""
        self._entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reauthorization flow."""
        errors: dict[str, str] = {}
        assert self._entry is not None

        if user_input and await self._test_extended_data(
            self._entry.data[CONF_HOST], user_input[CONF_PASSWORD]
        ):
            return self.async_update_reload_and_abort(
                self._entry, data={**self._entry.data, **user_input}
            )

        data_schema = vol.Schema(
            {
                vol.Required(
                    "has_password", default=self._entry.data["has_password"]
                ): bool,
                vol.Required(CONF_PASSWORD): str,
            }
        )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=data_schema,
            errors=errors,
        )
