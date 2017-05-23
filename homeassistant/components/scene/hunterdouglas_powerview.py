"""
Support for Powerview scenes from a Powerview hub.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/scene.hunterdouglas_powerview/
"""
import asyncio
import logging

import voluptuous as vol

from homeassistant.components.scene import Scene, DOMAIN
from homeassistant.const import CONF_PLATFORM
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import async_generate_entity_id

_LOGGER = logging.getLogger(__name__)
REQUIREMENTS = ['aiopvapi==1.4']

ENTITY_ID_FORMAT = DOMAIN + '.{}'
HUB_ADDRESS = 'address'

PLATFORM_SCHEMA = vol.Schema({
    vol.Required(CONF_PLATFORM): 'hunterdouglas_powerview',
    vol.Required(HUB_ADDRESS): cv.string,
})


@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """Set up home assistant scene entries."""
    from aiopvapi.hub import Hub

    hub_address = config.get(HUB_ADDRESS)
    websession = async_get_clientsession(hass)

    _hub = Hub(hub_address, hass.loop, websession)
    _scenes = yield from _hub.scenes.get_scenes()
    _rooms = yield from _hub.rooms.get_rooms()

    if not _scenes or not _rooms:
        return
    pvscenes = (PowerViewScene(hass, _scene, _rooms, _hub)
                for _scene in _scenes['sceneData'])
    async_add_devices(pvscenes)


class PowerViewScene(Scene):
    """Representation of a Powerview scene."""

    def __init__(self, hass, scene_data, room_data, hub):
        """Initialize the scene."""
        self.hub = hub
        self.hass = hass
        self._sync_room_data(room_data, scene_data)
        self._name = scene_data['name']
        self._scene_id = scene_data['id']
        self.entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT, str(scene_data['id']), hass=hass)

    def _sync_room_data(self, room_data, scene_data):
        """Sync the room data."""
        room = next((room for room in room_data['roomData']
                     if room['id'] == scene_data['roomId']), {})

        self._room_name = room.get('name', '')

    @property
    def name(self):
        """Return the name of the scene."""
        return self._name

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return {'roomName': self._room_name}

    @property
    def icon(self):
        """Icon to use in the frontend."""
        return 'mdi:blinds'

    def async_activate(self):
        """Activate scene. Try to get entities into requested state."""
        yield from self.hub.scenes.activate_scene(self._scene_id)
