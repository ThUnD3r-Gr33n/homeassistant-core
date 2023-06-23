"""Support for the Airzone Cloud binary sensors."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

from aioairzone_cloud.const import (
    AZD_ERRORS,
    AZD_PROBLEMS,
    AZD_SYSTEMS,
    AZD_WARNINGS,
    AZD_ZONES,
)

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import AirzoneUpdateCoordinator
from .entity import AirzoneEntity, AirzoneSystemEntity, AirzoneZoneEntity


@dataclass
class AirzoneBinarySensorEntityDescription(BinarySensorEntityDescription):
    """A class that describes Airzone Cloud binary sensor entities."""

    attributes: dict[str, str] | None = None


SYSTEM_BINARY_SENSOR_TYPES: Final[tuple[AirzoneBinarySensorEntityDescription, ...]] = (
    AirzoneBinarySensorEntityDescription(
        attributes={
            "errors": AZD_ERRORS,
            "warnings": AZD_WARNINGS,
        },
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        key=AZD_PROBLEMS,
    ),
)


ZONE_BINARY_SENSOR_TYPES: Final[tuple[AirzoneBinarySensorEntityDescription, ...]] = (
    AirzoneBinarySensorEntityDescription(
        attributes={
            "warnings": AZD_WARNINGS,
        },
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        key=AZD_PROBLEMS,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Add Airzone Cloud binary sensors from a config_entry."""
    coordinator: AirzoneUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    binary_sensors: list[AirzoneBinarySensor] = []

    for system_id, system_data in coordinator.data.get(AZD_SYSTEMS, {}).items():
        for description in SYSTEM_BINARY_SENSOR_TYPES:
            if description.key in system_data:
                binary_sensors.append(
                    AirzoneSystemBinarySensor(
                        coordinator,
                        description,
                        system_id,
                        system_data,
                    )
                )

    for zone_id, zone_data in coordinator.data.get(AZD_ZONES, {}).items():
        for description in ZONE_BINARY_SENSOR_TYPES:
            if description.key in zone_data:
                binary_sensors.append(
                    AirzoneZoneBinarySensor(
                        coordinator,
                        description,
                        entry,
                        zone_id,
                        zone_data,
                    )
                )

    async_add_entities(binary_sensors)


class AirzoneBinarySensor(AirzoneEntity, BinarySensorEntity):
    """Define an Airzone Cloud binary sensor."""

    entity_description: AirzoneBinarySensorEntityDescription

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update attributes when the coordinator updates."""
        self._async_update_attrs()
        super()._handle_coordinator_update()

    @callback
    def _async_update_attrs(self) -> None:
        """Update binary sensor attributes."""
        self._attr_is_on = self.get_airzone_value(self.entity_description.key)
        if self.entity_description.attributes:
            self._attr_extra_state_attributes = {
                key: self.get_airzone_value(val)
                for key, val in self.entity_description.attributes.items()
            }


class AirzoneSystemBinarySensor(AirzoneSystemEntity, AirzoneBinarySensor):
    """Define an Airzone Cloud System binary sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AirzoneUpdateCoordinator,
        description: AirzoneBinarySensorEntityDescription,
        system_id: str,
        system_data: dict[str, Any],
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, system_id, system_data)

        self._attr_unique_id = f"{system_id}_{description.key}"
        self.entity_description = description

        self._async_update_attrs()


class AirzoneZoneBinarySensor(AirzoneZoneEntity, AirzoneBinarySensor):
    """Define an Airzone Cloud Zone binary sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AirzoneUpdateCoordinator,
        description: AirzoneBinarySensorEntityDescription,
        entry: ConfigEntry,
        zone_id: str,
        zone_data: dict[str, Any],
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, zone_id, zone_data)

        self._attr_unique_id = f"{zone_id}_{description.key}"
        self.entity_description = description

        self._async_update_attrs()
