"""Test the Litter-Robot switch entity."""
from datetime import timedelta

import pytest

from homeassistant.components.litterrobot.hub import REFRESH_WAIT_TIME
from homeassistant.components.switch import (
    DOMAIN as PLATFORM_DOMAIN,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from homeassistant.const import ATTR_ENTITY_ID, STATE_ON
from homeassistant.util.dt import utcnow

from .conftest import setup_hub

from tests.common import async_fire_time_changed

NIGHT_LIGHT_MODE_ENTITY_ID = "switch.test_night_light_mode"
PANEL_LOCKOUT_ENTITY_ID = "switch.test_panel_lockout"


async def test_switch(hass, mock_hub):
    """Tests the switch entity was set up."""
    await setup_hub(hass, mock_hub, PLATFORM_DOMAIN)

    switch = hass.states.get(NIGHT_LIGHT_MODE_ENTITY_ID)
    assert switch
    assert switch.state == STATE_ON


@pytest.mark.parametrize(
    "entity_id,robot_command",
    [
        (NIGHT_LIGHT_MODE_ENTITY_ID, "set_night_light"),
        (PANEL_LOCKOUT_ENTITY_ID, "set_panel_lockout"),
    ],
)
async def test_on_off_commands(hass, mock_hub, entity_id, robot_command):
    """Test sending commands to the switch."""
    await setup_hub(hass, mock_hub, PLATFORM_DOMAIN)

    switch = hass.states.get(entity_id)
    assert switch

    data = {ATTR_ENTITY_ID: entity_id}

    count = 0
    for service in [SERVICE_TURN_ON, SERVICE_TURN_OFF]:
        count += 1
        await hass.services.async_call(
            PLATFORM_DOMAIN,
            service,
            data,
            blocking=True,
        )
        future = utcnow() + timedelta(seconds=REFRESH_WAIT_TIME)
        async_fire_time_changed(hass, future)
        assert getattr(mock_hub.account.robots[0], robot_command).call_count == count
