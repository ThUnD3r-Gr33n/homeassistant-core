"""Support for Toon van Eneco Thermostats."""
from homeassistant.components.climate import (
    ATTR_TEMPERATURE, STATE_COOL, STATE_ECO, STATE_HEAT, STATE_AUTO,
    SUPPORT_OPERATION_MODE, SUPPORT_TARGET_TEMPERATURE, ClimateDevice)
import homeassistant.components.toon as toon_main
from homeassistant.const import TEMP_CELSIUS

SUPPORT_FLAGS = SUPPORT_TARGET_TEMPERATURE | SUPPORT_OPERATION_MODE

HA_TOON = {
    STATE_AUTO: 'Comfort',
    STATE_HEAT: 'Home',
    STATE_ECO: 'Away',
    STATE_COOL: 'Sleep',
}
TOON_HA = {value: key for key, value in HA_TOON.items()}


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Toon climate device."""
    add_entities([ThermostatDevice(hass)], True)


class ThermostatDevice(ClimateDevice):
    """Representation of a Toon climate device."""

    def __init__(self, hass):
        """Initialize the Toon climate device."""
        self._name = 'Toon van Eneco'
        self.hass = hass
        self.thermos = hass.data[toon_main.TOON_HANDLE]

        self._state = None
        self._temperature = None
        self._setpoint = None
        self._operation_list = [
            STATE_AUTO,
            STATE_HEAT,
            STATE_ECO,
            STATE_COOL,
        ]

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_FLAGS

    @property
    def name(self):
        """Return the name of this thermostat."""
        return self._name

    @property
    def temperature_unit(self):
        """Return the unit of measurement used by the platform."""
        return TEMP_CELSIUS

    @property
    def current_operation(self):
        """Return current operation i.e. comfort, home, away."""
        return TOON_HA.get(self.thermos.get_data('state'))

    @property
    def operation_list(self):
        """Return a list of available operation modes."""
        return self._operation_list

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self.thermos.get_data('temp')

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self.thermos.get_data('setpoint')

    def set_temperature(self, **kwargs):
        """Change the setpoint of the thermostat."""
        temp = kwargs.get(ATTR_TEMPERATURE)
        self.thermos.set_temp(temp)

    def set_operation_mode(self, operation_mode):
        """Set new operation mode."""
        self.thermos.set_state(HA_TOON[operation_mode])

    def update(self):
        """Update local state."""
        self.thermos.update()
