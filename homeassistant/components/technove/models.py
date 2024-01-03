"""Models for TechnoVE."""
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import TechnoVEDataUpdateCoordinator


class TechnoVEEntity(CoordinatorEntity[TechnoVEDataUpdateCoordinator]):
    """Defines a base TechnoVE entity."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: TechnoVEDataUpdateCoordinator, key: str) -> None:
        """Initialize a base TechnoVE entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.data.info.mac_address}_{key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return information about this TechnoVE station."""
        info = self.coordinator.data.info
        return DeviceInfo(
            connections={(CONNECTION_NETWORK_MAC,info.mac_address)},
            identifiers={(DOMAIN,info.mac_address)},
            name=info.name,
            manufacturer="TechnoVE",
            model=f"TechnoVE i{info.max_station_current}",
            sw_version=info.version,
        )
