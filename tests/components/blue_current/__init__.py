"""Tests for the Blue Current integration."""
from __future__ import annotations

from asyncio import Event, Future
from functools import partial
from unittest.mock import MagicMock, patch

from bluecurrent_api import Client

from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry

DEFAULT_CHARGE_POINT = {
    "evse_id": "101",
    "model_type": "",
    "name": "",
}


async def start_loop(client, future: Future | None, receiver):
    """Set the receiver."""
    client.receiver = receiver

    client.started_loop.set()
    client.started_loop.clear()

    if future and not future.done():
        await future


async def get_charge_points(client, charge_point: dict) -> None:
    """Send a list of charge points to the callback."""
    await client.started_loop.wait()
    await client.receiver(
        {
            "object": "CHARGE_POINTS",
            "data": [charge_point],
        }
    )


async def get_status(client, status: dict, evse_id: str) -> None:
    """Send the status of a charge point to the callback."""
    await client.receiver(
        {
            "object": "CH_STATUS",
            "data": {"evse_id": evse_id} | status,
        }
    )


async def get_grid_status(client, grid: dict, evse_id: str) -> None:
    """Send the grid status to the callback."""
    await client.receiver({"object": "GRID_STATUS", "data": grid})


def create_client_mock(
    loop_future: Future | None,
    charge_point: dict,
    status: dict | None,
    grid: dict | None,
) -> MagicMock:
    """Create a mock of the bluecurrent-api Client."""
    client_mock = MagicMock(spec=Client)

    client_mock.started_loop = Event()

    client_mock.start_loop.side_effect = partial(start_loop, client_mock, loop_future)
    client_mock.get_charge_points.side_effect = partial(
        get_charge_points, client_mock, charge_point
    )
    client_mock.get_status.side_effect = partial(get_status, client_mock, status)
    client_mock.get_grid_status.side_effect = partial(
        get_grid_status, client_mock, grid
    )

    return client_mock


async def init_integration(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    platform="",
    charge_point: dict | None = None,
    status: dict | None = None,
    grid: dict | None = None,
    loop_future: Future | None = None,
) -> MagicMock:
    """Set up the Blue Current integration in Home Assistant."""

    if charge_point is None:
        charge_point = DEFAULT_CHARGE_POINT

    client_mock = create_client_mock(loop_future, charge_point, status, grid)

    with patch("homeassistant.components.blue_current.PLATFORMS", [platform]), patch(
        "homeassistant.components.blue_current.Client", return_value=client_mock
    ):
        config_entry.add_to_hass(hass)

        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
    return client_mock
