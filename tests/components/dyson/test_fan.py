"""Test the Dyson fan component."""
import json
import unittest
from unittest import mock

import asynctest
from libpurecool.const import FanSpeed, FanMode, NightMode, Oscillation
from libpurecool.dyson_pure_cool import DysonPureCool
from libpurecool.dyson_pure_cool_link import DysonPureCoolLink
from libpurecool.dyson_pure_state import DysonPureCoolState
from libpurecool.dyson_pure_state_v2 import DysonPureCoolV2State

import homeassistant.components.dyson.fan as dyson
from homeassistant.components import dyson as dyson_parent
from homeassistant.components.dyson import DYSON_DEVICES
from homeassistant.components.fan import (DOMAIN, ATTR_SPEED, ATTR_SPEED_LIST,
                                          ATTR_OSCILLATING, SPEED_LOW,
                                          SPEED_MEDIUM, SPEED_HIGH,
                                          SERVICE_OSCILLATE)
from homeassistant.const import (SERVICE_TURN_ON,
                                 SERVICE_TURN_OFF,
                                 ATTR_ENTITY_ID)
from homeassistant.setup import setup_component
from tests.common import get_test_home_assistant


class MockDysonState(DysonPureCoolState):
    """Mock Dyson state."""

    def __init__(self):
        """Create new Mock Dyson State."""
        pass


def _get_dyson_purecool_device():
    """Return a valid device provide by Dyson web services."""
    device = mock.Mock(spec=DysonPureCool)
    device.serial = "XX-XXXXX-XX"
    device.name = "Living room"
    device.connect = mock.Mock(return_value=True)
    device.auto_connect = mock.Mock(return_value=True)
    device.state = mock.Mock()
    device.state.oscillation = "OION"
    device.state.fan_power = "ON"
    device.state.speed = FanSpeed.FAN_SPEED_AUTO.value
    device.state.night_mode = "OFF"
    device.state.auto_mode = "ON"
    device.state.oscillation_angle_low = "0090"
    device.state.oscillation_angle_high = "0180"
    device.state.front_direction = "ON"
    device.state.sleep_timer = 60
    return device


def _get_supported_speeds():
    return [
        int(FanSpeed.FAN_SPEED_1.value),
        int(FanSpeed.FAN_SPEED_2.value),
        int(FanSpeed.FAN_SPEED_3.value),
        int(FanSpeed.FAN_SPEED_4.value),
        int(FanSpeed.FAN_SPEED_5.value),
        int(FanSpeed.FAN_SPEED_6.value),
        int(FanSpeed.FAN_SPEED_7.value),
        int(FanSpeed.FAN_SPEED_8.value),
        int(FanSpeed.FAN_SPEED_9.value),
        int(FanSpeed.FAN_SPEED_10.value),
    ]


def _get_config():
    """Return a config dictionary."""
    return {dyson_parent.DOMAIN: {
        dyson_parent.CONF_USERNAME: "email",
        dyson_parent.CONF_PASSWORD: "password",
        dyson_parent.CONF_LANGUAGE: "GB",
        dyson_parent.CONF_DEVICES: [
            {
                "device_id": "XX-XXXXX-XX",
                "device_ip": "192.168.0.1"
            }
        ]
    }}


def _get_device_with_no_state():
    """Return a device with no state."""
    device = mock.Mock()
    device.name = "Device_name"
    device.state = None
    return device


def _get_device_off():
    """Return a device with state off."""
    device = mock.Mock()
    device.name = "Device_name"
    device.state = mock.Mock()
    device.state.fan_mode = "OFF"
    device.state.night_mode = "ON"
    device.state.speed = "0004"
    return device


def _get_device_auto():
    """Return a device with state auto."""
    device = mock.Mock()
    device.name = "Device_name"
    device.state = mock.Mock()
    device.state.fan_mode = "AUTO"
    device.state.night_mode = "ON"
    device.state.speed = "AUTO"
    return device


def _get_device_on():
    """Return a valid state on."""
    device = mock.Mock(spec=DysonPureCoolLink)
    device.name = "Device_name"
    device.state = mock.Mock()
    device.state.fan_mode = "FAN"
    device.state.fan_state = "FAN"
    device.state.oscillation = "ON"
    device.state.night_mode = "OFF"
    device.state.speed = "0001"
    return device


class DysonSetupTest(unittest.TestCase):
    """Dyson component setup tests."""

    def setUp(self):  # pylint: disable=invalid-name
        """Set up things to be run when tests are started."""
        self.hass = get_test_home_assistant()

    def tearDown(self):  # pylint: disable=invalid-name
        """Stop everything that was started."""
        self.hass.stop()

    def test_setup_component_with_no_devices(self):
        """Test setup component with no devices."""
        self.hass.data[dyson.DYSON_DEVICES] = []
        add_entities = mock.MagicMock()
        dyson.setup_platform(self.hass, None, add_entities, mock.Mock())
        add_entities.assert_called_with([])

    def test_setup_component(self):
        """Test setup component with devices."""
        def _add_device(devices):
            assert len(devices) == 2
            assert devices[0].name == "Device_name"

        device_fan = _get_device_on()
        device_purecool_fan = _get_dyson_purecool_device()
        device_non_fan = _get_device_off()

        self.hass.data[dyson.DYSON_DEVICES] = [device_fan,
                                               device_purecool_fan,
                                               device_non_fan]
        dyson.setup_platform(self.hass, None, _add_device)


class DysonTest(unittest.TestCase):
    """Dyson fan component test class."""

    def setUp(self):  # pylint: disable=invalid-name
        """Set up things to be run when tests are started."""
        self.hass = get_test_home_assistant()

    def tearDown(self):  # pylint: disable=invalid-name
        """Stop everything that was started."""
        self.hass.stop()

    @mock.patch('libpurecool.dyson.DysonAccount.devices',
                return_value=[_get_device_on()])
    @mock.patch('libpurecool.dyson.DysonAccount.login', return_value=True)
    def test_get_state_attributes(self, mocked_login, mocked_devices):
        """Test async added to hass."""
        setup_component(self.hass, dyson_parent.DOMAIN, {
            dyson_parent.DOMAIN: {
                dyson_parent.CONF_USERNAME: "email",
                dyson_parent.CONF_PASSWORD: "password",
                dyson_parent.CONF_LANGUAGE: "US",
                }
            })
        self.hass.block_till_done()
        state = self.hass.states.get("{}.{}".format(
            DOMAIN,
            mocked_devices.return_value[0].name))

        assert dyson.ATTR_NIGHT_MODE in state.attributes
        assert dyson.ATTR_AUTO_MODE in state.attributes
        assert ATTR_SPEED in state.attributes
        assert ATTR_SPEED_LIST in state.attributes
        assert ATTR_OSCILLATING in state.attributes

    @mock.patch('libpurecool.dyson.DysonAccount.devices',
                return_value=[_get_device_on()])
    @mock.patch('libpurecool.dyson.DysonAccount.login', return_value=True)
    def test_async_added_to_hass(self, mocked_login, mocked_devices):
        """Test async added to hass."""
        setup_component(self.hass, dyson_parent.DOMAIN, {
            dyson_parent.DOMAIN: {
                dyson_parent.CONF_USERNAME: "email",
                dyson_parent.CONF_PASSWORD: "password",
                dyson_parent.CONF_LANGUAGE: "US",
                }
            })
        self.hass.block_till_done()
        assert len(self.hass.data[dyson.DYSON_DEVICES]) == 1
        assert mocked_devices.return_value[0].add_message_listener.called

    def test_dyson_set_speed(self):
        """Test set fan speed."""
        device = _get_device_on()
        component = dyson.DysonPureCoolLinkDevice(self.hass, device)
        assert not component.should_poll
        component.set_speed("1")
        set_config = device.set_configuration
        set_config.assert_called_with(fan_mode=FanMode.FAN,
                                      fan_speed=FanSpeed.FAN_SPEED_1)

        component.set_speed("AUTO")
        set_config = device.set_configuration
        set_config.assert_called_with(fan_mode=FanMode.AUTO)

    def test_dyson_turn_on(self):
        """Test turn on fan."""
        device = _get_device_on()
        component = dyson.DysonPureCoolLinkDevice(self.hass, device)
        assert not component.should_poll
        component.turn_on()
        set_config = device.set_configuration
        set_config.assert_called_with(fan_mode=FanMode.FAN)

    def test_dyson_turn_night_mode(self):
        """Test turn on fan with night mode."""
        device = _get_device_on()
        component = dyson.DysonPureCoolLinkDevice(self.hass, device)
        assert not component.should_poll
        component.set_night_mode(True)
        set_config = device.set_configuration
        set_config.assert_called_with(night_mode=NightMode.NIGHT_MODE_ON)

        component.set_night_mode(False)
        set_config = device.set_configuration
        set_config.assert_called_with(night_mode=NightMode.NIGHT_MODE_OFF)

    def test_is_night_mode(self):
        """Test night mode."""
        device = _get_device_on()
        component = dyson.DysonPureCoolLinkDevice(self.hass, device)
        assert not component.night_mode

        device = _get_device_off()
        component = dyson.DysonPureCoolLinkDevice(self.hass, device)
        assert component.night_mode

    def test_dyson_turn_auto_mode(self):
        """Test turn on/off fan with auto mode."""
        device = _get_device_on()
        component = dyson.DysonPureCoolLinkDevice(self.hass, device)
        assert not component.should_poll
        component.set_auto_mode(True)
        set_config = device.set_configuration
        set_config.assert_called_with(fan_mode=FanMode.AUTO)

        component.set_auto_mode(False)
        set_config = device.set_configuration
        set_config.assert_called_with(fan_mode=FanMode.FAN)

    def test_is_auto_mode(self):
        """Test auto mode."""
        device = _get_device_on()
        component = dyson.DysonPureCoolLinkDevice(self.hass, device)
        assert not component.auto_mode

        device = _get_device_auto()
        component = dyson.DysonPureCoolLinkDevice(self.hass, device)
        assert component.auto_mode

    def test_dyson_turn_on_speed(self):
        """Test turn on fan with specified speed."""
        device = _get_device_on()
        component = dyson.DysonPureCoolLinkDevice(self.hass, device)
        assert not component.should_poll
        component.turn_on("1")
        set_config = device.set_configuration
        set_config.assert_called_with(fan_mode=FanMode.FAN,
                                      fan_speed=FanSpeed.FAN_SPEED_1)

        component.turn_on("AUTO")
        set_config = device.set_configuration
        set_config.assert_called_with(fan_mode=FanMode.AUTO)

    def test_dyson_turn_off(self):
        """Test turn off fan."""
        device = _get_device_on()
        component = dyson.DysonPureCoolLinkDevice(self.hass, device)
        assert not component.should_poll
        component.turn_off()
        set_config = device.set_configuration
        set_config.assert_called_with(fan_mode=FanMode.OFF)

    def test_dyson_oscillate_off(self):
        """Test turn off oscillation."""
        device = _get_device_on()
        component = dyson.DysonPureCoolLinkDevice(self.hass, device)
        component.oscillate(False)
        set_config = device.set_configuration
        set_config.assert_called_with(oscillation=Oscillation.OSCILLATION_OFF)

    def test_dyson_oscillate_on(self):
        """Test turn on oscillation."""
        device = _get_device_on()
        component = dyson.DysonPureCoolLinkDevice(self.hass, device)
        component.oscillate(True)
        set_config = device.set_configuration
        set_config.assert_called_with(oscillation=Oscillation.OSCILLATION_ON)

    def test_dyson_oscillate_value_on(self):
        """Test get oscillation value on."""
        device = _get_device_on()
        component = dyson.DysonPureCoolLinkDevice(self.hass, device)
        assert component.oscillating

    def test_dyson_oscillate_value_off(self):
        """Test get oscillation value off."""
        device = _get_device_off()
        component = dyson.DysonPureCoolLinkDevice(self.hass, device)
        assert not component.oscillating

    def test_dyson_on(self):
        """Test device is on."""
        device = _get_device_on()
        component = dyson.DysonPureCoolLinkDevice(self.hass, device)
        assert component.is_on

    def test_dyson_off(self):
        """Test device is off."""
        device = _get_device_off()
        component = dyson.DysonPureCoolLinkDevice(self.hass, device)
        assert not component.is_on

        device = _get_device_with_no_state()
        component = dyson.DysonPureCoolLinkDevice(self.hass, device)
        assert not component.is_on

    def test_dyson_get_speed(self):
        """Test get device speed."""
        device = _get_device_on()
        component = dyson.DysonPureCoolLinkDevice(self.hass, device)
        assert component.speed == 1

        device = _get_device_off()
        component = dyson.DysonPureCoolLinkDevice(self.hass, device)
        assert component.speed == 4

        device = _get_device_with_no_state()
        component = dyson.DysonPureCoolLinkDevice(self.hass, device)
        assert component.speed is None

        device = _get_device_auto()
        component = dyson.DysonPureCoolLinkDevice(self.hass, device)
        assert component.speed == "AUTO"

    def test_dyson_get_direction(self):
        """Test get device direction."""
        device = _get_device_on()
        component = dyson.DysonPureCoolLinkDevice(self.hass, device)
        assert component.current_direction is None

    def test_dyson_get_speed_list(self):
        """Test get speeds list."""
        device = _get_device_on()
        component = dyson.DysonPureCoolLinkDevice(self.hass, device)
        assert len(component.speed_list) == 11

    def test_dyson_supported_features(self):
        """Test supported features."""
        device = _get_device_on()
        component = dyson.DysonPureCoolLinkDevice(self.hass, device)
        assert component.supported_features == 3

    def test_on_message(self):
        """Test when message is received."""
        device = _get_device_on()
        component = dyson.DysonPureCoolLinkDevice(self.hass, device)
        component.entity_id = "entity_id"
        component.schedule_update_ha_state = mock.Mock()
        component.on_message(MockDysonState())
        component.schedule_update_ha_state.assert_called_with()

    def test_service_set_night_mode(self):
        """Test set night mode service."""
        dyson_device = mock.MagicMock()
        self.hass.data[DYSON_DEVICES] = []
        dyson_device.entity_id = 'fan.living_room'
        self.hass.data[dyson.DYSON_FAN_DEVICES] = [dyson_device]
        dyson.setup_platform(self.hass, None,
                             mock.MagicMock(), mock.MagicMock())

        self.hass.services.call(dyson.DYSON_DOMAIN,
                                dyson.SERVICE_SET_NIGHT_MODE,
                                {"entity_id": "fan.bed_room",
                                 "night_mode": True}, True)
        assert not dyson_device.set_night_mode.called

        self.hass.services.call(dyson.DYSON_DOMAIN,
                                dyson.SERVICE_SET_NIGHT_MODE,
                                {"entity_id": "fan.living_room",
                                 "night_mode": True}, True)
        dyson_device.set_night_mode.assert_called_with(True)


@asynctest.patch('libpurecool.dyson.DysonAccount.login', return_value=True)
@asynctest.patch('libpurecool.dyson.DysonAccount.devices',
                 return_value=[_get_dyson_purecool_device()])
async def test_purecool_turn_on(devices, login, hass):
    """Test turn on."""
    device = devices.return_value[0]
    dyson_parent.setup(hass, _get_config())
    await hass.async_block_till_done()

    await hass.services.async_call(DOMAIN, SERVICE_TURN_ON,
                                   {ATTR_ENTITY_ID: "fan.bed_room"}, True)
    assert not device.turn_on.called

    await hass.services.async_call(DOMAIN, SERVICE_TURN_ON,
                                   {ATTR_ENTITY_ID: "fan.living_room"}, True)
    assert device.turn_on.called


@asynctest.patch('libpurecool.dyson.DysonAccount.login', return_value=True)
@asynctest.patch('libpurecool.dyson.DysonAccount.devices',
                 return_value=[_get_dyson_purecool_device()])
async def test_purecool_set_speed(devices, login, hass):
    """Test set speed."""
    device = devices.return_value[0]
    dyson_parent.setup(hass, _get_config())
    await hass.async_block_till_done()

    await hass.services.async_call(DOMAIN, SERVICE_TURN_ON,
                                   {ATTR_ENTITY_ID: "fan.bed_room",
                                    ATTR_SPEED: SPEED_LOW}, True)
    assert not device.set_fan_speed.called

    await hass.services.async_call(DOMAIN, SERVICE_TURN_ON,
                                   {ATTR_ENTITY_ID: "fan.living_room",
                                    ATTR_SPEED: SPEED_LOW}, True)
    device.set_fan_speed.assert_called_with(FanSpeed.FAN_SPEED_4)

    await hass.services.async_call(DOMAIN, SERVICE_TURN_ON,
                                   {ATTR_ENTITY_ID: "fan.living_room",
                                    ATTR_SPEED: SPEED_MEDIUM}, True)
    device.set_fan_speed.assert_called_with(FanSpeed.FAN_SPEED_7)

    await hass.services.async_call(DOMAIN, SERVICE_TURN_ON,
                                   {ATTR_ENTITY_ID: "fan.living_room",
                                    ATTR_SPEED: SPEED_HIGH}, True)
    device.set_fan_speed.assert_called_with(FanSpeed.FAN_SPEED_10)


@asynctest.patch('libpurecool.dyson.DysonAccount.login', return_value=True)
@asynctest.patch('libpurecool.dyson.DysonAccount.devices',
                 return_value=[_get_dyson_purecool_device()])
async def test_purecool_turn_off(devices, login, hass):
    """Test turn off."""
    device = devices.return_value[0]
    dyson_parent.setup(hass, _get_config())
    await hass.async_block_till_done()

    await hass.services.async_call(DOMAIN, SERVICE_TURN_OFF,
                                   {ATTR_ENTITY_ID: "fan.bed_room"}, True)
    assert not device.turn_off.called

    await hass.services.async_call(DOMAIN, SERVICE_TURN_OFF,
                                   {ATTR_ENTITY_ID: "fan.living_room"}, True)
    assert device.turn_off.called


@asynctest.patch('libpurecool.dyson.DysonAccount.login', return_value=True)
@asynctest.patch('libpurecool.dyson.DysonAccount.devices',
                 return_value=[_get_dyson_purecool_device()])
async def test_purecool_set_dyson_speed(devices, login, hass):
    """Test set exact dyson speed."""
    device = devices.return_value[0]
    dyson_parent.setup(hass, _get_config())
    await hass.async_block_till_done()

    await hass.services.async_call(dyson.DYSON_DOMAIN,
                                   dyson.SERVICE_SET_DYSON_SPEED,
                                   {ATTR_ENTITY_ID: "fan.bed_room",
                                    dyson.ATTR_DYSON_SPEED:
                                        int(FanSpeed.FAN_SPEED_2.value)},
                                   True)
    assert not device.set_fan_speed.called

    await hass.services.async_call(dyson.DYSON_DOMAIN,
                                   dyson.SERVICE_SET_DYSON_SPEED,
                                   {ATTR_ENTITY_ID: "fan.living_room",
                                    dyson.ATTR_DYSON_SPEED:
                                        int(FanSpeed.FAN_SPEED_2.value)},
                                   True)
    device.set_fan_speed.assert_called_with(FanSpeed.FAN_SPEED_2)


@asynctest.patch('libpurecool.dyson.DysonAccount.login', return_value=True)
@asynctest.patch('libpurecool.dyson.DysonAccount.devices',
                 return_value=[_get_dyson_purecool_device()])
async def test_purecool_oscillate(devices, login, hass):
    """Test set oscillation."""
    device = devices.return_value[0]
    dyson_parent.setup(hass, _get_config())
    await hass.async_block_till_done()

    await hass.services.async_call(DOMAIN, SERVICE_OSCILLATE,
                                   {ATTR_ENTITY_ID: "fan.bed_room",
                                    ATTR_OSCILLATING: True}, True)
    assert not device.enable_oscillation.called

    await hass.services.async_call(DOMAIN, SERVICE_OSCILLATE,
                                   {ATTR_ENTITY_ID: "fan.living_room",
                                    ATTR_OSCILLATING: True}, True)
    assert device.enable_oscillation.called

    await hass.services.async_call(DOMAIN, SERVICE_OSCILLATE,
                                   {ATTR_ENTITY_ID: "fan.living_room",
                                    ATTR_OSCILLATING: False}, True)
    assert device.disable_oscillation.called


@asynctest.patch('libpurecool.dyson.DysonAccount.login', return_value=True)
@asynctest.patch('libpurecool.dyson.DysonAccount.devices',
                 return_value=[_get_dyson_purecool_device()])
async def test_purecool_set_night_mode(devices, login, hass):
    """Test set night mode."""

    device = devices.return_value[0]
    dyson_parent.setup(hass, _get_config())

    await hass.async_block_till_done()

    await hass.services.async_call(dyson.DYSON_DOMAIN,
                                   dyson.SERVICE_SET_NIGHT_MODE,
                                   {"entity_id": "fan.bed_room",
                                    "night_mode": True}, True)
    assert not device.enable_night_mode.called

    await hass.services.async_call(dyson.DYSON_DOMAIN,
                                   dyson.SERVICE_SET_NIGHT_MODE,
                                   {"entity_id": "fan.living_room",
                                    "night_mode": True}, True)
    assert device.enable_night_mode.called

    await hass.services.async_call(dyson.DYSON_DOMAIN,
                                   dyson.SERVICE_SET_NIGHT_MODE,
                                   {"entity_id": "fan.living_room",
                                    "night_mode": False}, True)
    assert device.disable_night_mode.called


@asynctest.patch('libpurecool.dyson.DysonAccount.login', return_value=True)
@asynctest.patch('libpurecool.dyson.DysonAccount.devices',
                 return_value=[_get_dyson_purecool_device()])
async def test_purecool_set_auto_mode(devices, login, hass):
    """Test set auto mode."""
    device = devices.return_value[0]
    dyson_parent.setup(hass, _get_config())
    await hass.async_block_till_done()

    await hass.services.async_call(dyson.DYSON_DOMAIN,
                                   dyson.SERVICE_SET_AUTO_MODE,
                                   {ATTR_ENTITY_ID: "fan.bed_room",
                                    dyson.ATTR_AUTO_MODE: True}, True)
    assert not device.enable_auto_mode.called

    await hass.services.async_call(dyson.DYSON_DOMAIN,
                                   dyson.SERVICE_SET_AUTO_MODE,
                                   {ATTR_ENTITY_ID: "fan.living_room",
                                    dyson.ATTR_AUTO_MODE: True}, True)
    assert device.enable_auto_mode.called

    await hass.services.async_call(dyson.DYSON_DOMAIN,
                                   dyson.SERVICE_SET_AUTO_MODE,
                                   {ATTR_ENTITY_ID: "fan.living_room",
                                    dyson.ATTR_AUTO_MODE: False}, True)
    assert device.disable_auto_mode.called


@asynctest.patch('libpurecool.dyson.DysonAccount.login', return_value=True)
@asynctest.patch('libpurecool.dyson.DysonAccount.devices',
                 return_value=[_get_dyson_purecool_device()])
async def test_purecool_set_angle(devices, login, hass):
    """Test set angle."""
    device = devices.return_value[0]
    dyson_parent.setup(hass, _get_config())
    await hass.async_block_till_done()

    await hass.services.async_call(dyson.DYSON_DOMAIN, dyson.SERVICE_SET_ANGLE,
                                   {ATTR_ENTITY_ID: "fan.bed_room",
                                    dyson.ATTR_ANGLE_LOW: 90,
                                    dyson.ATTR_ANGLE_HIGH: 180}, True)
    assert not device.enable_oscillation.called

    await hass.services.async_call(dyson.DYSON_DOMAIN, dyson.SERVICE_SET_ANGLE,
                                   {ATTR_ENTITY_ID: "fan.living_room",
                                    dyson.ATTR_ANGLE_LOW: 90,
                                    dyson.ATTR_ANGLE_HIGH: 180}, True)
    device.enable_oscillation.assert_called_with(90, 180)


@asynctest.patch('libpurecool.dyson.DysonAccount.login', return_value=True)
@asynctest.patch('libpurecool.dyson.DysonAccount.devices',
                 return_value=[_get_dyson_purecool_device()])
async def test_purecool_set_flow_direction_front(devices, login, hass):
    """Test set frontal flow direction."""
    device = devices.return_value[0]
    dyson_parent.setup(hass, _get_config())
    await hass.async_block_till_done()

    await hass.services.async_call(dyson.DYSON_DOMAIN,
                                   dyson.SERVICE_SET_FLOW_DIRECTION_FRONT,
                                   {ATTR_ENTITY_ID: "fan.bed_room",
                                    dyson.ATTR_FLOW_DIRECTION_FRONT: True},
                                   True)
    assert not device.enable_frontal_direction.called

    await hass.services.async_call(dyson.DYSON_DOMAIN,
                                   dyson.SERVICE_SET_FLOW_DIRECTION_FRONT,
                                   {ATTR_ENTITY_ID: "fan.living_room",
                                    dyson.ATTR_FLOW_DIRECTION_FRONT: True},
                                   True)
    assert device.enable_frontal_direction.called

    await hass.services.async_call(dyson.DYSON_DOMAIN,
                                   dyson.SERVICE_SET_FLOW_DIRECTION_FRONT,
                                   {ATTR_ENTITY_ID: "fan.living_room",
                                    dyson.ATTR_FLOW_DIRECTION_FRONT: False},
                                   True)
    assert device.disable_frontal_direction.called


@asynctest.patch('libpurecool.dyson.DysonAccount.login', return_value=True)
@asynctest.patch('libpurecool.dyson.DysonAccount.devices',
                 return_value=[_get_dyson_purecool_device()])
async def test_purecool_set_timer(devices, login, hass):
    """Test set timer."""
    device = devices.return_value[0]
    dyson_parent.setup(hass, _get_config())
    await hass.async_block_till_done()

    await hass.services.async_call(dyson.DYSON_DOMAIN, dyson.SERVICE_SET_TIMER,
                                   {ATTR_ENTITY_ID: "fan.bed_room",
                                    dyson.ATTR_TIMER: 60},
                                   True)
    assert not device.enable_frontal_direction.called

    await hass.services.async_call(dyson.DYSON_DOMAIN, dyson.SERVICE_SET_TIMER,
                                   {ATTR_ENTITY_ID: "fan.living_room",
                                    dyson.ATTR_TIMER: 60},
                                   True)
    device.enable_sleep_timer.assert_called_with(60)

    await hass.services.async_call(dyson.DYSON_DOMAIN, dyson.SERVICE_SET_TIMER,
                                   {ATTR_ENTITY_ID: "fan.living_room",
                                    dyson.ATTR_TIMER: 0},
                                   True)
    assert device.disable_sleep_timer.called


@asynctest.patch('libpurecool.dyson.DysonAccount.login', return_value=True)
@asynctest.patch('libpurecool.dyson.DysonAccount.devices',
                 return_value=[_get_dyson_purecool_device()])
async def test_purecool_attributes(devices, login, hass):
    """Test state attributes."""
    dyson_parent.setup(hass, _get_config())
    await hass.async_block_till_done()
    fan_state = hass.states.get("fan.living_room")
    attributes = fan_state.attributes

    assert fan_state.state is "on"
    assert attributes[dyson.ATTR_NIGHT_MODE] is False
    assert attributes[dyson.ATTR_AUTO_MODE] is True
    assert attributes[dyson.ATTR_ANGLE_LOW] is 90
    assert attributes[dyson.ATTR_ANGLE_HIGH] is 180
    assert attributes[dyson.ATTR_FLOW_DIRECTION_FRONT] is True
    assert attributes[dyson.ATTR_TIMER] is 60
    assert attributes[dyson.ATTR_DYSON_SPEED] is FanSpeed.FAN_SPEED_AUTO.value
    assert attributes[ATTR_SPEED] is SPEED_MEDIUM
    assert attributes[ATTR_OSCILLATING] is True
    assert attributes[dyson.ATTR_DYSON_SPEED_LIST] == _get_supported_speeds()


@asynctest.patch('libpurecool.dyson.DysonAccount.login', return_value=True)
@asynctest.patch('libpurecool.dyson.DysonAccount.devices',
                 return_value=[_get_dyson_purecool_device()])
async def test_purecool_update_state(devices, login, hass):
    """Test state update."""
    device = devices.return_value[0]
    dyson_parent.setup(hass, _get_config())
    await hass.async_block_till_done()
    event = {"msg": "CURRENT-STATE",
             "product-state": {"fpwr": "OFF", "fdir": "OFF", "auto": "OFF",
                               "oscs": "ON", "oson": "ON", "nmod": "OFF",
                               "rhtm": "ON", "fnst": "FAN", "ercd": "11E1",
                               "wacd": "NONE", "nmdv": "0004", "fnsp": "0002",
                               "bril": "0002", "corf": "ON", "cflr": "0084",
                               "hflr": "0084", "sltm": "OFF", "osal": "0045",
                               "osau": "0095", "ancp": "CUST"}}
    device.state = DysonPureCoolV2State(json.dumps(event))

    callback = device.add_message_listener.call_args_list[0][0][0]
    callback(device.state)
    await hass.async_block_till_done()
    fan_state = hass.states.get("fan.living_room")
    attributes = fan_state.attributes

    assert fan_state.state is "off"
    assert attributes[dyson.ATTR_NIGHT_MODE] is False
    assert attributes[dyson.ATTR_AUTO_MODE] is False
    assert attributes[dyson.ATTR_ANGLE_LOW] is 45
    assert attributes[dyson.ATTR_ANGLE_HIGH] is 95
    assert attributes[dyson.ATTR_FLOW_DIRECTION_FRONT] is False
    assert attributes[dyson.ATTR_TIMER] == "OFF"
    assert attributes[dyson.ATTR_DYSON_SPEED] is \
        int(FanSpeed.FAN_SPEED_2.value)
    assert attributes[ATTR_SPEED] is SPEED_LOW
    assert attributes[ATTR_OSCILLATING] is False
    assert attributes[dyson.ATTR_DYSON_SPEED_LIST] == _get_supported_speeds()
