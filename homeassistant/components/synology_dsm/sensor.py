"""Support for Synology DSM sensors."""
from datetime import timedelta
import logging
from typing import Dict

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_DISKS,
    DATA_MEGABYTES,
    DATA_RATE_KILOBYTES_PER_SECOND,
    DATA_TERABYTES,
    PRECISION_TENTHS,
    TEMP_CELSIUS,
)
from homeassistant.helpers.temperature import display_temp
from homeassistant.helpers.typing import HomeAssistantType
from homeassistant.util.dt import utcnow

from . import SynoApi, SynologyDSMDeviceEntity, SynologyDSMEntity
from .const import (
    CONF_VOLUMES,
    DOMAIN,
    INFORMATION_SENSORS,
    STORAGE_DISK_SENSORS,
    STORAGE_VOL_SENSORS,
    SYNO_API,
    TEMP_SENSORS_KEYS,
    UTILISATION_SENSORS,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistantType, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up the Synology NAS Sensor."""

    api = hass.data[DOMAIN][entry.unique_id][SYNO_API]

    entities = [
        SynoDSMUtilSensor(api, sensor_type, UTILISATION_SENSORS[sensor_type])
        for sensor_type in UTILISATION_SENSORS
    ]

    # Handle all volumes
    if api.storage.volumes_ids:
        for volume in entry.data.get(CONF_VOLUMES, api.storage.volumes_ids):
            entities += [
                SynoDSMStorageSensor(
                    api, sensor_type, STORAGE_VOL_SENSORS[sensor_type], volume
                )
                for sensor_type in STORAGE_VOL_SENSORS
            ]

    # Handle all disks
    if api.storage.disks_ids:
        for disk in entry.data.get(CONF_DISKS, api.storage.disks_ids):
            entities += [
                SynoDSMStorageSensor(
                    api, sensor_type, STORAGE_DISK_SENSORS[sensor_type], disk
                )
                for sensor_type in STORAGE_DISK_SENSORS
            ]

    entities += [
        SynoDSMInfoSensor(api, sensor_type, INFORMATION_SENSORS[sensor_type])
        for sensor_type in INFORMATION_SENSORS
    ]

    _LOGGER.debug("async_setup_entry - %s", entities)
    async_add_entities(entities)


class SynoDSMUtilSensor(SynologyDSMEntity):
    """Representation a Synology Utilisation sensor."""

    @property
    def state(self):
        """Return the state."""
        attr = getattr(self._api.utilisation, self.entity_type)
        if callable(attr):
            attr = attr()
        if attr is None:
            return None

        # Data (RAM)
        if self._unit == DATA_MEGABYTES:
            return round(attr / 1024.0 ** 2, 1)

        # Network
        if self._unit == DATA_RATE_KILOBYTES_PER_SECOND:
            return round(attr / 1024.0, 1)

        return attr

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return bool(self._api.utilisation)


class SynoDSMStorageSensor(SynologyDSMDeviceEntity):
    """Representation a Synology Storage sensor."""

    @property
    def state(self):
        """Return the state."""
        attr = getattr(self._api.storage, self.entity_type)(self._device_id)
        if attr is None:
            return None

        # Data (disk space)
        if self._unit == DATA_TERABYTES:
            return round(attr / 1024.0 ** 4, 2)

        # Temperature
        if self.entity_type in TEMP_SENSORS_KEYS:
            return display_temp(self.hass, attr, TEMP_CELSIUS, PRECISION_TENTHS)

        return attr


class SynoDSMInfoSensor(SynologyDSMEntity):
    """Representation a Synology information sensor."""

    def __init__(self, api: SynoApi, entity_type: str, entity_info: Dict[str, str]):
        """Initialize the Synology SynoDSMInfoSensor entity."""
        super().__init__(api, entity_type, entity_info)
        self._previous_uptime = None
        self._last_boot = None

    @property
    def state(self):
        """Return the state."""
        attr = getattr(self._api.information, self.entity_type)
        if attr is None:
            return None

        # Temperature
        if self.entity_type in TEMP_SENSORS_KEYS:
            return display_temp(self.hass, attr, TEMP_CELSIUS, PRECISION_TENTHS)

        if self.entity_type == "uptime":
            # reboot happened or entity creation
            if self._previous_uptime is None or self._previous_uptime > attr:
                last_boot = utcnow() - timedelta(seconds=attr)
                self._last_boot = last_boot.replace(microsecond=0).isoformat()

            self._previous_uptime = attr
            return self._last_boot
        return attr
