"""Support for powerwall binary sensors."""
import logging

from tesla_powerwall import GridStatus

from homeassistant.components.binary_sensor import (
    DEVICE_CLASS_BATTERY_CHARGING,
    DEVICE_CLASS_CONNECTIVITY,
    BinarySensorEntity,
)
from homeassistant.const import DEVICE_CLASS_POWER

from .const import (
    ATTR_GRID_CODE,
    ATTR_NOMINAL_SYSTEM_POWER,
    ATTR_REGION,
    CHARGING_MARGIN_OF_ERROR,
    DOMAIN,
    POWERWALL_API_DEVICE_TYPE,
    POWERWALL_API_GRID_STATUS,
    POWERWALL_API_METERS,
    POWERWALL_API_SERIAL_NUMBERS,
    POWERWALL_API_SITE_INFO,
    POWERWALL_API_SITEMASTER,
    POWERWALL_API_STATUS,
    POWERWALL_BATTERY_METER,
    POWERWALL_COORDINATOR,
)
from .entity import PowerWallEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the August sensors."""
    powerwall_data = hass.data[DOMAIN][config_entry.entry_id]

    coordinator = powerwall_data[POWERWALL_COORDINATOR]
    site_info = powerwall_data[POWERWALL_API_SITE_INFO]
    device_type = powerwall_data[POWERWALL_API_DEVICE_TYPE]
    status = powerwall_data[POWERWALL_API_STATUS]
    powerwalls_serial_numbers = powerwall_data[POWERWALL_API_SERIAL_NUMBERS]

    entities = []
    for sensor_class in (
        PowerWallRunningSensor,
        PowerWallGridStatusSensor,
        PowerWallConnectedSensor,
        PowerWallChargingStatusSensor,
    ):
        entities.append(
            sensor_class(
                coordinator, site_info, status, device_type, powerwalls_serial_numbers
            )
        )

    async_add_entities(entities, True)


class PowerWallRunningSensor(PowerWallEntity, BinarySensorEntity):
    """Representation of an Powerwall running sensor."""

    @property
    def name(self):
        """Device Name."""
        return "Powerwall Status"

    @property
    def device_class(self):
        """Device Class."""
        return DEVICE_CLASS_POWER

    @property
    def unique_id(self):
        """Device Uniqueid."""
        return f"{self.base_unique_id}_running"

    @property
    def is_on(self):
        """Get the powerwall running state."""
        return self._coordinator.data[POWERWALL_API_SITEMASTER].running

    @property
    def device_state_attributes(self):
        """Return the device specific state attributes."""
        return {
            ATTR_REGION: self._site_info.region,
            ATTR_GRID_CODE: self._site_info.grid_code,
            ATTR_NOMINAL_SYSTEM_POWER: self._site_info.nominal_system_power_kW,
        }


class PowerWallConnectedSensor(PowerWallEntity, BinarySensorEntity):
    """Representation of an Powerwall connected sensor."""

    @property
    def name(self):
        """Device Name."""
        return "Powerwall Connected to Tesla"

    @property
    def device_class(self):
        """Device Class."""
        return DEVICE_CLASS_CONNECTIVITY

    @property
    def unique_id(self):
        """Device Uniqueid."""
        return f"{self.base_unique_id}_connected_to_tesla"

    @property
    def is_on(self):
        """Get the powerwall connected to tesla state."""
        return self._coordinator.data[POWERWALL_API_SITEMASTER].connected_to_tesla


class PowerWallGridStatusSensor(PowerWallEntity, BinarySensorEntity):
    """Representation of an Powerwall grid status sensor."""

    @property
    def name(self):
        """Device Name."""
        return "Grid Status"

    @property
    def device_class(self):
        """Device Class."""
        return DEVICE_CLASS_POWER

    @property
    def unique_id(self):
        """Device Uniqueid."""
        return f"{self.base_unique_id}_grid_status"

    @property
    def is_on(self):
        """Grid is online."""
        return self._coordinator.data[POWERWALL_API_GRID_STATUS] == GridStatus.CONNECTED


class PowerWallChargingStatusSensor(PowerWallEntity, BinarySensorEntity):
    """Representation of an Powerwall grid status sensor."""

    @property
    def name(self):
        """Device Name."""
        return "Powerwall Charging"

    @property
    def device_class(self):
        """Device Class."""
        return DEVICE_CLASS_BATTERY_CHARGING

    @property
    def unique_id(self):
        """Device Uniqueid."""
        return f"{self.base_unique_id}_powerwall_charging"

    @property
    def is_on(self):
        """Grid is online."""
        return (
            self._coordinator.data[POWERWALL_API_METERS][
                POWERWALL_BATTERY_METER
            ].instant_power
            < CHARGING_MARGIN_OF_ERROR
        )
