"""Component to embed TP-Link smart home devices."""
from __future__ import annotations

from datetime import timedelta
import logging

from kasa import SmartDevice, SmartDeviceException

from homeassistant.const import ATTR_VOLTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    ATTR_CURRENT_A,
    ATTR_CURRENT_POWER_W,
    ATTR_TODAY_ENERGY_KWH,
    ATTR_TOTAL_ENERGY_KWH,
    CONF_EMETER_PARAMS,
)

_LOGGER = logging.getLogger(__name__)


class TPLinkDataUpdateCoordinator(DataUpdateCoordinator):
    """DataUpdateCoordinator to gather data for specific SmartPlug."""

    def __init__(
        self,
        hass: HomeAssistant,
        device: SmartDevice,
    ) -> None:
        """Initialize DataUpdateCoordinator to gather data for specific SmartPlug."""
        self.device = device
        self.update_children = True
        update_interval = timedelta(seconds=10)
        super().__init__(
            hass,
            _LOGGER,
            name=device.host,
            update_interval=update_interval,
        )

    async def _async_update_data(self) -> dict:
        """Fetch all device and sensor data from api."""
        try:
            await self.device.update(update_children=self.update_children)
        except SmartDeviceException as ex:
            raise UpdateFailed(ex) from ex
        else:
            self.update_children = True

        self.name = self.device.alias

        # Check if the device has emeter
        if not self.device.has_emeter:
            return {}

        if (emeter_today := self.device.emeter_today) is not None:
            consumption_today = emeter_today
        else:
            # today's consumption not available, when device was off all the day
            # bulb's do not report this information, so filter it out
            consumption_today = None if self.device.is_bulb else 0.0

        emeter_readings = self.device.emeter_realtime
        return {
            CONF_EMETER_PARAMS: {
                ATTR_CURRENT_POWER_W: emeter_readings.power,
                ATTR_TOTAL_ENERGY_KWH: emeter_readings.total,
                ATTR_VOLTAGE: emeter_readings.voltage,
                ATTR_CURRENT_A: emeter_readings.current,
                ATTR_TODAY_ENERGY_KWH: consumption_today,
            }
        }
