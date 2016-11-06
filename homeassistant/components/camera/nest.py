"""
Support for Nest Cameras.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/camera.nest/
"""

import logging
from datetime import timedelta
import requests
from IPython import embed
# import voluptuous as vol
from homeassistant.components.camera import (PLATFORM_SCHEMA, Camera)
import homeassistant.components.nest as nest
from homeassistant.util import Throttle


DEPENDENCIES = ['nest']
_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({})
# 2/minute for 
# TODO be NestAware subscription aware, (10/min subscribed, 2/min otherwise)
MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=6)
#MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=30)


# pylint: disable=unused-argument
def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup a generic IP Camera."""
    add_devices([NestCamera(structure, device)
                 for structure, device in hass.data[nest.DATA_NEST].camera_devices()])


class NestCamera(Camera):
    """Representation of a Nest Camera."""

    def __init__(self, structure, device):
        """Initialize a Nest Camera."""
        super().__init__()
        self.structure = structure
        self.device = device

        # data attributes
        self._location = None
        self._name = None
        self._is_online = None
        self._is_video_history_enabled = False
        

    # FIXME ends up with double name, ie Hallway(Hallway (E5C0))
    # FIXME duplication with climate/nest
    @property
    def name(self):
        """Return the name of the nest, if any."""
        self.update()
        if self._location is None or self._location == self._name:
            return self._name
        else:
            if self._name == '': 
                return self._location.capitalize()
            else:
                return self._location.capitalize() + '(' + self._name + ')'
    @property
    def is_recording(self):
        """Return true if the device is recording."""
        return self._is_online

    def update(self):
        """Cache value from Python-nest."""
        self._location = self.device.where
        self._name = self.device.name
        self._is_online = self.device.is_online
        self._is_video_history_enabled = self.device.is_video_history_enabled

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def camera_image(self):
        """Return a still image response from the camera."""
        url = self.device.snapshot_url
        # sadly, can't test against a simulator
        if url == 'https://developer.nest.com/simulator/api/v1/nest/devices/camera/snapshot':
            url = 'http://i.imgur.com/2CPHwxn.jpg'

        try:
            response = requests.get(url)
            #embed()
        except requests.exceptions.RequestException as error:
            _LOGGER.error('Error getting camera image: %s', error)
            return None
        
            _LOGGER.error('Error getting camera image: %s', error)
            return None

        return response.content
