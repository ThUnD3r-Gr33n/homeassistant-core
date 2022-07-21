"""Support for sensorpush ble sensors."""
from __future__ import annotations

from sensorpush_ble import (
    ATTR_MANUFACTURER as SENSOR_MANUFACTURER,
    ATTR_MODEL as SENSOR_MODEL,
    ATTR_NAME as SENSOR_NAME,
    DeviceClass,
    DeviceKey,
    SensorDeviceInfo,
    SensorUpdate,
)

from homeassistant import config_entries
from homeassistant.components.bluetooth.passive_update_coordinator import (
    PassiveBluetoothCoordinatorEntity,
    PassiveBluetoothDataUpdate,
    PassiveBluetoothEntityKey,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    ATTR_MANUFACTURER,
    ATTR_MODEL,
    ATTR_NAME,
    PERCENTAGE,
    PRESSURE_PA,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    TEMP_CELSIUS,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SensorPushDataUpdateCoordinator
from .const import DOMAIN

SENSOR_DESCRIPTIONS = {
    (DeviceClass.TEMPERATURE, "°C"): SensorEntityDescription(
        key=f"{DeviceClass.TEMPERATURE}_°C",
        name=DeviceClass.TEMPERATURE.name.replace("_", " ").title(),
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=TEMP_CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    (DeviceClass.HUMIDITY, "%"): SensorEntityDescription(
        key=f"{DeviceClass.HUMIDITY}_%",
        name=DeviceClass.HUMIDITY.name.replace("_", " ").title(),
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    (DeviceClass.PRESSURE, "Pa"): SensorEntityDescription(
        key=f"{DeviceClass.PRESSURE}_Pa",
        name=DeviceClass.PRESSURE.name.replace("_", " ").title(),
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement=PRESSURE_PA,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    (DeviceClass.SIGNAL_STRENGTH, "dBm"): SensorEntityDescription(
        key=f"{DeviceClass.SIGNAL_STRENGTH}_dBm",
        name=DeviceClass.SIGNAL_STRENGTH.name.replace("_", " ").title(),
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
}


def _device_key_to_bluetooth_entity_key(
    device_key: DeviceKey,
) -> PassiveBluetoothEntityKey:
    """Convert a device key to an entity key."""
    return PassiveBluetoothEntityKey(device_key.key, device_key.device_id)


def _sensor_device_info_to_hass(
    sensor_device_info: SensorDeviceInfo,
) -> DeviceInfo:
    """Convert a sensor device info to a sensor device info."""
    hass_device_info = DeviceInfo({})
    if sensor_device_info.get(SENSOR_NAME) is not None:
        hass_device_info[ATTR_NAME] = sensor_device_info[SENSOR_NAME]
    if sensor_device_info.get(SENSOR_MANUFACTURER) is not None:
        hass_device_info[ATTR_MANUFACTURER] = sensor_device_info[SENSOR_MANUFACTURER]
    if sensor_device_info.get(SENSOR_MODEL) is not None:
        hass_device_info[ATTR_MODEL] = sensor_device_info[SENSOR_MODEL]
    return hass_device_info


def sensor_update_to_bluetooth_data_update(
    sensor_update: SensorUpdate,
) -> PassiveBluetoothDataUpdate:
    """Convert a sensor update to a bluetooth data update."""
    return PassiveBluetoothDataUpdate(
        devices={
            device_id: _sensor_device_info_to_hass(device_info)
            for device_id, device_info in sensor_update.devices.items()
        },
        entity_descriptions={
            _device_key_to_bluetooth_entity_key(device_key): SENSOR_DESCRIPTIONS[
                (description.device_class, description.native_unit_of_measurement)
            ]
            for device_key, description in sensor_update.entity_descriptions.items()
            if description.device_class and description.native_unit_of_measurement
        },
        entity_data={
            _device_key_to_bluetooth_entity_key(device_key): sensor_values.native_value
            for device_key, sensor_values in sensor_update.entity_values.items()
        },
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the SensorPush BLE sensors."""
    coordinator: SensorPushDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    entry.async_on_unload(
        coordinator.async_add_entities_listener(
            SensorPushBluetoothSensorEntity, async_add_entities
        )
    )


class SensorPushBluetoothSensorEntity(
    PassiveBluetoothCoordinatorEntity[SensorPushDataUpdateCoordinator], SensorEntity
):
    """Representation of a sensorpush ble sensor."""

    @property
    def native_value(self) -> int | float | None:
        """Return the native value."""
        return self.coordinator.entity_data.get(self.entity_key)
