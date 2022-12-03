"""The PurpleAir integration."""
from __future__ import annotations

from aiopurpleair.models.sensors import SensorModel

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_LATITUDE, ATTR_LONGITUDE, Platform
from homeassistant.core import HomeAssistant
import homeassistant.helpers.device_registry as dr
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .config_flow import async_remove_sensor_device, async_untrack_sensor_index
from .const import CONF_LAST_UPDATE_REMOVAL, DOMAIN
from .coordinator import PurpleAirDataUpdateCoordinator

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up PurpleAir from a config entry."""
    coordinator = PurpleAirDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_handle_entry_update))

    return True


async def async_handle_entry_update(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle an options update."""
    if entry.options[CONF_LAST_UPDATE_REMOVAL]:
        # If the last options update was to remove a sensor, we return immediately and
        # don't reload (in order to avoid calling async_remove twice on the old device's
        # entities):
        return
    await hass.config_entries.async_reload(entry.entry_id)


async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: ConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    """Remove a config entry from a device."""
    removed_sensor_index = async_remove_sensor_device(
        hass, config_entry, device_entry.id
    )
    new_options = async_untrack_sensor_index(config_entry, removed_sensor_index)
    hass.config_entries.async_update_entry(config_entry, options=new_options)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class PurpleAirEntity(CoordinatorEntity[PurpleAirDataUpdateCoordinator]):
    """Define a base PurpleAir entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PurpleAirDataUpdateCoordinator,
        entry: ConfigEntry,
        sensor_index: int,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)

        self._sensor_index = sensor_index

        self._attr_device_info = DeviceInfo(
            configuration_url=self.coordinator.async_get_map_url(sensor_index),
            hw_version=self.sensor_data.hardware,
            identifiers={(DOMAIN, str(self._sensor_index))},
            manufacturer="PurpleAir, Inc.",
            model=self.sensor_data.model,
            name=self.sensor_data.name,
            sw_version=self.sensor_data.firmware_version,
        )
        self._attr_extra_state_attributes = {
            ATTR_LATITUDE: self.sensor_data.latitude,
            ATTR_LONGITUDE: self.sensor_data.longitude,
        }

    @property
    def sensor_data(self) -> SensorModel:
        """Define a property to get this entity's SensorModel object."""
        return self.coordinator.data.data[self._sensor_index]
