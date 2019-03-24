import logging
from datetime import timedelta
from homeassistant.components.sector_alarm import DOMAIN as SECTOR_DOMAIN
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle
from homeassistant.const import TEMP_CELSIUS

UPDATE_INTERVAL = timedelta(minutes=5)

DEPENDENCIES = ['sector_alarm']

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """ Initial setup of the platform. """
    sector_connection = hass.data.get(SECTOR_DOMAIN)

    temps = sector_connection.GetTemps()

    dev = []

    for temp in temps:
        dev.append(SectorTempSensor(temp, sector_connection))

    async_add_entities(dev, False)

class SectorTempSensor(Entity):
    """ Secotor Alarm temperature class """
    def __init__(self, temp, sectorconnection):
        """Initialize the sensor."""
        self._sector = sectorconnection
        self._state = None
        self._name = temp[0]
        self._state = temp[1]

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
        """Return the unit of measurement."""
        return TEMP_CELSIUS

    @Throttle(UPDATE_INTERVAL)
    def update(self):
        temps = self._sector.GetTemps()
        for x,y in temps:
            if x == self._name:
                self._state = y
