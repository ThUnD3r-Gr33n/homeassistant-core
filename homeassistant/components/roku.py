"""
Support for roku platform.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/roku/
"""
import logging

import voluptuous as vol

from typing import Sequence, TypeVar, Union
from homeassistant.components.discovery import SERVICE_ROKU
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.helpers import discovery
import homeassistant.helpers.config_validation as cv

REQUIREMENTS = ['python-roku==3.1.5']

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'roku'

SERVICE_SCAN = 'roku_scan'

ATTR_ROKU = 'roku'

DATA_ROKU = 'data_roku'
DATA_ENTITIES = 'data_roku_entities'

DEFAULT_NAME = 'Roku'

NOTIFICATION_ID = 'roku_notification'
NOTIFICATION_TITLE = 'Roku Setup'
NOTIFICATION_SCAN_ID = 'roku_scan_notification'
NOTIFICATION_SCAN_TITLE = 'Roku Scan'

T = TypeVar('T')


# This version of ensure_list interprets an empty dict as no value
def ensure_list(value: Union[T, Sequence[T]]) -> Sequence[T]:
    """Wrap value in list if it is not one."""
    if value is None or (isinstance(value, dict) and not value):
        return []
    return value if isinstance(value, list) else [value]


CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.All(ensure_list, [vol.Schema({
        vol.Optional(CONF_HOST): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    })])
}, extra=vol.ALLOW_EXTRA)

# Currently no attributes but it might change later
ROKU_SCAN_SCHEMA = vol.Schema({})


def scan_for_rokus(hass):
    """Scan for devices and present a notification of the ones found."""
    from roku import Roku, RokuException

    rokus = Roku.discover()

    devices = []
    for roku in rokus:
        try:
            r_info = roku.device_info
        except RokuException:  # skip non-roku device
            continue
        devices.append('Name: {0}<br />Host: {1}<br />'.format(
            r_info.userdevicename if r_info.userdevicename
            else "{} {}".format(r_info.modelname, r_info.sernum),
            roku.host))

    if not devices:
        devices = ['No device(s) found']

    hass.components.persistent_notification.create(
        'The following devices were found:<br /><br />' +
        '<br /><br />'.join(devices),
        title=NOTIFICATION_SCAN_TITLE,
        notification_id=NOTIFICATION_SCAN_ID)


def setup(hass, config):
    """Set up the Roku component."""
    if DATA_ROKU not in hass.data:
        hass.data[DATA_ROKU] = {}

    def service_handler(service):
        """Handle service calls."""
        if service.service == SERVICE_SCAN:
            hass.add_job(scan_for_rokus, hass)
            return

    def roku_discovered(service, info):
        """Set up an Roku that was auto discovered."""
        _setup_roku(hass, {
            CONF_NAME: info['name'],
            CONF_HOST: info['host'],
        })

    discovery.listen(hass, SERVICE_ROKU, roku_discovered)

    for conf in config.get(DOMAIN, []):
        _setup_roku(hass, conf)

    hass.services.register(
        DOMAIN, SERVICE_SCAN, service_handler,
        schema=ROKU_SCAN_SCHEMA)

    return True


def _setup_roku(hass, roku_config):
    """Set up a Roku."""
    from roku import Roku
    host = roku_config.get(CONF_HOST)

    if host in hass.data[DATA_ROKU]:
        return

    roku = Roku(host)
    r_info = roku.device_info

    hass.data[DATA_ROKU][host] = {
        ATTR_ROKU: r_info.sernum
    }

    discovery.load_platform(
        hass, 'media_player', DOMAIN, roku_config)

    discovery.load_platform(
        hass, 'remote', DOMAIN, roku_config)
