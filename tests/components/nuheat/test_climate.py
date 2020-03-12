"""The test for the NuHeat thermostat module."""
import unittest
from unittest.mock import Mock, patch

from homeassistant import setup
from homeassistant.components.climate.const import (
    HVAC_MODE_AUTO,
    HVAC_MODE_HEAT,
    SUPPORT_PRESET_MODE,
    SUPPORT_TARGET_TEMPERATURE,
)
from homeassistant.components.nuheat import DOMAIN
import homeassistant.components.nuheat.climate as nuheat
from homeassistant.const import (
    CONF_DEVICES,
    CONF_PASSWORD,
    CONF_USERNAME,
    TEMP_CELSIUS,
    TEMP_FAHRENHEIT,
)

from tests.common import get_test_home_assistant

SCHEDULE_HOLD = 3
SCHEDULE_RUN = 1
SCHEDULE_TEMPORARY_HOLD = 2


class TestNuHeat(unittest.TestCase):
    """Tests for NuHeat climate."""

    # pylint: disable=protected-access, no-self-use

    def setUp(self):  # pylint: disable=invalid-name
        """Set up test variables."""
        serial_number = "12345"
        temperature_unit = "F"

        thermostat = Mock(
            serial_number=serial_number,
            room="Master bathroom",
            online=True,
            heating=True,
            temperature=2222,
            celsius=22,
            fahrenheit=72,
            max_celsius=69,
            max_fahrenheit=157,
            min_celsius=5,
            min_fahrenheit=41,
            schedule_mode=SCHEDULE_RUN,
            target_celsius=22,
            target_fahrenheit=72,
        )

        thermostat.get_data = Mock()
        thermostat.resume_schedule = Mock()

        self.api = Mock()
        self.api.get_thermostat.return_value = thermostat

        self.hass = get_test_home_assistant()
        self.thermostat = nuheat.NuHeatThermostat(
            self.api, serial_number, temperature_unit
        )

    def tearDown(self):  # pylint: disable=invalid-name
        """Stop hass."""
        self.hass.stop()

    @patch("homeassistant.components.nuheat.nuheat.NuHeat")
    @patch("homeassistant.components.nuheat.climate.NuHeatThermostat")
    def test_setup_platform(self, mocked_thermostat, mock_api):
        """Test setup_platform."""
        mocked_thermostat.return_value = self.thermostat
        config = {
            DOMAIN: {
                CONF_USERNAME: "username",
                CONF_PASSWORD: "password",
                CONF_DEVICES: ["12345"],
            }
        }
        assert setup.setup_component(self.hass, DOMAIN, config)
        self.hass.block_till_done()

    @patch("homeassistant.components.nuheat.nuheat.NuHeat")
    @patch("homeassistant.components.nuheat.climate.NuHeatThermostat")
    def test_resume_program_service(self, mocked_thermostat, mock_api):
        """Test resume program service."""
        mocked_thermostat.return_value = self.thermostat
        thermostat = mocked_thermostat(mock_api, "12345", "F")
        thermostat.resume_program = Mock()
        thermostat.schedule_update_ha_state = Mock()
        thermostat.entity_id = "climate.master_bathroom"

        config = {
            DOMAIN: {
                CONF_USERNAME: "username",
                CONF_PASSWORD: "password",
                CONF_DEVICES: ["12345"],
            }
        }
        assert setup.setup_component(self.hass, DOMAIN, config)
        self.hass.block_till_done()

        # Explicit entity
        self.hass.services.call(
            nuheat.DOMAIN,
            nuheat.SERVICE_RESUME_PROGRAM,
            {"entity_id": "climate.master_bathroom"},
            True,
        )

        thermostat.resume_program.assert_called_with()
        thermostat.schedule_update_ha_state.assert_called_with(True)

        thermostat.resume_program.reset_mock()
        thermostat.schedule_update_ha_state.reset_mock()

        # All entities
        self.hass.services.call(nuheat.DOMAIN, nuheat.SERVICE_RESUME_PROGRAM, {}, True)

        thermostat.resume_program.assert_called_with()
        thermostat.schedule_update_ha_state.assert_called_with(True)

    def test_name(self):
        """Test name property."""
        assert self.thermostat.name == "Master bathroom"

    def test_supported_features(self):
        """Test name property."""
        features = SUPPORT_TARGET_TEMPERATURE | SUPPORT_PRESET_MODE
        assert self.thermostat.supported_features == features

    def test_temperature_unit(self):
        """Test temperature unit."""
        assert self.thermostat.temperature_unit == TEMP_FAHRENHEIT
        self.thermostat._temperature_unit = "C"
        assert self.thermostat.temperature_unit == TEMP_CELSIUS

    def test_current_temperature(self):
        """Test current temperature."""
        assert self.thermostat.current_temperature == 72
        self.thermostat._temperature_unit = "C"
        assert self.thermostat.current_temperature == 22

    def test_current_operation(self):
        """Test requested mode."""
        assert self.thermostat.hvac_mode == HVAC_MODE_AUTO

    def test_min_temp(self):
        """Test min temp."""
        assert self.thermostat.min_temp == 41
        self.thermostat._temperature_unit = "C"
        assert self.thermostat.min_temp == 5

    def test_max_temp(self):
        """Test max temp."""
        assert self.thermostat.max_temp == 157
        self.thermostat._temperature_unit = "C"
        assert self.thermostat.max_temp == 69

    def test_target_temperature(self):
        """Test target temperature."""
        assert self.thermostat.target_temperature == 72
        self.thermostat._temperature_unit = "C"
        assert self.thermostat.target_temperature == 22

    def test_operation_list(self):
        """Test the operation list."""
        assert self.thermostat.hvac_modes == [HVAC_MODE_AUTO, HVAC_MODE_HEAT]

    def test_resume_program(self):
        """Test resume schedule."""
        self.thermostat.resume_program()
        self.thermostat._thermostat.resume_schedule.assert_called_once_with()
        assert self.thermostat._force_update

    def test_set_temperature(self):
        """Test set temperature."""
        self.thermostat.set_temperature(temperature=85)
        assert self.thermostat._thermostat.target_fahrenheit == 85
        assert self.thermostat._force_update

        self.thermostat._temperature_unit = "C"
        self.thermostat.set_temperature(temperature=23)
        assert self.thermostat._thermostat.target_celsius == 23
        assert self.thermostat._force_update

    @patch.object(nuheat.NuHeatThermostat, "_throttled_update")
    def test_update_without_throttle(self, throttled_update):
        """Test update without throttle."""
        self.thermostat._force_update = True
        self.thermostat.update()
        throttled_update.assert_called_once_with(no_throttle=True)
        assert not self.thermostat._force_update

    @patch.object(nuheat.NuHeatThermostat, "_throttled_update")
    def test_update_with_throttle(self, throttled_update):
        """Test update with throttle."""
        self.thermostat._force_update = False
        self.thermostat.update()
        throttled_update.assert_called_once_with()
        assert not self.thermostat._force_update

    def test_throttled_update(self):
        """Test update with throttle."""
        self.thermostat._throttled_update()
        self.thermostat._thermostat.get_data.assert_called_once_with()
