"""Implementation of the Radarr sensor."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import OverseerrUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class OverseerrSensorEntityDescription(SensorEntityDescription):
    """Entity description class for Overseerr sensors."""

    value_fn: Callable[[OverseerrUpdateCoordinator], StateType]


SENSOR_TYPES: tuple[OverseerrSensorEntityDescription, ...] = (
    OverseerrSensorEntityDescription(
        key="requested_movies",
        translation_key="requested_movies",
        icon="mdi:movie",
        value_fn=lambda coordinator: coordinator.data.movie,
    ),
    OverseerrSensorEntityDescription(
        key="requested_tv",
        translation_key="requested_tv",
        icon="mdi:television-classic",
        value_fn=lambda coordinator: coordinator.data.tv,
    ),
    OverseerrSensorEntityDescription(
        key="requested_pending",
        translation_key="requested_pending",
        icon="mdi:clock-alert-outline",
        value_fn=lambda coordinator: coordinator.data.pending,
    ),
    OverseerrSensorEntityDescription(
        key="requested_approved",
        translation_key="requested_approved",
        icon="mdi:check",
        value_fn=lambda coordinator: coordinator.data.approved,
    ),
    OverseerrSensorEntityDescription(
        key="requested_available",
        translation_key="requested_available",
        icon="mdi:download",
        value_fn=lambda coordinator: coordinator.data.available,
    ),
    OverseerrSensorEntityDescription(
        key="requested_total",
        translation_key="requested_total",
        icon="mdi:movie",
        value_fn=lambda coordinator: coordinator.data.total,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add sensors for passed config_entry in HA."""
    coordinator: OverseerrUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    async_add_entities(
        OverseeerrRequestsSensor(coordinator, config_entry, description)
        for description in SENSOR_TYPES
    )


class OverseeerrRequestsSensor(
    CoordinatorEntity[OverseerrUpdateCoordinator], SensorEntity
):
    """Representation of Overseerr total requests."""

    _attr_has_entity_name = True
    entity_description: OverseerrSensorEntityDescription

    def __init__(
        self,
        coordinator: OverseerrUpdateCoordinator,
        config_entry,
        entity_description: OverseerrSensorEntityDescription,
    ) -> None:
        """Initialize the Overseerr sensor."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._attr_unique_id = f"{config_entry.entry_id}-{entity_description.key}"
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, config_entry.entry_id)},
            manufacturer="Overseerr",
        )

    @property
    def native_value(self) -> StateType:
        """Return the value of the sensor."""
        return self.entity_description.value_fn(self.coordinator)
