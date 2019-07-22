"""Support for Velbus sensors."""
import logging

from .const import DOMAIN
from . import VelbusEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
        hass, config, async_add_entities, discovery_info=None):
    """ Old way """
    pass


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Velbus sensor based on config_entry."""
    cntrl = hass.data[DOMAIN][entry.entry_id]['cntrl']
    items = []
    for item in hass.data[DOMAIN][entry.entry_id]['sensor']:
        module = cntrl.get_module(item[0])
        channel = item[1]
        items.append(VelbusSensor(module, channel))
    async_add_entities(items)


class VelbusSensor(VelbusEntity):
    """Representation of a sensor."""

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        return self._module.get_class(self._channel)

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._module.get_state(self._channel)

    @property
    def unit_of_measurement(self):
        """Return the unit this state is expressed in."""
        return self._module.get_unit(self._channel)
