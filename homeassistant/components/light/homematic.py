"""
The homematic light platform.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/light.homematic/

Important: For this platform to work the homematic component has to be
properly configured.

Configuration:

light:
  - platform: homematic
    addresss: <Homematic addresss for device> # e.g. "JEQ0XXXXXXX"
    name: <User defined name> (optional)
    button: n (integer of channel to map, device-dependent)
"""

import logging
from homeassistant.components.light import (ATTR_BRIGHTNESS, Light)
from homeassistant.const import STATE_UNKNOWN
import homeassistant.components.homematic as homematic

_LOGGER = logging.getLogger(__name__)

# List of component names (string) your component depends upon.
DEPENDENCIES = ['homematic']


def setup_platform(hass, config, add_callback_devices, discovery_info=None):
    """Setup the platform."""
    if discovery_info:
        config = discovery_info
    return homematic.setup_hmdevice_entity_helper(HMLight,
                                                  config,
                                                  add_callback_devices)


class HMLight(homematic.HMDevice, Light):
    """Represents a Homematic Light in Home Assistant."""

    @property
    def brightness(self):
        """Return the brightness of this light between 0..255."""
        if not self.available:
            return None
        # Is dimmer?
        if self._state is "LEVEL":
            return int(self._hm_get_state() * 255)
        else:
            return None

    @property
    def is_on(self):
        """Return True if light is on."""
        try:
            return self._hm_get_state() > 0
        except TypeError:
            return False

    def turn_on(self, **kwargs):
        """Turn the light on."""
        if not self.available:
            return

        if ATTR_BRIGHTNESS in kwargs and self._state is "LEVEL":
            percent_bright = float(kwargs[ATTR_BRIGHTNESS]) / 255
            self._hmdevice.set_level(percent_bright, self._channel)
        else:
            self._hmdevice.on(self._channel)

    def turn_off(self, **kwargs):
        """Turn the light off."""
        if self.available:
            self._hmdevice.off(self._channel)

    def _check_hm_to_ha_object(self):
        """Check if possible to use the HM Object as this HA type."""
        from pyhomematic.devicetypes.actors import Dimmer, Switch

        # Check compatibility from HMDevice
        if not super()._check_hm_to_ha_object():
            return False

        # Check if the homematic device is correct for this HA device
        if isinstance(self._hmdevice, Switch):
            return True
        if isinstance(self._hmdevice, Dimmer):
            return True

        _LOGGER.critical("This %s can't be use as light!", self._name)
        return False

    def _init_data_struct(self):
        """Generate a data dict (self._data) from hm metadata."""
        from pyhomematic.devicetypes.actors import Dimmer, Switch

        super()._init_data_struct()

        # Use STATE
        if isinstance(self._hmdevice, Switch):
            self._state = "STATE"

        # Use LEVEL
        if isinstance(self._hmdevice, Dimmer):
            self._state = "LEVEL"

        # Add state to data dict
        if self._state:
            _LOGGER.debug("%s init datadict with main node '%s'", self._name,
                          self._state)
            self._data.update({self._state: STATE_UNKNOWN})
        else:
            _LOGGER.critical("Can't correctly init light %s.", self._name)
