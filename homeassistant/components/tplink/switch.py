"""Support for TPLink HS100/HS110/HS200 smart switch."""
from __future__ import annotations

import asyncio
from collections.abc import Mapping
from contextlib import suppress
import logging
import time
from typing import Any

from pyHS100 import SmartDeviceException, SmartPlug

from homeassistant.components.switch import (
    ATTR_CURRENT_POWER_W,
    ATTR_TODAY_ENERGY_KWH,
    SwitchEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_VOLTAGE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import PlatformNotReady
import homeassistant.helpers.device_registry as dr
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import CONF_SWITCH, DOMAIN as TPLINK_DOMAIN
from .common import TPLinkEntity, add_available_devices

PARALLEL_UPDATES = 0

_LOGGER = logging.getLogger(__name__)

ATTR_TOTAL_ENERGY_KWH = "total_energy_kwh"
ATTR_CURRENT_A = "current_a"

MAX_ATTEMPTS = 300
SLEEP_TIME = 2


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switches."""
    entities = await hass.async_add_executor_job(
        add_available_devices, hass, CONF_SWITCH, SmartPlugSwitch
    )

    if entities:
        async_add_entities(entities, update_before_add=True)

    if hass.data[TPLINK_DOMAIN][f"{CONF_SWITCH}_remaining"]:
        raise PlatformNotReady


class SmartPlugSwitch(TPLinkEntity, SwitchEntity):
    """Representation of a TPLink Smart Plug switch."""

    def __init__(self, smartplug: SmartPlug) -> None:
        """Initialize the switch."""
        super().__init__(smartplug)
        self.smartplug = smartplug
        self._sysinfo = smartplug.sys_info
        self._is_available = False
        # Set up emeter cache
        self._emeter_params: dict[str, float] = {}

        self._host: str = self.smartplug.host
        self._mac: str = smartplug.mac
        self._model: str = self._sysinfo["model"]

        if self.smartplug.context is None:
            self._device_id = self._mac
            self._alias: str = self._sysinfo["alias"]
            self._state = self.smartplug.state == self.smartplug.SWITCH_STATE_ON
        else:
            children = self.smartplug.sys_info["children"]
            child = next(c for c in children if c["id"] == self.smartplug.context)
            self._device_id = self.smartplug.context
            self._alias = child["alias"]
            self._state = child["state"] == 1

    @property
    def unique_id(self) -> str | None:
        """Return a unique ID."""
        return self._device_id

    @property
    def name(self) -> str | None:
        """Return the name of the Smart Plug."""
        return self._alias

    @property
    def device_info(self) -> DeviceInfo:
        """Return information about the device."""
        return {
            "name": self._alias,
            "model": self._model,
            "manufacturer": "TP-Link",
            "connections": {(dr.CONNECTION_NETWORK_MAC, self._mac)},
            "sw_version": self._sysinfo["sw_ver"],
        }

    @property
    def available(self) -> bool:
        """Return if switch is available."""
        return self._is_available

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        return self._state

    def turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        self.smartplug.turn_on()

    def turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        self.smartplug.turn_off()

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return the state attributes of the device."""
        return self._emeter_params

    @property
    def _plug_from_context(self) -> Any:
        """Return the plug from the context."""
        children = self.smartplug.sys_info["children"]
        return next(c for c in children if c["id"] == self.smartplug.context)

    def update_state(self) -> None:
        """Update the TP-Link switch's state."""
        if self.smartplug.context is None:
            self._state = self.smartplug.state == self.smartplug.SWITCH_STATE_ON
        else:
            self._state = self._plug_from_context["state"] == 1

    def attempt_update(self, update_attempt: int) -> bool:
        """Attempt to get details from the TP-Link switch."""
        try:
            self.update_state()

            if self.smartplug.has_emeter:
                emeter_readings = self.smartplug.get_emeter_realtime()

                self._emeter_params[ATTR_CURRENT_POWER_W] = round(
                    float(emeter_readings["power"]), 2
                )
                self._emeter_params[ATTR_TOTAL_ENERGY_KWH] = round(
                    float(emeter_readings["total"]), 3
                )
                self._emeter_params[ATTR_VOLTAGE] = round(
                    float(emeter_readings["voltage"]), 1
                )
                self._emeter_params[ATTR_CURRENT_A] = round(
                    float(emeter_readings["current"]), 2
                )

                emeter_statics = self.smartplug.get_emeter_daily()
                with suppress(KeyError):  # Device returned no daily history
                    self._emeter_params[ATTR_TODAY_ENERGY_KWH] = round(
                        float(emeter_statics[int(time.strftime("%e"))]), 3
                    )
            return True
        except (SmartDeviceException, OSError) as ex:
            if update_attempt == 0:
                _LOGGER.debug(
                    "Retrying in %s seconds for %s|%s due to: %s",
                    SLEEP_TIME,
                    self._host,
                    self._alias,
                    ex,
                )
            return False

    async def async_update(self) -> None:
        """Update the TP-Link switch's state."""
        for update_attempt in range(MAX_ATTEMPTS):
            is_ready = await self.hass.async_add_executor_job(
                self.attempt_update, update_attempt
            )

            if is_ready:
                self._is_available = True
                if update_attempt > 0:
                    _LOGGER.debug(
                        "Device %s|%s responded after %s attempts",
                        self._host,
                        self._alias,
                        update_attempt,
                    )
                break
            await asyncio.sleep(SLEEP_TIME)

        else:
            if self._is_available:
                _LOGGER.warning(
                    "Could not read state for %s|%s", self.smartplug.host, self._alias
                )
            self._is_available = False
