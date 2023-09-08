"""Vodafone Station sensors."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Final

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfDataRate
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util.dt import utcnow

from .const import _LOGGER, DOMAIN
from .coordinator import VodafoneStationRouter


@dataclass
class VodafoneStationBaseEntityDescription:
    """Vodafone Station entity base description."""

    value: Callable[[Any], Any] = lambda val: val
    is_suitable: Callable[[dict], bool] = lambda val: True


@dataclass
class VodafoneStationEntityDescription(
    VodafoneStationBaseEntityDescription, SensorEntityDescription
):
    """Vodafone Station entity description."""


def _calculate_uptime(uptime: str) -> datetime:
    """Calculate device uptime."""
    d = int(uptime.split(":")[0])
    h = int(uptime.split(":")[1])
    m = int(uptime.split(":")[2])

    return utcnow() - timedelta(days=d, hours=h, minutes=m)


SENSOR_TYPES: Final = (
    VodafoneStationEntityDescription(
        key="wan_ip4_addr",
        translation_key="external_ipv4",
        icon="mdi:earth",
        is_suitable=lambda info: info["wan_ip4_addr"] != "",
    ),
    VodafoneStationEntityDescription(
        key="wan_ip6_addr",
        translation_key="external_ipv6",
        icon="mdi:earth",
        is_suitable=lambda info: info["wan_ip6_addr"] != "",
    ),
    VodafoneStationEntityDescription(
        key="down_str",
        translation_key="down_stream",
        device_class=SensorDeviceClass.DATA_RATE,
        native_unit_of_measurement=UnitOfDataRate.KILOBYTES_PER_SECOND,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    VodafoneStationEntityDescription(
        key="up_str",
        translation_key="up_stream",
        device_class=SensorDeviceClass.DATA_RATE,
        native_unit_of_measurement=UnitOfDataRate.KILOBYTES_PER_SECOND,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    VodafoneStationEntityDescription(
        key="fw_version",
        translation_key="fw_version",
        icon="mdi:new-box",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    VodafoneStationEntityDescription(
        key="phone_num1",
        translation_key="phone_num1",
        icon="mdi:phone",
        is_suitable=lambda info: info["phone_unavailable1"] == "0",
    ),
    VodafoneStationEntityDescription(
        key="phone_num2",
        translation_key="phone_num2",
        icon="mdi:phone",
        is_suitable=lambda info: info["phone_unavailable2"] == "0",
    ),
    VodafoneStationEntityDescription(
        key="sys_uptime",
        translation_key="sys_uptime",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value=_calculate_uptime,
    ),
    VodafoneStationEntityDescription(
        key="sys_cpu_usage",
        translation_key="sys_cpu_usage",
        icon="mdi:chip",
        native_unit_of_measurement=PERCENTAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
        value=lambda value: float(value[:-1]),
    ),
    VodafoneStationEntityDescription(
        key="sys_memory_usage",
        translation_key="sys_memory_usage",
        icon="mdi:memory",
        native_unit_of_measurement=PERCENTAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
        value=lambda value: float(value[:-1]),
    ),
    VodafoneStationEntityDescription(
        key="sys_reboot_cause",
        translation_key="sys_reboot_cause",
        icon="mdi:restart-alert",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up entry."""
    _LOGGER.debug("Setting up Vodafone Station sensors")

    coordinator: VodafoneStationRouter = hass.data[DOMAIN][entry.entry_id]

    sensors_data = coordinator.data.sensors

    entities = (
        VodafoneStationSensorEntity(coordinator, sensor_descr)
        for sensor_descr in SENSOR_TYPES
        if sensor_descr.key in sensors_data and sensor_descr.is_suitable(sensors_data)
    )

    async_add_entities(entities, True)


class VodafoneStationSensorEntity(CoordinatorEntity, SensorEntity):
    """Representation of a Vodafone Station sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: VodafoneStationRouter,
        description: VodafoneStationEntityDescription,
    ) -> None:
        """Initialize a Vodafone Station sensor."""
        super().__init__(coordinator)

        sensors_data = coordinator.data.sensors
        serial_num = sensors_data["sys_serial_number"]
        self.entity_description = description

        self._attr_device_info = DeviceInfo(
            configuration_url=coordinator.api.base_url,
            identifiers={(DOMAIN, serial_num)},
            name=f"Vodafone Station ({serial_num})",
            manufacturer="Vodafone",
            model=sensors_data["sys_model_name"],
            hw_version=sensors_data["sys_hardware_version"],
            sw_version=sensors_data["sys_firmware_version"],
        )
        self._attr_native_value = self.entity_description.value(
            sensors_data.get(self.entity_description.key)
        )
        self._attr_unique_id = f"{serial_num}_{description.key}"
