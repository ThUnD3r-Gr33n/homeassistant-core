"""Tests for the HDMI-CEC component."""
from unittest.mock import ANY, PropertyMock, call, patch

import pytest
import voluptuous as vol

from homeassistant.components.hdmi_cec import (
    DOMAIN,
    EVENT_HDMI_CEC_UNAVAILABLE,
    SERVICE_POWER_ON,
    SERVICE_SELECT_DEVICE,
    SERVICE_SEND_COMMAND,
    SERVICE_STANDBY,
    SERVICE_UPDATE_DEVICES,
    SERVICE_VOLUME,
    WATCHDOG_INTERVAL,
    CecCommand,
    KeyPressCommand,
    KeyReleaseCommand,
    PhysicalAddress,
    parse_mapping,
)
from homeassistant.const import EVENT_HOMEASSISTANT_START, EVENT_HOMEASSISTANT_STOP
from homeassistant.setup import async_setup_component

from tests.common import MockEntity, MockEntityPlatform, async_capture_events
from tests.components.hdmi_cec import assert_key_press_release


@pytest.fixture
def mock_tcp_adapter():
    """Mock TcpAdapter."""
    with patch(
        "homeassistant.components.hdmi_cec.TcpAdapter", autospec=True
    ) as MockTcpAdapter:
        yield MockTcpAdapter


@pytest.mark.parametrize(
    "mapping,expected",
    [
        ({}, []),
        (
            {
                "TV": "0.0.0.0",
                "Pi Zero": "1.0.0.0",
                "Fire TV Stick": "2.1.0.0",
                "Chromecast": "2.2.0.0",
                "Another Device": "2.3.0.0",
                "BlueRay player": "3.0.0.0",
            },
            [
                ("TV", "0.0.0.0"),
                ("Pi Zero", "1.0.0.0"),
                ("Fire TV Stick", "2.1.0.0"),
                ("Chromecast", "2.2.0.0"),
                ("Another Device", "2.3.0.0"),
                ("BlueRay player", "3.0.0.0"),
            ],
        ),
        (
            {
                1: "Pi Zero",
                2: {
                    1: "Fire TV Stick",
                    2: "Chromecast",
                    3: "Another Device",
                },
                3: "BlueRay player",
            },
            [
                ("Pi Zero", [1, 0, 0, 0]),
                ("Fire TV Stick", [2, 1, 0, 0]),
                ("Chromecast", [2, 2, 0, 0]),
                ("Another Device", [2, 3, 0, 0]),
                ("BlueRay player", [3, 0, 0, 0]),
            ],
        ),
    ],
)
def test_parse_mapping_physical_address(mapping, expected):
    """Test the device config mapping function."""
    result = parse_mapping(mapping)
    result = [
        (r[0], str(r[1]) if isinstance(r[1], PhysicalAddress) else r[1]) for r in result
    ]
    assert result == expected


# Test Setup


async def test_setup_cec_adapter(hass, mock_cec_adapter, mock_hdmi_network):
    """Test the general setup of this component."""
    await async_setup_component(hass, DOMAIN, {DOMAIN: {}})

    mock_cec_adapter.assert_called_once_with(name="HA", activate_source=False)
    mock_hdmi_network.assert_called_once()
    call_args = mock_hdmi_network.call_args
    assert call_args == call(mock_cec_adapter.return_value, loop=ANY)
    assert call_args.kwargs["loop"] in (None, hass.loop)

    mock_hdmi_network_instance = mock_hdmi_network.return_value

    hass.bus.async_fire(EVENT_HOMEASSISTANT_START)
    await hass.async_block_till_done()
    mock_hdmi_network_instance.start.assert_called_once_with()
    mock_hdmi_network_instance.set_new_device_callback.assert_called_once()
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STOP)
    await hass.async_block_till_done()
    mock_hdmi_network_instance.stop.assert_called_once_with()


@pytest.mark.parametrize("osd_name", ["test", "test_a_long_name"])
async def test_setup_set_osd_name(hass, osd_name, mock_cec_adapter):
    """Test the setup of this component with the `osd_name` config setting."""
    await async_setup_component(hass, DOMAIN, {DOMAIN: {"osd_name": osd_name}})

    mock_cec_adapter.assert_called_once_with(name=osd_name[:12], activate_source=False)


async def test_setup_tcp_adapter(hass, mock_tcp_adapter, mock_hdmi_network):
    """Test the setup of this component with the TcpAdapter (`host` config setting)."""
    host = "0.0.0.0"

    await async_setup_component(hass, DOMAIN, {DOMAIN: {"host": host}})

    mock_tcp_adapter.assert_called_once_with(host, name="HA", activate_source=False)
    mock_hdmi_network.assert_called_once()
    call_args = mock_hdmi_network.call_args
    assert call_args == call(mock_tcp_adapter.return_value, loop=ANY)
    assert call_args.kwargs["loop"] in (None, hass.loop)

    mock_hdmi_network_instance = mock_hdmi_network.return_value

    hass.bus.async_fire(EVENT_HOMEASSISTANT_START)
    await hass.async_block_till_done()
    mock_hdmi_network_instance.start.assert_called_once_with()
    mock_hdmi_network_instance.set_new_device_callback.assert_called_once()
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STOP)
    await hass.async_block_till_done()
    mock_hdmi_network_instance.stop.assert_called_once_with()


# Test services


async def test_service_power_on(hass, mock_hdmi_network):
    """Test the power on service call."""
    await async_setup_component(hass, DOMAIN, {DOMAIN: {}})

    mock_hdmi_network_instance = mock_hdmi_network.return_value

    hass.bus.async_fire(EVENT_HOMEASSISTANT_START)
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        SERVICE_POWER_ON,
        {},
        blocking=True,
    )

    mock_hdmi_network_instance.power_on.assert_called_once_with()


async def test_service_standby(hass, mock_hdmi_network):
    """Test the standby service call."""
    await async_setup_component(hass, DOMAIN, {DOMAIN: {}})

    mock_hdmi_network_instance = mock_hdmi_network.return_value

    hass.bus.async_fire(EVENT_HOMEASSISTANT_START)
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        SERVICE_STANDBY,
        {},
        blocking=True,
    )

    mock_hdmi_network_instance.standby.assert_called_once_with()


async def test_service_select_device_alias(hass, mock_hdmi_network):
    """Test the select device service call with a known alias."""
    await async_setup_component(
        hass, DOMAIN, {DOMAIN: {"devices": {"Chromecast": "1.0.0.0"}}}
    )

    mock_hdmi_network_instance = mock_hdmi_network.return_value

    hass.bus.async_fire(EVENT_HOMEASSISTANT_START)
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        SERVICE_SELECT_DEVICE,
        {"device": "Chromecast"},
        blocking=True,
    )

    mock_hdmi_network_instance.active_source.assert_called_once()
    physical_address = mock_hdmi_network_instance.active_source.call_args.args[0]
    assert isinstance(physical_address, PhysicalAddress)
    assert str(physical_address) == "1.0.0.0"


class MockCecEntity(MockEntity):
    """Mock CEC entity."""

    @property
    def extra_state_attributes(self):
        """Set the physical address in the attributes."""
        return {"physical_address": self._values["physical_address"]}


async def test_service_select_device_entity(hass, mock_hdmi_network):
    """Test the select device service call with an existing entity."""
    platform = MockEntityPlatform(hass)
    await platform.async_add_entities(
        [MockCecEntity(name="hdmi_3", physical_address="3.0.0.0")]
    )

    await async_setup_component(hass, DOMAIN, {DOMAIN: {}})

    mock_hdmi_network_instance = mock_hdmi_network.return_value

    hass.bus.async_fire(EVENT_HOMEASSISTANT_START)
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        SERVICE_SELECT_DEVICE,
        {"device": "test_domain.hdmi_3"},
        blocking=True,
    )

    mock_hdmi_network_instance.active_source.assert_called_once()
    physical_address = mock_hdmi_network_instance.active_source.call_args.args[0]
    assert isinstance(physical_address, PhysicalAddress)
    assert str(physical_address) == "3.0.0.0"


async def test_service_select_device_physical_address(hass, mock_hdmi_network):
    """Test the select device service call with a raw physical address."""
    await async_setup_component(hass, DOMAIN, {DOMAIN: {}})

    mock_hdmi_network_instance = mock_hdmi_network.return_value

    hass.bus.async_fire(EVENT_HOMEASSISTANT_START)
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        SERVICE_SELECT_DEVICE,
        {"device": "1.1.0.0"},
        blocking=True,
    )

    mock_hdmi_network_instance.active_source.assert_called_once()
    physical_address = mock_hdmi_network_instance.active_source.call_args.args[0]
    assert isinstance(physical_address, PhysicalAddress)
    assert str(physical_address) == "1.1.0.0"


async def test_service_update_devices(hass, mock_hdmi_network):
    """Test the update devices service call."""
    await async_setup_component(hass, DOMAIN, {DOMAIN: {}})

    mock_hdmi_network_instance = mock_hdmi_network.return_value

    hass.bus.async_fire(EVENT_HOMEASSISTANT_START)
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        SERVICE_UPDATE_DEVICES,
        {},
        blocking=True,
    )

    mock_hdmi_network_instance.scan.assert_called_once_with()


@pytest.mark.parametrize(
    "count,calls",
    [
        (3, 3),
        (1, 1),
        (0, 0),
        pytest.param(
            "",
            1,
            marks=pytest.mark.xfail(
                reason="While the code allows for an empty string the schema doesn't allow it",
                raises=vol.MultipleInvalid,
            ),
        ),
    ],
)
@pytest.mark.parametrize("direction,key", [("up", 65), ("down", 66)])
async def test_service_volume_x_times(
    hass, mock_hdmi_network, count, calls, direction, key
):
    """Test the volume service call with steps."""
    await async_setup_component(hass, DOMAIN, {DOMAIN: {}})

    mock_hdmi_network_instance = mock_hdmi_network.return_value

    hass.bus.async_fire(EVENT_HOMEASSISTANT_START)
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        SERVICE_VOLUME,
        {direction: count},
        blocking=True,
    )

    assert mock_hdmi_network_instance.send_command.call_count == calls * 2
    for i in range(calls):
        assert_key_press_release(
            mock_hdmi_network_instance.send_command, i, dst=5, key=key
        )


@pytest.mark.parametrize("direction,key", [("up", 65), ("down", 66)])
async def test_service_volume_press(hass, mock_hdmi_network, direction, key):
    """Test the volume service call with press attribute."""
    await async_setup_component(hass, DOMAIN, {DOMAIN: {}})

    mock_hdmi_network_instance = mock_hdmi_network.return_value

    hass.bus.async_fire(EVENT_HOMEASSISTANT_START)
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        SERVICE_VOLUME,
        {direction: "press"},
        blocking=True,
    )

    mock_hdmi_network_instance.send_command.assert_called_once()
    arg = mock_hdmi_network_instance.send_command.call_args.args[0]
    assert isinstance(arg, KeyPressCommand)
    assert arg.key == key
    assert arg.dst == 5


@pytest.mark.parametrize("direction,key", [("up", 65), ("down", 66)])
async def test_service_volume_release(hass, mock_hdmi_network, direction, key):
    """Test the volume service call with release attribute."""
    await async_setup_component(hass, DOMAIN, {DOMAIN: {}})

    mock_hdmi_network_instance = mock_hdmi_network.return_value

    hass.bus.async_fire(EVENT_HOMEASSISTANT_START)
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        SERVICE_VOLUME,
        {direction: "release"},
        blocking=True,
    )

    mock_hdmi_network_instance.send_command.assert_called_once()
    arg = mock_hdmi_network_instance.send_command.call_args.args[0]
    assert isinstance(arg, KeyReleaseCommand)
    assert arg.dst == 5


@pytest.mark.parametrize(
    "attr,key",
    [
        ("toggle", 67),
        ("on", 101),
        ("off", 102),
        pytest.param(
            "",
            101,
            marks=pytest.mark.xfail(
                reason="The documentation mention it's allowed to pass an empty string, but the schema does not allow this",
                raises=vol.MultipleInvalid,
            ),
        ),
    ],
)
async def test_service_volume_mute(hass, mock_hdmi_network, attr, key):
    """Test the volume service call with mute."""
    await async_setup_component(hass, DOMAIN, {DOMAIN: {}})

    mock_hdmi_network_instance = mock_hdmi_network.return_value

    hass.bus.async_fire(EVENT_HOMEASSISTANT_START)
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        SERVICE_VOLUME,
        {"mute": attr},
        blocking=True,
    )

    assert mock_hdmi_network_instance.send_command.call_count == 2
    assert_key_press_release(mock_hdmi_network_instance.send_command, key=key, dst=5)


@pytest.mark.parametrize(
    "data,expected",
    [
        ({"raw": "20:0D"}, "20:0d"),
        pytest.param(
            {"cmd": "36"},
            "ff:36",
            marks=pytest.mark.xfail(
                reason="String is converted in hex value, the final result looks like 'ff:24', not what you'd expect."
            ),
        ),
        ({"cmd": 54}, "ff:36"),
        pytest.param(
            {"cmd": "36", "src": "1", "dst": "0"},
            "10:36",
            marks=pytest.mark.xfail(
                reason="String is converted in hex value, the final result looks like 'ff:24', not what you'd expect."
            ),
        ),
        ({"cmd": 54, "src": "1", "dst": "0"}, "10:36"),
        pytest.param(
            {"cmd": "64", "src": "1", "dst": "0", "att": "4f:44"},
            "10:64:4f:44",
            marks=pytest.mark.xfail(
                reason="`att` only accepts a int or a HEX value, it seems good to allow for raw data here.",
                raises=vol.MultipleInvalid,
            ),
        ),
        pytest.param(
            {"cmd": "0A", "src": "1", "dst": "0", "att": "1B"},
            "10:0a:1b",
            marks=pytest.mark.xfail(
                reason="The code tries to run `reduce` on this string and fails.",
                raises=TypeError,
            ),
        ),
        pytest.param(
            {"cmd": "0A", "src": "1", "dst": "0", "att": "01"},
            "10:0a:1b",
            marks=pytest.mark.xfail(
                reason="The code tries to run `reduce` on this as an `int` and fails.",
                raises=TypeError,
            ),
        ),
        pytest.param(
            {"cmd": "0A", "src": "1", "dst": "0", "att": ["1B", "44"]},
            "10:0a:1b:44",
            marks=pytest.mark.xfail(
                reason="While the code shows that it's possible to passthrough a list, the call schema does not allow it.",
                raises=(vol.MultipleInvalid, TypeError),
            ),
        ),
    ],
)
async def test_service_send_command(hass, mock_hdmi_network, data, expected):
    """Test the send command service call."""
    await async_setup_component(hass, DOMAIN, {DOMAIN: {}})

    mock_hdmi_network_instance = mock_hdmi_network.return_value

    hass.bus.async_fire(EVENT_HOMEASSISTANT_START)
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        SERVICE_SEND_COMMAND,
        data,
        blocking=True,
    )

    mock_hdmi_network_instance.send_command.assert_called_once()
    command = mock_hdmi_network_instance.send_command.call_args.args[0]
    assert isinstance(command, CecCommand)
    assert str(command) == expected


async def test_watchdog_down(hass, mock_hdmi_network, mock_cec_adapter):
    """Test that the watchdog is initialized and works as expected when adapter is down."""
    adapter_initialized = PropertyMock(return_value=False)
    events = async_capture_events(hass, EVENT_HDMI_CEC_UNAVAILABLE)

    with patch("homeassistant.components.hdmi_cec.event.async_call_later") as mock_call:
        await async_setup_component(hass, DOMAIN, {DOMAIN: {}})

        mock_cec_adapter_instance = mock_cec_adapter.return_value
        type(mock_cec_adapter_instance).initialized = adapter_initialized

        mock_hdmi_network_instance = mock_hdmi_network.return_value

        mock_hdmi_network_instance.set_initialized_callback.assert_called_once()
        callback = mock_hdmi_network_instance.set_initialized_callback.call_args.args[0]
        callback()

        mock_call.assert_called_once_with(hass, WATCHDOG_INTERVAL, ANY)
        watchdog = mock_call.call_args.args[2]
        watchdog()
        await hass.async_block_till_done()

        assert mock_call.call_count == 2
        mock_call.assert_called_with(hass, WATCHDOG_INTERVAL, watchdog)
        adapter_initialized.assert_called_once_with()
        assert len(events) == 1
        mock_cec_adapter_instance.init.assert_called_once_with()


async def test_watchdog_up(hass, mock_hdmi_network, mock_cec_adapter):
    """Test that the watchdog is initialized and works as expected when adapter is up."""
    adapter_initialized = PropertyMock(return_value=True)
    events = async_capture_events(hass, EVENT_HDMI_CEC_UNAVAILABLE)

    with patch("homeassistant.components.hdmi_cec.event.async_call_later") as mock_call:
        await async_setup_component(hass, DOMAIN, {DOMAIN: {}})

        mock_cec_adapter_instance = mock_cec_adapter.return_value
        type(mock_cec_adapter_instance).initialized = adapter_initialized

        mock_hdmi_network_instance = mock_hdmi_network.return_value

        mock_hdmi_network_instance.set_initialized_callback.assert_called_once()
        callback = mock_hdmi_network_instance.set_initialized_callback.call_args.args[0]
        callback()

        mock_call.assert_called_once_with(hass, WATCHDOG_INTERVAL, ANY)
        watchdog = mock_call.call_args.args[2]
        watchdog()
        await hass.async_block_till_done()

        assert mock_call.call_count == 2
        mock_call.assert_called_with(hass, WATCHDOG_INTERVAL, watchdog)
        adapter_initialized.assert_called_once_with()
        assert len(events) == 0
        mock_cec_adapter_instance.init.assert_not_called()
