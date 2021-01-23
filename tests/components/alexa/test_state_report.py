"""Test report state."""
import asyncio
from unittest.mock import Mock, patch

from homeassistant import core
from homeassistant.components.alexa import state_report

from . import DEFAULT_CONFIG, TEST_URL


async def test_report_state(hass, aioclient_mock):
    """Test proactive state reports."""
    aioclient_mock.post(TEST_URL, text="", status=202)

    hass.states.async_set(
        "binary_sensor.test_contact",
        "on",
        {"friendly_name": "Test Contact Sensor", "device_class": "door"},
    )

    await state_report.async_enable_proactive_mode(hass, DEFAULT_CONFIG)

    hass.states.async_set(
        "binary_sensor.test_contact",
        "off",
        {"friendly_name": "Test Contact Sensor", "device_class": "door"},
    )

    # To trigger event listener
    await hass.async_block_till_done()

    assert len(aioclient_mock.mock_calls) == 1
    call = aioclient_mock.mock_calls

    call_json = call[0][2]
    assert call_json["event"]["header"]["namespace"] == "Alexa"
    assert call_json["event"]["header"]["name"] == "ChangeReport"
    assert (
        call_json["event"]["payload"]["change"]["properties"][0]["value"]
        == "NOT_DETECTED"
    )
    assert call_json["event"]["endpoint"]["endpointId"] == "binary_sensor#test_contact"


async def test_report_state_instance(hass, aioclient_mock):
    """Test proactive state reports with instance."""
    aioclient_mock.post(TEST_URL, text="", status=202)

    hass.states.async_set(
        "fan.test_fan",
        "off",
        {
            "friendly_name": "Test fan",
            "supported_features": 3,
            "speed": "off",
            "speed_list": ["off", "low", "high"],
            "oscillating": False,
        },
    )

    await state_report.async_enable_proactive_mode(hass, DEFAULT_CONFIG)

    hass.states.async_set(
        "fan.test_fan",
        "on",
        {
            "friendly_name": "Test fan",
            "supported_features": 3,
            "speed": "high",
            "speed_list": ["off", "low", "high"],
            "oscillating": True,
        },
    )

    # To trigger event listener
    await hass.async_block_till_done()

    assert len(aioclient_mock.mock_calls) == 1
    call = aioclient_mock.mock_calls

    call_json = call[0][2]
    assert call_json["event"]["header"]["namespace"] == "Alexa"
    assert call_json["event"]["header"]["name"] == "ChangeReport"

    change_reports = call_json["event"]["payload"]["change"]["properties"]
    for report in change_reports:
        if report["name"] == "toggleState":
            assert report["value"] == "ON"
            assert report["instance"] == "fan.oscillating"
            assert report["namespace"] == "Alexa.ToggleController"

    assert call_json["event"]["endpoint"]["endpointId"] == "fan#test_fan"


async def test_send_add_or_update_message(hass, aioclient_mock):
    """Test sending an AddOrUpdateReport message."""
    aioclient_mock.post(TEST_URL, text="")

    hass.states.async_set(
        "binary_sensor.test_contact",
        "on",
        {"friendly_name": "Test Contact Sensor", "device_class": "door"},
    )

    await state_report.async_send_add_or_update_message(
        hass, DEFAULT_CONFIG, ["binary_sensor.test_contact", "zwave.bla"]
    )

    assert len(aioclient_mock.mock_calls) == 1
    call = aioclient_mock.mock_calls

    call_json = call[0][2]
    assert call_json["event"]["header"]["namespace"] == "Alexa.Discovery"
    assert call_json["event"]["header"]["name"] == "AddOrUpdateReport"
    assert len(call_json["event"]["payload"]["endpoints"]) == 1
    assert (
        call_json["event"]["payload"]["endpoints"][0]["endpointId"]
        == "binary_sensor#test_contact"
    )


async def test_send_delete_message(hass, aioclient_mock):
    """Test sending an AddOrUpdateReport message."""
    aioclient_mock.post(TEST_URL, json={"data": "is irrelevant"})

    hass.states.async_set(
        "binary_sensor.test_contact",
        "on",
        {"friendly_name": "Test Contact Sensor", "device_class": "door"},
    )

    await state_report.async_send_delete_message(
        hass, DEFAULT_CONFIG, ["binary_sensor.test_contact", "zwave.bla"]
    )

    assert len(aioclient_mock.mock_calls) == 1
    call = aioclient_mock.mock_calls

    call_json = call[0][2]
    assert call_json["event"]["header"]["namespace"] == "Alexa.Discovery"
    assert call_json["event"]["header"]["name"] == "DeleteReport"
    assert len(call_json["event"]["payload"]["endpoints"]) == 1
    assert (
        call_json["event"]["payload"]["endpoints"][0]["endpointId"]
        == "binary_sensor#test_contact"
    )


async def test_doorbell_event(hass, aioclient_mock):
    """Test doorbell press reports."""
    aioclient_mock.post(TEST_URL, text="", status=202)

    hass.states.async_set(
        "binary_sensor.test_doorbell",
        "off",
        {"friendly_name": "Test Doorbell Sensor", "device_class": "occupancy"},
    )

    await state_report.async_enable_proactive_mode(hass, DEFAULT_CONFIG)

    hass.states.async_set(
        "binary_sensor.test_doorbell",
        "on",
        {"friendly_name": "Test Doorbell Sensor", "device_class": "occupancy"},
    )

    # To trigger event listener
    await hass.async_block_till_done()

    assert len(aioclient_mock.mock_calls) == 1
    call = aioclient_mock.mock_calls

    call_json = call[0][2]
    assert call_json["event"]["header"]["namespace"] == "Alexa.DoorbellEventSource"
    assert call_json["event"]["header"]["name"] == "DoorbellPress"
    assert call_json["event"]["payload"]["cause"]["type"] == "PHYSICAL_INTERACTION"
    assert call_json["event"]["endpoint"]["endpointId"] == "binary_sensor#test_doorbell"


async def test_proactive_mode_filter_states(hass, aioclient_mock):
    """Test all the cases that filter states."""
    hass.states.async_set(
        "binary_sensor.test_contact",
        "on",
        {"friendly_name": "Test Contact Sensor", "device_class": "door"},
    )

    await state_report.async_enable_proactive_mode(hass, DEFAULT_CONFIG)

    # Force update should not report
    hass.states.async_set(
        "binary_sensor.test_contact",
        "on",
        {"friendly_name": "Test Contact Sensor", "device_class": "door"},
        force_update=True,
    )
    await hass.async_block_till_done()
    await hass.async_block_till_done()
    assert len(aioclient_mock.mock_calls) == 0

    # hass not running should not report
    hass.states.async_set(
        "binary_sensor.test_contact",
        "off",
        {"friendly_name": "Test Contact Sensor", "device_class": "door"},
    )
    with patch.object(hass, "state", core.CoreState.stopping):
        await hass.async_block_till_done()
        await hass.async_block_till_done()
    assert len(aioclient_mock.mock_calls) == 0

    # unsupported entity should not report
    hass.states.async_set(
        "binary_sensor.test_contact",
        "on",
        {"friendly_name": "Test Contact Sensor", "device_class": "door"},
    )
    with patch.dict(
        "homeassistant.components.alexa.state_report.ENTITY_ADAPTERS", {}, clear=True
    ):
        await hass.async_block_till_done()
        await hass.async_block_till_done()
    assert len(aioclient_mock.mock_calls) == 0

    # Not exposed by config should not report
    hass.states.async_set(
        "binary_sensor.test_contact",
        "off",
        {"friendly_name": "Test Contact Sensor", "device_class": "door"},
    )
    with patch.object(DEFAULT_CONFIG, "should_expose", return_value=False):
        await hass.async_block_till_done()
        await hass.async_block_till_done()
    assert len(aioclient_mock.mock_calls) == 0

    # Removing an entity
    hass.states.async_remove("binary_sensor.test_contact")
    await hass.async_block_till_done()
    await hass.async_block_till_done()
    assert len(aioclient_mock.mock_calls) == 0


async def test_proactive_mode_filter_in_progress(hass, aioclient_mock):
    """When in progress, queue up state."""
    hass.states.async_set(
        "binary_sensor.test_contact",
        "off",
        {"friendly_name": "Test Contact Sensor", "device_class": "door"},
    )

    await state_report.async_enable_proactive_mode(hass, DEFAULT_CONFIG)

    # Progress should filter out the 2nd event.
    long_sendchange = asyncio.Event()

    with patch(
        "homeassistant.components.alexa.state_report.async_send_changereport_message",
        Mock(side_effect=lambda *args: long_sendchange.wait()),
    ) as mock_report:
        hass.states.async_set(
            "binary_sensor.test_contact",
            "on",
            {
                "friendly_name": "Test Contact Sensor",
                "device_class": "door",
                "update": 1,
            },
        )

        await asyncio.sleep(0)
        await asyncio.sleep(0)
        await asyncio.sleep(0)

    assert len(mock_report.mock_calls) == 1

    with patch(
        "homeassistant.components.alexa.state_report.async_send_changereport_message",
    ) as mock_report_2:
        hass.states.async_set(
            "binary_sensor.test_contact",
            "off",
            {
                "friendly_name": "Test Contact Sensor",
                "device_class": "door",
                "update": 2,
            },
        )
        hass.states.async_set(
            "binary_sensor.test_contact",
            "on",
            {
                "friendly_name": "Test Contact Sensor",
                "device_class": "door",
                "update": 3,
            },
        )
        hass.states.async_set(
            "binary_sensor.test_contact",
            "off",
            {
                "friendly_name": "Test Contact Sensor",
                "device_class": "door",
                "update": 4,
            },
        )

        await asyncio.sleep(0)
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        long_sendchange.set()
        await hass.async_block_till_done()

    # Should be 1 because the 4rd state change
    assert len(mock_report_2.mock_calls) == 1
    mock_report_2.mock_calls[0][1][2].entity.attributes["update"] == 4
