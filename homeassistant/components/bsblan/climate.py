"""BSBLAN platform to control a compatible Climate Device."""
from __future__ import annotations

from typing import Any

from bsblan import BSBLAN, BSBLANError, Device, Info, State

from homeassistant.components.climate import (
    ATTR_HVAC_MODE,
    ATTR_PRESET_MODE,
    PRESET_ECO,
    PRESET_NONE,
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, TEMP_CELSIUS, TEMP_FAHRENHEIT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from . import HomeAssistantBSBLANData
from .const import ATTR_TARGET_TEMPERATURE, DOMAIN, LOGGER
from .entity import BSBLANEntity

PARALLEL_UPDATES = 1

HVAC_MODES = [
    HVACMode.AUTO,
    HVACMode.HEAT,
    HVACMode.OFF,
]

PRESET_MODES = [
    PRESET_ECO,
    PRESET_NONE,
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BSBLAN device based on a config entry."""
    data: HomeAssistantBSBLANData = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            BSBLANClimate(
                data.coordinator,
                data.client,
                data.device,
                data.info,
                entry,
            )
        ],
        True,
    )


class BSBLANClimate(BSBLANEntity, CoordinatorEntity, ClimateEntity):
    """Defines a BSBLAN climate device."""

    coordinator: DataUpdateCoordinator[State]

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        client: BSBLAN,
        device: Device,
        info: Info,
        entry: ConfigEntry,
    ) -> None:
        """Initialize BSBLAN climate device."""
        super().__init__(client, device, info, entry)
        CoordinatorEntity.__init__(self, coordinator)
        self._attr_unique_id = f"{format_mac(device.MAC)}-climate"
        self._attr_name = device.name

        self._attr_supported_features = SUPPORT_FLAGS
        self._attr_hvac_modes = HVAC_MODES
        self._attr_preset_modes = PRESET_MODES
        self._attr_min_temp = float(self.coordinator.data.min_temp.value)
        self._attr_max_temp = float(self.coordinator.data.max_temp.value)
        self._attr_temperature_unit = (
            TEMP_CELSIUS
            if self.coordinator.data.current_temperature.unit == "&deg;C"
            else TEMP_FAHRENHEIT
        )

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return float(self.coordinator.data.current_temperature.value)

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        return float(self.coordinator.data.target_temperature.value)

    @property
    def hvac_mode(self) -> str:
        """Return hvac operation ie. heat, cool mode."""
        if self.coordinator.data.hvac_mode.value == PRESET_ECO:
            return HVAC_MODE_AUTO

        return self.coordinator.data.hvac_mode.value

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode."""
        if (
            self.hvac_mode == HVAC_MODE_AUTO
            and self.coordinator.data.hvac_mode.value == PRESET_ECO
        ):
            return PRESET_ECO
        return PRESET_NONE

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        """Set hvac mode."""
        await self.async_set_data(hvac_mode=hvac_mode)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set preset mode."""
        # only allow preset mode when hvac mode is auto
        if self.hvac_mode == HVAC_MODE_AUTO:
            await self.async_set_data(preset_mode=preset_mode)
        else:
            LOGGER.error("Can't set preset mode when hvac mode is not auto")

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperatures."""
        await self.async_set_data(**kwargs)

    async def async_set_data(self, **kwargs: Any) -> None:
        """Set device settings using BSBLAN."""
        data = {}
        if ATTR_TEMPERATURE in kwargs:
            data[ATTR_TARGET_TEMPERATURE] = kwargs[ATTR_TEMPERATURE]
        if ATTR_HVAC_MODE in kwargs:
            data[ATTR_HVAC_MODE] = kwargs[ATTR_HVAC_MODE]
        if ATTR_PRESET_MODE in kwargs:
            # If preset mode is None, set hvac to auto
            if kwargs[ATTR_PRESET_MODE] == PRESET_NONE:
                data[ATTR_HVAC_MODE] = HVAC_MODE_AUTO
            else:
                data[ATTR_HVAC_MODE] = kwargs[ATTR_PRESET_MODE]
        try:
            await self.client.thermostat(**data)
        except BSBLANError:
            LOGGER.error("An error occurred while updating the BSBLAN device")
        await self.coordinator.async_request_refresh()
