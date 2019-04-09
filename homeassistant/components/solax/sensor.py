"""Support for Solax inverter via local API."""
import asyncio
import json

from datetime import timedelta
import logging

import voluptuous as vol

from homeassistant.const import (
        TEMP_CELSIUS,
        CONF_IP_ADDRESS
)
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers.event import async_track_time_interval

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_IP_ADDRESS): cv.string,
})

SCAN_INTERVAL = timedelta(seconds=30)

async def async_setup_platform(hass, config, async_add_entities,
                               discovery_info=None):
    """Platform setup."""
    import solax

    api = solax.solax.RealTimeAPI(config.get(CONF_IP_ADDRESS))
    endpoint = RealTimeDataEndpoint(hass, api)
    hass.async_add_job(endpoint.async_refresh)
    async_track_time_interval(hass, endpoint.async_refresh, SCAN_INTERVAL)
    devices = []
    for sensor in solax.INVERTER_SENSORS:
        unit = solax.INVERTER_SENSORS[sensor][1]
        if unit == 'C':
            unit = TEMP_CELSIUS
        devices.append(Inverter(sensor, unit))
    endpoint.sensors = devices
    async_add_entities(devices)

class RealTimeDataEndpoint:
    """Representation of a Sensor."""

    def __init__(self, hass, api):
        """Initialize the sensor."""
        self.hass = hass
        self.api = api
        self.data = {}
        self.ready = asyncio.Event()
        self.sensors = []

    async def async_refresh(self, now=None):
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        try:
            self.data = await self.api.get_data()
            self.ready.set()
        except SolaxRequestError:
            if now is not None:
                self.ready.clear()
            else:
                raise PlatformNotReady
        for sensor in self.sensors:
            if sensor.key in self.data:
                sensor.value = self.data[sensor.key]
            sensor.async_schedule_update_ha_state()


class Inverter(Entity):
    """Class for a sensor."""

    def __init__(self, key, unit):
        """Initialize an inverter sensor."""
        self.key = key
        self.value = None
        self.unit = unit

    @property
    def state(self):
        """State of this inverter attribute."""
        return self.value

    @property
    def name(self):
        """Name of this inverter attribute."""
        return self.key

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self.unit

    @property
    def should_poll(self):
        """No polling needed."""
        return False
