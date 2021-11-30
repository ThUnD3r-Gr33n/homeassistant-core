"""Base class for KNX devices."""
from __future__ import annotations

from xknx.devices import Device as XknxDevice

from homeassistant.helpers.entity import Entity


class KnxEntity(Entity):
    """Representation of a KNX entity."""

    _attr_should_poll = False

    def __init__(self, device: XknxDevice) -> None:
        """Set up device."""
        self._device = device

    @property
    def name(self) -> str:
        """Return the name of the KNX device."""
        return self._device.name

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._device.available

    async def async_update(self) -> None:
        """Request a state update from KNX bus."""
        await self._device.sync()

    async def after_update_callback(self, device: XknxDevice) -> None:
        """Call after device was updated."""
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Store register state change callback."""
        self._device.register_device_updated_cb(self.after_update_callback)

    async def async_will_remove_from_hass(self) -> None:
        """Disconnect device object when removed."""
        self._device.unregister_device_updated_cb(self.after_update_callback)
