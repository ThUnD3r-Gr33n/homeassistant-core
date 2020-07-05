"""The tests for the Rfxtrx sensor platform."""
from homeassistant.setup import async_setup_component

from . import _signal_event


async def test_default_config(hass, rfxtrx):
    """Test with 0 sensor."""
    await async_setup_component(
        hass, "binary_sensor", {"binary_sensor": {"platform": "rfxtrx", "devices": {}}}
    )
    await hass.async_block_till_done()

    assert len(hass.states.async_all()) == 0


async def test_one(hass, rfxtrx):
    """Test with 1 sensor."""
    await async_setup_component(
        hass,
        "binary_sensor",
        {
            "binary_sensor": {
                "platform": "rfxtrx",
                "devices": {"0a52080705020095220269": {"name": "Test"}},
            }
        },
    )
    await hass.async_block_till_done()

    state = hass.states.get("binary_sensor.test")
    assert state
    assert state.state == "off"
    assert state.attributes.get("friendly_name") == "Test"


async def test_several(hass, rfxtrx):
    """Test with 3."""
    await async_setup_component(
        hass,
        "binary_sensor",
        {
            "binary_sensor": {
                "platform": "rfxtrx",
                "devices": {
                    "0b1100cd0213c7f230010f71": {"name": "Test"},
                    "0b1100100118cdea02010f70": {"name": "Bath"},
                    "0b1100101118cdea02010f70": {"name": "Living"},
                },
            }
        },
    )
    await hass.async_block_till_done()

    state = hass.states.get("binary_sensor.test")
    assert state
    assert state.state == "off"
    assert state.attributes.get("friendly_name") == "Test"

    state = hass.states.get("binary_sensor.bath")
    assert state
    assert state.state == "off"
    assert state.attributes.get("friendly_name") == "Bath"

    state = hass.states.get("binary_sensor.living")
    assert state
    assert state.state == "off"
    assert state.attributes.get("friendly_name") == "Living"


async def test_discover(hass, rfxtrx):
    """Test with discovery."""
    await async_setup_component(
        hass,
        "binary_sensor",
        {"binary_sensor": {"platform": "rfxtrx", "automatic_add": True, "devices": {}}},
    )
    await hass.async_block_till_done()

    await _signal_event(hass, "0b1100100118cdea02010f70")
    state = hass.states.get("binary_sensor.0b1100100118cdea02010f70")
    assert state
    assert state.state == "on"

    await _signal_event(hass, "0b1100100118cdeb02010f70")
    state = hass.states.get("binary_sensor.0b1100100118cdeb02010f70")
    assert state
    assert state.state == "on"

    # Trying to add a sensor
    await _signal_event(hass, "0a52085e070100b31b0279")
    state = hass.states.get("sensor.0a52085e070100b31b0279")
    assert state is None

    # Trying to add a light
    await _signal_event(hass, "0b1100100118cdea02010f70")
    state = hass.states.get("light.0b1100100118cdea02010f70")
    assert state is None

    # Trying to add a rollershutter
    await _signal_event(hass, "0a1400adf394ab020e0060")
    state = hass.states.get("cover.0a1400adf394ab020e0060")
    assert state is None


async def test_discover_noautoadd(hass, rfxtrx):
    """Test with discovery of switch when auto add is False."""
    await async_setup_component(
        hass,
        "binary_sensor",
        {
            "binary_sensor": {
                "platform": "rfxtrx",
                "automatic_add": False,
                "devices": {},
            }
        },
    )
    await hass.async_block_till_done()

    # Trying to add switch
    await _signal_event(hass, "0b1100100118cdea02010f70")
    assert hass.states.async_all() == []
