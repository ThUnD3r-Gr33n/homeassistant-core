"""Define a config flow manager for AirVisual."""
from pyairvisual import Client
from pyairvisual.errors import InvalidKeyError
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import (
    CONF_API_KEY,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_SHOW_ON_MAP,
)
from homeassistant.core import callback
from homeassistant.helpers import aiohttp_client, config_validation as cv

from . import async_get_geography_id
from .const import DOMAIN  # pylint: disable=unused-import


class AirVisualFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle an AirVisual config flow."""

    VERSION = 2
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        """Initialize."""
        self._api_key_checked = False

    @property
    def cloud_api_schema(self):
        """Return the data schema for the cloud API."""
        return vol.Schema(
            {
                vol.Required(CONF_API_KEY): str,
                vol.Required(
                    CONF_LATITUDE, default=self.hass.config.latitude
                ): cv.latitude,
                vol.Required(
                    CONF_LONGITUDE, default=self.hass.config.longitude
                ): cv.longitude,
            }
        )

    async def _async_set_unique_id(self, unique_id):
        """Set the unique ID of the config flow and abort if it already exists."""
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

    @callback
    async def _show_form(self, errors=None):
        """Show the form to the user."""
        return self.async_show_form(
            step_id="user", data_schema=self.cloud_api_schema, errors=errors or {},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Define the config flow to handle options."""
        return AirVisualOptionsFlowHandler(config_entry)

    async def async_step_import(self, import_config):
        """Import a config entry from configuration.yaml."""
        return await self.async_step_user(import_config)

    async def async_step_user(self, user_input=None):
        """Handle the start of the config flow."""
        if not user_input:
            return await self._show_form()

        geo_id = async_get_geography_id(user_input)
        await self._async_set_unique_id(geo_id)

        websession = aiohttp_client.async_get_clientsession(self.hass)
        client = Client(websession, api_key=user_input[CONF_API_KEY])

        if not self._api_key_checked:
            # If the user configures multiple geographies via configuration.yaml, we
            # only need to determine the API key's validity once:
            try:
                await client.api.nearest_city()
            except InvalidKeyError:
                return await self._show_form(errors={CONF_API_KEY: "invalid_api_key"})

            self._api_key_checked = True

        return self.async_create_entry(title=f"Cloud API ({geo_id})", data=user_input)


class AirVisualOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle an AirVisual options flow."""

    def __init__(self, config_entry):
        """Initialize."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SHOW_ON_MAP,
                        default=self.config_entry.options.get(CONF_SHOW_ON_MAP),
                    ): bool
                }
            ),
        )
