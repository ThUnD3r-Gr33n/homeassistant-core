"""
Support for Fibaro cover - curtains, rollershutters etc.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/cover.fibaro/
"""
import logging

from homeassistant.components.cover import CoverDevice, ENTITY_ID_FORMAT, \
    ATTR_POSITION, ATTR_TILT_POSITION
from homeassistant.components.fibaro import (
    FIBARO_CONTROLLER, FIBARO_DEVICES, FibaroDevice)

DEPENDENCIES = ['fibaro']

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Fibaro covers."""
    if discovery_info is None:
        return

    add_entities(
        [FibaroCover(device, hass.data[FIBARO_CONTROLLER]) for
         device in hass.data[FIBARO_DEVICES]['cover']], True)


class FibaroCover(FibaroDevice, CoverDevice):
    """Representation a Fibaro Cover."""

    def __init__(self, fibaro_device, controller):
        """Initialize the Vera device."""
        FibaroDevice.__init__(self, fibaro_device, controller)
        self.entity_id = ENTITY_ID_FORMAT.format(self.ha_id)

    @staticmethod
    def bound(position):
        """Normalize the position."""
        if position is None:
            return None
        position = int(position)
        if position <= 5:
            return 0
        if position >= 95:
            return 100
        return position

    @property
    def current_cover_position(self):
        """Return current position of cover. 0 is closed, 100 is open."""
        return self.bound(self.get_level())

    @property
    def current_cover_tilt_position(self):
        """Return the current tilt position for venetian blinds."""
        return self.bound(self.get_level2())

    def set_cover_position(self, **kwargs):
        """Move the cover to a specific position."""
        self.set_level(kwargs.get(ATTR_POSITION))

    def set_cover_tilt_position(self, **kwargs):
        """Move the cover to a specific position."""
        self.action("setValue2", kwargs.get(ATTR_TILT_POSITION))

    @property
    def is_closed(self):
        """Return if the cover is closed."""
        if self.current_cover_position is not None:
            return self.current_cover_position == 0

    def open_cover(self, **kwargs):
        """Open the cover."""
        self.action("open")

    def close_cover(self, **kwargs):
        """Close the cover."""
        self.action("close")

    def open_cover_tilt(self, **kwargs):
        """Open the cover tilt."""
        self.action("setValue2", 100)

    def close_cover_tilt(self, **kwargs):
        """Close the cover."""
        self.action("setValue2", 0)

    def stop_cover(self, **kwargs):
        """Stop the cover."""
        self.action("stop")
