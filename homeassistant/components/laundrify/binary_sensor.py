"""Platform for binary sensor integration."""
from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import LaundrifyUpdateCoordinator
from .model import LaundrifyDevice

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up sensors from a config entry created in the integrations UI."""

    coordinator: LaundrifyUpdateCoordinator = hass.data[DOMAIN][config.entry_id][
        "coordinator"
    ]

    async_add_entities(
        LaundrifyPowerPlug(coordinator, device) for device in coordinator.data.values()
    )


class LaundrifyPowerPlug(
    CoordinatorEntity[LaundrifyUpdateCoordinator], BinarySensorEntity
):
    """Representation of a laundrify Power Plug."""

    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_icon = "mdi:washing-machine"
    _attr_unique_id: str
    _attr_has_entity_name = True
    _attr_name = None

    def __init__(
        self, coordinator: LaundrifyUpdateCoordinator, device: LaundrifyDevice
    ) -> None:
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator)
        self._device = device
        self._attr_unique_id = device["_id"]

    @property
    def device_info(self) -> DeviceInfo:
        """Configure the Device of this Entity."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._device["_id"])},
            name=self._device["name"],
            manufacturer=MANUFACTURER,
            model=MODEL,
            sw_version=self._device["firmwareVersion"],
        )

    @property
    def available(self) -> bool:
        """Check if the device is available."""
        return (
            self._attr_unique_id in self.coordinator.data
            and self.coordinator.last_update_success
        )

    @property
    def is_on(self) -> bool:
        """Return entity state."""
        return self._device["status"] == "ON"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._device = self.coordinator.data[self._attr_unique_id]
        super()._handle_coordinator_update()
