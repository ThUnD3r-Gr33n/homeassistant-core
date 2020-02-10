"""Support for Vilfo Router sensors."""
from homeassistant.helpers.entity import Entity

from .const import (
    ATTR_API_DATA_FIELD,
    ATTR_DEVICE_CLASS,
    ATTR_ICON,
    ATTR_LABEL,
    ATTR_UNIT,
    DOMAIN,
    ROUTER_DEFAULT_MODEL,
    ROUTER_DEFAULT_NAME,
    ROUTER_MANUFACTURER,
    SENSOR_TYPES,
)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add Vilfo Router entities from a config_entry."""
    vilfo = hass.data[DOMAIN][config_entry.entry_id]

    sensors = []

    device_info = {
        "identifiers": {(DOMAIN, vilfo.host, vilfo.mac_address)},
        "name": ROUTER_DEFAULT_NAME,
        "manufacturer": ROUTER_MANUFACTURER,
        "model": ROUTER_DEFAULT_MODEL,
        "sw_version": vilfo.firmware_version,
    }

    for sensor_type in SENSOR_TYPES:
        sensors.append(VilfoRouterSensor(sensor_type, vilfo, device_info))

    async_add_entities(sensors, True)


class VilfoRouterSensor(Entity):
    """Define a Vilfo Router Sensor."""

    def __init__(self, sensor_type, api, device_info):
        """Initialize."""
        self.api = api
        self.sensor_type = sensor_type
        self._device_info = device_info
        self._unique_id = f"{self.api.unique_id}_{self.sensor_type}"
        self._state = None

    @property
    def device_info(self):
        """Return the device info."""
        return self._device_info

    @property
    def device_class(self):
        """Return the device class."""
        return SENSOR_TYPES[self.sensor_type].get(ATTR_DEVICE_CLASS, None)

    @property
    def icon(self):
        """Return the icon for the sensor."""
        return SENSOR_TYPES[self.sensor_type][ATTR_ICON]

    @property
    def name(self):
        """Return the name of the sensor."""
        parent_device_name = self._device_info["name"]
        sensor_name = SENSOR_TYPES[self.sensor_type][ATTR_LABEL]
        return f"{parent_device_name} {sensor_name}"

    @property
    def state(self):
        """Return the state."""
        return self._state

    @property
    def unique_id(self):
        """Return a unique_id for this entity."""
        return self._unique_id

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity."""
        return SENSOR_TYPES[self.sensor_type][ATTR_UNIT]

    async def async_update(self):
        """Update the router data."""
        await self.api.async_update()
        self._state = self.api.data.get(
            SENSOR_TYPES[self.sensor_type][ATTR_API_DATA_FIELD]
        )
