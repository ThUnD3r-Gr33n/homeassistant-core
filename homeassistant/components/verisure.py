"""
Support for Verisure components.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/verisure/
"""
import logging
import threading
import os.path
from datetime import timedelta

import voluptuous as vol

from homeassistant.const import (CONF_PASSWORD, CONF_USERNAME,
                                 EVENT_HOMEASSISTANT_STOP)
from homeassistant.helpers import discovery
from homeassistant.util import Throttle
import homeassistant.config as conf_util
import homeassistant.helpers.config_validation as cv

REQUIREMENTS = ['vsure==1.3.5']

_LOGGER = logging.getLogger(__name__)

ATTR_DEVICE_SERIAL = 'device_serial'

CONF_ALARM = 'alarm'
CONF_CODE_DIGITS = 'code_digits'
CONF_DOOR_WINDOW = 'door_window'
CONF_HYDROMETERS = 'hygrometers'
CONF_LOCKS = 'locks'
CONF_MOUSE = 'mouse'
CONF_SMARTPLUGS = 'smartplugs'
CONF_THERMOMETERS = 'thermometers'
CONF_SMARTCAM = 'smartcam'

DOMAIN = 'verisure'

SERVICE_CAPTURE_SMARTCAM = 'capture_smartcam'

HUB = None

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_USERNAME): cv.string,
        vol.Optional(CONF_ALARM, default=True): cv.boolean,
        vol.Optional(CONF_CODE_DIGITS, default=4): cv.positive_int,
        vol.Optional(CONF_DOOR_WINDOW, default=True): cv.boolean,
        vol.Optional(CONF_HYDROMETERS, default=True): cv.boolean,
        vol.Optional(CONF_LOCKS, default=True): cv.boolean,
        vol.Optional(CONF_MOUSE, default=True): cv.boolean,
        vol.Optional(CONF_SMARTPLUGS, default=True): cv.boolean,
        vol.Optional(CONF_THERMOMETERS, default=True): cv.boolean,
        vol.Optional(CONF_SMARTCAM, default=True): cv.boolean,
    }),
}, extra=vol.ALLOW_EXTRA)

CAPTURE_IMAGE_SCHEMA = vol.Schema({
    vol.Required(ATTR_DEVICE_SERIAL): cv.string
})


def setup(hass, config):
    """Set up the Verisure component."""
    import verisure
    global HUB
    HUB = VerisureHub(config[DOMAIN], verisure)
    if not HUB.login():
        return False
    hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP,
                         lambda event: HUB.logout())
    HUB.update_overview()

    for component in ('sensor', 'switch', 'alarm_control_panel', 'lock',
                      'camera', 'binary_sensor'):
        discovery.load_platform(hass, component, DOMAIN, {}, config)

    descriptions = conf_util.load_yaml_config_file(
        os.path.join(os.path.dirname(__file__), 'services.yaml'))

    def capture_smartcam(service):
        """Capture a new picture from a smartcam."""
        device_id = service.data.get(ATTR_DEVICE_SERIAL)
        HUB.smartcam_capture(device_id)
        _LOGGER.debug("Capturing new image from %s", ATTR_DEVICE_SERIAL)

    hass.services.register(DOMAIN, SERVICE_CAPTURE_SMARTCAM,
                           capture_smartcam,
                           descriptions[DOMAIN][SERVICE_CAPTURE_SMARTCAM],
                           schema=CAPTURE_IMAGE_SCHEMA)

    return True


class VerisureHub(object):
    """A Verisure hub wrapper class."""

    def __init__(self, domain_config, verisure):
        """Initialize the Verisure hub."""
        self.overview = {}

        self.config = domain_config
        self._verisure = verisure

        self._lock = threading.Lock()

        self.session = verisure.Session(
            domain_config[CONF_USERNAME],
            domain_config[CONF_PASSWORD])

    def login(self):
        """Login to Verisure."""
        try:
            self.session.login()
        except self._verisure.Error as ex:
            _LOGGER.error('Could not log in to verisure, %s', ex)
            return False
        return True

    def logout(self):
        """Logout from Verisure."""
        try:
            self.session.logout()
        except self._verisure.Error as ex:
            _LOGGER.error('Could not log out from verisure, %s', ex)
            return False
        return True

    @Throttle(timedelta(seconds=60))
    def update_overview(self):
        """Update the status."""
        self.overview = self.session.get_overview()

    @Throttle(timedelta(seconds=30))
    def smartcam_capture(self, device_id):
        """Capture a new image from a smartcam."""
        self.session.capture_image(device_id)
