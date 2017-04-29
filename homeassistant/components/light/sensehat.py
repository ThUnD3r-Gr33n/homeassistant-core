"""
Support for Sense Hat LEDs.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/light.sensehat/
"""
import logging
import subprocess

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.light import (
    ATTR_BRIGHTNESS, SUPPORT_BRIGHTNESS, ATTR_RGB_COLOR, SUPPORT_RGB_COLOR,
    Light, PLATFORM_SCHEMA)
from homeassistant.const import CONF_NAME

REQUIREMENTS = ['sense-hat==2.2.0']

_LOGGER = logging.getLogger(__name__)

SUPPORT_SENSEHAT = (SUPPORT_BRIGHTNESS | SUPPORT_RGB_COLOR)

DEFAULT_NAME = 'sensehat'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
})

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Sense Hat Light platform."""
    from sense_hat import SenseHat
    sensehat = SenseHat()

    name = config.get(CONF_NAME)

    add_devices([SenseHatLight(sensehat, name)])

class SenseHatLight(Light):
    """Representation of an Sense Hat Light."""

    def __init__(self, sensehat, name):
        """Initialize an Sense Hat Light."""
        self._sensehat = sensehat
        self._name = name
        self._is_on = False
        self._brightness = 255
        self._rgb_color = [255, 255, 255]

    @property
    def name(self):
        """Return the display name of this light."""
        return self._name

    @property
    def brightness(self):
        """Read back the brightness of the light (an integer in the range 1-255)."""
        return self._brightness

    @property
    def rgb_color(self):
        """Read back the color of the light, tuple of (r, g, b) values in range of 0-255."""
        return self._rgb_color

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_SENSEHAT

    @property
    def is_on(self):
        """Return true if light is on."""
        return self._is_on

    def turn_on(self, **kwargs):
        """Instruct the light to turn on, and set correct brightness / color."""
        self._brightness = kwargs.get(ATTR_BRIGHTNESS, 255)
        percent_bright = (self._brightness / 255)

        if ATTR_RGB_COLOR in kwargs:
            self._rgb_color = kwargs[ATTR_RGB_COLOR]

        self._sensehat.clear(int(self._rgb_color[0] * percent_bright),
                             int(self._rgb_color[1] * percent_bright),
                             int(self._rgb_color[2] * percent_bright))

        self._is_on = True

    def turn_off(self, **kwargs):
        """Instruct the light to turn off."""
        self._sensehat.clear()
        self._is_on = False
