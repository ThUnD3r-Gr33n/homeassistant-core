"""The test for the Ecobee thermostat module."""
from unittest import mock

import pytest

from homeassistant.components.ecobee import climate as ecobee
import homeassistant.const as const
from homeassistant.const import STATE_OFF

from .common import data_fixture, ecobee_fixture

__all__ = ["data_fixture", "ecobee_fixture"]


@pytest.fixture(name="thermostat")
def thermostat_fixture(data):
    """Set up ecobee thermostat object."""
    return ecobee.Thermostat(data, 1)


async def test_name(thermostat):
    """Test name property."""
    assert thermostat.name == "Ecobee"


async def test_current_temperature(ecobee_fixture, thermostat):
    """Test current temperature."""
    assert thermostat.current_temperature == 30
    ecobee_fixture["runtime"]["actualTemperature"] = const.HTTP_NOT_FOUND
    assert thermostat.current_temperature == 40.4


async def test_target_temperature_low(ecobee_fixture, thermostat):
    """Test target low temperature."""
    assert thermostat.target_temperature_low == 40
    ecobee_fixture["runtime"]["desiredHeat"] = 502
    assert thermostat.target_temperature_low == 50


async def test_target_temperature_high(ecobee_fixture, thermostat):
    """Test target high temperature."""
    assert thermostat.target_temperature_high == 20
    ecobee_fixture["runtime"]["desiredCool"] = 679
    assert thermostat.target_temperature_high == 68


async def test_target_temperature(ecobee_fixture, thermostat):
    """Test target temperature."""
    assert thermostat.target_temperature is None
    ecobee_fixture["settings"]["hvacMode"] = "heat"
    assert thermostat.target_temperature == 40
    ecobee_fixture["settings"]["hvacMode"] = "cool"
    assert thermostat.target_temperature == 20
    ecobee_fixture["settings"]["hvacMode"] = "auxHeatOnly"
    assert thermostat.target_temperature == 40
    ecobee_fixture["settings"]["hvacMode"] = "off"
    assert thermostat.target_temperature is None


async def test_desired_fan_mode(ecobee_fixture, thermostat):
    """Test desired fan mode property."""
    assert thermostat.fan_mode == "on"
    ecobee_fixture["runtime"]["desiredFanMode"] = "auto"
    assert thermostat.fan_mode == "auto"


async def test_fan(ecobee_fixture, thermostat):
    """Test fan property."""
    assert const.STATE_ON == thermostat.fan
    ecobee_fixture["equipmentStatus"] = ""
    assert thermostat.fan == STATE_OFF
    ecobee_fixture["equipmentStatus"] = "heatPump, heatPump2"
    assert thermostat.fan == STATE_OFF


async def test_hvac_mode(ecobee_fixture, thermostat):
    """Test current operation property."""
    assert thermostat.hvac_mode == "heat_cool"
    ecobee_fixture["settings"]["hvacMode"] = "heat"
    assert thermostat.hvac_mode == "heat"
    ecobee_fixture["settings"]["hvacMode"] = "cool"
    assert thermostat.hvac_mode == "cool"
    ecobee_fixture["settings"]["hvacMode"] = "auxHeatOnly"
    assert thermostat.hvac_mode == "heat"
    ecobee_fixture["settings"]["hvacMode"] = "off"
    assert thermostat.hvac_mode == "off"


async def test_hvac_modes(thermostat):
    """Test operation list property."""
    assert ["heat_cool", "heat", "cool", "off"] == thermostat.hvac_modes


async def test_hvac_mode2(ecobee_fixture, thermostat):
    """Test operation mode property."""
    assert thermostat.hvac_mode == "heat_cool"
    ecobee_fixture["settings"]["hvacMode"] = "heat"
    assert thermostat.hvac_mode == "heat"


async def test_extra_state_attributes(ecobee_fixture, thermostat):
    """Test device state attributes property."""
    ecobee_fixture["equipmentStatus"] = "heatPump2"
    assert {
        "fan": "off",
        "climate_mode": "Climate1",
        "fan_min_on_time": 10,
        "equipment_running": "heatPump2",
    } == thermostat.extra_state_attributes

    ecobee_fixture["equipmentStatus"] = "auxHeat2"
    assert {
        "fan": "off",
        "climate_mode": "Climate1",
        "fan_min_on_time": 10,
        "equipment_running": "auxHeat2",
    } == thermostat.extra_state_attributes

    ecobee_fixture["equipmentStatus"] = "compCool1"
    assert {
        "fan": "off",
        "climate_mode": "Climate1",
        "fan_min_on_time": 10,
        "equipment_running": "compCool1",
    } == thermostat.extra_state_attributes
    ecobee_fixture["equipmentStatus"] = ""
    assert {
        "fan": "off",
        "climate_mode": "Climate1",
        "fan_min_on_time": 10,
        "equipment_running": "",
    } == thermostat.extra_state_attributes

    ecobee_fixture["equipmentStatus"] = "Unknown"
    assert {
        "fan": "off",
        "climate_mode": "Climate1",
        "fan_min_on_time": 10,
        "equipment_running": "Unknown",
    } == thermostat.extra_state_attributes

    ecobee_fixture["program"]["currentClimateRef"] = "c2"
    assert {
        "fan": "off",
        "climate_mode": "Climate2",
        "fan_min_on_time": 10,
        "equipment_running": "Unknown",
    } == thermostat.extra_state_attributes


async def test_is_aux_heat_on(ecobee_fixture, thermostat):
    """Test aux heat property."""
    assert not thermostat.is_aux_heat
    ecobee_fixture["equipmentStatus"] = "fan, auxHeat"
    assert thermostat.is_aux_heat


async def test_set_temperature(ecobee_fixture, thermostat, data):
    """Test set temperature."""
    # Auto -> Auto
    data.reset_mock()
    thermostat.set_temperature(target_temp_low=20, target_temp_high=30)
    data.ecobee.set_hold_temp.assert_has_calls(
        [mock.call(1, 30, 20, "nextTransition", None)]
    )

    # Auto -> Hold
    data.reset_mock()
    thermostat.set_temperature(temperature=20)
    data.ecobee.set_hold_temp.assert_has_calls(
        [mock.call(1, 25, 15, "nextTransition", None)]
    )

    # Cool -> Hold
    data.reset_mock()
    ecobee_fixture["settings"]["hvacMode"] = "cool"
    thermostat.set_temperature(temperature=20.5)
    data.ecobee.set_hold_temp.assert_has_calls(
        [mock.call(1, 20.5, 20.5, "nextTransition", None)]
    )

    # Heat -> Hold
    data.reset_mock()
    ecobee_fixture["settings"]["hvacMode"] = "heat"
    thermostat.set_temperature(temperature=20)
    data.ecobee.set_hold_temp.assert_has_calls(
        [mock.call(1, 20, 20, "nextTransition", None)]
    )

    # Heat -> Auto
    data.reset_mock()
    ecobee_fixture["settings"]["hvacMode"] = "heat"
    thermostat.set_temperature(target_temp_low=20, target_temp_high=30)
    assert not data.ecobee.set_hold_temp.called


async def test_set_hvac_mode(thermostat, data):
    """Test operation mode setter."""
    data.reset_mock()
    thermostat.set_hvac_mode("heat_cool")
    data.ecobee.set_hvac_mode.assert_has_calls([mock.call(1, "auto")])
    data.reset_mock()
    thermostat.set_hvac_mode("heat")
    data.ecobee.set_hvac_mode.assert_has_calls([mock.call(1, "heat")])


async def test_set_fan_min_on_time(thermostat, data):
    """Test fan min on time setter."""
    data.reset_mock()
    thermostat.set_fan_min_on_time(15)
    data.ecobee.set_fan_min_on_time.assert_has_calls([mock.call(1, 15)])
    data.reset_mock()
    thermostat.set_fan_min_on_time(20)
    data.ecobee.set_fan_min_on_time.assert_has_calls([mock.call(1, 20)])


async def test_resume_program(thermostat, data):
    """Test resume program."""
    # False
    data.reset_mock()
    thermostat.resume_program(False)
    data.ecobee.resume_program.assert_has_calls([mock.call(1, "false")])
    data.reset_mock()
    thermostat.resume_program(None)
    data.ecobee.resume_program.assert_has_calls([mock.call(1, "false")])
    data.reset_mock()
    thermostat.resume_program(0)
    data.ecobee.resume_program.assert_has_calls([mock.call(1, "false")])

    # True
    data.reset_mock()
    thermostat.resume_program(True)
    data.ecobee.resume_program.assert_has_calls([mock.call(1, "true")])
    data.reset_mock()
    thermostat.resume_program(1)
    data.ecobee.resume_program.assert_has_calls([mock.call(1, "true")])


async def test_hold_preference(ecobee_fixture, thermostat):
    """Test hold preference."""
    ecobee_fixture["settings"]["holdAction"] = "indefinite"
    assert thermostat.hold_preference() == "indefinite"
    for action in ["useEndTime2hour", "useEndTime4hour"]:
        ecobee_fixture["settings"]["holdAction"] = action
        assert thermostat.hold_preference() == "holdHours"
    for action in [
        "nextPeriod",
        "askMe",
    ]:
        ecobee_fixture["settings"]["holdAction"] = action
        assert thermostat.hold_preference() == "nextTransition"


def test_hold_hours(ecobee_fixture, thermostat):
    """Test hold hours preference."""
    ecobee_fixture["settings"]["holdAction"] = "useEndTime2hour"
    assert thermostat.hold_hours() == 2
    ecobee_fixture["settings"]["holdAction"] = "useEndTime4hour"
    assert thermostat.hold_hours() == 4
    for action in [
        "nextPeriod",
        "indefinite",
        "askMe",
    ]:
        ecobee_fixture["settings"]["holdAction"] = action
        assert thermostat.hold_hours() is None


async def test_set_fan_mode_on(thermostat, data):
    """Test set fan mode to on."""
    data.reset_mock()
    thermostat.set_fan_mode("on")
    data.ecobee.set_fan_mode.assert_has_calls(
        [mock.call(1, "on", "nextTransition", holdHours=None)]
    )


async def test_set_fan_mode_auto(thermostat, data):
    """Test set fan mode to auto."""
    data.reset_mock()
    thermostat.set_fan_mode("auto")
    data.ecobee.set_fan_mode.assert_has_calls(
        [mock.call(1, "auto", "nextTransition", holdHours=None)]
    )
