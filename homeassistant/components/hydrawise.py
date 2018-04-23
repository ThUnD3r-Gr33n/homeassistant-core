"""
Support for Hydrawise cloud.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/hydrawise
"""
import asyncio
from datetime import timedelta
import logging

from requests.exceptions import ConnectTimeout, HTTPError
import voluptuous as vol

from homeassistant.const import (
    ATTR_ATTRIBUTION, CONF_ACCESS_TOKEN, CONF_SCAN_INTERVAL)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect, dispatcher_send)
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import track_time_interval

REQUIREMENTS = ['hydrawiser==0.1.0']

_LOGGER = logging.getLogger(__name__)

ALLOWED_WATERING_TIME = [5, 10, 15, 30, 45, 60]

CONF_ATTRIBUTION = "Data provided by hydrawise.com"
CONF_WATERING_TIME = 'watering_minutes'

NOTIFICATION_ID = 'hydrawise_notification'
NOTIFICATION_TITLE = 'Hydrawise Setup'

DATA_HYDRAWISE = 'hydrawise'
DOMAIN = 'hydrawise'
DEFAULT_WATERING_TIME = 15

KEY_MAP = {
    'auto_watering': 'Automatic Watering',
    'is_watering': 'Watering',
    'manual_watering': 'Manual Watering',
    'next_cycle': 'Next Cycle',
    'status': 'Status',
    'watering_time': 'Watering Time',
    'rain_sensor': 'Rain Sensor',
}

ICON_MAP = {
    'auto_watering': 'mdi:autorenew',
    'is_watering': '',
    'manual_watering': 'mdi:water-pump',
    'next_cycle': 'mdi:calendar-clock',
    'status': '',
    'watering_time': 'mdi:water-pump',
    'rain_sensor': ''
}

UNIT_OF_MEASUREMENT_MAP = {
    'auto_watering': '',
    'is_watering': '',
    'manual_watering': '',
    'next_cycle': '',
    'status': '',
    'watering_time': 'min',
}

BINARY_SENSORS = ['is_watering', 'status', 'rain_sensor']

SENSORS = ['next_cycle', 'watering_time']

SWITCHES = ['auto_watering', 'manual_watering']

SCAN_INTERVAL = timedelta(seconds=20)

SIGNAL_UPDATE_HYDRAWISE = "hydrawise_update"

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_ACCESS_TOKEN): cv.string,
        vol.Optional(CONF_SCAN_INTERVAL, default=SCAN_INTERVAL):
            cv.time_period,
    }),
}, extra=vol.ALLOW_EXTRA)


def setup(hass, config):
    """Set up the Hunter Hydrawise component."""
    conf = config[DOMAIN]
    access_token = conf.get(CONF_ACCESS_TOKEN)
    scan_interval = conf.get(CONF_SCAN_INTERVAL)

    try:
        from hydrawiser.core import Hydrawiser

        hydrawise = Hydrawiser(user_token=access_token)
        hass.data[DATA_HYDRAWISE] = HydrawiseHub(hydrawise)
    except (ConnectTimeout, HTTPError) as ex:
        _LOGGER.error(
            "Unable to connect to Hydrawise cloud service: %s", str(ex))
        hass.components.persistent_notification.create(
            'Error: {}<br />'
            'You will need to restart hass after fixing.'
            ''.format(ex),
            title=NOTIFICATION_TITLE,
            notification_id=NOTIFICATION_ID)
        return False

    def hub_refresh(event_time):
        """Call Hydrawise hub to refresh information."""
        _LOGGER.debug("Updating Hydrawise Hub component")
        hass.data[DATA_HYDRAWISE].data.update_controller_info()
        dispatcher_send(hass, SIGNAL_UPDATE_HYDRAWISE)

    # Call the Hydrawise API to refresh updates
    track_time_interval(hass, hub_refresh, scan_interval)

    return True


class HydrawiseHub(object):
    """Representation of a base Hydrawise device."""

    def __init__(self, data):
        """Initialize the entity."""
        self.data = data


class HydrawiseEntity(Entity):
    """Entity class for Hydrawise devices."""

    def __init__(self, data, sensor_type):
        """Initialize the Hydrawise entity."""
        self.data = data
        self._sensor_type = sensor_type
        self._name = "{0} {1}".format(
            self.data.get('name'), KEY_MAP.get(self._sensor_type))
        self._state = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @asyncio.coroutine
    def async_added_to_hass(self):
        """Register callbacks."""
        async_dispatcher_connect(
            self.hass, SIGNAL_UPDATE_HYDRAWISE, self._update_callback)

    def _update_callback(self):
        """Call update method."""
        self.schedule_update_ha_state(True)

    @property
    def unit_of_measurement(self):
        """Return the units of measurement."""
        return UNIT_OF_MEASUREMENT_MAP.get(self._sensor_type)

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return {
                ATTR_ATTRIBUTION: CONF_ATTRIBUTION,
                'identifier': self.data.get('relay'),
                'last contact:': self.hass.data['hydrawise'].data
                .controller_info['controllers'][0]['last_contact_readable'],
        }

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return ICON_MAP.get(self._sensor_type)
