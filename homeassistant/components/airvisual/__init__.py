"""The airvisual component."""
import asyncio
from datetime import timedelta
import logging

from pyairvisual import Client
from pyairvisual.errors import AirVisualError, InvalidKeyError
import voluptuous as vol

from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.const import (
    CONF_API_KEY,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_SCAN_INTERVAL,
    CONF_SHOW_ON_MAP,
    CONF_STATE,
)
from homeassistant.core import callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import aiohttp_client, config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval

from .config_flow import configured_instances
from .const import (
    CONF_CITY,
    CONF_COUNTRY,
    CONF_GEOGRAPHIES,
    DATA_CLIENT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    TOPIC_OPTIONS_UPDATE,
    TOPIC_UPDATE,
)

_LOGGER = logging.getLogger(__name__)

DATA_LISTENER = "listener"

CONF_NODE_ID = "node_id"

GEOGRAPHY_SCHEMA = vol.All(
    vol.Schema(
        {
            vol.Inclusive(CONF_CITY, "city"): cv.string,
            vol.Inclusive(CONF_STATE, "city"): cv.string,
            vol.Inclusive(CONF_COUNTRY, "city"): cv.string,
            vol.Inclusive(CONF_LATITUDE, "coords"): cv.latitude,
            vol.Inclusive(CONF_LONGITUDE, "coords"): cv.longitude,
            vol.Optional(CONF_SHOW_ON_MAP, default=True): cv.boolean,
        },
        cv.has_at_least_one_key(CONF_CITY, CONF_LATITUDE),
    )
)

CLOUD_API_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): cv.string,
        vol.Optional(CONF_GEOGRAPHIES, default=[]): vol.All(
            cv.ensure_list, [GEOGRAPHY_SCHEMA]
        ),
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
            cv.time_period, lambda value: value.total_seconds()
        ),
    }
)

CONFIG_SCHEMA = vol.Schema({DOMAIN: CLOUD_API_SCHEMA}, extra=vol.ALLOW_EXTRA,)


@callback
def async_get_geography_id(geography_dict):
    """Generate a unique ID from a geography_dict dict."""
    if CONF_CITY in geography_dict:
        return ",".join(
            (
                geography_dict[CONF_CITY],
                geography_dict[CONF_STATE],
                geography_dict[CONF_COUNTRY],
            )
        )
    return ",".join(
        (str(geography_dict[CONF_LATITUDE]), str(geography_dict[CONF_LONGITUDE]))
    )


async def async_setup(hass, config):
    """Set up the AirVisual component."""
    hass.data[DOMAIN] = {}
    hass.data[DOMAIN][DATA_CLIENT] = {}
    hass.data[DOMAIN][DATA_LISTENER] = {}

    if DOMAIN not in config:
        return True

    conf = config[DOMAIN]

    if conf[CONF_API_KEY] in configured_instances(hass):
        return True

    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_IMPORT}, data=conf
        )
    )

    return True


async def async_setup_entry(hass, config_entry):
    """Set up AirVisual as config entry."""
    websession = aiohttp_client.async_get_clientsession(hass)

    hass.data[DOMAIN][DATA_CLIENT][config_entry.entry_id] = AirVisualData(
        hass,
        Client(websession, api_key=config_entry.data[CONF_API_KEY]),
        config_entry.data[CONF_GEOGRAPHIES],
        config_entry.options.get(CONF_SHOW_ON_MAP, config_entry.data[CONF_SHOW_ON_MAP]),
    )

    try:
        await hass.data[DOMAIN][DATA_CLIENT][config_entry.entry_id].async_update()
    except InvalidKeyError:
        _LOGGER.error("Invalid API key provided")
        raise ConfigEntryNotReady

    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(config_entry, "sensor")
    )

    async def refresh(event_time):
        """Refresh data from AirVisual."""
        await hass.data[DOMAIN][DATA_CLIENT][config_entry.entry_id].async_update()

    hass.data[DOMAIN][DATA_LISTENER][config_entry.entry_id] = async_track_time_interval(
        hass, refresh, timedelta(seconds=config_entry.data[CONF_SCAN_INTERVAL])
    )

    config_entry.add_update_listener(async_update_entry)

    return True


async def async_update_entry(hass, config_entry):
    """Process an options update to the config entry."""
    hass.data[DOMAIN][DATA_CLIENT][
        config_entry.entry_id
    ].show_on_map = config_entry.options[CONF_SHOW_ON_MAP]
    async_dispatcher_send(hass, TOPIC_OPTIONS_UPDATE)


async def async_unload_entry(hass, config_entry):
    """Unload an AirVisual config entry."""
    hass.data[DOMAIN][DATA_CLIENT].pop(config_entry.entry_id)

    remove_listener = hass.data[DOMAIN][DATA_LISTENER].pop(config_entry.entry_id)
    remove_listener()

    await hass.config_entries.async_forward_entry_unload(config_entry, "sensor")

    return True


class AirVisualData:
    """Define a class to manage data from the AirVisual cloud API."""

    def __init__(self, hass, client, geographies, show_on_map):
        """Initialize."""
        self._client = client
        self._hass = hass
        self.data = {}
        self.show_on_map = show_on_map

        if geographies:
            self.geographies = {
                async_get_geography_id(geography): geography
                for geography in geographies
            }
        else:
            default_geography = GEOGRAPHY_SCHEMA(
                {
                    CONF_LATITUDE: hass.config.latitude,
                    CONF_LONGITUDE: hass.config.longitude,
                }
            )
            self.geographies = {
                async_get_geography_id(default_geography): default_geography
            }

    async def async_update(self):
        """Get new data for all locations from the AirVisual cloud API."""
        tasks = []

        for geography in self.geographies.values():
            if CONF_CITY in geography:
                tasks.append(
                    self._client.api.city(
                        geography[CONF_CITY],
                        geography[CONF_STATE],
                        geography[CONF_COUNTRY],
                    )
                )
            else:
                tasks.append(
                    self._client.api.nearest_city(
                        geography[CONF_LATITUDE], geography[CONF_LONGITUDE],
                    )
                )

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for geography_id, result in zip(self.geographies, results):
            if isinstance(result, AirVisualError):
                _LOGGER.error("Error while retrieving data: %s", result)
                self.data[geography_id] = {}
                continue
            self.data[geography_id] = result

        _LOGGER.debug("Received new data")
        async_dispatcher_send(self._hass, TOPIC_UPDATE)
