"""Base Entity for Sonarr."""
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo, EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SonarrDataUpdateCoordinator


class SonarrEntity(CoordinatorEntity[SonarrDataUpdateCoordinator]):
    """Defines a base Sonarr entity."""

    def __init__(
        self,
        coordinator: SonarrDataUpdateCoordinator,
        description: EntityDescription,
    ) -> None:
        """Initialize the Sonarr entity."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information about the application."""
        return DeviceInfo(
            configuration_url=self.coordinator.host_configuration.base_url,
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, self.coordinator.config_entry.entry_id)},
            manufacturer="Sonarr",
            name="Activity Sensor",
            sw_version=self.coordinator.system_version,
        )
