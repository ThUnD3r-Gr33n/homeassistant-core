"""Support for a ScreenLogic Binary Sensor."""
from screenlogicpy.const import DATA as SL_DATA, DEVICE_TYPE, EQUIPMENT, ON_OFF

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ScreenlogicEntity
from .const import DOMAIN

SL_DEVICE_TYPE_TO_HA_DEVICE_CLASS = {DEVICE_TYPE.ALARM: BinarySensorDeviceClass.PROBLEM}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up entry."""
    entities = []
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    # Generic binary sensor
    entities.append(ScreenLogicBinarySensor(coordinator, "chem_alarm"))

    if (
        coordinator.data[SL_DATA.KEY_CONFIG]["equipment_flags"]
        & EQUIPMENT.FLAG_INTELLICHEM
    ):
        # IntelliChem alarm sensors
        entities.extend(
            [
                ScreenlogicChemistryAlarmBinarySensor(coordinator, chem_alarm)
                for chem_alarm in coordinator.data[SL_DATA.KEY_CHEMISTRY][
                    SL_DATA.KEY_ALERTS
                ]
            ]
        )

        # Intellichem notification sensors
        entities.extend(
            [
                ScreenlogicChemistryNotificationBinarySensor(coordinator, chem_notif)
                for chem_notif in coordinator.data[SL_DATA.KEY_CHEMISTRY][
                    SL_DATA.KEY_NOTIFICATIONS
                ]
            ]
        )

    if (
        coordinator.data[SL_DATA.KEY_CONFIG]["equipment_flags"]
        & EQUIPMENT.FLAG_CHLORINATOR
    ):
        # SCG binary sensor
        entities.append(ScreenlogicSCGBinarySensor(coordinator, "scg_status"))

    async_add_entities(entities)


class ScreenLogicBinarySensor(ScreenlogicEntity, BinarySensorEntity):
    """Representation of the basic ScreenLogic binary sensor entity."""

    _attr_has_entity_name = True

    @property
    def name(self):
        """Return the sensor name."""
        return self.sensor["name"]

    @property
    def device_class(self):
        """Return the device class."""
        device_type = self.sensor.get("device_type")
        return SL_DEVICE_TYPE_TO_HA_DEVICE_CLASS.get(device_type)

    @property
    def entity_category(self) -> EntityCategory:
        """Entity Category of the sensor."""
        return EntityCategory.DIAGNOSTIC

    @property
    def is_on(self) -> bool:
        """Determine if the sensor is on."""
        return self.sensor["value"] == ON_OFF.ON

    @property
    def sensor(self):
        """Shortcut to access the sensor data."""
        return self.coordinator.data[SL_DATA.KEY_SENSORS][self._data_key]


class ScreenlogicChemistryAlarmBinarySensor(ScreenLogicBinarySensor):
    """Representation of a ScreenLogic IntelliChem alarm binary sensor entity."""

    @property
    def sensor(self):
        """Shortcut to access the sensor data."""
        return self.coordinator.data[SL_DATA.KEY_CHEMISTRY][SL_DATA.KEY_ALERTS][
            self._data_key
        ]


class ScreenlogicChemistryNotificationBinarySensor(ScreenLogicBinarySensor):
    """Representation of a ScreenLogic IntelliChem notification binary sensor entity."""

    @property
    def sensor(self):
        """Shortcut to access the sensor data."""
        return self.coordinator.data[SL_DATA.KEY_CHEMISTRY][SL_DATA.KEY_NOTIFICATIONS][
            self._data_key
        ]


class ScreenlogicSCGBinarySensor(ScreenLogicBinarySensor):
    """Representation of a ScreenLogic SCG binary sensor entity."""

    @property
    def sensor(self):
        """Shortcut to access the sensor data."""
        return self.coordinator.data[SL_DATA.KEY_SCG][self._data_key]
