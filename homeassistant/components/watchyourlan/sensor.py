"""Support for the WatchYourLAN service."""

from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import WatchYourLANUpdateCoordinator

# Define entity descriptions for each sensor type
ENTITY_DESCRIPTIONS = [
    SensorEntityDescription(
        key="online_status",
        name="Online Status",
        icon="mdi:lan-connect",
    ),
    SensorEntityDescription(
        key="ip_address",
        name="IP Address",
        icon="mdi:ip-network",
    ),
    SensorEntityDescription(
        key="mac_address",
        name="MAC Address",
        icon="mdi:lan",
    ),
    SensorEntityDescription(
        key="iface",
        name="Network Interface",
        icon="mdi:ethernet",
    ),
]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the WatchYourLAN sensors."""
    coordinator: WatchYourLANUpdateCoordinator = entry.runtime_data

    entities: list[SensorEntity] = [WatchYourLANDeviceCountSensor(coordinator)] + [
        WatchYourLANGenericSensor(coordinator, device, description)
        for device in coordinator.data
        for description in ENTITY_DESCRIPTIONS
    ]

    async_add_entities(entities)


class WatchYourLANGenericSensor(
    CoordinatorEntity[WatchYourLANUpdateCoordinator], SensorEntity
):
    """Generic WatchYourLAN sensor for different data points."""

    def __init__(
        self,
        coordinator: WatchYourLANUpdateCoordinator,
        device: dict[str, Any],
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.device = device
        self.entity_description = description
        self._attr_unique_id = f"{self.device.get('ID')}_{description.key}"

    @property
    def native_value(self) -> str:
        """Return the native value of the sensor based on its description."""
        if self.entity_description.key == "online_status":
            return "Online" if self.device.get("Now", 0) == 1 else "Offline"
        return self.device.get(self._get_device_field_for_key(), "Unknown")

    def _get_device_field_for_key(self) -> str:
        """Map description key to the appropriate device field."""
        field_mapping = {
            "online_status": "Now",
            "ip_address": "IP",
            "mac_address": "Mac",
            "iface": "Iface",
        }
        return field_mapping.get(self.entity_description.key, "")

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for the sensor."""
        return DeviceInfo(
            connections={
                (CONNECTION_NETWORK_MAC, self.device.get("Mac", "00:00:00:00:00:00"))
            },
            name=self.device.get("Name")
            or f"WatchYourLAN {self.device.get('ID', 'Unknown')}",
            manufacturer=self.device.get("Hw", "Unknown Manufacturer"),
            model="WatchYourLAN Device",
        )


class WatchYourLANDeviceCountSensor(
    CoordinatorEntity[WatchYourLANUpdateCoordinator], SensorEntity
):
    """Sensor that tracks the total number of devices."""

    def __init__(self, coordinator: WatchYourLANUpdateCoordinator) -> None:
        """Initialize the device count sensor."""
        super().__init__(coordinator)

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return "WatchYourLAN Total Devices"

    @property
    def native_value(self) -> int:
        """Return the state of the sensor."""
        return (
            len(self.coordinator.data) if isinstance(self.coordinator.data, list) else 0
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional details such as known/unknown devices and devices per network interface."""
        if isinstance(self.coordinator.data, list):
            online_count = sum(
                1 for device in self.coordinator.data if device.get("Now") == 1
            )
            offline_count = len(self.coordinator.data) - online_count
            known_count = sum(
                1 for device in self.coordinator.data if device.get("Known") == 1
            )
            unknown_count = len(self.coordinator.data) - known_count

            iface_counts: dict[str, int] = {}
            for device in self.coordinator.data:
                iface = device.get("Iface", "Unknown")
                iface_counts[iface] = iface_counts.get(iface, 0) + 1

            return {
                "online": online_count,
                "offline": offline_count,
                "total": len(self.coordinator.data),
                "known": known_count,
                "unknown": unknown_count,
                "devices_per_iface": iface_counts,
            }
        return {}
