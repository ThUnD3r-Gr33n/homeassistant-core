"""Class to hold all switch accessories."""
import logging

from homeassistant.core import split_entity_id
from homeassistant.helpers.event import async_track_state_change

from . import TYPES
from .accessories import HomeAccessory, add_preload_service
from .const import (SERV_SWITCH, CHAR_ON)

_LOGGER = logging.getLogger(__name__)


@TYPES.register('Switch')
class Switch(HomeAccessory):
    """Generate a Switch accessory."""

    def __init__(self, hass, entity_id, display_name):
        """Initialize a Switch accessory object to represent a remote."""
        super().__init__(display_name, entity_id, 'SWITCH')

        self._hass = hass
        self._entity_id = entity_id
        self._domain = split_entity_id(entity_id)[0]

        self.current_on = None
        self.homekit_target_on = None

        self.service_switch = add_preload_service(self, SERV_SWITCH)
        self.char_on = self.service_switch.get_characteristic(CHAR_ON)
        self.char_on.setter_callback = self.set_state

    def run(self):
        """Method called be object after driver is started."""
        state = self._hass.states.get(self._entity_id)
        self.update_state(new_state=state)

        async_track_state_change(self._hass, self._entity_id,
                                 self.update_state)

    def set_state(self, value):
        """Move switch state to value if call came from HomeKit."""
        if value != self.current_on:
            _LOGGER.debug("%s: Set switch state to %s",
                          self._entity_id, value)
            self.homekit_target_on = value
            service = 'turn_on' if value else 'turn_off'
            self._hass.services.call(self._domain, service,
                                     {'entity_id': self._entity_id})

    def update_state(self, entity_id=None, old_state=None, new_state=None):
        """Update switch state after state changed."""
        if new_state is None:
            return

        self.current_on = (new_state.state == 'on')
        if self.homekit_target_on is None:
            self.char_on.set_value(self.current_on, should_callback=False)
        _LOGGER.debug("%s: Set current state to %s",
                      self._entity_id, self.current_on)
        if self.homekit_target_on is None \
                or self.homekit_target_on == self.current_on:
            self.homekit_target_on = None
