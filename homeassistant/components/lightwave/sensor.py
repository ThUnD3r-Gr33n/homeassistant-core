"""Support for LightwaveRF TRV - Associated Battery."""
import logging

from homeassistant.const import CONF_NAME, DEVICE_CLASS_BATTERY, UNIT_PERCENTAGE
from homeassistant.helpers.entity import Entity

from . import CONF_SERIAL, LIGHTWAVE_LINK

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Find and return battery."""
    if discovery_info is None:
        return

    batteries = []

    lwlink = hass.data[LIGHTWAVE_LINK]

    for _, device_config in discovery_info.items():
        name = device_config[CONF_NAME]
        serial = device_config[CONF_SERIAL]
        batteries.append(LightwaveBattery(name, lwlink, serial))

    async_add_entities(batteries)


class LightwaveBattery(Entity):
    """Lightwave TRV Battery."""

    def __init__(self, name, lwlink, serial):
        """Initialize the Lightwave Trv battery sensor."""
        self._name = name
        self._state = None
        self._lwlink = lwlink
        self._serial = serial

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        return DEVICE_CLASS_BATTERY

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the state of the sensor."""
        return UNIT_PERCENTAGE

    def update(self):
        """Communicate with a Lightwave RTF Proxy to get state."""
        battery = None
        (dummy_temp, dummy_targ, battery, dummy_output) = self._lwlink.read_trv_status(
            self._serial
        )
        self._state = battery
