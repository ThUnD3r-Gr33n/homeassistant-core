"""Code to handle a Livisi switches."""
from __future__ import annotations

from typing import Any

from collections.abc import Mapping
from aiolivisi.const import CAPABILITY_MAP

from homeassistant.helpers.entity import Entity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import LivisiDataUpdateCoordinator

from .const import DOMAIN, LIVISI_REACHABILITY_CHANGE


class LivisiEntity(CoordinatorEntity[LivisiDataUpdateCoordinator], Entity):
    """Represents a base livisi entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        config_entry: ConfigEntry,
        coordinator: LivisiDataUpdateCoordinator,
        device: dict[str, Any],
    ) -> None:
        """Initialize the common properties of a Livisi device."""
        self.config_details: Mapping[str, Any] = device["config"]

        self.aio_livisi = coordinator.aiolivisi
        self.config_entry = config_entry
        self.capabilities: Mapping[str, Any] = device[CAPABILITY_MAP]

        name = self.config_details["name"]
        unique_id = device["id"]
        manufacturer = device["manufacturer"]
        device_type = device["type"]

        room_id: str = device.get("location")
        room_name: str | None = None
        if room_id is not None:
            room_name = coordinator.rooms.get(room_id)

        self._attr_available = False
        self._attr_unique_id = unique_id
        self._attr_name = name

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, unique_id)},
            manufacturer=manufacturer,
            model=device_type,
            name=name,
            suggested_area=room_name,
            via_device=(DOMAIN, config_entry.entry_id),
        )
        super().__init__(coordinator)

    async def async_added_to_hass(self) -> None:
        """Register callback for reachability."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{LIVISI_REACHABILITY_CHANGE}_{self.unique_id}",
                self.update_reachability,
            )
        )

    @callback
    def update_reachability(self, is_reachable: bool) -> None:
        """Update the reachability of the device."""
        self._attr_available = is_reachable
        self.async_write_ha_state()
