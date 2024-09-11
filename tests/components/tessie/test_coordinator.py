"""Test the Tessie sensor platform."""

from copy import deepcopy
from datetime import timedelta
from unittest.mock import AsyncMock

from freezegun.api import FrozenDateTimeFactory
from tesla_fleet_api.exceptions import Forbidden, InvalidToken

from homeassistant.components.tessie.coordinator import (
    TESSIE_FLEET_API_SYNC_INTERVAL,
    TESSIE_SYNC_INTERVAL,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE, Platform
from homeassistant.core import HomeAssistant

from .common import (
    ERROR_AUTH,
    ERROR_CONNECTION,
    ERROR_UNKNOWN,
    TEST_VEHICLE_STATE_ONLINE,
    setup_platform,
)

from tests.common import async_fire_time_changed

WAIT = timedelta(seconds=TESSIE_SYNC_INTERVAL)


async def test_coordinator(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, mock_get_state: AsyncMock
) -> None:
    """Tests that the coordinator updates vehicles."""

    await setup_platform(hass, [Platform.BINARY_SENSOR])

    # Since the fixture data is old, the status will be offline
    assert hass.states.get("binary_sensor.test_status").state == STATE_OFF

    # Trigger a coordinator refresh
    freezer.tick(WAIT)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    mock_get_state.assert_called_once()

    # Since the fixture data is old, the status will be offline
    assert hass.states.get("binary_sensor.test_status").state == STATE_OFF

    # Update the fixture to be "current"
    mock_get_state.reset_mock()
    future = freezer.tick(WAIT)
    data = deepcopy(TEST_VEHICLE_STATE_ONLINE)
    data["vehicle_state"]["timestamp"] = int(future.timestamp() * 1000)
    mock_get_state.return_value = data

    # Trigger a coordinator refresh
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    mock_get_state.assert_called_once()

    # Since the timestamp is now current, the state will be online
    assert hass.states.get("binary_sensor.test_status").state == STATE_ON


async def test_coordinator_clienterror(
    hass: HomeAssistant, mock_get_state: AsyncMock, freezer: FrozenDateTimeFactory
) -> None:
    """Tests that the coordinator handles client errors."""

    mock_get_state.side_effect = ERROR_UNKNOWN
    await setup_platform(hass, [Platform.BINARY_SENSOR])

    freezer.tick(WAIT)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    mock_get_state.assert_called_once()

    assert hass.states.get("binary_sensor.test_status").state == STATE_UNAVAILABLE


async def test_coordinator_auth(
    hass: HomeAssistant, mock_get_state: AsyncMock, freezer: FrozenDateTimeFactory
) -> None:
    """Tests that the coordinator handles auth errors."""

    mock_get_state.side_effect = ERROR_AUTH
    await setup_platform(hass, [Platform.BINARY_SENSOR])

    freezer.tick(WAIT)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    mock_get_state.assert_called_once()


async def test_coordinator_connection(
    hass: HomeAssistant, mock_get_state: AsyncMock, freezer: FrozenDateTimeFactory
) -> None:
    """Tests that the coordinator handles connection errors."""

    mock_get_state.side_effect = ERROR_CONNECTION
    await setup_platform(hass, [Platform.BINARY_SENSOR])
    freezer.tick(WAIT)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert hass.states.get("binary_sensor.test_status").state == STATE_UNAVAILABLE


async def test_coordinator_live_error(
    hass: HomeAssistant, mock_live_status: AsyncMock, freezer: FrozenDateTimeFactory
) -> None:
    """Tests that the energy live coordinator handles fleet errors."""

    await setup_platform(hass, [Platform.SENSOR])

    mock_live_status.reset_mock()
    mock_live_status.side_effect = Forbidden
    freezer.tick(TESSIE_FLEET_API_SYNC_INTERVAL)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    mock_live_status.assert_called_once()
    assert hass.states.get("sensor.energy_site_solar_power").state == STATE_UNAVAILABLE


async def test_coordinator_info_error(
    hass: HomeAssistant, mock_site_info: AsyncMock, freezer: FrozenDateTimeFactory
) -> None:
    """Tests that the energy info coordinator handles fleet errors."""

    await setup_platform(hass, [Platform.SENSOR])

    mock_site_info.reset_mock()
    mock_site_info.side_effect = Forbidden
    freezer.tick(TESSIE_FLEET_API_SYNC_INTERVAL)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    mock_site_info.assert_called_once()
    assert (
        hass.states.get("sensor.energy_site_vpp_backup_reserve").state
        == STATE_UNAVAILABLE
    )


async def test_coordinator_live_reauth(
    hass: HomeAssistant, mock_live_status: AsyncMock
) -> None:
    """Tests that the energy live coordinator handles auth errors."""

    mock_live_status.side_effect = InvalidToken
    entry = await setup_platform(hass, [Platform.SENSOR])
    assert entry.state is ConfigEntryState.SETUP_ERROR


async def test_coordinator_info_reauth(
    hass: HomeAssistant, mock_site_info: AsyncMock
) -> None:
    """Tests that the energy info coordinator handles auth errors."""

    mock_site_info.side_effect = InvalidToken
    entry = await setup_platform(hass, [Platform.SENSOR])
    assert entry.state is ConfigEntryState.SETUP_ERROR
