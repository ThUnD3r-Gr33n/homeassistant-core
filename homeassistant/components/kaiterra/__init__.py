"""The Kaiterra component"""
import voluptuous as vol

from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers import config_validation as cv

from homeassistant.const import (
    CONF_API_KEY,
    CONF_DEVICES,
    CONF_DEVICE_ID,
    CONF_SCAN_INTERVAL,
    CONF_TYPE,
    CONF_NAME
)

from .const import (
    AVAILABLE_AQI_STANDARDS,
    AVAILABLE_UNITS,
    AVAILABLE_DEVICE_TYPES,
    CONF_AQI_STANDARD,
    CONF_PREFERRED_UNITS,
    DOMAIN,
    DEFAULT_AQI_STANDARD,
    DEFAULT_PREFERRED_UNIT,
    DEFAULT_SCAN_INTERVAL,
    KAITERRA_COMPONENTS
)

from .api_data import KaiterraApiData

KAITERRA_DEVICE_SCHEMA = vol.Schema({
    vol.Required(CONF_DEVICE_ID): cv.string,
    vol.Required(CONF_TYPE): vol.In(AVAILABLE_DEVICE_TYPES),
    vol.Optional(CONF_NAME): cv.string,
})

KAITERRA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): cv.string,
        vol.Required(CONF_DEVICES): vol.All(cv.ensure_list, [KAITERRA_DEVICE_SCHEMA]),
        vol.Optional(CONF_AQI_STANDARD, default=DEFAULT_AQI_STANDARD): vol.In(AVAILABLE_AQI_STANDARDS),
        vol.Optional(CONF_PREFERRED_UNITS, default=DEFAULT_PREFERRED_UNIT): vol.All(cv.ensure_list, [vol.In(AVAILABLE_UNITS)]),
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): cv.time_period,
    },
    extra=vol.PREVENT_EXTRA
)

CONFIG_SCHEMA = vol.Schema({DOMAIN: KAITERRA_SCHEMA}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass, config):
    """Set up the Kaiterra components."""
    from kaiterra_async_client import KaiterraAPIClient, AQIStandard, Units

    config = config.get(DOMAIN, {})
    scan_interval = config.get(CONF_SCAN_INTERVAL)
    devices = config.get(CONF_DEVICES)
    session = async_get_clientsession(hass)
    api = hass.data[DOMAIN] = KaiterraApiData(hass, config, session)

    await api.async_update()

    async def _update(now=None):
        """Periodic update."""
        await api.async_update()

    async_track_time_interval(hass, _update, scan_interval)

    # Load platforms for each device
    for device in devices:
        device_name, device_id = device.get(CONF_NAME) or device.get(CONF_TYPE), device.get(CONF_DEVICE_ID)
        for component in KAITERRA_COMPONENTS:
            hass.async_create_task(async_load_platform(hass, component, DOMAIN, {CONF_NAME: device_name, CONF_DEVICE_ID: device_id}, config))

    return True
