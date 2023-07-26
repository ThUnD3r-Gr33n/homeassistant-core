"""Base class for Owlet entities."""
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo

from .coordinator import OwletCoordinator
from .const import DOMAIN, MANUFACTURER


class OwletBaseEntity(CoordinatorEntity[OwletCoordinator]):
    """Base class for Owlet Sock entities."""
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: OwletCoordinator,
    ) -> None:
        """Initialize the base entity."""
        super().__init__(coordinator)
        self.sock = coordinator.sock

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info of the device"""
        return DeviceInfo(
            identifiers={(DOMAIN, self.sock.serial)},
            name="Owlet Baby Care Sock",
            manufacturer=MANUFACTURER,
            model=self.sock.model,
            sw_version=self.sock.sw_version,
            hw_version=self.sock.version,
        )

