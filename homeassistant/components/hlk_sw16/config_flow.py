"""Config flow for HLK-SW16."""
import asyncio

from hlk_sw16 import create_hlk_sw16_connection
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant, callback

from .const import (
    CONNECTION_TIMEOUT,
    DEFAULT_KEEP_ALIVE_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_RECONNECT_INTERVAL,
    DOMAIN,
)
from .errors import AlreadyConfigured, CannotConnect, NameExists

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): vol.Coerce(int),
    }
)


async def validate_input(hass: HomeAssistant, user_input):
    """Validate the user input allows us to connect."""
    for entry in hass.config_entries.async_entries(DOMAIN):
        if (
            entry.data[CONF_HOST] == user_input[CONF_HOST]
            and entry.data[CONF_PORT] == user_input[CONF_PORT]
        ):
            raise AlreadyConfigured

    client_aw = create_hlk_sw16_connection(
        host=user_input[CONF_HOST],
        port=user_input[CONF_PORT],
        loop=hass.loop,
        timeout=CONNECTION_TIMEOUT,
        reconnect_interval=DEFAULT_RECONNECT_INTERVAL,
        keep_alive_interval=DEFAULT_KEEP_ALIVE_INTERVAL,
    )
    try:
        client = await asyncio.wait_for(client_aw, timeout=CONNECTION_TIMEOUT)
    except asyncio.TimeoutError:
        raise CannotConnect
    else:
        try:

            def disconnect_callback():
                if client.in_transaction:
                    client.active_transaction.set_exception(CannotConnect)

            client.disconnect_callback = disconnect_callback
            await client.status()
        except CannotConnect:
            client.disconnect_callback = None
            client.stop()
            raise CannotConnect
        else:
            client.disconnect_callback = None
            client.stop()


class SW16FlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a HLK-SW16 config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the HLK-SW16 options flow."""
        return SW16OptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            try:
                await validate_input(self.hass, user_input)
                address = f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}"
                return self.async_create_entry(title=address, data=user_input)
            except AlreadyConfigured:
                errors["base"] = "already_configured"
            except NameExists:
                errors["base"] = "name_exists"
            except CannotConnect:
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )


class SW16OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle a HLK-SW16 options flow."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = {
            vol.Required(
                CONF_HOST, default=self.config_entry.options.get(CONF_HOST),
            ): str,
            vol.Optional(
                CONF_PORT,
                default=self.config_entry.options.get(CONF_PORT, DEFAULT_PORT),
            ): vol.Coerce(int),
        }

        return self.async_show_form(step_id="init", data_schema=vol.Schema(options))
