"""Coordinator for the SamsungTV integration."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .bridge import SamsungTVBridge
from .const import DOMAIN, LOGGER

SCAN_INTERVAL = 10


class SamsungTVDataUpdateCoordinator(DataUpdateCoordinator[None]):
    """Coordinator for the SamsungTV integration."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, bridge: SamsungTVBridge) -> None:
        """Initialize the coordinator."""
        self.bridge = bridge
        self.is_on: bool | None = False

        interval = timedelta(seconds=SCAN_INTERVAL)
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=interval,
        )

    async def _async_update_data(self) -> None:
        """Fetch data from SamsungTV bridge."""
        if self.bridge.auth_failed or self.hass.is_stopping:
            return
        old_state = self.is_on
        if self.bridge.power_off_in_progress:
            self.is_on = False
        else:
            self.is_on = await self.bridge.async_is_on()
        if self.is_on != old_state:
            LOGGER.debug("TV %s state updated to %s", self.bridge.host, self.is_on)
