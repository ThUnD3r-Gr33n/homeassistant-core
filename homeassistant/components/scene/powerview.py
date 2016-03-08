"""
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Gets powerview scenes from a powerview hub
defined by a Hunter Douglas powerview app.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/scene/
"""

import logging

from homeassistant.components.scene import Scene

_LOGGER = logging.getLogger(__name__)
REQUIREMENTS = [
    'https://github.com/sander76/powerviewApi/'
    'archive/master.zip#powerview_api==0.2']

HUB_ADDRESS = 'address'


# pylint: disable=unused-argument
def setup_platform(hass, config, add_devices, discovery_info=None):
    """sets up the powerview scenes stored in a powerview hub"""
    import powerview

    hub_address = config.get(HUB_ADDRESS)

    _pv = powerview.PowerView(hub_address)
    try:
        _scenes = _pv.get_scenes()
        _rooms = _pv.get_rooms()
    except ConnectionError:
        _LOGGER.exception("error connecting to powerview "
                          "hub with ip address: %s", hub_address)
        return False
    add_devices(PowerViewScene(hass, scene, _rooms, _pv)
                for scene in _scenes['sceneData'])

    return True


class PowerViewScene(Scene):
    """ A scene is a group of entities and the states we want them to be. """

    def __init__(self, hass, scene_data, room_data, pv_instance):
        self.pv_instance = pv_instance
        self.hass = hass
        self.scene_data = scene_data
        self._sync_room_data(room_data)

    def _sync_room_data(self, room_data):
        room = next((room for room in room_data["roomData"]
                     if room["id"] == self.scene_data["roomId"]), None)
        if room is not None:
            self.scene_data["roomName"] = room["name"]

    @property
    def name(self):
        return self.scene_data["name"]

    @property
    def device_state_attributes(self):
        return {"roomName": self.scene_data["roomName"]}

    def activate(self):
        """ Activates scene. Tries to get entities into requested state. """
        self.pv_instance.activate_scene(self.scene_data["id"])
