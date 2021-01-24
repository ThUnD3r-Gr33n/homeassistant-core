"""Test cases around the demo fan platform."""
import pytest

from homeassistant.components import fan
from homeassistant.components.demo.fan import PRESET_MODE_AUTO, PRESET_MODE_SMART
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ENTITY_MATCH_ALL,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.setup import async_setup_component

FULL_FAN_ENTITY_IDS = ["fan.living_room_fan", "fan.percentage_full_fan"]
LIMITED_AND_FULL_FAN_ENTITY_IDS = FULL_FAN_ENTITY_IDS.copy()
LIMITED_AND_FULL_FAN_ENTITY_IDS.extend(
    ["fan.ceiling_fan", "fan.percentage_limited_fan"]
)


@pytest.fixture(autouse=True)
async def setup_comp(hass):
    """Initialize components."""
    assert await async_setup_component(hass, fan.DOMAIN, {"fan": {"platform": "demo"}})
    await hass.async_block_till_done()


@pytest.mark.parametrize("fan_entity_id", LIMITED_AND_FULL_FAN_ENTITY_IDS)
async def test_turn_on(hass, fan_entity_id):
    """Test turning on the device."""
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_OFF

    await hass.services.async_call(
        fan.DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: fan_entity_id}, blocking=True
    )
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_ON


@pytest.mark.parametrize("fan_entity_id", FULL_FAN_ENTITY_IDS)
async def test_turn_on_with_speed_and_percentage(hass, fan_entity_id):
    """Test turning on the device."""
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_OFF
    await hass.services.async_call(
        fan.DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_SPEED: fan.SPEED_HIGH},
        blocking=True,
    )
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_ON
    assert state.attributes[fan.ATTR_SPEED] == fan.SPEED_HIGH
    assert state.attributes[fan.ATTR_PERCENTAGE] == 100

    await hass.services.async_call(
        fan.DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_PERCENTAGE: 100},
        blocking=True,
    )
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_ON
    assert state.attributes[fan.ATTR_SPEED] == fan.SPEED_HIGH
    assert state.attributes[fan.ATTR_PERCENTAGE] == 100


@pytest.mark.parametrize("fan_entity_id", FULL_FAN_ENTITY_IDS)
async def test_turn_on_with_preset_mode(hass, fan_entity_id):
    """Test turning on the device with a preset_mode."""
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_OFF
    await hass.services.async_call(
        fan.DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_PRESET_MODE: PRESET_MODE_AUTO},
        blocking=True,
    )
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_ON
    assert state.attributes[fan.ATTR_SPEED] == PRESET_MODE_AUTO
    assert state.attributes[fan.ATTR_PERCENTAGE] is None
    assert state.attributes[fan.ATTR_PRESET_MODE] == PRESET_MODE_AUTO
    assert state.attributes[fan.ATTR_SPEED_LIST] == [
        fan.SPEED_OFF,
        fan.SPEED_LOW,
        fan.SPEED_MEDIUM,
        fan.SPEED_HIGH,
        PRESET_MODE_AUTO,
        PRESET_MODE_SMART,
    ]
    assert state.attributes[fan.ATTR_PRESET_MODES] == [
        PRESET_MODE_AUTO,
        PRESET_MODE_SMART,
    ]

    await hass.services.async_call(
        fan.DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_PERCENTAGE: 100},
        blocking=True,
    )
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_ON
    assert state.attributes[fan.ATTR_SPEED] == fan.SPEED_HIGH
    assert state.attributes[fan.ATTR_PERCENTAGE] == 100
    assert state.attributes[fan.ATTR_PRESET_MODE] is None

    await hass.services.async_call(
        fan.DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_PRESET_MODE: PRESET_MODE_SMART},
        blocking=True,
    )
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_ON
    assert state.attributes[fan.ATTR_SPEED] == PRESET_MODE_SMART
    assert state.attributes[fan.ATTR_PERCENTAGE] is None
    assert state.attributes[fan.ATTR_PRESET_MODE] == PRESET_MODE_SMART

    await hass.services.async_call(
        fan.DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: fan_entity_id}, blocking=True
    )
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_OFF
    assert state.attributes[fan.ATTR_SPEED] == fan.SPEED_OFF
    assert state.attributes[fan.ATTR_PERCENTAGE] == 0
    assert state.attributes[fan.ATTR_PRESET_MODE] is None

    with pytest.raises(ValueError):
        await hass.services.async_call(
            fan.DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_PRESET_MODE: "invalid"},
            blocking=True,
        )
        await hass.aync_block_till_done()

    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_OFF
    assert state.attributes[fan.ATTR_SPEED] == fan.SPEED_OFF
    assert state.attributes[fan.ATTR_PERCENTAGE] == 0
    assert state.attributes[fan.ATTR_PRESET_MODE] is None


@pytest.mark.parametrize("fan_entity_id", LIMITED_AND_FULL_FAN_ENTITY_IDS)
async def test_turn_off(hass, fan_entity_id):
    """Test turning off the device."""
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_OFF

    await hass.services.async_call(
        fan.DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: fan_entity_id}, blocking=True
    )
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_ON

    await hass.services.async_call(
        fan.DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: fan_entity_id}, blocking=True
    )
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_OFF


@pytest.mark.parametrize("fan_entity_id", LIMITED_AND_FULL_FAN_ENTITY_IDS)
async def test_turn_off_without_entity_id(hass, fan_entity_id):
    """Test turning off all fans."""
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_OFF

    await hass.services.async_call(
        fan.DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: fan_entity_id}, blocking=True
    )
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_ON

    await hass.services.async_call(
        fan.DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: ENTITY_MATCH_ALL}, blocking=True
    )
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_OFF


@pytest.mark.parametrize("fan_entity_id", FULL_FAN_ENTITY_IDS)
async def test_set_direction(hass, fan_entity_id):
    """Test setting the direction of the device."""
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_OFF

    await hass.services.async_call(
        fan.DOMAIN,
        fan.SERVICE_SET_DIRECTION,
        {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_DIRECTION: fan.DIRECTION_REVERSE},
        blocking=True,
    )
    state = hass.states.get(fan_entity_id)
    assert state.attributes[fan.ATTR_DIRECTION] == fan.DIRECTION_REVERSE


@pytest.mark.parametrize("fan_entity_id", FULL_FAN_ENTITY_IDS)
async def test_set_speed(hass, fan_entity_id):
    """Test setting the speed of the device."""
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_OFF

    await hass.services.async_call(
        fan.DOMAIN,
        fan.SERVICE_SET_SPEED,
        {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_SPEED: fan.SPEED_LOW},
        blocking=True,
    )
    state = hass.states.get(fan_entity_id)
    assert state.attributes[fan.ATTR_SPEED] == fan.SPEED_LOW


@pytest.mark.parametrize("fan_entity_id", FULL_FAN_ENTITY_IDS)
async def test_set_preset_mode(hass, fan_entity_id):
    """Test setting the preset mode of the device."""
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_OFF

    await hass.services.async_call(
        fan.DOMAIN,
        fan.SERVICE_SET_PRESET_MODE,
        {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_PRESET_MODE: PRESET_MODE_AUTO},
        blocking=True,
    )
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_ON
    assert state.attributes[fan.ATTR_SPEED] == PRESET_MODE_AUTO
    assert state.attributes[fan.ATTR_PERCENTAGE] is None
    assert state.attributes[fan.ATTR_PRESET_MODE] == PRESET_MODE_AUTO


@pytest.mark.parametrize("fan_entity_id", FULL_FAN_ENTITY_IDS)
async def test_set_percentage(hass, fan_entity_id):
    """Test setting the percentage speed of the device."""
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_OFF

    await hass.services.async_call(
        fan.DOMAIN,
        fan.SERVICE_SET_PERCENTAGE,
        {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_PERCENTAGE: 33},
        blocking=True,
    )
    state = hass.states.get(fan_entity_id)
    assert state.attributes[fan.ATTR_SPEED] == fan.SPEED_LOW
    assert state.attributes[fan.ATTR_PERCENTAGE] == 33


@pytest.mark.parametrize("fan_entity_id", FULL_FAN_ENTITY_IDS)
async def test_oscillate(hass, fan_entity_id):
    """Test oscillating the fan."""
    state = hass.states.get(fan_entity_id)
    assert state.state == STATE_OFF
    assert not state.attributes.get(fan.ATTR_OSCILLATING)

    await hass.services.async_call(
        fan.DOMAIN,
        fan.SERVICE_OSCILLATE,
        {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_OSCILLATING: True},
        blocking=True,
    )
    state = hass.states.get(fan_entity_id)
    assert state.attributes[fan.ATTR_OSCILLATING] is True

    await hass.services.async_call(
        fan.DOMAIN,
        fan.SERVICE_OSCILLATE,
        {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_OSCILLATING: False},
        blocking=True,
    )
    state = hass.states.get(fan_entity_id)
    assert state.attributes[fan.ATTR_OSCILLATING] is False


@pytest.mark.parametrize("fan_entity_id", LIMITED_AND_FULL_FAN_ENTITY_IDS)
async def test_is_on(hass, fan_entity_id):
    """Test is on service call."""
    assert not fan.is_on(hass, fan_entity_id)

    await hass.services.async_call(
        fan.DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: fan_entity_id}, blocking=True
    )
    assert fan.is_on(hass, fan_entity_id)
