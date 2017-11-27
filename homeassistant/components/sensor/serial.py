"""
Support for reading data from a serial port.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.serial/
"""
import asyncio
import logging
import json

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA
<<<<<<< HEAD
from homeassistant.const import CONF_NAME, CONF_VALUE_TEMPLATE, EVENT_HOMEASSISTANT_STOP
=======
from homeassistant.const import (
    CONF_NAME, CONF_VALUE_TEMPLATE, EVENT_HOMEASSISTANT_STOP)
>>>>>>> home-assistant/dev
from homeassistant.helpers.entity import Entity

REQUIREMENTS = ['pyserial-asyncio==0.4']

_LOGGER = logging.getLogger(__name__)

CONF_SERIAL_PORT = 'serial_port'
CONF_BAUDRATE = 'baudrate'

DEFAULT_NAME = "Serial Sensor"
DEFAULT_BAUDRATE = 9600

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_SERIAL_PORT): cv.string,
    vol.Optional(CONF_BAUDRATE, default=DEFAULT_BAUDRATE):
        cv.positive_int,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_VALUE_TEMPLATE): cv.template,
})


@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """Set up the Serial sensor platform."""
    name = config.get(CONF_NAME)
    port = config.get(CONF_SERIAL_PORT)
    baudrate = config.get(CONF_BAUDRATE)

    value_template = config.get(CONF_VALUE_TEMPLATE)
    if value_template is not None:
        value_template.hass = hass

    sensor = SerialSensor(name, port, baudrate, value_template)

    hass.bus.async_listen_once(
        EVENT_HOMEASSISTANT_STOP, sensor.stop_serial_read())
    async_add_devices([sensor], True)


class SerialSensor(Entity):
    """Representation of a Serial sensor."""

    def __init__(self, name, port, baudrate, value_template):
        """Initialize the Serial sensor."""
        self._name = name
        self._state = None
        self._port = port
        self._baudrate = baudrate
        self._serial_loop_task = None
        self._template = value_template
        self._attributes = []

    @asyncio.coroutine
    def async_added_to_hass(self):
        """Handle when an entity is about to be added to Home Assistant."""
        self._serial_loop_task = self.hass.loop.create_task(
            self.serial_read(self._port, self._baudrate))

    @asyncio.coroutine
    def serial_read(self, device, rate, **kwargs):
        """Read the data from the port."""
        import serial_asyncio
        reader, _ = yield from serial_asyncio.open_serial_connection(
            url=device, baudrate=rate, **kwargs)
        while True:
            line = yield from reader.readline()
            line = line.decode('utf-8').strip()
<<<<<<< HEAD
            
            """ Parse the return text as JSON and save the json as an attribute. """
            try:
                self._attributes = json.loads(line)
            except json.JSONDecodeError:
                self._attributes = []
=======

            try:
                data = json.loads(line)
                if isinstance(data, dict):
                    self._attributes = data
            except ValueError:
                pass
>>>>>>> home-assistant/dev

            if self._template is not None:
                line = self._template.async_render_with_possible_json_value(
                    line)

            self._state = line
            self.async_schedule_update_ha_state()

    @asyncio.coroutine
    def stop_serial_read(self):
        """Close resources."""
        if self._serial_loop_task:
            self._serial_loop_task.cancel()

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
<<<<<<< HEAD
    def state_attributes(self):
        """Return the attributes of the entity.

           Provide the parsed JSON data (if any).
        """

=======
    def device_state_attributes(self):
        """Return the attributes of the entity (if any JSON present)."""
>>>>>>> home-assistant/dev
        return self._attributes

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state
