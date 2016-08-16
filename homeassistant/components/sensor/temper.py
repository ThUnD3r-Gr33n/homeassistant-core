"""
Support for getting temperature from TEMPer devices.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.temper/
"""
import logging
import voluptuous as vol

from homeassistant.const import CONF_NAME, DEVICE_DEFAULT_NAME, TEMP_FAHRENHEIT
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)

REQUIREMENTS = ['https://github.com/rkabadi/temper-python/archive/'
                '3dbdaf2d87b8db9a3cd6e5585fc704537dd2d09b.zip'
                '#temperusb==1.2.3']

CONF_SCALE = 'scale'
CONF_OFFSET = 'offset'

PLATFORM_SCHEMA = vol.Schema({
    vol.Required('platform'): 'temper',
    vol.Optional(CONF_NAME): vol.Coerce(str),
    vol.Optional(CONF_SCALE): vol.Coerce(float),
    vol.Optional(CONF_OFFSET): vol.Coerce(float)
})


# pylint: disable=unused-argument
def setup_platform(hass, config, add_devices_callback, discovery_info=None):
    """Setup the Temper sensors."""
    from temperusb.temper import TemperHandler

    temp_unit = hass.config.units.temperature_unit
    name = config.get(CONF_NAME, DEVICE_DEFAULT_NAME)
    scaling = {
        "scale": config.get(CONF_SCALE, 1),
        "offset": config.get(CONF_OFFSET, 0)
    }
    temper_devices = TemperHandler().get_devices()
    add_devices_callback([TemperSensor(dev,
                                       temp_unit,
                                       name if name != DEVICE_DEFAULT_NAME
                                       else name + '_' + str(idx),
                                       scaling)
                          for idx, dev in enumerate(temper_devices)])


class TemperSensor(Entity):
    """Representation of a Temper temperature sensor."""

    def __init__(self, temper_device, temp_unit, name, scaling):
        """Initialize the sensor."""
        self.temper_device = temper_device
        self.temp_unit = temp_unit
        self.scale = scaling["scale"]
        self.offset = scaling["offset"]
        self.current_value = None
        self._name = name

    @property
    def name(self):
        """Return the name of the temperature sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the entity."""
        return self.current_value

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return self.temp_unit

    def update(self):
        """Retrieve latest state."""
        try:
            format_str = ('fahrenheit' if self.temp_unit == TEMP_FAHRENHEIT
                          else 'celsius')
            sensor_value = self.temper_device.get_temperature(format_str)
            self.current_value = self.scale * sensor_value + self.offset
        except IOError:
            _LOGGER.error('Failed to get temperature due to insufficient '
                          'permissions. Try running with "sudo"')
