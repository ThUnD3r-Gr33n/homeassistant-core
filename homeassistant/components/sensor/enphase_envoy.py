"""
Support for Enphase Envoy solar energy monitor.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.enphase_envoy/
"""
import logging

import voluptuous as vol

from homeassistant.helpers.entity import Entity
from homeassistant.components.sensor import PLATFORM_SCHEMA
import homeassistant.helpers.config_validation as cv
from homeassistant.const import (CONF_IP_ADDRESS, CONF_MONITORED_CONDITIONS)


REQUIREMENTS = ['envoy_reader==0.2']
_LOGGER = logging.getLogger(__name__)

SENSORS = {
    "production": ("Envoy Current Energy Production", 'W'),
    "daily_production": ("Envoy Today's Energy Production", "Wh"),
    "7_days_production": ("Envoy Last Seven Days Energy Production", "Wh"),
    "lifetime_production": ("Envoy Lifetime Energy Production", "Wh"),
    "consumption": ("Envoy Current Energy Consumption", "W"),
    "daily_consumption": ("Envoy Today's Energy Consumption", "Wh"),
    "7_days_consumption": ("Envoy Last Seven Days Energy Consumption", "Wh"),
    "lifetime_consumption": ("Envoy Lifetime Energy Consumption", "Wh")
    }


ICON = 'mdi:flash'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_IP_ADDRESS, default="envoy"): cv.string,
    vol.Optional(CONF_MONITORED_CONDITIONS, default=list(SENSORS)):
        vol.All(cv.ensure_list, [vol.In(list(SENSORS))])})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Enphase Envoy sensor."""
    ip_address = config[CONF_IP_ADDRESS]
    monitored_conditions = config[CONF_MONITORED_CONDITIONS]

    # Iterate through the list of sensors
    for condition in monitored_conditions:
        add_devices([Envoy(ip_address, condition, SENSORS[condition][0],
                           SENSORS[condition][1])], True)


class Envoy(Entity):
    """Implementation of the Enphase Envoy sensors."""

    def __init__(self, ip_address, sensor_type, name, unit):
        """Initialize the sensor."""
        self._ip_address = ip_address
        self._name = name
        self._unit_of_measurement = unit
        self._type = sensor_type
        self._state = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return self._unit_of_measurement

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return ICON

    def update(self):
        """Get the energy production data from the Enphase Envoy."""
        from envoy_reader import EnvoyReader

        if self._type == "production":
            self._state = EnvoyReader(self._ip_address).production()
        elif self._type == "daily_production":
            self._state = EnvoyReader(self._ip_address).daily_production()
        elif self._type == "7_days_production":
            self._state = EnvoyReader(self._ip_address).seven_days_production()
        elif self._type == "lifetime_production":
            self._state = EnvoyReader(self._ip_address).lifetime_production()

        elif self._type == "consumption":
            self._state = EnvoyReader(self._ip_address).consumption()
        elif self._type == "daily_consumption":
            self._state = EnvoyReader(self._ip_address).daily_consumption()
        elif self._type == "7_days_consumption":
            self._state = (EnvoyReader(self._ip_address)
                           .seven_days_consumption())
        elif self._type == "lifetime_consumption":
            self._state = EnvoyReader(self._ip_address).lifetime_consumption()
