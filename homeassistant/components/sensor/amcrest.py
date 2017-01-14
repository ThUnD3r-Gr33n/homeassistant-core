"""
This component provides HA sensor support for Amcrest IP cameras.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.amcrest/
"""
from datetime import timedelta
import logging

import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_HOST, CONF_NAME, CONF_MONITORED_CONDITIONS,
    CONF_USERNAME, CONF_PASSWORD, CONF_PORT,
    STATE_UNKNOWN)
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle
import homeassistant.loader as loader

REQUIREMENTS = ['amcrest==1.1.0']

_LOGGER = logging.getLogger(__name__)

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=30)

NOTIFICATION_ID = 'amcrest_notification'
NOTIFICATION_TITLE = 'Amcrest Sensor Setup'

DEFAULT_NAME = 'Amcrest'
DEFAULT_PORT = 80

# Sensor types are defined like: Name, units, icon
SENSOR_TYPES = {
    'motion_detector': ['Motion Detected', None, 'run'],
    'sdcard': ['SD Used', '%', 'sd'],
    'ptz_preset': ['PTZ Preset', None, 'camera-iris'],
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
    vol.Required(CONF_MONITORED_CONDITIONS, default=[]):
        vol.All(cv.ensure_list, [vol.In(SENSOR_TYPES)]),
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up a sensor for an Amcrest IP Camera."""
    from amcrest import AmcrestCamera

    data = AmcrestCamera(
        config.get(CONF_HOST), config.get(CONF_PORT),
        config.get(CONF_USERNAME), config.get(CONF_PASSWORD))

    persistent_notification = loader.get_component('persistent_notification')
    try:
        data.camera.current_time
    # pylint: disable=broad-except
    except Exception as ex:
        _LOGGER.error("Unable to connect to Amcrest camera: %s", str(ex))
        persistent_notification.create(
            hass, 'Error: {}<br />'
            'You will need to restart hass after fixing.'
            ''.format(ex),
            title=NOTIFICATION_TITLE,
            notification_id=NOTIFICATION_ID)
        return False

    sensors = []
    for sensor_type in config.get(CONF_MONITORED_CONDITIONS):
        sensors.append(AmcrestSensor(config, data, sensor_type))

    add_devices(sensors)

    return True


class AmcrestSensor(Entity):
    """A sensor implementation for Amcrest IP camera."""

    def __init__(self, device_info, data, sensor_type):
        """Initialize a sensor for Amcrest camera."""
        super(AmcrestSensor, self).__init__()
        self._attrs = {}
        self._data = data
        self._sensor_type = sensor_type
        self._name = '{0}_{1}'.format(device_info.get(CONF_NAME),
                                      SENSOR_TYPES.get(self._sensor_type)[0])
        self._icon = 'mdi:{}'.format(SENSOR_TYPES.get(self._sensor_type)[2])
        self._state = STATE_UNKNOWN

        self.update()

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return self._attrs

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return self._icon

    @property
    def unit_of_measurement(self):
        """Return the units of measurement."""
        return SENSOR_TYPES.get(self._sensor_type)[1]

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Get the latest data and updates the state."""
        version, build_date = self._data.camera.software_information
        self._attrs['Build Date'] = build_date.split('=')[-1]
        self._attrs['Serial Number'] = self._data.camera.serial_number
        self._attrs['Version'] = version.split('=')[-1]

        if self._sensor_type == 'motion_detector':
            self._state = self._data.camera.is_motion_detected
            self._attrs['Record Mode'] = self._data.camera.record_mode

        elif self._sensor_type == 'ptz_preset':
            self._state = self._data.camera.ptz_presets_count

        elif self._sensor_type == 'sdcard':
            sd_used = self._data.camera.storage_used
            sd_total = self._data.camera.storage_total
            self._attrs['Total'] = '{0} {1}'.format(*sd_total)
            self._attrs['Used'] = '{0} {1}'.format(*sd_used)
            self._state = self._data.camera.percent(sd_used[0], sd_total[0])
