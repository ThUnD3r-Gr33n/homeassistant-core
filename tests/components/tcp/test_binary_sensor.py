"""The tests for the TCP binary sensor platform."""
from copy import deepcopy
from datetime import timedelta
from unittest.mock import call

import pytest

from homeassistant.components.tcp import DOMAIN
from homeassistant.components.tcp.const import CONF_VALUE_ON, DEFAULT_NAME
from homeassistant.const import (
    CONF_NAME,
    CONF_SSL,
    CONF_TIMEOUT,
    CONF_VALUE_TEMPLATE,
    CONF_VERIFY_SSL,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.setup import async_setup_component

from .conftest import (
    BINARY_SENSOR_TEST_CONFIG,
    HOST_TEST_CONFIG,
    TEST_CONFIG,
    TEST_CONFIG_COMPONENTS,
)

from tests.common import assert_setup_component, async_fire_time_changed

TEST_ENTITY = "binary_sensor.test_name"

KEYS_AND_DEFAULTS = {
    CONF_NAME: DEFAULT_NAME,
    CONF_VALUE_TEMPLATE: None,
    CONF_VALUE_ON: None,
}


async def test_setup_platform_valid_config(hass, mock_socket):
    """Check a valid configuration."""
    with assert_setup_component(1, "binary_sensor"):
        assert await async_setup_component(
            hass, "binary_sensor", TEST_CONFIG_COMPONENTS
        )
        await hass.async_block_till_done()


async def test_setup_platform_invalid_config(hass, mock_socket):
    """Check the invalid configuration."""
    with assert_setup_component(0):
        assert await async_setup_component(
            hass,
            "binary_sensor",
            {"binary_sensor": {"platform": "tcp", "porrt": 1234}},
        )
        await hass.async_block_till_done()


@pytest.mark.parametrize(
    "ssl, verify_ssl, expected_state",
    [(False, False, STATE_OFF), (True, False, STATE_OFF), (True, True, STATE_OFF)],
)
async def test_state(
    hass,
    mock_socket,
    mock_select,
    mock_ssl_context,
    now,
    ssl,
    verify_ssl,
    expected_state,
):
    """Return the contents of _state, updated over SSL."""
    config = deepcopy(TEST_CONFIG)
    config[DOMAIN][0][CONF_SSL] = "on" if ssl else "off"
    config[DOMAIN][0][CONF_VERIFY_SSL] = "on" if verify_ssl else "off"

    assert await async_setup_component(hass, DOMAIN, config)
    await hass.async_block_till_done()

    state = hass.states.get(TEST_ENTITY)

    assert state
    assert state.state == expected_state

    assert mock_socket.connect.called
    assert mock_socket.connect.call_args == call(
        (HOST_TEST_CONFIG["host"], HOST_TEST_CONFIG["port"])
    )

    if not ssl:
        assert mock_socket.send.called
        assert mock_socket.send.call_args == call(
            BINARY_SENSOR_TEST_CONFIG["payload"].encode()
        )
        assert mock_select.call_args == call(
            [mock_socket], [], [], HOST_TEST_CONFIG[CONF_TIMEOUT]
        )

        mock_socket.recv.return_value = b"on"
    else:
        assert mock_ssl_context.called
        assert bool(mock_ssl_context.return_value.check_hostname) == verify_ssl
        mock_ssl_socket = mock_ssl_context.return_value.wrap_socket.return_value
        assert mock_ssl_socket.send.called
        assert mock_ssl_socket.send.call_args == call(
            BINARY_SENSOR_TEST_CONFIG["payload"].encode()
        )
        assert mock_select.call_args == call(
            [mock_ssl_socket], [], [], HOST_TEST_CONFIG[CONF_TIMEOUT]
        )
        assert mock_ssl_socket.recv.called
        assert mock_ssl_socket.recv.call_args == call(HOST_TEST_CONFIG["buffer_size"])

        mock_ssl_socket.recv.return_value = b"on"

    async_fire_time_changed(hass, now + timedelta(seconds=45))
    await hass.async_block_till_done()

    state = hass.states.get(TEST_ENTITY)

    assert state
    assert state.state == STATE_ON


async def test_config_uses_defaults(hass, mock_socket):
    """Check if defaults were set."""
    config = deepcopy(TEST_CONFIG)

    for key in KEYS_AND_DEFAULTS:
        del config[DOMAIN][0]["binary_sensors"][0][key]

    with assert_setup_component(1, DOMAIN) as result_config:
        assert await async_setup_component(hass, DOMAIN, config)
        await hass.async_block_till_done()

    state = hass.states.get("binary_sensor.tcp_sensor")

    assert state
    assert state.state == STATE_OFF

    for key, default in KEYS_AND_DEFAULTS.items():
        assert result_config[DOMAIN][0]["binary_sensors"][0].get(key) == default


async def test_update_select_fails(hass, mock_socket, mock_select):
    """Test select fails to return a socket for reading."""
    mock_select.return_value = (False, False, False)

    assert await async_setup_component(hass, DOMAIN, TEST_CONFIG)
    await hass.async_block_till_done()

    state = hass.states.get(TEST_ENTITY)

    assert state
    assert state.state == STATE_OFF


async def test_update_returns_if_template_render_fails(hass, mock_socket):
    """Return None if rendering the template fails."""
    config = deepcopy(TEST_CONFIG)
    config[DOMAIN][0]["binary_sensors"][0][CONF_VALUE_TEMPLATE] = "{{ value / 0 }}"

    assert await async_setup_component(hass, DOMAIN, config)
    await hass.async_block_till_done()

    state = hass.states.get(TEST_ENTITY)

    assert state
    assert state.state == STATE_OFF
