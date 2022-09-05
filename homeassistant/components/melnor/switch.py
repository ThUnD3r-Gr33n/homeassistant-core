"""Switch support for Melnor Bluetooth water timer."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from melnor_bluetooth.device import Valve

from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .models import MelnorDataUpdateCoordinator, MelnorZoneEntity


@dataclass
class MelnorSwitchEntityDescriptionMixin:
    """Mixin for required keys."""

    on_fn: Callable[[Valve], Any]
    off_fn: Callable[[Valve], Any]
    state_fn: Callable[[Valve], Any]


@dataclass
class MelnorSwitchEntityDescription(
    SwitchEntityDescription, MelnorSwitchEntityDescriptionMixin
):
    """Describes Melnor switch entity."""


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_devices: AddEntitiesCallback,
) -> None:
    """Set up the switch platform."""
    entities: list[MelnorZoneSwitch] = []

    coordinator: MelnorDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    # This device may not have 4 valves total, but the library will only expose the right number of valves
    for i in range(1, 5):
        valve = coordinator.data[f"zone{i}"]
        if valve is not None:

            entities.append(
                MelnorZoneSwitch(
                    coordinator,
                    valve,
                    MelnorSwitchEntityDescription(
                        device_class=SwitchDeviceClass.SWITCH,
                        icon="mdi:sprinkler",
                        key="manual",
                        name="Manual",
                        on_fn=lambda valve: setattr(valve, "is_watering", True),
                        off_fn=lambda valve: setattr(valve, "is_watering", False),
                        state_fn=lambda valve: valve.is_watering,
                    ),
                )
            )

    async_add_devices(entities)


class MelnorZoneSwitch(MelnorZoneEntity, SwitchEntity):
    """A switch implementation for a melnor device."""

    entity_description: MelnorSwitchEntityDescription

    def __init__(
        self,
        coordinator: MelnorDataUpdateCoordinator,
        valve: Valve,
        entity_description: MelnorSwitchEntityDescription,
    ) -> None:
        """Initialize a switch for a melnor device."""
        super().__init__(coordinator, valve)

        self._attr_unique_id = f"{self._device.mac}-zone{valve.id}-manual"
        self.entity_description = entity_description

    @property
    def is_on(self) -> bool:
        """Return true if device is on."""
        return self.entity_description.state_fn(self._valve)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the device on."""
        self.entity_description.on_fn(self._valve)
        await self._device.push_state()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the device off."""
        self.entity_description.off_fn(self._valve)
        await self._device.push_state()
        self.async_write_ha_state()
