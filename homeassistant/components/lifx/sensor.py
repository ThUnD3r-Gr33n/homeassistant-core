"""Sensor entities for LIFX integration."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import TIME_SECONDS
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import ATTR_RSSI, ATTR_UPTIME, DOMAIN
from .coordinator import LIFXSensorUpdateCoordinator
from .entity import LIFXEntity
from .models import LIFXCoordination

SCAN_INTERVAL = timedelta(seconds=60)

RSSI_SENSOR = SensorEntityDescription(
    key=ATTR_RSSI,
    name="RSSI",
    entity_category=EntityCategory.DIAGNOSTIC,
    state_class=SensorStateClass.MEASUREMENT,
    device_class=SensorDeviceClass.SIGNAL_STRENGTH,
    entity_registry_enabled_default=False,
)

UPTIME_SENSOR = SensorEntityDescription(
    key=ATTR_UPTIME,
    name="Uptime",
    entity_category=EntityCategory.DIAGNOSTIC,
    state_class=SensorStateClass.MEASUREMENT,
    device_class=SensorDeviceClass.DURATION,
    entity_registry_enabled_default=False,
    native_unit_of_measurement=TIME_SECONDS,
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up LIFX from a config entry."""
    lifx_coordination: LIFXCoordination = hass.data[DOMAIN][entry.entry_id]
    coordinator: LIFXSensorUpdateCoordinator = lifx_coordination.sensor_coordinator

    sensors: list[LIFXSensorEntity] = [
        LIFXSensorEntity(coordinator, RSSI_SENSOR),
        LIFXSensorEntity(coordinator, UPTIME_SENSOR),
    ]

    async_add_entities(sensors)


class LIFXSensorEntity(LIFXEntity, SensorEntity):
    """LIFX sensor entity base class."""

    _attr_has_entity_name: bool = True
    coordinator: LIFXSensorUpdateCoordinator
    entity_description: SensorEntityDescription

    def __init__(
        self,
        coordinator: LIFXSensorUpdateCoordinator,
        description: SensorEntityDescription,
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)

        self.entity_description = description
        self._attr_name = description.name
        self._attr_unique_id = f"{coordinator.serial_number}_{description.key}"

        if description.key == "rssi":
            self._attr_native_unit_of_measurement = (
                coordinator.get_rssi_unit_of_measurement()
            )
        self._async_update_attrs()

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        """Return the sensor native value."""
        return self._attr_native_value

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._async_update_attrs()
        super()._handle_coordinator_update()

    @callback
    def _async_update_attrs(self) -> None:
        """Handle coordinator updates."""
        self._attr_native_value = self.coordinator.async_get_native_value(
            self.entity_description.key
        )

    @callback
    async def async_added_to_hass(self) -> None:
        """Enable update of sensor data."""
        self.async_on_remove(
            self.coordinator.async_enable_sensor(self.entity_description.key)
        )
        await super().async_added_to_hass()
