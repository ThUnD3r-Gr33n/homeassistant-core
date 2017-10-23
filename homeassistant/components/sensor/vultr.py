"""
Support for monitoring the state of Vultr Subscriptions.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/sensor.vultr/
"""
import logging
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.const import (
    CONF_MONITORED_CONDITIONS, CONF_NAME)
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.components.vultr import (
    CONF_SUBSCRIPTION, ATTR_CURRENT_BANDWIDTH_GB, ATTR_PENDING_CHARGES,
    DATA_VULTR)

DEFAULT_NAME = '{} {}'
DEPENDENCIES = ['vultr']

_LOGGER = logging.getLogger(__name__)

# Monitored conditions: name, units, icon
MONITORED_CONDITIONS = {
    ATTR_CURRENT_BANDWIDTH_GB: ['Current Bandwidth Used', 'GB',
                                'mdi:chart-histogram'],
    ATTR_PENDING_CHARGES: ['Pending Charges', 'US$',
                           'mdi:currency-usd']
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_SUBSCRIPTION): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_MONITORED_CONDITIONS, default=MONITORED_CONDITIONS):
        vol.All(cv.ensure_list, [vol.In(MONITORED_CONDITIONS)])
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Vultr subscription (server) sensor."""
    vultr = hass.data.get(DATA_VULTR)
    if not vultr:
        return False

    subscription = config.get(CONF_SUBSCRIPTION)
    name = config.get(CONF_NAME)
    monitored_conditions = config.get(CONF_MONITORED_CONDITIONS)

    for condition in monitored_conditions:
        if subscription in vultr.data:
            sensors.append(VultrSensor(vultr,
                                       subscription,
                                       condition,
                                       name))
        else:
            _LOGGER.error(
                "Subscription %s not found. Perhaps API key issue?",
                subscription)

    if not sensors:
        _LOGGER.error("No Vultr sensors to be added")
        return False

    add_devices(sensors, True)


class VultrSensor(Entity):
    """Representation of a Vultr subscription sensor."""

    def __init__(self, vultr, subscription, variable, name):
        """Initialize a new Vultr sensor."""
        self._vultr = vultr
        self._subscription = subscription
        self._var_id = variable
        self.data = self._vultr.data.get(self._subscription, {})

        variable_info = MONITORED_CONDITIONS[variable]

        self._name = name.format(self.data['label'], variable_info[0])
        self._var_units = variable_info[1]
        self._var_icon = variable_info[2]

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def icon(self):
        """Icon used in the frontend if any."""
        return self._var_icon

    @property
    def unit_of_measurement(self):
        """The unit of measurement to present the value in."""
        return self._var_units

    @property
    def state(self):
        """Return the value of this given sensor type."""
        try:
            return round(float(self.data.get(self._var_id)), 2)
        except (TypeError, ValueError):
            return self.data.get(self._var_id)

    def update(self):
        """Update state of sensor."""
        self._vultr.update()
        self.data = self._vultr.data[self._subscription]
