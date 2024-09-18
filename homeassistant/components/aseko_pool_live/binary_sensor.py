"""Support for Aseko Pool Live binary sensors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from aioaseko import Unit

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import AsekoDataUpdateCoordinator
from .entity import AsekoEntity


@dataclass(frozen=True, kw_only=True)
class AsekoBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes an Aseko binary sensor entity."""

    value_fn: Callable[[Unit], bool | None]


BINARY_SENSORS: tuple[AsekoBinarySensorEntityDescription, ...] = (
    AsekoBinarySensorEntityDescription(
        key="water_flow_to_probes",
        translation_key="water_flow_to_probes",
        value_fn=lambda unit: unit.water_flow_to_probes,
    ),
    AsekoBinarySensorEntityDescription(
        key="heating",
        translation_key="heating",
        value_fn=lambda unit: unit.heating,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Aseko Pool Live binary sensors."""
    data: tuple[str, AsekoDataUpdateCoordinator] = hass.data[DOMAIN][
        config_entry.entry_id
    ]
    user_id, coordinator = data
    units = coordinator.data.values()
    async_add_entities(
        AsekoBinarySensorEntity(unit, user_id, coordinator, description)
        for description in BINARY_SENSORS
        for unit in units
        if description.value_fn(unit) is not None
    )


class AsekoBinarySensorEntity(AsekoEntity, BinarySensorEntity):
    """Representation of an Aseko binary sensor entity."""

    entity_description: AsekoBinarySensorEntityDescription

    @property
    def is_on(self) -> bool | None:
        """Return the state of the sensor."""
        return self.entity_description.value_fn(self.unit)
