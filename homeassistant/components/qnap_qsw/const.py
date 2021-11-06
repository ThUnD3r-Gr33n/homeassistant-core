"""Constants for QNAP QSW integration."""
from __future__ import annotations

from typing import Final

from qnap_qsw.const import (
    DATA_CONDITION_ANOMALY,
    DATA_FAN1_SPEED,
    DATA_FAN2_SPEED,
    DATA_FIRMWARE_UPDATE,
    DATA_PORTS_ACTIVE,
    DATA_SYSTEM_MAC_ADDR,
    DATA_TEMPERATURE_CURRENT,
    DATA_UPTIME_DATETIME_ISOFORMAT,
)

from homeassistant.components.binary_sensor import (
    DEVICE_CLASS_PROBLEM,
    DEVICE_CLASS_UPDATE,
    BinarySensorEntityDescription,
)
from homeassistant.components.sensor import (
    STATE_CLASS_MEASUREMENT,
    SensorEntityDescription,
)
from homeassistant.const import (
    DEVICE_CLASS_TEMPERATURE,
    DEVICE_CLASS_TIMESTAMP,
    ENTITY_CATEGORY_DIAGNOSTIC,
    TEMP_CELSIUS,
)

ASYNC_TIMEOUT: Final = 30
DOMAIN: Final = "qnap_qsw"
MANUFACTURER: Final = "QNAP"
SERVICE_REBOOT: Final = "reboot"
UNIT_RPM: Final = "rpm"

BINARY_SENSOR_TYPES: Final[tuple[BinarySensorEntityDescription, ...]] = (
    BinarySensorEntityDescription(
        device_class=DEVICE_CLASS_PROBLEM,
        entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
        key=DATA_CONDITION_ANOMALY,
        name="Anomaly",
    ),
    BinarySensorEntityDescription(
        device_class=DEVICE_CLASS_UPDATE,
        entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
        key=DATA_FIRMWARE_UPDATE,
        name="Update",
    ),
)

SENSOR_TYPES: Final[tuple[SensorEntityDescription, ...]] = (
    SensorEntityDescription(
        entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
        key=DATA_FAN1_SPEED,
        icon="mdi:fan-speed-1",
        name="Fan 1 Speed",
        native_unit_of_measurement=UNIT_RPM,
        state_class=STATE_CLASS_MEASUREMENT,
    ),
    SensorEntityDescription(
        entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
        icon="mdi:fan-speed-2",
        key=DATA_FAN2_SPEED,
        name="Fan 2 Speed",
        native_unit_of_measurement=UNIT_RPM,
        state_class=STATE_CLASS_MEASUREMENT,
    ),
    SensorEntityDescription(
        entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
        icon="mdi:network",
        key=DATA_SYSTEM_MAC_ADDR,
        name="Mac address",
    ),
    SensorEntityDescription(
        entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
        icon="mdi:ethernet",
        key=DATA_PORTS_ACTIVE,
        name="Ports",
        state_class=STATE_CLASS_MEASUREMENT,
    ),
    SensorEntityDescription(
        device_class=DEVICE_CLASS_TEMPERATURE,
        entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
        key=DATA_TEMPERATURE_CURRENT,
        name="Temperature",
        native_unit_of_measurement=TEMP_CELSIUS,
        state_class=STATE_CLASS_MEASUREMENT,
    ),
    SensorEntityDescription(
        device_class=DEVICE_CLASS_TIMESTAMP,
        entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
        entity_registry_enabled_default=False,
        key=DATA_UPTIME_DATETIME_ISOFORMAT,
        name="Uptime",
    ),
)
