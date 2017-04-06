"""
Support for real-time departure information for public transport in Munich.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.mvglive/
"""
import logging
from datetime import timedelta

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_NAME, ATTR_ATTRIBUTION, STATE_UNKNOWN
    )

REQUIREMENTS = ['PyMVGLive==1.1.3']

_LOGGER = logging.getLogger(__name__)

CONF_NEXT_DEPARTURE = 'nextdeparture'

CONF_STATION = 'station'
CONF_DESTINATIONS = 'destinations'
CONF_UBAHNDIRECTION = 'ubahndirection'
CONF_LINES = 'lines'
CONF_PRODUCTS = 'products'
CONF_TIMEOFFSET = 'timeoffset'

ICONS_PRODUCTS = {
    'U-Bahn': 'mdi:subway',
    'Tram': 'mdi:tram',
    'Bus': 'mdi:bus',
    'S-Bahn': 'mdi:train',
    'SEV': 'mdi:checkbox-blank-circle-outline',
    '-': 'mdi:clock'
}
ATTRIBUTION = "Data provided by MVG-live.de"

SCAN_INTERVAL = timedelta(minutes=1)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NEXT_DEPARTURE): [{
        vol.Required(CONF_STATION): cv.string,
        vol.Optional(CONF_DESTINATIONS, default=['']): cv.ensure_list_csv,
        vol.Optional(CONF_UBAHNDIRECTION, default=0): cv.positive_int,
        vol.Optional(CONF_LINES, default=['']): cv.ensure_list_csv,
        vol.Optional(CONF_PRODUCTS,
                     default=['U-Bahn', 'Tram',
                              'Bus', 'S-Bahn']): cv.ensure_list_csv,
        vol.Optional(CONF_TIMEOFFSET, default=0): cv.positive_int,
        vol.Optional(CONF_NAME): cv.string}]
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Get the MVGLive sensor."""
    sensors = []
    for nextdeparture in config.get(CONF_NEXT_DEPARTURE):
        sensors.append(
            MVGLiveSensor(
                nextdeparture.get(CONF_STATION),
                nextdeparture.get(CONF_DESTINATIONS),
                nextdeparture.get(CONF_UBAHNDIRECTION),
                nextdeparture.get(CONF_LINES),
                nextdeparture.get(CONF_PRODUCTS),
                nextdeparture.get(CONF_TIMEOFFSET),
                nextdeparture.get(CONF_NAME)))
    add_devices(sensors, True)


# pylint: disable=too-few-public-methods
class MVGLiveSensor(Entity):
    """Implementation of an MVG Live sensor."""

    def __init__(self, station, destinations, ubahndirection,
                 lines, products, timeoffset, name):
        """Initialize the sensor."""
        self._station = station
        self._name = name
        self.data = MVGLiveData(station, destinations, ubahndirection,
                                lines, products, timeoffset)
        self._state = STATE_UNKNOWN
        self._icon = ICONS_PRODUCTS['-']

    @property
    def name(self):
        """Return the name of the sensor."""
        if self._name:
            return self._name
        else:
            return self._station

    @property
    def state(self):
        """Return the next departure time."""
        return self._state

    @property
    def state_attributes(self):
        """Return the state attributes."""
        return self.data.departures

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return self._icon

    @property
    def unit_of_measurement(self):
        """Return the unit this state is expressed in."""
        return "min"

    def update(self):
        """Get the latest data and update the state."""
        self.data.update()
        if not self.data.departures:
            self._state = '-'
            self._icon = ICONS_PRODUCTS['-']
        else:
            self._state = self.data.departures.get('time', '-')
            self._icon = ICONS_PRODUCTS[self.data.departures.get('product', '-')]


class MVGLiveData(object):
    """Pull data from the mvg-live.de web page."""

    def __init__(self, station, destinations, ubahndirection,
                 lines, products, timeoffset):
        """Initialize the sensor."""
        import MVGLive
        self._station = station
        self._destinations = destinations
        self._ubahndirection = ubahndirection
        self._lines = lines
        self._products = products
        self._timeoffset = timeoffset
        self._include_ubahn = True if 'U-Bahn' in self._products else False
        self._include_tram = True if 'Tram' in self._products else False
        self._include_bus = True if 'Bus' in self._products else False
        self._include_sbahn = True if 'S-Bahn' in self._products else False
        self.mvg = MVGLive.MVGLive()
        self.departures = {}

    def update(self):
        """Update the connection data."""
        try:
            _departures = self.mvg.getlivedata(station=self._station,
                                               ubahn=self._include_ubahn,
                                               tram=self._include_tram,
                                               bus=self._include_bus,
                                               sbahn=self._include_sbahn)
        except ValueError:
            self.departures = {}
            _LOGGER.warning("Returned data not understood.")
            return
        for _departure in _departures:
            # find the first departure meeting the criteria
            if ('' not in self._destinations[:1] and
                    _departure['destination'] not in self._destinations):
                continue
            elif (self._ubahndirection > 0 and
                  int(_departure['direction']) != self._ubahndirection):
                continue
            elif ('' not in self._lines[:1] and
                  _departure['linename'] not in self._lines):
                continue
            elif _departure['time'] < self._timeoffset:
                continue
            # now select the relevant data
            _nextdep = {ATTR_ATTRIBUTION: ATTRIBUTION}
            for k in ['destination', 'linename', 'time', 'direction',
                      'product']:
                _nextdep[k] = _departure.get(k, '')
            _nextdep['time'] = int(_nextdep['time'])
            self.departures = _nextdep
            break
