"""
Support for IP Webcam sensors.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.android_ip_webcam/
"""
import logging

from homeassistant.components.android_ip_webcam import (SENSOR_KEY_MAP,
                                                        DATA_IP_WEBCAM)
from homeassistant.helpers.entity import Entity

DEPENDENCIES = ['android_ip_webcam']

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the IP Webcam Sensor."""
    if discovery_info is None:
        return

    ip_webcam = hass.data[DATA_IP_WEBCAM]

    all_sensors = []

    for device in ip_webcam.values():
        for sensor in discovery_info:
            all_sensors.append(IPWebcamSensor(device, sensor))

    add_devices(all_sensors, True)

    return True


class IPWebcamSensor(Entity):
    """Representation of a IP Webcam sensor."""

    def __init__(self, device, variable):
        """Initialize the sensor."""
        self._device = device
        self.variable = variable

        # device specific
        self._mapped_name = SENSOR_KEY_MAP.get(self.variable, self.variable)
        self._name = '{} {}'.format(self._device.name, self._mapped_name)
        self._state = None
        self._unit = None

    @property
    def name(self):
        """Return the name of the sensor, if any."""
        return self._name

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return self._unit

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    def update(self):
        """Retrieve latest state."""
        self._device.update()
        container = self._device.sensor_data.get(self.variable)
        self._unit = container.get('unit', self._unit)
        data_point = container.get('data', [[0, [0.0]]])
        if data_point and data_point[0]:
            self._state = data_point[0][-1][0]

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return self._device.device_state_attributes
