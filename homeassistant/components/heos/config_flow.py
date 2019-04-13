"""Config flow to configure Heos."""
import asyncio

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME

from .const import DOMAIN


def format_title(host: str) -> str:
    """Format the title for config entries."""
    return "Controller ({})".format(host)


@config_entries.HANDLERS.register(DOMAIN)
class HeosFlowHandler(config_entries.ConfigFlow):
    """Define a flow for HEOS."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH
    DISCOVERED_HOSTS = {}

    async def async_step_discovery(self, discovery_info):
        """Handle a discovered Heos device."""
        friendly_name = "{} ({})".format(
            discovery_info[CONF_NAME], discovery_info[CONF_HOST])
        self.DISCOVERED_HOSTS[friendly_name] = discovery_info[CONF_HOST]
        # Only a single entry is needed for all devices
        entries = self.hass.config_entries.async_entries(DOMAIN)
        if entries:
            return self.async_abort(reason='already_setup')
        # Only continue if this is the only active flow
        flows = self.hass.config_entries.flow.async_progress()
        heos_flows = [flow for flow in flows if flow['handler'] == DOMAIN]
        if len(heos_flows) == 1:
            return self.async_show_form(step_id='user')
        return self.async_abort(reason='already_setup')

    async def async_step_import(self, user_input=None):
        """Occurs when an entry is setup through config."""
        host = user_input[CONF_HOST]
        return self.async_create_entry(
            title=format_title(host),
            data={CONF_HOST: host})

    async def async_step_user(self, user_input=None):
        """Obtain host and validate connection."""
        from pyheos import Heos

        # Only a single entry is needed for all devices
        entries = self.hass.config_entries.async_entries(DOMAIN)
        if entries:
            return self.async_abort(reason='already_setup')

        # Try connecting to host if provided
        errors = {}
        host = None
        if user_input is not None:
            host = user_input[CONF_HOST]
            # Map host from friendly name if in discovered hosts
            host = self.DISCOVERED_HOSTS.get(host, host)
            heos = Heos(host)
            try:
                await heos.connect()
                self.DISCOVERED_HOSTS.clear()
                return await self.async_step_import({CONF_HOST: host})
            except (asyncio.TimeoutError, ConnectionError):
                errors[CONF_HOST] = 'connection_failure'
            finally:
                await heos.disconnect()

        # Return form
        host_type = str if not self.DISCOVERED_HOSTS \
            else vol.In(list(self.DISCOVERED_HOSTS))
        return self.async_show_form(
            step_id='user',
            data_schema=vol.Schema({
                vol.Required(CONF_HOST, default=host): host_type
            }),
            errors=errors)
