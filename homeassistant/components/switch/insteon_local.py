"""
Support for Insteon switch devices via local hub support

Based on the insteonlocal library
https://github.com/phareous/insteonlocal

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/switch.insteon_local/

--
Example platform config
--

insteon_local:
  host: YOUR HUB IP
  username: YOUR HUB USERNAME
  password: YOUR HUB PASSWORD
  timeout: 10
  port: 25105
"""
import json
import logging
import os
from time import sleep
from datetime import timedelta
from homeassistant.components.switch import SwitchDevice
from homeassistant.loader import get_component
import homeassistant.util as util

INSTEON_LOCAL_SWITCH_CONF = 'insteon_local_switch.conf'

DEPENDENCIES = ['insteon_local']

_LOGGER = logging.getLogger(__name__)

MIN_TIME_BETWEEN_SCANS = timedelta(seconds=5)
MIN_TIME_BETWEEN_FORCED_SCANS = timedelta(milliseconds=100)

DOMAIN = "switch"

_LOGGER = logging.getLogger(__name__)
_CONFIGURING = {}


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the Insteon local switch platform."""
    insteonhub = hass.data['insteon_local']

    conf_switches = config_from_file(hass.config.path(INSTEON_LOCAL_SWITCH_CONF))
    if len(conf_switches):
        for device_id in conf_switches:
            setup_switch(device_id, conf_switches[device_id], insteonhub, hass, add_devices)

    linked = insteonhub.getLinked()

    for id in linked:
        if linked[id]['cat_type'] == 'switch' and id not in conf_switches:
            request_configuration(id, insteonhub, hass, add_devices)

def request_configuration(id, insteonhub, hass, add_devices_callback):
    """Request configuration steps from the user."""
    configurator = get_component('configurator')

    # We got an error if this method is called while we are configuring
    if id in _CONFIGURING:
        configurator.notify_errors(
            _CONFIGURING[id], 'Failed to register, please try again.')

        return

    def insteon_light_configuration_callback(data):
        """The actions to do when our configuration callback is called."""
        setup_switch(id, data.get('name'), insteonhub, hass, add_devices_callback)

    _CONFIGURING[id] = configurator.request_config(
        hass, 'Insteon Switch ' + id, insteon_light_configuration_callback,
        description=('Enter a name for Switch ' + id),
        entity_picture='/static/images/config_insteon.png',
        submit_caption='Confirm',
        fields=[{'id': 'name','name': 'Name', 'type': ''}]
    )

def setup_switch(id, name, insteonhub, hass, add_devices_callback):
    """Setup switch."""

    if id in _CONFIGURING:
        request_id = _CONFIGURING.pop(id)
        configurator = get_component('configurator')
        configurator.request_done(request_id)
        _LOGGER.info('Device configuration done!')

    conf_lights = config_from_file(hass.config.path(INSTEON_LOCAL_SWITCH_CONF))
    if id not in conf_lights:
        conf_lights[id] = name

    if not config_from_file(
            hass.config.path(INSTEON_LOCAL_SWITCH_CONF),
            conf_lights):
        _LOGGER.error('failed to save config file')

    device = insteonhub.switch(id)
    add_devices_callback([InsteonLocalSwitchDevice(device, name)])


def config_from_file(filename, config=None):
    """Small configuration file management function."""
    if config:
        # We're writing configuration
        try:
            with open(filename, 'w') as fdesc:
                fdesc.write(json.dumps(config))
        except IOError as error:
            _LOGGER.error('Saving config file failed: %s', error)
            return False
        return True
    else:
        # We're reading config
        if os.path.isfile(filename):
            try:
                with open(filename, 'r') as fdesc:
                    return json.loads(fdesc.read())
            except IOError as error:
                _LOGGER.error('Reading config file failed: %s', error)
                # This won't work yet
                return False
        else:
            return {}

class InsteonLocalSwitchDevice(SwitchDevice):
    """An abstract Class for an Insteon node."""

    def __init__(self, node, name):
        """Initialize the device."""
        self.node = node
        self.node.deviceName = name
        self._state = False

    @property
    def name(self):
        """Return the the name of the node."""
        return self.node.deviceName

    @property
    def unique_id(self):
        """Return the ID of this insteon node."""
        return 'insteon_local_' + self.node.deviceId

    @util.Throttle(MIN_TIME_BETWEEN_SCANS, MIN_TIME_BETWEEN_FORCED_SCANS)
    def update(self):
        """Update state of the sensor."""
        devid = self.node.deviceId.upper()
        self.node.hub.directCommand(devid, '19', '00')
        resp = self.node.hub.getBufferStatus(devid)
        attempts = 1
        while 'cmd2' not in resp and attempts < 9:
            if attempts % 3 == 0:
                self.node.hub.directCommand(devid, '19', '00')
            else:
                sleep(2)
            resp = self.node.hub.getBufferStatus(devid)
            attempts += 1

        if 'cmd2' in resp:
            _LOGGER.info("cmd2 value = " + resp['cmd2'])
            self._state = int(resp['cmd2'], 16) > 0

    @property
    def is_on(self):
        """Return the boolean response if the node is on."""
        return self._state

    def turn_on(self, **kwargs):
        """Turn device on."""
        self.node.on()
        self._state = True

    def turn_off(self, **kwargs):
        """Turn device off."""
        self.node.off()
        self._state = False
