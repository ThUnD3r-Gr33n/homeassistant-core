"""Representation of an SleepIQ device."""

from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers import device_registry

from .const import DOMAIN


class SleepNumberEntity(CoordinatorEntity, Entity):
    """Representation of an SleepIQ privacy mode."""

    def __init__(self, bed, status_coordinator):
        super().__init__(status_coordinator)
        self._bed = bed

    @property
    def device_info(self) -> DeviceInfo:
        """Return information about the device."""

        return DeviceInfo(
            identifiers={(DOMAIN, self._bed.id)},
            connections={(device_registry.CONNECTION_NETWORK_MAC, self._bed.mac_addr)},
            manufacturer="SleepNumber",
            name=self._bed.name,
            model=self._bed.model,
        )
