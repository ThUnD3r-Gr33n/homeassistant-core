"""Base entity for the BSBLAN integration."""

from __future__ import annotations

from bsblan import BSBLAN, Device, Info, StaticState

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.helpers.device_registry import (
    CONNECTION_NETWORK_MAC,
    DeviceInfo,
    format_mac,
)
from homeassistant.helpers.entity import Entity

from .const import DOMAIN


class BSBLANEntity(Entity):
    """Defines a BSBLAN entity."""

    def __init__(
        self,
        client: BSBLAN,
        device: Device,
        info: Info,
        static: StaticState,
        entry: ConfigEntry,
    ) -> None:
        """Initialize an BSBLAN entity."""
        self.client = client

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, format_mac(device.MAC))},
            connections={(CONNECTION_NETWORK_MAC, format_mac(device.MAC))},
            name=device.name,
            manufacturer="BSBLAN Inc.",
            model=info.device_identification.value,
            sw_version=f"{device.version}",
            hw_version=getattr(info, "hardware_version", None),
            configuration_url=f"http://{entry.data[CONF_HOST]}",
        )
