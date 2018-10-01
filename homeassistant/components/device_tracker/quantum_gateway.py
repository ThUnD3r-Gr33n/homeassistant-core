"""
Support for Verizon FiOS Quantum Gateways.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/device_tracker.quantum_gateway/
"""
import logging

import voluptuous as vol

from homeassistant.components.device_tracker import (DOMAIN, PLATFORM_SCHEMA,
                                                     DeviceScanner)
from homeassistant.const import (CONF_HOST, CONF_PASSWORD)
import homeassistant.helpers.config_validation as cv

REQUIREMENTS = ['quantum-gateway==0.0.2']

_LOGGER = logging.getLogger(__name__)

DEFAULT_HOST = 'myfiosgateway.com'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_HOST, default=DEFAULT_HOST): cv.string
})


def get_scanner(hass, config):
    """Validate the configuration and return a Quantum Gateway scanner."""
    scanner = QuantumGatewayDeviceScanner(config[DOMAIN])

    return scanner if scanner.success_init else None


class QuantumGatewayDeviceScanner(DeviceScanner):
    """This class queries a Quantum Gateway."""

    def __init__(self, config):
        """Initialize the scanner."""
        from quantum_gateway import QuantumGatewayScanner

        self.host = config[CONF_HOST]
        self.password = config[CONF_PASSWORD]
        _LOGGER.debug('Initializing')

        self.quantum = QuantumGatewayScanner(self.host, self.password)

        self.success_init = self.quantum.success_init

        if not self.success_init:
            _LOGGER.error("Unable to login to gateway. Check password and "
                          "host.")

    def scan_devices(self):
        """Scan for new devices and return a list of found MACs."""
        return self.quantum.scan_devices()

    def get_device_name(self, device):
        """Return the name of the given device or None if we don't know."""
        return self.quantum.get_device_name(device)
