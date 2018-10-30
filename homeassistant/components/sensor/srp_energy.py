"""
Platform for retrieving energy data from SRP.

For more details about this platform, please refer to the documentation
https://home-assistant.io/components/energy.srp/
"""
from datetime import datetime, timedelta
import logging

from requests.exceptions import (
    ConnectionError as ConnectError, HTTPError, Timeout)
import voluptuous as vol

from homeassistant.const import (
    CONF_NAME, CONF_PASSWORD,
    CONF_USERNAME, CONF_ID)
import homeassistant.helpers.config_validation as cv
from homeassistant.util import Throttle
from homeassistant.helpers.config_validation import PLATFORM_SCHEMA  # noqa
from homeassistant.helpers.entity import Entity

REQUIREMENTS = ['srpenergy==1.0.1']

_LOGGER = logging.getLogger(__name__)

ATTRIBUTION = "Powered by SRP Energy"

DEFAULT_NAME = 'SRP Energy'
MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=1440)
ENERGY_KWH = 'kWh'

ATTR_READING_COST = "reading_cost"
ATTR_READING_TIME = 'datetime'
ATTR_READING_USAGE = 'reading_usage'
ATTR_DAILY_USAGE = 'daily_usage'
ATTR_USAGE_HISTORY = 'usage_history'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Required(CONF_ID): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string
})


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the SRP energy."""
    _LOGGER.info("Setting up Srp Energy.")

    name = config.get(CONF_NAME)
    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)
    account_id = config.get(CONF_ID)

    from srpenergy.client import SrpEnergyClient

    srp_client = SrpEnergyClient(account_id, username, password)

    add_entities([SrpEnergy(name, srp_client)], True)


class SrpEnergy(Entity):
    """Representation of an srp usage."""

    def __init__(self, name, client):
        """Initialize SRP Usage."""
        self._state = None
        self._name = name
        self._client = client
        self._history = None
        self._unit_of_measurement = ENERGY_KWH

        self.usage = None

    @property
    def attribution(self):
        """Return the attribution."""
        return ATTRIBUTION

    @property
    def state(self):
        """Return the current state."""
        if self._state is None:
            return None

        return "{0:.2f}".format(self._state)

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return self._unit_of_measurement

    @property
    def history(self):
        """Return the energy usage history of this entity, if any."""
        if self.data is None:
            return None

        data = [{
                ATTR_READING_TIME:
                    isodate,
                ATTR_READING_USAGE:
                    kwh,
                ATTR_READING_COST:
                    cost
                } for date, hour, isodate, kwh, cost in self.data]

        return data

    @property
    def state_attributes(self):
        """Return the state attributes."""
        data = {
            ATTR_DAILY_USAGE: self.state,
            ATTR_USAGE_HISTORY: self.history
        }

        return data

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Get the latest data from SRP Energy."""
        start_date = datetime.now() + timedelta(days=-1)
        end_date = datetime.now()

        try:

            usage = self._client.usage(start_date, end_date)

            daily_usage = 0.0
            for date, hour, isodate, kwh, cost in usage:
                daily_usage = daily_usage + float(kwh)

            if(len(usage) > 0):

                self._state = daily_usage
                self.data = usage

            else:
                _LOGGER.error("Unable to fetch data from SRP. No data")

        except (ConnectError, HTTPError, Timeout) as error:
            _LOGGER.error("Unable to connect to SRP. %s", error)
            self.data = None
        except ValueError as error:
            _LOGGER.error("Value error connecting to SRP. %s", error)
            self.data = None
        except TypeError as error:
            _LOGGER.error("Type error connecting to SRP. "
                          "Check username and password. %s", error)
            self.data = None
        except Exception as error:
            _LOGGER.error("Unknown error connecting to SRP. %s", error)
            self.data = None
