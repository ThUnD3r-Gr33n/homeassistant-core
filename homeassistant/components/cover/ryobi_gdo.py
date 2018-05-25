"""
Ryobi platform for the cover component.

For more details about this platform, please refer to the documentation
https://home-assistant.io/components/cover.ryobi_gdo/
"""
from datetime import timedelta

import logging
import voluptuous as vol

import homeassistant.helpers.config_validation as cv

from homeassistant.components.cover import (
    CoverDevice, PLATFORM_SCHEMA, SUPPORT_OPEN, SUPPORT_CLOSE)
from homeassistant.const import (
    CONF_USERNAME, CONF_PASSWORD, STATE_UNKNOWN, STATE_CLOSED)

REQUIREMENTS = ['py_ryobi_gdo==0.0.10']

_LOGGER = logging.getLogger(__name__)

CONF_DEVICE_ID = 'device_id'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Required(CONF_DEVICE_ID): vol.All(cv.ensure_list, [cv.string]),
})

SCAN_INTERVAL = timedelta(seconds=30)

SUPPORTED_FEATURES = (SUPPORT_OPEN | SUPPORT_CLOSE)


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Ryobi covers."""
    from py_ryobi_gdo import RyobiGDO as ryobi_door
    covers = []

    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)
    devices = config.get(CONF_DEVICE_ID)

    _LOGGER.debug("%s devices to set up", len(devices))

    for device_id in devices:
        my_door = ryobi_door(username, password, device_id)
        if my_door.get_api_key() is True:
            _LOGGER.debug("Credentials OK, api key retrieved")
        else:
            _LOGGER.error("Wrong credentials, no api key retrieved")
            return
        _LOGGER.debug('Checking device_id')
        if my_door.check_device_id() is True:
            _LOGGER.debug("Adding device %s to covers", device_id)
            covers.append(RyobiCover(hass, my_door))
        else:
            _LOGGER.error("%s not in your devices. Check conf", device_id)
    if covers:
        _LOGGER.debug("Adding covers")
        add_devices(covers, True)


class RyobiCover(CoverDevice):
    """Representation of a ryobi cover."""

    def __init__(self, hass, ryobi_door):
        """Initialize the cover."""
        self.ryobi_door = ryobi_door
        self._name = 'ryobi_gdo_{}'.format(ryobi_door.get_device_id())

    @property
    def name(self):
        """Return the name of the cover."""
        return self._name

    @property
    def is_closed(self):
        """Return if the cover is closed."""
        if self._door_state == STATE_UNKNOWN:
            return None
        return self._door_state == STATE_CLOSED

    @property
    def device_class(self):
        """Return the class of this device, from component DEVICE_CLASSES."""
        return 'garage'

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORTED_FEATURES

    def close_cover(self, **kwargs):
        """Close the cover."""
        _LOGGER.debug("Closing garage door")
        self.ryobi_door.close_device()

    def open_cover(self, **kwargs):
        """Open the cover."""
        _LOGGER.debug("Opening garage door")
        self.ryobi_door.open_device()

    def update(self):
        """Update status from the door."""
        _LOGGER.debug("Updating RyobiGDO status")
        self.ryobi_door.update()
        self._door_state = self.ryobi_door.get_door_status()
