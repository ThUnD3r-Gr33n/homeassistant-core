"""Test qwikswitch sensors."""
import asyncio
import logging

from homeassistant.bootstrap import async_setup_component
from homeassistant.components.qwikswitch import DOMAIN as QWIKSWITCH
from homeassistant.const import EVENT_HOMEASSISTANT_START

_LOGGER = logging.getLogger(__name__)


DEVICES = """[
        {"id":"@000001","name":"Switch 1","type":"rel","val":"OFF",
        "time":"1522777506","rssi":"51%"},
        {"id":"@000002","name":"Light 2","type":"rel","val":"ON",
        "time":"1522777507","rssi":"45%"},
        {"id":"@000003","name":"Dim 3","type":"dim","val":"280c00",
        "time":"1522777544","rssi":"62%"}]"""


async def test_binary_sensor_device(hass, aioclient_mock):  # noqa: F811
    """Test a binary sensor device."""
    config = {
        "qwikswitch": {
            "sensors": {"name": "s1", "id": "@a00001", "channel": 1, "type": "imod"}
        }
    }
    aioclient_mock.get("http://127.0.0.1:2020/&device", text=DEVICES)
    aioclient_mock.get("http://127.0.0.1:2020/&listen", long_poll=True)
    await async_setup_component(hass, QWIKSWITCH, config)
    hass.bus.async_fire(EVENT_HOMEASSISTANT_START)
    await hass.async_block_till_done()

    state_obj = hass.states.get("binary_sensor.s1")
    assert state_obj.state == "off"

    aioclient_mock.get(
        "http://127.0.0.1:2020/&listen",
        long_poll=True,
        text='{"id":"@a00001","cmd":"","data":"4e0e1601","rssi":"61%"}',
    )
    await asyncio.sleep(0.01)
    await hass.async_block_till_done()
    state_obj = hass.states.get("binary_sensor.s1")
    assert state_obj.state == "on"

    aioclient_mock.get(
        "http://127.0.0.1:2020/&listen",
        long_poll=True,
        text='{"id":"@a00001","cmd":"","data":"4e0e1701","rssi":"61%"}',
    )
    await asyncio.sleep(0.01)
    await hass.async_block_till_done()
    state_obj = hass.states.get("binary_sensor.s1")
    assert state_obj.state == "off"


async def test_sensor_device(hass, aioclient_mock):  # noqa: F811
    """Test a sensor device."""
    config = {
        "qwikswitch": {
            "sensors": {
                "name": "ss1",
                "id": "@a00001",
                "channel": 1,
                "type": "qwikcord",
            }
        }
    }
    aioclient_mock.get("http://127.0.0.1:2020/&device", text=DEVICES)
    aioclient_mock.get("http://127.0.0.1:2020/&listen", long_poll=True)
    await async_setup_component(hass, QWIKSWITCH, config)
    hass.bus.async_fire(EVENT_HOMEASSISTANT_START)
    await hass.async_block_till_done()

    state_obj = hass.states.get("sensor.ss1")
    assert state_obj.state == "None"

    aioclient_mock.get(
        "http://127.0.0.1:2020/&listen",
        long_poll=True,
        text='{"id":"@a00001","name":"ss1","type":"rel",' '"val":"4733800001a00000"}',
    )
    await asyncio.sleep(0.01)
    await hass.async_block_till_done()
    state_obj = hass.states.get("sensor.ss1")
    assert state_obj.state == "416"
