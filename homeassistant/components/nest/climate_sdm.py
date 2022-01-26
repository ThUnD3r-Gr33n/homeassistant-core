"""Support for Google Nest SDM climate devices."""
from __future__ import annotations

from typing import Any, cast

from google_nest_sdm.device import Device
from google_nest_sdm.device_traits import FanTrait, TemperatureTrait
from google_nest_sdm.exceptions import ApiException
from google_nest_sdm.thermostat_traits import (
    ThermostatEcoTrait,
    ThermostatHeatCoolTrait,
    ThermostatHvacTrait,
    ThermostatModeTrait,
    ThermostatTemperatureSetpointTrait,
)

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    CURRENT_HVAC_COOL,
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_IDLE,
    CURRENT_HVAC_OFF,
    FAN_OFF,
    FAN_ON,
    HVAC_MODE_AUTO,
    HVAC_MODE_COOL,
    HVAC_MODE_FAN_ONLY,
    HVAC_MODE_HEAT,
    HVAC_MODE_HEAT_COOL,
    HVAC_MODE_OFF,
    PRESET_ECO,
    PRESET_NONE,
    SUPPORT_FAN_MODE,
    SUPPORT_PRESET_MODE,
    SUPPORT_TARGET_TEMPERATURE,
    SUPPORT_TARGET_TEMPERATURE_RANGE,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, TEMP_CELSIUS
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_SUBSCRIBER, DOMAIN
from .device_info import NestDeviceInfo

# Mapping for sdm.devices.traits.ThermostatMode mode field
THERMOSTAT_MODE_MAP: dict[str, str] = {
    "OFF": HVAC_MODE_OFF,
    "HEAT": HVAC_MODE_HEAT,
    "COOL": HVAC_MODE_COOL,
    "HEATCOOL": HVAC_MODE_HEAT_COOL,
}
THERMOSTAT_INV_MODE_MAP = {v: k for k, v in THERMOSTAT_MODE_MAP.items()}

# Mode for sdm.devices.traits.ThermostatEco
THERMOSTAT_ECO_MODE = "MANUAL_ECO"

# Mapping for sdm.devices.traits.ThermostatHvac status field
THERMOSTAT_HVAC_STATUS_MAP = {
    "OFF": CURRENT_HVAC_OFF,
    "HEATING": CURRENT_HVAC_HEAT,
    "COOLING": CURRENT_HVAC_COOL,
}

THERMOSTAT_RANGE_MODES = [HVAC_MODE_HEAT_COOL, HVAC_MODE_AUTO]

PRESET_MODE_MAP = {
    "MANUAL_ECO": PRESET_ECO,
    "OFF": PRESET_NONE,
}
PRESET_INV_MODE_MAP = {v: k for k, v in PRESET_MODE_MAP.items()}

FAN_MODE_MAP = {
    "ON": FAN_ON,
    "OFF": FAN_OFF,
}
FAN_INV_MODE_MAP = {v: k for k, v in FAN_MODE_MAP.items()}

MAX_FAN_DURATION = 43200  # 15 hours is the max in the SDM API


async def async_setup_sdm_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the client entities."""

    subscriber = hass.data[DOMAIN][DATA_SUBSCRIBER]
    try:
        device_manager = await subscriber.async_get_device_manager()
    except ApiException as err:
        raise PlatformNotReady from err

    entities = []
    for device in device_manager.devices.values():
        if ThermostatHvacTrait.NAME in device.traits:
            entities.append(ThermostatEntity(device))
    async_add_entities(entities)


class ThermostatEntity(ClimateEntity):
    """A nest thermostat climate entity."""

    def __init__(self, device: Device) -> None:
        """Initialize ThermostatEntity."""
        self._device = device
        self._device_info = NestDeviceInfo(device)
        self._supported_features = 0

    @property
    def should_poll(self) -> bool:
        """Disable polling since entities have state pushed via pubsub."""
        return False

    @property
    def unique_id(self) -> str | None:
        """Return a unique ID."""
        # The API "name" field is a unique device identifier.
        return self._device.name

    @property
    def name(self) -> str | None:
        """Return the name of the entity."""
        return self._device_info.device_name

    @property
    def device_info(self) -> DeviceInfo:
        """Return device specific attributes."""
        return self._device_info.device_info

    async def async_added_to_hass(self) -> None:
        """Run when entity is added to register update signal handler."""
        self._supported_features = self._get_supported_features()
        self.async_on_remove(
            self._device.add_update_listener(self.async_write_ha_state)
        )

    @property
    def temperature_unit(self) -> str:
        """Return the unit of temperature measurement for the system."""
        return TEMP_CELSIUS

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        if TemperatureTrait.NAME not in self._device.traits:
            return None
        trait: TemperatureTrait = self._device.traits[TemperatureTrait.NAME]
        return trait.ambient_temperature_celsius

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature currently set to be reached."""
        if not (trait := self._target_temperature_trait):
            return None
        if self.hvac_mode == HVAC_MODE_HEAT:
            return trait.heat_celsius
        if self.hvac_mode == HVAC_MODE_COOL:
            return trait.cool_celsius
        return None

    @property
    def target_temperature_high(self) -> float | None:
        """Return the upper bound target temperature."""
        if self.hvac_mode != HVAC_MODE_HEAT_COOL:
            return None
        if not (trait := self._target_temperature_trait):
            return None
        return trait.cool_celsius

    @property
    def target_temperature_low(self) -> float | None:
        """Return the lower bound target temperature."""
        if self.hvac_mode != HVAC_MODE_HEAT_COOL:
            return None
        if not (trait := self._target_temperature_trait):
            return None
        return trait.heat_celsius

    @property
    def _target_temperature_trait(
        self,
    ) -> ThermostatHeatCoolTrait | None:
        """Return the correct trait with a target temp depending on mode."""
        if (
            self.preset_mode == PRESET_ECO
            and ThermostatEcoTrait.NAME in self._device.traits
        ):
            return cast(
                ThermostatEcoTrait, self._device.traits[ThermostatEcoTrait.NAME]
            )
        if ThermostatTemperatureSetpointTrait.NAME in self._device.traits:
            return cast(
                ThermostatTemperatureSetpointTrait,
                self._device.traits[ThermostatTemperatureSetpointTrait.NAME],
            )
        return None

    @property
    def hvac_mode(self) -> str:
        """Return the current operation (e.g. heat, cool, idle)."""
        hvac_mode = HVAC_MODE_OFF
        if ThermostatModeTrait.NAME in self._device.traits:
            trait = self._device.traits[ThermostatModeTrait.NAME]
            if trait.mode in THERMOSTAT_MODE_MAP:
                hvac_mode = THERMOSTAT_MODE_MAP[trait.mode]
        if hvac_mode == HVAC_MODE_OFF and self.fan_mode == FAN_ON:
            hvac_mode = HVAC_MODE_FAN_ONLY
        return hvac_mode

    @property
    def hvac_modes(self) -> list[str]:
        """List of available operation modes."""
        supported_modes = []
        for mode in self._get_device_hvac_modes:
            if mode in THERMOSTAT_MODE_MAP:
                supported_modes.append(THERMOSTAT_MODE_MAP[mode])
        if self.supported_features & SUPPORT_FAN_MODE:
            supported_modes.append(HVAC_MODE_FAN_ONLY)
        return supported_modes

    @property
    def _get_device_hvac_modes(self) -> set[str]:
        """Return the set of SDM API hvac modes supported by the device."""
        modes = []
        if ThermostatModeTrait.NAME in self._device.traits:
            trait = self._device.traits[ThermostatModeTrait.NAME]
            modes.extend(trait.available_modes)
        return set(modes)

    @property
    def hvac_action(self) -> str | None:
        """Return the current HVAC action (heating, cooling)."""
        trait = self._device.traits[ThermostatHvacTrait.NAME]
        if trait.status == "OFF" and self.hvac_mode != HVAC_MODE_OFF:
            return CURRENT_HVAC_IDLE
        if trait.status in THERMOSTAT_HVAC_STATUS_MAP:
            return THERMOSTAT_HVAC_STATUS_MAP[trait.status]
        return None

    @property
    def preset_mode(self) -> str:
        """Return the current active preset."""
        if ThermostatEcoTrait.NAME in self._device.traits:
            trait = self._device.traits[ThermostatEcoTrait.NAME]
            return PRESET_MODE_MAP.get(trait.mode, PRESET_NONE)
        return PRESET_NONE

    @property
    def preset_modes(self) -> list[str]:
        """Return the available presets."""
        modes = []
        if ThermostatEcoTrait.NAME in self._device.traits:
            trait = self._device.traits[ThermostatEcoTrait.NAME]
            for mode in trait.available_modes:
                if mode in PRESET_MODE_MAP:
                    modes.append(PRESET_MODE_MAP[mode])
        return modes

    @property
    def fan_mode(self) -> str:
        """Return the current fan mode."""
        if FanTrait.NAME in self._device.traits:
            trait = self._device.traits[FanTrait.NAME]
            return FAN_MODE_MAP.get(trait.timer_mode, FAN_OFF)
        return FAN_OFF

    @property
    def fan_modes(self) -> list[str]:
        """Return the list of available fan modes."""
        modes = []
        if FanTrait.NAME in self._device.traits:
            modes = list(FAN_INV_MODE_MAP)
        return modes

    @property
    def supported_features(self) -> int:
        """Bitmap of supported features."""
        return self._supported_features

    def _get_supported_features(self) -> int:
        """Compute the bitmap of supported features from the current state."""
        features = 0
        if HVAC_MODE_HEAT_COOL in self.hvac_modes:
            features |= SUPPORT_TARGET_TEMPERATURE_RANGE
        if HVAC_MODE_HEAT in self.hvac_modes or HVAC_MODE_COOL in self.hvac_modes:
            features |= SUPPORT_TARGET_TEMPERATURE
        if ThermostatEcoTrait.NAME in self._device.traits:
            features |= SUPPORT_PRESET_MODE
        if FanTrait.NAME in self._device.traits:
            # Fan trait may be present without actually support fan mode
            fan_trait = self._device.traits[FanTrait.NAME]
            if fan_trait.timer_mode is not None:
                features |= SUPPORT_FAN_MODE
        return features

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        """Set new target hvac mode."""
        if hvac_mode not in self.hvac_modes:
            raise ValueError(f"Unsupported hvac_mode '{hvac_mode}'")
        if hvac_mode == HVAC_MODE_FAN_ONLY:
            # Turn the fan on but also turn off the hvac if it is on
            await self.async_set_fan_mode(FAN_ON)
            hvac_mode = HVAC_MODE_OFF
        api_mode = THERMOSTAT_INV_MODE_MAP[hvac_mode]
        trait = self._device.traits[ThermostatModeTrait.NAME]
        await trait.set_mode(api_mode)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        low_temp = kwargs.get(ATTR_TARGET_TEMP_LOW)
        high_temp = kwargs.get(ATTR_TARGET_TEMP_HIGH)
        temp = kwargs.get(ATTR_TEMPERATURE)
        if ThermostatTemperatureSetpointTrait.NAME not in self._device.traits:
            return
        trait = self._device.traits[ThermostatTemperatureSetpointTrait.NAME]
        if self.preset_mode == PRESET_ECO or self.hvac_mode == HVAC_MODE_HEAT_COOL:
            if low_temp and high_temp:
                await trait.set_range(low_temp, high_temp)
        elif self.hvac_mode == HVAC_MODE_COOL and temp:
            await trait.set_cool(temp)
        elif self.hvac_mode == HVAC_MODE_HEAT and temp:
            await trait.set_heat(temp)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new target preset mode."""
        if preset_mode not in self.preset_modes:
            raise ValueError(f"Unsupported preset_mode '{preset_mode}'")
        trait = self._device.traits[ThermostatEcoTrait.NAME]
        await trait.set_mode(PRESET_INV_MODE_MAP[preset_mode])

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new target fan mode."""
        if fan_mode not in self.fan_modes:
            raise ValueError(f"Unsupported fan_mode '{fan_mode}'")
        trait = self._device.traits[FanTrait.NAME]
        duration = None
        if fan_mode != FAN_OFF:
            duration = MAX_FAN_DURATION
        await trait.set_timer(FAN_INV_MODE_MAP[fan_mode], duration=duration)
