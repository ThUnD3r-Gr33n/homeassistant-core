"""Switch platform for Ecoforest."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from pyecoforest.models.device import Device

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import EcoforestCoordinator
from .entity import EcoforestEntity


@dataclass
class EcoforestSwitchRequiredKeysMixin:
    """Mixin for required keys."""

    value_fn: Callable[[Device], bool]


@dataclass
class EcoforestSwitchEntityDescription(
    SwitchEntityDescription, EcoforestSwitchRequiredKeysMixin
):
    """Describes an Ecoforest switch entity."""


SWITCH_TYPES: tuple[EcoforestSwitchEntityDescription, ...] = (
    EcoforestSwitchEntityDescription(
        key="status", name=None, value_fn=lambda data: data.on
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ecoforest switch platform."""
    coordinator: EcoforestCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = [
        EcoforestSwitchEntity(coordinator, description) for description in SWITCH_TYPES
    ]

    async_add_entities(entities)


class EcoforestSwitchEntity(EcoforestEntity, SwitchEntity):
    """Representation of an Ecoforest switch entity."""

    entity_description: EcoforestSwitchEntityDescription

    @property
    def is_on(self) -> bool:
        """Return the state of the ecoforest device."""
        return self.entity_description.value_fn(self.data)

    async def async_turn_on(self):
        """Turn on the ecoforest device."""
        await self.coordinator.api.turn(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self):
        """Turn off the ecoforest device."""
        await self.coordinator.api.turn(False)
        await self.coordinator.async_request_refresh()
