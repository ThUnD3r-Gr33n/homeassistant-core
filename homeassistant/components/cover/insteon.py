"""
Support for Insteon lights via PowerLinc Modem.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/light.insteon/
"""
import asyncio
import logging
import math

from homeassistant.components.insteon import InsteonEntity
from homeassistant.components.cover import (CoverDevice, ATTR_POSITION,
                                            SUPPORT_OPEN, SUPPORT_CLOSE,
                                            SUPPORT_SET_POSITION)
# from homeassistant.const import (
#     STATE_OPEN, STATE_CLOSED, STATE_OPENING, STATE_CLOSING, STATE_UNKNOWN)

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = ['insteon']


@asyncio.coroutine
def async_setup_platform(hass, config, async_add_entities,
                         discovery_info=None):
    """Set up the Insteon component."""
    insteon_modem = hass.data['insteon'].get('modem')

    address = discovery_info['address']
    device = insteon_modem.devices[address]
    state_key = discovery_info['state_key']

    _LOGGER.debug('Adding device %s entity %s to Light platform',
                  device.address.hex, device.states[state_key].name)

    new_entity = InsteonCoverDevice(device, state_key)

    async_add_entities([new_entity])


class InsteonCoverDevice(InsteonEntity, CoverDevice):
    """A Class for an Insteon device."""

    @property
    def current_cover_position(self):
        """Return the current cover position."""
        return int(math.ceil(self._insteon_device_state.value*100/255))

    @property
    def supported_features(self):
        """Return the supported features for this entity."""
        return SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_SET_POSITION

    @property
    def is_closed(self):
        """Return the boolean response if the node is on."""
        return bool(self.current_cover_position)

    @asyncio.coroutine
    def async_open_cover(self, **kwargs):
        """Open device."""
        if ATTR_POSITION in kwargs:
            position = int(kwargs[ATTR_POSITION]*255/100)
            self._insteon_device_state.set_position(position)
        else:
            self._insteon_device_state.open()

    @asyncio.coroutine
    def async_close_cover(self, **kwargs):
        """Close device."""
        self._insteon_device_state.close()

    @asyncio.coroutine
    def async_set_cover_position(self, **kwargs):
        """Set the cover position."""
        yield from self.async_open_cover(**kwargs)
