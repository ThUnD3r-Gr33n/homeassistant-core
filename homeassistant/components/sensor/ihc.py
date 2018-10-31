"""IHC sensor platform.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.ihc/
"""
import voluptuous as vol
from homeassistant.components.ihc import (
    validate_name, IHC_DATA, IHC_CONTROLLER, CONTROLLER_ID, IHC_INFO)
from homeassistant.components.ihc.ihcdevice import IHCDevice
from homeassistant.components.ihc.const import (
    CONF_SECONDARY)
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_ID, CONF_NAME, CONF_UNIT_OF_MEASUREMENT, CONF_SENSORS,
    TEMP_CELSIUS)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity

DEPENDENCIES = ['ihc']

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_SENSORS, default=[]):
        vol.All(cv.ensure_list, [
            vol.All({
                vol.Required(CONF_ID): cv.positive_int,
                vol.Optional(CONF_SECONDARY, default=False): cv.boolean,
                vol.Optional(CONF_NAME): cv.string,
                vol.Optional(CONF_UNIT_OF_MEASUREMENT,
                             default=TEMP_CELSIUS): cv.string
            }, validate_name)
        ])
})


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the IHC sensor platform."""
    devices = []
    if discovery_info:
        for name, device in discovery_info.items():
            ihc_id = device['ihc_id']
            product_cfg = device['product_cfg']
            product = device['product']
            # Find controller that corresponds with device id
            ctrl_id = device['ctrl_id']
            ihc_key = IHC_DATA.format(ctrl_id)
            info = hass.data[ihc_key][IHC_INFO]
            ihc_controller = hass.data[ihc_key][IHC_CONTROLLER]

            sensor = IHCSensor(ihc_controller, name, ihc_id, info,
                               product_cfg[CONF_UNIT_OF_MEASUREMENT],
                               product)
            devices.append(sensor)
    else:
        sensors = config[CONF_SENSORS]
        for sensor_cfg in sensors:
            ihc_id = sensor_cfg[CONF_ID]
            # Get controller id
            ihc_secondary = bool(sensor_cfg[CONF_SECONDARY])
            ihc_key = IHC_DATA.format(CONTROLLER_ID[ihc_secondary])
            ihc_controller = hass.data[ihc_key][IHC_CONTROLLER]

            info = hass.data[ihc_key][IHC_INFO]
            name = sensor_cfg[CONF_NAME]
            unit = sensor_cfg[CONF_UNIT_OF_MEASUREMENT]
            sensor = IHCSensor(ihc_controller, name, ihc_id, info, unit)
            devices.append(sensor)

    add_entities(devices)


class IHCSensor(IHCDevice, Entity):
    """Implementation of the IHC sensor."""

    def __init__(self, ihc_controller, name, ihc_id: int, info: bool,
                 unit, product=None) -> None:
        """Initialize the IHC sensor."""
        super().__init__(ihc_controller, name, ihc_id, info, product)
        self._state = None
        self._unit_of_measurement = unit

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return self._unit_of_measurement

    def on_ihc_change(self, ihc_id, value):
        """Handle IHC resource change."""
        self._state = value
        self.schedule_update_ha_state()
