"""The SensorPush Bluetooth integration."""
from __future__ import annotations

from bluetooth_sensor_state_data import SIGNAL_STRENGTH_KEY
from sensor_state_data import DeviceClass, DeviceKey, SensorUpdate
from sensor_state_data.data import (
    ATTR_HW_VERSION as SENSOR_HW_VERSION,
    ATTR_MANUFACTURER as SENSOR_MANUFACTURER,
    ATTR_MODEL as SENSOR_MODEL,
    ATTR_NAME as SENSOR_NAME,
    ATTR_SW_VERSION as SENSOR_SW_VERSION,
    SensorDeviceInfo,
)

from homeassistant.components.bluetooth.passive_update_coordinator import (
    PassiveBluetoothDataUpdate,
    PassiveBluetoothEntityKey,
)
from homeassistant.components.sensor import SensorDeviceClass, SensorEntityDescription
from homeassistant.const import (
    ATTR_HW_VERSION,
    ATTR_MANUFACTURER,
    ATTR_MODEL,
    ATTR_NAME,
    ATTR_SW_VERSION,
)
from homeassistant.helpers.entity import DeviceInfo

SENSOR_DEVICE_CLASS_TO_HASS = {
    DeviceClass.APPARENT_POWER: SensorDeviceClass.APPARENT_POWER,
    DeviceClass.BATTERY: SensorDeviceClass.BATTERY,
    DeviceClass.HUMIDITY: SensorDeviceClass.HUMIDITY,
    DeviceClass.ILLUMINANCE: SensorDeviceClass.ILLUMINANCE,
    DeviceClass.TEMPERATURE: SensorDeviceClass.TEMPERATURE,
    DeviceClass.PRESSURE: SensorDeviceClass.PRESSURE,
    DeviceClass.VOLTAGE: SensorDeviceClass.VOLTAGE,
    DeviceClass.CURRENT: SensorDeviceClass.CURRENT,
    DeviceClass.FREQUENCY: SensorDeviceClass.FREQUENCY,
    DeviceClass.POWER: SensorDeviceClass.POWER,
    DeviceClass.ENERGY: SensorDeviceClass.ENERGY,
    DeviceClass.POWER_FACTOR: SensorDeviceClass.POWER_FACTOR,
    DeviceClass.SIGNAL_STRENGTH: SensorDeviceClass.SIGNAL_STRENGTH,
}
SENSOR_DEVICE_INFO_TO_HASS = {
    SENSOR_NAME: ATTR_NAME,
    SENSOR_MANUFACTURER: ATTR_MANUFACTURER,
    SENSOR_SW_VERSION: ATTR_SW_VERSION,
    SENSOR_HW_VERSION: ATTR_HW_VERSION,
    SENSOR_MODEL: ATTR_MODEL,
}


def _device_key_to_bluetooth_entity_key(
    device_key: DeviceKey,
) -> PassiveBluetoothEntityKey:
    """Convert a device key to an entity key."""
    return PassiveBluetoothEntityKey(device_key.key, device_key.device_id)


def _sensor_device_class_to_hass(
    sensor_device_class: DeviceClass | None,
) -> SensorDeviceClass | None:
    """Convert a sensor device class to a sensor device class."""
    if sensor_device_class is None:
        return None
    return SENSOR_DEVICE_CLASS_TO_HASS.get(sensor_device_class)


def _sensor_device_info_to_hass(
    device_info: SensorDeviceInfo,
) -> DeviceInfo:
    """Convert a sensor device info to a sensor device info."""
    return DeviceInfo(  # type: ignore[misc]
        {
            SENSOR_DEVICE_INFO_TO_HASS[key]: value
            for key, value in device_info.items()
            if device_info.get(key) is not None
        }
    )


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
            _device_key_to_bluetooth_entity_key(device_key): SensorEntityDescription(
                key=f"{device_key.key}_{device_key.device_id}",
                name=sensor_description.name,
                device_class=_sensor_device_class_to_hass(
                    sensor_description.device_class
                ),
                native_unit_of_measurement=sensor_description.native_unit_of_measurement,
                entity_registry_enabled_default=device_key.key != SIGNAL_STRENGTH_KEY,
            )
            for device_key, sensor_description in sensor_update.entity_descriptions.items()
        },
        entity_data={
            _device_key_to_bluetooth_entity_key(device_key): sensor_values.native_value
            for device_key, sensor_values in sensor_update.entity_values.items()
        },
    )
