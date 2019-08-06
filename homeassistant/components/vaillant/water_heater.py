"""Interfaces with Vaillant water heater."""
import logging

from vr900connector.model import System, HotWater, QuickMode, HeatingMode
from homeassistant.helpers.temperature import display_temp as show_temp
from homeassistant.const import ATTR_TEMPERATURE, TEMP_CELSIUS, STATE_ON, STATE_OFF
from homeassistant.components.water_heater import (
    WaterHeaterDevice,
    SUPPORT_TARGET_TEMPERATURE,
    SUPPORT_AWAY_MODE,
    SUPPORT_OPERATION_MODE,
    ATTR_MIN_TEMP,
    ATTR_MAX_TEMP,
    ATTR_OPERATION_MODE,
    ATTR_OPERATION_LIST,
    ATTR_AWAY_MODE,
    DOMAIN,
)
from . import HUB, BaseVaillantEntity, CONF_WATER_HEATER, ATTR_VAILLANT_MODE

_LOGGER = logging.getLogger(__name__)

SUPPORTED_FLAGS = (
    SUPPORT_TARGET_TEMPERATURE | SUPPORT_OPERATION_MODE | SUPPORT_AWAY_MODE
)
ATTR_CURRENT_TEMPERATURE = "current_temperature"
ATTR_TIME_PROGRAM = "time_program"

AWAY_MODES = [
    HeatingMode.OFF,
    QuickMode.QM_HOLIDAY,
    QuickMode.QM_ONE_DAY_AWAY,
    QuickMode.QM_SYSTEM_OFF,
]


async def async_setup_platform(hass, config, async_add_entities,
                               discovery_info=None):
    """Set up water_heater platform."""
    entities = []
    hub = hass.data[HUB]

    if hub.system and hub.system.hot_water and hub.config[CONF_WATER_HEATER]:
        entity = VaillantWaterHeater(hub.system)
        entities.append(entity)
        hub.add_listener(entity)

    _LOGGER.info("Added water heater? %s", len(entities) > 0)
    async_add_entities(entities, True)
    return True


class VaillantWaterHeater(BaseVaillantEntity, WaterHeaterDevice):
    """Represent the vaillant water heater."""

    def __init__(self, system: System):
        """Initialize entity."""
        super().__init__(DOMAIN, None, system.hot_water.id,
                         system.hot_water.name)
        self._system = None
        self._active_mode = None
        mode_list = HotWater.MODES + QuickMode.for_hot_water()
        mode_list.remove(QuickMode.QM_HOLIDAY)
        self._operation_list = [mode.name for mode in mode_list]
        self._operation_list_to_mode = {mode.name: mode for mode in mode_list}
        self._refresh(system)

    @property
    def supported_features(self):
        """Return the list of supported features.

        !! It could be misleading here, since when heater is not heating,
        target temperature if fixed (35 °C) - The API doesn't allow to change
        this setting. It means if the user wants to change the target
        temperature, it will always be the target temperature when the
        heater is on function. See example below:

        1. Target temperature when heater is off is 35 (this is a fixed
        setting)
        2. Target temperature when heater is on is for instance 50 (this is a
        configurable setting)
        3. While heater is off, user changes target_temperature to 45. It will
        actually change the target temperature from 50 to 45
        4. While heater is off, user will still see 35 in UI
        (even if he changes to 45 before)
        5. When heater will go on, user will see the target temperature he set
         at point 3 -> 45.

        Maybe I can remove the SUPPORT_TARGET_TEMPERATURE flag if the heater
        is off, but it means the user will be able to change the target
         temperature only when the heater is ON (which seems odd to me)
        """
        return SUPPORTED_FLAGS

    @property
    def available(self):
        """Return True if entity is available."""
        return self._system.hot_water is not None

    @property
    def temperature_unit(self):
        """Return the unit of measurement used by the platform."""
        return TEMP_CELSIUS

    @property
    def state_attributes(self):
        """Return the optional state attributes.

        Adding current temperature
        """
        attrs = super().state_attributes
        attrs.update({
            ATTR_VAILLANT_MODE: self._active_mode.current_mode.name
        })
        return attrs
        # return {
        #     ATTR_MIN_TEMP: show_temp(
        #         self.hass, self.min_temp, self.temperature_unit, self.precision
        #     ),
        #     ATTR_MAX_TEMP: show_temp(
        #         self.hass, self.max_temp, self.temperature_unit, self.precision
        #     ),
        #     ATTR_TEMPERATURE: show_temp(
        #         self.hass,
        #         self.target_temperature,
        #         self.temperature_unit,
        #         self.precision,
        #     ),
        #     ATTR_CURRENT_TEMPERATURE: show_temp(
        #         self.hass, self.temperature, self.temperature_unit,
        #         self.precision
        #     ),
        #     ATTR_OPERATION_MODE: self.current_operation,
        #     ATTR_OPERATION_LIST: self.operation_list,
        #     ATTR_AWAY_MODE: STATE_ON if self.is_away_mode_on else STATE_OFF,
        #     ATTR_VAILLANT_MODE: self._active_mode.current_mode.name
        # }

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        _LOGGER.debug("target temperature is %s",
                      self._active_mode.target_temperature)
        return self._active_mode.target_temperature

    @property
    def current_temperature(self):
        """Return the current temperature."""
        _LOGGER.debug(
            "current temperature is %s",
            self._system.hot_water.current_temperature
        )
        return self._system.hot_water.current_temperature

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return HotWater.MIN_TEMP

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return HotWater.MAX_TEMP

    @property
    def current_operation(self):
        """Return current operation ie. eco, electric, performance, ..."""
        _LOGGER.debug("current_operation is %s",
                      self._active_mode.current_mode)
        return self._active_mode.current_mode.name

    @property
    def operation_list(self):
        """Return current operation ie. eco, electric, performance, ..."""
        return self._operation_list

    @property
    def is_away_mode_on(self):
        """Return true if away mode is on."""
        return self._active_mode.current_mode in AWAY_MODES

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        target_temp = float(kwargs.get(ATTR_TEMPERATURE))
        _LOGGER.debug("Trying to set target temp to %s", target_temp)
        # HUB will call sync update
        self.hub.set_hot_water_target_temperature(
            self, self._system.hot_water, target_temp
        )

    def set_operation_mode(self, operation_mode):
        """Set new target operation mode."""
        _LOGGER.debug("Will set new operation_mode %s", operation_mode)
        # HUB will call sync update
        if operation_mode in self._operation_list:
            mode = self._operation_list_to_mode[operation_mode]
            self.hub.set_hot_water_operation_mode(self, self._system.hot_water,
                                                  mode)
        else:
            _LOGGER.debug("Operation mode is unknown")

    def turn_away_mode_on(self):
        """Turn away mode on."""
        self.hub.set_hot_water_operation_mode(
            self, self._system.hot_water, HeatingMode.OFF
        )

    def turn_away_mode_off(self):
        """Turn away mode off."""
        self.hub.set_hot_water_operation_mode(
            self, self._system.hot_water, HeatingMode.AUTO
        )

    async def vaillant_update(self):
        """Update specific for vaillant."""
        self._refresh(self.hub.system)

    def _refresh(self, system):
        """Refresh the entity."""
        self._system = system
        self._active_mode = self._system.get_active_mode_hot_water()

        if self._system.holiday_mode and \
                self._system.holiday_mode.is_currently_active:
            self._operation_list.append(QuickMode.QM_HOLIDAY.name)
        elif QuickMode.QM_HOLIDAY.name in self._operation_list:
            self._operation_list.remove(QuickMode.QM_HOLIDAY.name)
