"""The Flexit Nordic (BACnet) integration."""
from collections.abc import Callable
from dataclasses import dataclass
import logging

from flexit_bacnet import FlexitBACnet

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import (
    DOMAIN as SENSOR_DOMAIN,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
    StateType,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    REVOLUTIONS_PER_MINUTE,
    EntityCategory,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

ENTITY_ID_SENSOR_FORMAT = (
    SENSOR_DOMAIN + ".{}_{}"
)  # should use f"{some_value} {some_other_value}"


@dataclass(kw_only=True, frozen=True)
class FlexitSensorEntityDescription(SensorEntityDescription):
    """Describes a Flexit sensor entity."""

    value_fn: Callable[[FlexitBACnet], float]


SENSOR_TYPES: tuple[FlexitSensorEntityDescription, ...] = (
    FlexitSensorEntityDescription(
        key="outside_air_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        translation_key="outside_air_temperature",
        # icon="mdi:thermometer",
        value_fn=lambda data: data.outside_air_temperature,
        # unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    FlexitSensorEntityDescription(
        key="supply_air_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        translation_key="supply_air_temperature",
        # icon="mdi:thermometer",
        value_fn=lambda data: data.supply_air_temperature,
        # unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    FlexitSensorEntityDescription(
        key="exhaust_air_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        translation_key="exhaust_air_temperaturee",
        # icon="mdi:thermometer",
        value_fn=lambda data: data.exhaust_air_temperature,
        # unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    FlexitSensorEntityDescription(
        key="extract_air_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        translation_key="extract_air_temperature",
        # icon="mdi:thermometer",
        value_fn=lambda data: data.extract_air_temperature,
        # unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    FlexitSensorEntityDescription(
        key="room_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        translation_key="room_temperature",
        # icon="mdi:thermometer",
        value_fn=lambda data: data.room_temperature,
        # unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    FlexitSensorEntityDescription(
        key="room_1_humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        translation_key="room_1_humidity",
        # icon="mdi:thermometer",
        value_fn=lambda data: data.room_1_humidity,
        # unit_of_measurement=UnitOfTemperature.HUMIDITY
    ),
    FlexitSensorEntityDescription(
        key="room_2_humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        translation_key="room_2_humidity",
        # icon="mdi:thermometer",
        value_fn=lambda data: data.room_2_humidity,
        # unit_of_measurement=UnitOfTemperature.CELSIUS
    ),
    FlexitSensorEntityDescription(
        key="room_3_humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        translation_key="room_3_humidity",
        # icon="mdi:thermometer",
        value_fn=lambda data: data.room_3_humidity,
        # unit_of_measurement=UnitOfTemperature.CELSIUS
    ),
    FlexitSensorEntityDescription(
        key="comfort_button",
        device_class=BinarySensorDeviceClass.RUNNING,
        # native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        translation_key="comfort_button",
        # icon="mdi:thermometer",
        value_fn=lambda data: data.comfort_button,
        # unit_of_measurement=UnitOfTemperature.CELSIUS
    ),
    FlexitSensorEntityDescription(
        key="fireplace_ventilation_remaining_duration",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        translation_key="fireplace_ventilation_remaining_duration",
        # icon="mdi:thermometer",
        value_fn=lambda data: data.fireplace_ventilation_remaining_duration,
        # unit_of_measurement=UnitOfTime.MINUTES,
    ),
    FlexitSensorEntityDescription(
        key="rapid_ventilation_remaining_duration",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        translation_key="rapid_ventilation_remaining_duration",
        # icon="mdi:thermometer",
        value_fn=lambda data: data.rapid_ventilation_remaining_duration,
        # unit_of_measurement=UnitOfTime.MINUTES,
    ),
    FlexitSensorEntityDescription(
        key="supply_air_fan_control_signal",
        device_class=SensorDeviceClass.POWER_FACTOR,
        # native_unit_of_measurement=PERCENTAGE,
        translation_key="supply_air_fan_control_signal",
        # icon="mdi:thermometer",
        value_fn=lambda data: data.supply_air_fan_control_signal,
        # unit_of_measurement=PERCENTAGE,
    ),
    # What sensor type should be used for this sensor?
    FlexitSensorEntityDescription(
        key="supply_air_fan_rpm",
        device_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=REVOLUTIONS_PER_MINUTE,
        translation_key="supply_air_fan_rpm",
        # icon="mdi:thermometer",
        value_fn=lambda data: data.supply_air_fan_rpm,
        # unit_of_measurement=REVOLUTIONS_PER_MINUTE,
    ),
    FlexitSensorEntityDescription(
        key="exhaust_air_fan_control_signal",
        device_class=SensorDeviceClass.POWER_FACTOR,
        # native_unit_of_measurement=PERCENTAGE,
        translation_key="exhaust_air_fan_control_signal",
        # icon="mdi:gauge",
        value_fn=lambda data: data.exhaust_air_fan_control_signal,
        # unit_of_measurement=PERCENTAGE,
    ),
    FlexitSensorEntityDescription(
        key="exhaust_air_fan_rpm",
        device_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=REVOLUTIONS_PER_MINUTE,
        translation_key="exhaust_air_fan_rpm",
        icon="mdi:thermometer",
        value_fn=lambda data: data.exhaust_air_fan_rpm,
        # unit_of_measurement=REVOLUTIONS_PER_MINUTE,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    FlexitSensorEntityDescription(
        key="electric_heater",
        device_class=BinarySensorDeviceClass.RUNNING,
        # native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        translation_key="electric_heater",
        # icon="mdi:thermometer",
        value_fn=lambda data: data.electric_heater,
        # unit_of_measurement=UnitOfTemperature.CELSIUS
    ),
    FlexitSensorEntityDescription(
        key="electric_heater_nominal_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        translation_key="electric_heater_nominal_power",
        # icon="mdi:thermometer",
        value_fn=lambda data: data.electric_heater_nominal_power,
        # unit_of_measurement=UnitOfPower.KILO_WATT,
    ),
    FlexitSensorEntityDescription(
        key="electric_heater_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        translation_key="electric_heater_power",
        # icon="mdi:thermometer",
        value_fn=lambda data: data.electric_heater_power,
        # unit_of_measurement=UnitOfPower.KILO_WATT,
    ),
    FlexitSensorEntityDescription(
        key="air_filter_operating_time",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
        translation_key="air_filter_operating_time",
        # icon="mdi:thermometer",
        value_fn=lambda data: data.air_filter_operating_time,
        # unit_of_measurement=UnitOfTime.HOURS,
    ),
    FlexitSensorEntityDescription(
        key="heat_exchanger_efficiency",
        device_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        translation_key="heat_exchanger_efficiency",
        icon="mdi:gauge",
        value_fn=lambda data: data.heat_exchanger_efficiency,
        # unit_of_measurement=PERCENTAGE,
        entity_category=EntityCategory.DIAGNOSTIC,  # Is this correct?
    ),
    FlexitSensorEntityDescription(
        key="heat_exchanger_speed",
        device_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        translation_key="heat_exchanger_speed",
        icon="mdi:gauge",
        value_fn=lambda data: data.heat_exchanger_speed,
        unit_of_measurement=PERCENTAGE,
        entity_category=EntityCategory.DIAGNOSTIC,  # Is this correct?
    ),
    FlexitSensorEntityDescription(
        key="air_filter_polluted",
        device_class=BinarySensorDeviceClass.RUNNING,  # What should be used for this sensor?
        # native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        translation_key="air_filter_polluted",
        # icon="mdi:thermometer",
        value_fn=lambda data: data.air_filter_polluted,
        # unit_of_measurement=UnitOfTemperature.CELSIUS
    ),
)

# These attributes are already in the climate entity
#   operation_mode
#   ventilation_mode

# These attributes exist in flexit_bacnet but seem too redundant as sensors since they almost never change
#   air_temp_setpoint_away
#   air_temp_setpoint_home
#   fan_setpoint_supply_air_home
#   fan_setpoint_extract_air_home
#   fan_setpoint_supply_air_high
#   fan_setpoint_extract_air_high
#   fan_setpoint_supply_air_away
#   fan_setpoint_extract_air_away
#   fan_setpoint_supply_air_cooker
#   fan_setpoint_extract_air_cooker
#   fan_setpoint_supply_air_fire
#   fan_setpoint_extract_air_fire
#   air_filter_exchange_interval


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Flexit (bacnet) sensor from a config entry."""

    _LOGGER.debug("Setting up Flexit (bacnet) sensor from a config entry")
    entity = hass.data[DOMAIN][config_entry.entry_id]

    async_add_entities(
        [
            FlexitSensor(entity, description, config_entry.entry_id)
            for description in SENSOR_TYPES
        ]
    )


class FlexitSensor(SensorEntity):
    """Representation of a Flexit Sensor."""

    # Should it have a name?
    # _attr_name = None

    # Should it have a entity_name?
    # _attr_has_entity_name = True

    # Should it be polled?
    # _attr_should_poll = False

    entity_description: FlexitSensorEntityDescription

    def __init__(
        self,
        device: FlexitBACnet,
        entity_description: FlexitSensorEntityDescription,
        entry_id: str,
    ) -> None:
        """Initialize Flexit (bacnet) sensor."""
        self.entity_description = entity_description
        self.entity_id = ENTITY_ID_SENSOR_FORMAT.format(
            device.device_name, entity_description.key
        )
        self._attr_unique_id = f"{entry_id}-{entity_description.key}"
        self._device = device
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name=device.device_name,
            manufacturer="Flexit",
            model="Nordic",
            serial_number=device.serial_number,
        )

    async def async_update(self) -> None:
        """Refresh unit state."""
        await self._device.update()

    @property
    def native_value(self) -> StateType:
        """Return value of sensor."""
        return self.entity_description.value_fn(self._device)
