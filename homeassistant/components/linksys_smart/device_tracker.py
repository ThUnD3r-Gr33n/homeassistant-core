"""Support for Linksys Smart Wifi routers."""
from __future__ import annotations

import base64
from http import HTTPStatus
import logging

import requests
import voluptuous as vol

from homeassistant.components.device_tracker import (
    DOMAIN,
    PLATFORM_SCHEMA as PARENT_PLATFORM_SCHEMA,
    DeviceScanner,
)
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import ConfigType

DEFAULT_TIMEOUT = 10
DEFAULT_USERNAME = "admin"

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PARENT_PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_USERNAME, default=DEFAULT_USERNAME): cv.string,
        vol.Optional(CONF_PASSWORD): cv.string,
    }
)


def get_scanner(
    hass: HomeAssistant, config: ConfigType
) -> LinksysSmartWifiDeviceScanner | None:
    """Validate the configuration and return a Linksys AP scanner."""
    try:
        return LinksysSmartWifiDeviceScanner(config[DOMAIN])
    except ConnectionError:
        return None


class LinksysSmartWifiDeviceScanner(DeviceScanner):
    """This class queries a Linksys Access Point."""

    def __init__(self, config):
        """Initialize the scanner."""
        self.host = config[CONF_HOST]
        self.username = config[CONF_USERNAME]
        self.password = config.get(CONF_PASSWORD)
        self.last_results = {}

        # Check if the access point is accessible
        response = self._make_request()
        if response.status_code != HTTPStatus.OK:
            raise ConnectionError("Cannot connect to Linksys Access Point")

    def scan_devices(self):
        """Scan for new devices and return a list with device IDs (MACs)."""
        self._update_info()

        return self.last_results.keys()

    def get_device_name(self, device):
        """Return the name (if known) of the device."""
        return self.last_results.get(device)

    def _update_info(self):
        """Check for connected devices."""
        _LOGGER.info("Checking Linksys Smart Wifi")

        self.last_results = {}
        response = self._make_request()
        if response.status_code != HTTPStatus.OK:
            _LOGGER.error(
                "Got HTTP status code %d when getting device list", response.status_code
            )
            return False
        try:
            data = response.json()
            result = data["responses"][0]
            devices = result["output"]["devices"]
            for device in devices:
                if not (macs := device["knownMACAddresses"]):
                    _LOGGER.warning("Skipping device without known MAC address")
                    continue
                mac = macs[-1]
                if not device["connections"]:
                    _LOGGER.debug("Device %s is not connected", mac)
                    continue

                name = None
                for prop in device["properties"]:
                    if prop["name"] == "userDeviceName":
                        name = prop["value"]
                if not name:
                    name = device.get("friendlyName", device["deviceID"])

                _LOGGER.debug("Device %s is connected", mac)
                self.last_results[mac] = name
        except (KeyError, IndexError):
            _LOGGER.exception("Router returned unexpected response")
            return False
        return True

    def _make_request(self):
        # Older firmware versions do not require authentication
        data = [
            {
                "request": {"sinceRevision": 0},
                "action": "http://linksys.com/jnap/devicelist/GetDevices",
            }
        ]

        auth_token = self._get_auth_token(self.username, self.password)
        headers = {
            "X-JNAP-Action": "http://linksys.com/jnap/core/Transaction",
        }
        if auth_token is not None:
            headers["X-JNAP-Authorization"] = auth_token

        return requests.post(
            f"http://{self.host}/JNAP/",
            timeout=DEFAULT_TIMEOUT,
            headers=headers,
            json=data,
        )

    def _get_auth_token(self, username, password):
        # An X-JNAP-Authorization HTTP header with basic access authentication

        if password is None:
            return None

        login = username + ":" + password
        token = base64.b64encode(login.encode("ascii")).decode("ascii")
        return "Basic " + token
