"""Test the MySensors config flow."""
from typing import Dict
from unittest.mock import patch

import pytest

from homeassistant import config_entries, setup
from homeassistant.components.mysensors.const import (
    CONF_BAUD_RATE,
    CONF_DEVICE,
    CONF_GATEWAY_TYPE,
    CONF_GATEWAY_TYPE_MQTT,
    CONF_GATEWAY_TYPE_SERIAL,
    CONF_GATEWAY_TYPE_TCP,
    CONF_PERSISTENCE,
    CONF_PERSISTENCE_FILE,
    CONF_RETAIN,
    CONF_TCP_PORT,
    CONF_TOPIC_IN_PREFIX,
    CONF_TOPIC_OUT_PREFIX,
    CONF_VERSION,
    DOMAIN,
    ConfGatewayType,
)
from homeassistant.helpers.typing import HomeAssistantType


async def get_form(
    hass: HomeAssistantType, gatway_type: ConfGatewayType, expected_step_id: str
):
    """Get a form for the given gateway type."""
    await setup.async_setup_component(hass, "persistent_notification", {})
    stepuser = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert stepuser["type"] == "form"
    assert not stepuser["errors"]

    result = await hass.config_entries.flow.async_configure(
        stepuser["flow_id"],
        {CONF_GATEWAY_TYPE: gatway_type},
    )
    await hass.async_block_till_done()
    assert result["type"] == "form"
    assert result["step_id"] == expected_step_id

    return result


async def test_config_mqtt(hass: HomeAssistantType):
    """Test configuring a mqtt gateway."""
    step = await get_form(hass, CONF_GATEWAY_TYPE_MQTT, "gw_mqtt")
    flow_id = step["flow_id"]

    with patch(
        "homeassistant.components.mysensors.async_setup", return_value=True
    ) as mock_setup, patch(
        "homeassistant.components.mysensors.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            flow_id,
            {
                CONF_RETAIN: True,
                CONF_TOPIC_IN_PREFIX: "bla",
                CONF_TOPIC_OUT_PREFIX: "blub",
                CONF_VERSION: "2.4",
            },
        )
        await hass.async_block_till_done()

    if "errors" in result2:
        assert not result2["errors"]
    assert result2["type"] == "create_entry"
    assert result2["title"] == "mqtt"
    assert result2["data"] == {
        CONF_DEVICE: "mqtt",
        CONF_RETAIN: True,
        CONF_TOPIC_IN_PREFIX: "bla",
        CONF_TOPIC_OUT_PREFIX: "blub",
        CONF_VERSION: "2.4",
    }
    assert len(mock_setup.mock_calls) == 1
    assert len(mock_setup_entry.mock_calls) == 1


async def test_config_serial(hass: HomeAssistantType):
    """Test configuring a gateway via serial."""
    step = await get_form(hass, CONF_GATEWAY_TYPE_SERIAL, "gw_serial")
    flowid = step["flow_id"]

    with patch(  # mock is_serial_port because otherwise the test will be platform dependent (/dev/ttyACMx vs COMx)
        "homeassistant.components.mysensors.config_flow.is_serial_port",
        return_value=True,
    ), patch(
        "homeassistant.components.mysensors.config_flow.try_connect", return_value=True
    ), patch(
        "homeassistant.components.mysensors.async_setup", return_value=True
    ) as mock_setup, patch(
        "homeassistant.components.mysensors.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            flowid,
            {
                CONF_BAUD_RATE: 115200,
                CONF_DEVICE: "/dev/ttyACM0",
                CONF_VERSION: "2.4",
            },
        )
        await hass.async_block_till_done()

    if "errors" in result2:
        assert not result2["errors"]
    assert result2["type"] == "create_entry"
    assert result2["title"] == "/dev/ttyACM0"
    assert result2["data"] == {
        CONF_DEVICE: "/dev/ttyACM0",
        CONF_BAUD_RATE: 115200,
        CONF_VERSION: "2.4",
    }
    assert len(mock_setup.mock_calls) == 1
    assert len(mock_setup_entry.mock_calls) == 1


async def test_config_tcp(hass: HomeAssistantType):
    """Test configuring a gateway via tcp."""
    step = await get_form(hass, CONF_GATEWAY_TYPE_TCP, "gw_tcp")
    flowid = step["flow_id"]

    with patch(
        "homeassistant.components.mysensors.config_flow.try_connect", return_value=True
    ), patch(
        "homeassistant.components.mysensors.async_setup", return_value=True
    ) as mock_setup, patch(
        "homeassistant.components.mysensors.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            flowid,
            {
                CONF_TCP_PORT: 5003,
                CONF_DEVICE: "127.0.0.1",
                CONF_VERSION: "2.4",
            },
        )
        await hass.async_block_till_done()

    if "errors" in result2:
        assert not result2["errors"]
    assert result2["type"] == "create_entry"
    assert result2["title"] == "127.0.0.1"
    assert result2["data"] == {
        CONF_DEVICE: "127.0.0.1",
        CONF_TCP_PORT: 5003,
        CONF_VERSION: "2.4",
    }
    assert len(mock_setup.mock_calls) == 1
    assert len(mock_setup_entry.mock_calls) == 1


async def test_fail_to_connect(hass: HomeAssistantType):
    """Test configuring a gateway via tcp."""
    step = await get_form(hass, CONF_GATEWAY_TYPE_TCP, "gw_tcp")
    flowid = step["flow_id"]

    with patch(
        "homeassistant.components.mysensors.config_flow.try_connect", return_value=False
    ), patch(
        "homeassistant.components.mysensors.async_setup", return_value=True
    ) as mock_setup, patch(
        "homeassistant.components.mysensors.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            flowid,
            {
                CONF_TCP_PORT: 5003,
                CONF_DEVICE: "127.0.0.1",
                CONF_VERSION: "2.4",
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == "form"
    assert "errors" in result2
    assert "base" in result2["errors"]
    assert result2["errors"]["base"] == "cannot_connect"
    assert len(mock_setup.mock_calls) == 0
    assert len(mock_setup_entry.mock_calls) == 0


@pytest.mark.parametrize(
    "gateway_type, expected_step_id, user_input, err_field, err_string",
    [
        (
            CONF_GATEWAY_TYPE_TCP,
            "gw_tcp",
            {
                CONF_TCP_PORT: 600_000,
                CONF_DEVICE: "127.0.0.1",
                CONF_VERSION: "2.4",
            },
            CONF_TCP_PORT,
            "port_out_of_range",
        ),
        (
            CONF_GATEWAY_TYPE_TCP,
            "gw_tcp",
            {
                CONF_TCP_PORT: 0,
                CONF_DEVICE: "127.0.0.1",
                CONF_VERSION: "2.4",
            },
            CONF_TCP_PORT,
            "port_out_of_range",
        ),
        (
            CONF_GATEWAY_TYPE_TCP,
            "gw_tcp",
            {
                CONF_TCP_PORT: 5003,
                CONF_DEVICE: "127.0.0.1",
                CONF_VERSION: "a",
            },
            CONF_VERSION,
            "invalid_version",
        ),
        (
            CONF_GATEWAY_TYPE_TCP,
            "gw_tcp",
            {
                CONF_TCP_PORT: 5003,
                CONF_DEVICE: "127.0.0.1",
                CONF_VERSION: "a.b",
            },
            CONF_VERSION,
            "invalid_version",
        ),
        (
            CONF_GATEWAY_TYPE_TCP,
            "gw_tcp",
            {
                CONF_TCP_PORT: 5003,
                CONF_DEVICE: "127.0.0.1",
            },
            CONF_VERSION,
            "invalid_version",
        ),
        (
            CONF_GATEWAY_TYPE_TCP,
            "gw_tcp",
            {
                CONF_TCP_PORT: 5003,
                CONF_DEVICE: "127.0.0.",
            },
            CONF_DEVICE,
            "invalid_ip",
        ),
        (
            CONF_GATEWAY_TYPE_TCP,
            "gw_tcp",
            {
                CONF_TCP_PORT: 5003,
                CONF_DEVICE: "abcd",
            },
            CONF_DEVICE,
            "invalid_ip",
        ),
        (
            CONF_GATEWAY_TYPE_MQTT,
            "gw_mqtt",
            {
                CONF_RETAIN: True,
                CONF_TOPIC_IN_PREFIX: "bla",
                CONF_TOPIC_OUT_PREFIX: "blub",
                CONF_PERSISTENCE_FILE: "asdf.zip",
                CONF_VERSION: "2.4",
            },
            CONF_PERSISTENCE_FILE,
            "invalid_persistence_file",
        ),
        (
            CONF_GATEWAY_TYPE_MQTT,
            "gw_mqtt",
            {
                CONF_RETAIN: True,
                CONF_TOPIC_IN_PREFIX: "/#/#",
                CONF_TOPIC_OUT_PREFIX: "blub",
                CONF_VERSION: "2.4",
            },
            CONF_TOPIC_IN_PREFIX,
            "invalid_subscribe_topic",
        ),
        (
            CONF_GATEWAY_TYPE_MQTT,
            "gw_mqtt",
            {
                CONF_RETAIN: True,
                CONF_TOPIC_IN_PREFIX: "asdf",
                CONF_TOPIC_OUT_PREFIX: "/#/#",
                CONF_VERSION: "2.4",
            },
            CONF_TOPIC_OUT_PREFIX,
            "invalid_publish_topic",
        ),
    ],
)
async def test_config_invalid(
    hass: HomeAssistantType,
    gateway_type: ConfGatewayType,
    expected_step_id: str,
    user_input: Dict[str, any],
    err_field,
    err_string,
):
    """Perform a test that is expected to generate an error."""
    step = await get_form(hass, gateway_type, expected_step_id)
    flowid = step["flow_id"]

    with patch(
        "homeassistant.components.mysensors.config_flow.try_connect", return_value=True
    ), patch(
        "homeassistant.components.mysensors.async_setup", return_value=True
    ) as mock_setup, patch(
        "homeassistant.components.mysensors.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            flowid,
            user_input,
        )
        await hass.async_block_till_done()

    assert result2["type"] == "form"
    assert "errors" in result2
    assert err_field in result2["errors"]
    assert result2["errors"][err_field] == err_string
    assert len(mock_setup.mock_calls) == 0
    assert len(mock_setup_entry.mock_calls) == 0


@pytest.mark.parametrize(
    "user_input",
    [
        {
            CONF_DEVICE: "COM5",
            CONF_BAUD_RATE: 57600,
            CONF_TCP_PORT: 5003,
            CONF_RETAIN: True,
            CONF_VERSION: "2.3",
            CONF_PERSISTENCE_FILE: "bla.json",
        },
        {
            CONF_DEVICE: "COM5",
            CONF_PERSISTENCE_FILE: "bla.json",
            CONF_BAUD_RATE: 57600,
            CONF_TCP_PORT: 5003,
            CONF_VERSION: "2.3",
            CONF_PERSISTENCE: False,
            CONF_RETAIN: True,
        },
        {
            CONF_DEVICE: "mqtt",
            CONF_BAUD_RATE: 115200,
            CONF_TCP_PORT: 5003,
            CONF_TOPIC_IN_PREFIX: "intopic",
            CONF_TOPIC_OUT_PREFIX: "outtopic",
            CONF_VERSION: "2.4",
            CONF_PERSISTENCE: False,
            CONF_RETAIN: False,
        },
        {
            CONF_DEVICE: "127.0.0.1",
            CONF_PERSISTENCE_FILE: "blub.pickle",
            CONF_BAUD_RATE: 115200,
            CONF_TCP_PORT: 343,
            CONF_VERSION: "2.4",
            CONF_PERSISTENCE: False,
            CONF_RETAIN: False,
        },
    ],
)
async def test_import(hass: HomeAssistantType, user_input: Dict):
    """Test importing a gateway."""
    await setup.async_setup_component(hass, "persistent_notification", {})

    with patch("sys.platform", "win32"), patch(
        "homeassistant.components.mysensors.config_flow.try_connect", return_value=True
    ), patch(
        "homeassistant.components.mysensors.async_setup_entry",
        return_value=True,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, data=user_input, context={"source": config_entries.SOURCE_IMPORT}
        )
        await hass.async_block_till_done()

    assert result["type"] == "create_entry"
