"""
Support for the for Danfoss Air HRV sswitch platform.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/switch.danfoss_air/
"""
import logging

from homeassistant.components.switch import (
    SwitchDevice)
from homeassistant.components.danfoss_air import DOMAIN \
     as DANFOSS_AIR_DOMAIN

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Danfoss Air HRV switch platform."""
    from pydanfossair.commands import ReadCommand, UpdateCommand

    data = hass.data[DANFOSS_AIR_DOMAIN]

    switches = [
        ["Danfoss Air Boost",
         ReadCommand.boost,
         UpdateCommand.boost_activate,
         UpdateCommand.boost_deactivate]
    ]

    dev = []

    for switch in switches:
        dev.append(DanfossAir(data,
                              switch[0],
                              switch[1],
                              switch[2],
                              switch[3]))

    add_entities(dev)


class DanfossAir(SwitchDevice):
    """Representation of a Danfoss Air HRV Switch."""

    def __init__(self, data, name, state_command, on_command, off_command):
        """Initialize the switch."""
        self._data = data
        self._name = name
        self._state_command = state_command
        self._on_command = on_command
        self._off_command = off_command
        self._state = None

    @property
    def name(self):
        """Return the name of the switch."""
        return self._name

    @property
    def is_on(self):
        """Return true if switch is on."""
        return self._state

    def turn_on(self, **kwargs):
        """Turn the switch on."""
        _LOGGER.debug("Turning on switch with command %s.", self._on_command)
        self._data.update_state(self._on_command, self._state_command)

    def turn_off(self, **kwargs):
        """Turn the switch off."""
        _LOGGER.debug("Turning of switch with command %s", self._off_command)
        self._data.update_state(self._off_command, self._state_command)

    def update(self):
        """Update the switch's state."""

        self._data.update()

        self._state = self._data.get_value(self._state_command)
        if self._state is None:
            _LOGGER.debug("Could not get data for %s.", self._state_command)
