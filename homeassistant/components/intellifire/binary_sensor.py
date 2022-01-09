"""Support for Intellifire Binary Sensors."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import IntellifireDataUpdateCoordinator
from .const import DOMAIN

POWER = "on_off"
TIMER = "timer_on"
HOT = "is_hot"
THERMOSTAT = "thermostat_on"
FAN = "fan_on"
LIGHT = "light_on"
PILOT = "pilot_light_on"


@dataclass
class IntellifireSensorEntityDescriptionMixin:
    """Mixin for required keys."""

    value_fn: Callable[[Any], int | str | float | None]


@dataclass
class IntellifireBinarySensorEntityDescription(
    BinarySensorEntityDescription, IntellifireSensorEntityDescriptionMixin
):
    """Describes a binary sensor entity."""


INTELLIFIRE_BINARY_SENSORS: tuple[IntellifireBinarySensorEntityDescription, ...] = (
    IntellifireBinarySensorEntityDescription(
        key=POWER,  # This is the sensor name
        name="Power",  # This is the human readable name
        icon="mdi:power",
        device_class=BinarySensorDeviceClass.POWER,
        value_fn=lambda data: data.is_on,
    ),
    IntellifireBinarySensorEntityDescription(
        key=TIMER,
        name="Timer On",
        icon="mdi:camera-timer",
        value_fn=lambda data: data.timer_on,
    ),
    IntellifireBinarySensorEntityDescription(
        key=PILOT,
        name="Pilot Light On",
        icon="mdi:fire-alert",
        value_fn=lambda data: data.pilot_on,
    ),
    IntellifireBinarySensorEntityDescription(
        key=THERMOSTAT,
        name="Thermostat On",
        icon="mdi:home-thermometer-outline",
        value_fn=lambda data: data.thermostat_on,
    ),
)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up a Intellifire On/Off Sensor."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        IntellifireBinarySensor(
            coordinator=coordinator, entry_id=entry.entry_id, description=description
        )
        for description in INTELLIFIRE_BINARY_SENSORS
    ]
    async_add_entities(entities)


class IntellifireBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """A semi generic wrapper around Binary Sensor entiteis for Intellifire."""

    def __init__(
        self,
        coordinator: IntellifireDataUpdateCoordinator,
        entry_id,
        description: IntellifireBinarySensorEntityDescription,
    ):
        """Class initializer."""
        super().__init__(coordinator=coordinator)
        self.entity_description: IntellifireBinarySensorEntityDescription = description

        self.coordinator = coordinator
        self._entry_id = entry_id

        # Set the Display name the User will see
        self._attr_name = f"{coordinator.intellifire_name} Fireplace {description.name}"
        self._attr_unique_id = f"Intellifire_{coordinator.serial}"

    @property
    def is_on(self):
        """Use this to get the correct value."""
        return bool(self.entity_description.value_fn(self.coordinator.api.data))
