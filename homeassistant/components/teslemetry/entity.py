"""Teslemetry parent entity class."""

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MODELS
from .coordinator import TeslemetryVehicleDataCoordinator
from .models import TeslemetryVehicleData


class TeslemetryVehicleEntity(CoordinatorEntity[TeslemetryVehicleDataCoordinator]):
    """Parent class for Teslemetry Entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        vehicle: TeslemetryVehicleData,
        key: str,
    ) -> None:
        """Initialize common aspects of a Teslemetry entity."""
        super().__init__(vehicle.coordinator)
        self.key = key
        self.api = vehicle.api

        car_type = self.coordinator.data["vehicle_config_car_type"]

        self._attr_translation_key = self.key
        self._attr_unique_id = f"{self.api.vin}-{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.api.vin)},
            manufacturer="Tesla",
            configuration_url="https://teslemetry.com/console",
            name=self.coordinator.data["vehicle_state_vehicle_name"],
            model=MODELS.get(car_type, car_type),
            sw_version=self.coordinator.data["vehicle_state_car_version"].split(" ")[0],
            hw_version=self.coordinator.data["vehicle_config_driver_assist"],
            serial_number=self.api.vin,
        )

    def get(self, key: str | None = None, default: Any | None = None) -> Any:
        """Return a specific value from coordinator data."""
        return self.coordinator.data.get(key or self.key, default)

    def set(self, *args: Any) -> None:
        """Set a value in coordinator data."""
        for key, value in args:
            self.coordinator.data[key] = value
        self.async_write_ha_state()
