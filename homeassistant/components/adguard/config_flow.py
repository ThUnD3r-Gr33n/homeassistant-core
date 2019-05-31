"""Config flow to configure the AdGuard Home integration."""
import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.adguard.const import DOMAIN
from homeassistant.config_entries import ConfigFlow
from homeassistant.const import (
    CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_SSL, CONF_USERNAME,
    CONF_VERIFY_SSL)
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)


@config_entries.HANDLERS.register(DOMAIN)
class AdGuardHomeFlowHandler(ConfigFlow):
    """Handle a AdGuard Home config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    _hassio_discovery = None

    def __init__(self):
        """Initialize AgGuard Home flow."""
        pass

    async def _show_setup_form(self, errors=None):
        """Show the setup form to the user."""
        return self.async_show_form(
            step_id='user',
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Required(CONF_PORT, default=3000): vol.Coerce(int),
                    vol.Optional(CONF_USERNAME): str,
                    vol.Optional(CONF_PASSWORD): str,
                    vol.Required(CONF_SSL, default=True): bool,
                    vol.Required(CONF_VERIFY_SSL, default=True): bool,
                }
            ),
            errors=errors or {},
        )

    async def _show_hassio_form(self, errors=None):
        """Show the Hass.io confirmation form to the user."""
        return self.async_show_form(
            step_id='hassio_confirm',
            description_placeholders={
                'addon': self._hassio_discovery['addon']
            },
            data_schema=vol.Schema({}),
            errors=errors or {},
        )

    async def async_step_init(self, user_input=None):
        """Needed in order to not require re-translation of strings."""
        return await self.async_step_user(user_input)

    async def async_step_user(self, user_input=None):
        """Handle a flow initiated by the user."""
        from adguardhome import AdGuardHome
        from adguardhome.exceptions import AdGuardHomeConnectionError

        if self._async_current_entries():
            return self.async_abort(reason='single_instance_allowed')

        if user_input is None:
            return await self._show_setup_form(user_input)

        errors = {}

        session = async_get_clientsession(
            self.hass, user_input[CONF_VERIFY_SSL]
        )

        adguard = AdGuardHome(
            user_input[CONF_HOST],
            port=user_input[CONF_PORT],
            username=user_input.get(CONF_USERNAME),
            password=user_input.get(CONF_PASSWORD),
            tls=user_input[CONF_SSL],
            verify_ssl=user_input[CONF_VERIFY_SSL],
            loop=self.hass.loop,
            session=session,
        )

        try:
            await adguard.version()
        except AdGuardHomeConnectionError:
            errors['base'] = 'connection_error'
            return await self._show_setup_form(errors)

        return self.async_create_entry(
            title=user_input[CONF_HOST],
            data={
                CONF_HOST: user_input[CONF_HOST],
                CONF_PASSWORD: user_input.get(CONF_PASSWORD),
                CONF_PORT: user_input[CONF_PORT],
                CONF_SSL: user_input[CONF_SSL],
                CONF_USERNAME: user_input.get(CONF_USERNAME),
                CONF_VERIFY_SSL: user_input[CONF_VERIFY_SSL],
            },
        )

    async def async_step_hassio(self, user_input=None):
        """Prepare configuration for a Hass.io AdGuard Home add-on.

        This flow is triggered by the discovery component.
        """
        if self._async_current_entries():
            return self.async_abort(reason='single_instance_allowed')

        self._hassio_discovery = user_input

        return await self.async_step_hassio_confirm()

    async def async_step_hassio_confirm(self, user_input=None):
        """Confirm Hass.io discovery."""
        from adguardhome import AdGuardHome
        from adguardhome.exceptions import AdGuardHomeConnectionError

        if user_input is None:
            return await self._show_hassio_form()

        errors = {}

        session = async_get_clientsession(self.hass, False)

        adguard = AdGuardHome(
            self._hassio_discovery[CONF_HOST],
            port=self._hassio_discovery[CONF_PORT],
            tls=False,
            loop=self.hass.loop,
            session=session,
        )

        try:
            await adguard.version()
        except AdGuardHomeConnectionError:
            errors['base'] = 'connection_error'
            return await self._show_hassio_form(errors)

        return self.async_create_entry(
            title=self._hassio_discovery['addon'],
            data={
                CONF_HOST: self._hassio_discovery[CONF_HOST],
                CONF_PORT: self._hassio_discovery[CONF_PORT],
                CONF_PASSWORD: None,
                CONF_SSL: False,
                CONF_USERNAME: None,
                CONF_VERIFY_SSL: True,
            },
        )
