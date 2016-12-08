"""
Support for Zabbix Sensors.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.zabbix/
"""
import logging
from datetime import datetime

from homeassistant.helpers.entity import Entity
import homeassistant.components.zabbix as zabbix
import voluptuous as vol
from homeassistant.components.sensor import PLATFORM_SCHEMA
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = ['zabbix']

_CONF_TYPE = "type"
_CONF_HOSTIDS = "hostids"
_CONF_INDIVIDUAL = "individual"
_CONF_NAME = "name"

_ZABBIX_ID_LIST_SCHEMA = vol.Schema([int])

SCAN_INTERVAL = 30

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(_CONF_TYPE): cv.string,
    vol.Optional(_CONF_HOSTIDS, default=[]): _ZABBIX_ID_LIST_SCHEMA,
    vol.Optional(_CONF_INDIVIDUAL, default=False): cv.boolean(True),
    vol.Optional(_CONF_NAME, default=None): cv.string,
})

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Zabbix sensor platform."""
    sensors = []

    _LOGGER.info("Connected to Zabbix API Version %s" % zabbix.ZAPI.api_version())
    
    hostids = config.get(_CONF_HOSTIDS)
    individual = config.get(_CONF_INDIVIDUAL)
    name = config.get(_CONF_NAME)

    if (individual):
        # Individual sensor per host
        if not hostids:
            # We need hostids
            _LOGGER.critical("If using 'individual', must specify a list of hostids")
            return False

        for hostid in hostids:
            _LOGGER.info("Creating Zabbix Sensor: " + str(hostid))
            sensor = ZabbixSingleHostTriggerCountSensor([hostid], name)
            sensors.append(sensor)
    else:
        if not hostids:
            # Single sensor that provides the total count of triggers.
            _LOGGER.info("Creating Zabbix Sensor")
            sensor = ZabbixTriggerCountSensor(name)
        else:
            # Single sensor that sums total issues for all hosts
            _LOGGER.info("Creating Zabbix Sensor for group: " + str(hostids))
            sensor = ZabbixMultipleHostTriggerCountSensor(hostids, name)
        sensors.append(sensor)

    add_devices(sensors)


class ZabbixTriggerCountSensor(Entity):
    """Get the active trigger count for all Zabbix hosts."""

    def __init__(self, name):
        """Initiate Zabbix sensor."""
        self._name = "Zabbix"
        if name:
            self._name = name
        self._state = None
        self._attributes = {}

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    def _callZabbixAPI(self):
        return zabbix.ZAPI.trigger.get(output="extend", only_true=1, filter={"value": 1})

    def update(self):
        """Update the sensor."""
        _LOGGER.info("Updating ZabbixTriggerCountSensor: " + str(self._name))
        triggers = self._callZabbixAPI()
        self._state = len(triggers)
        self._attributes['Last Update'] = datetime.now().strftime('%Y%m%d%H%M%S')


    @property
    def device_state_attributes(self):
        """Return the state attributes of the device."""
        return self._attributes

class ZabbixSingleHostTriggerCountSensor(ZabbixTriggerCountSensor):
    def __init__(self, hostid, name=None):
        super().__init__(name)
        """Initiate Zabbix sensor."""
        self._hostid = hostid
        if not name:
            self._name = zabbix.ZAPI.host.get(hostids=self._hostid, output="extend")[0]["name"]

        self._attributes["Host ID"] = self._hostid

    def _callZabbixAPI(self):
        return zabbix.ZAPI.trigger.get(hostids=self._hostid, output="extend", only_true=1, filter={"value": 1})

class ZabbixMultipleHostTriggerCountSensor(ZabbixTriggerCountSensor):
    def __init__(self, hostids, name=None):
        super().__init__(name)
        """Initiate Zabbix sensor."""
        self._hostids = hostids
        if not name:
            hostNames = zabbix.ZAPI.host.get(hostids=self._hostids, output="extend")
            self._name = " ".join(name["name"] for name in hostNames)
        self._attributes["Host IDs"] = self._hostids

    def _callZabbixAPI(self):
        return zabbix.ZAPI.trigger.get(hostids=self._hostids, output="extend", only_true=1, filter={"value": 1})
