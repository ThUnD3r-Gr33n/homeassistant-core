"""Creates Homewizard Energy switch entities."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import (
    DEVICE_CLASS_OUTLET,
    DEVICE_CLASS_SWITCH,
    SwitchEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ENTITY_CATEGORY_CONFIG
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import COORDINATOR, DOMAIN, DeviceResponseEntry
from .coordinator import HWEnergyDeviceUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switches."""

    coordinator: HWEnergyDeviceUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        COORDINATOR
    ]

    if coordinator.api.state is not None:
        async_add_entities(
            [
                HWEnergyMainSwitchEntity(coordinator, entry),
                HWEnergySwitchLockEntity(coordinator, entry),
            ]
        )


class HWEnergySwitchEntity(CoordinatorEntity[DeviceResponseEntry], SwitchEntity):
    """Representation switchable entity."""

    def __init__(
        self,
        coordinator: HWEnergyDeviceUpdateCoordinator,
        entry: ConfigEntry,
        key: str,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self.entry = entry

        # Config attributes
        self.api = coordinator.api
        self._attr_unique_id = f"{entry.unique_id}_{key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return information about the device."""
        return {
            "name": self.entry.title,
            "manufacturer": "HomeWizard",
            "sw_version": self.data["device"].firmware_version,
            "model": self.data["device"].product_type,
            "identifiers": {(DOMAIN, self.data["device"].serial)},
        }

    @property
    def data(self) -> DeviceResponseEntry:
        """Return data from DataUpdateCoordinator."""
        return self.coordinator.data


class HWEnergyMainSwitchEntity(HWEnergySwitchEntity):
    """Representation of the main power switch."""

    def __init__(
        self, coordinator: HWEnergyDeviceUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, entry, "power_on")

        # Config attributes
        self._attr_name = entry.title
        self._attr_device_class = DEVICE_CLASS_OUTLET

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self.api.state.set(power_on=True)
        await self.coordinator.async_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self.api.state.set(power_on=False)
        await self.coordinator.async_refresh()

    @property
    def available(self) -> bool:
        """
        Return availability of power_on.

        This switch becomes unavailable when switch_lock is enabled.
        """
        return super().available and not self.api.state.switch_lock

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        return bool(self.api.state.power_on)


class HWEnergySwitchLockEntity(HWEnergySwitchEntity):
    """
    Representation of the switch-lock configuration.

    Switch-lock is a feature that forces the relay in 'on' state.
    It disables any method that can turn of the relay.
    """

    def __init__(
        self, coordinator: HWEnergyDeviceUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, entry, "switch_lock")

        # Config attributes
        self._attr_name = f"{entry.title} Switch Lock"
        self._attr_entity_category = ENTITY_CATEGORY_CONFIG
        self._attr_device_class = DEVICE_CLASS_SWITCH
        self._attr_icon = "mdi:lock"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn switch-lock on."""
        await self.api.state.set(switch_lock=True)
        await self.coordinator.async_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn switch-lock off."""
        await self.api.state.set(switch_lock=False)
        await self.coordinator.async_refresh()

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        return bool(self.api.state.switch_lock)
