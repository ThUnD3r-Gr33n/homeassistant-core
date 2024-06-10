"""Basic coordinator tests."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import EntityRegistry

from tests.common import async_fire_time_changed


async def test_coordinator_simple_update(
    hass: HomeAssistant,
    entity_registry: EntityRegistry,
    init_integration,
    freezer,
    sensor_keys,
) -> None:
    """Run coordinator tests."""
    for key in sensor_keys:
        state = hass.states.get(f"sensor.sunsynk_{key}")
        assert state.state == "unknown"

    freezer.tick(timedelta(seconds=10))
    async_fire_time_changed(hass)  # noqa: F821
    entity_registry.async_update_entity(state.entity_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    for key in sensor_keys:
        state = hass.states.get(f"sensor.sunsynk_{key}")
        assert state.state in ("0", "-0", "3")

    freezer.tick(timedelta(seconds=31))
    async_fire_time_changed(hass)  # noqa: F821
    entity_registry.async_update_entity(state.entity_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    for key in sensor_keys:
        state = hass.states.get(f"sensor.sunsynk_{key}")
        assert state.state in ("0", "-0", "4")


async def test_coordinator_fail_update_and_recover(
    hass: HomeAssistant,
    entity_registry: EntityRegistry,
    init_integration,
    freezer,
    sensor_keys,
) -> None:
    """Run coordinator tests."""
    coordinator = init_integration.runtime_data

    async def raisekeyerror():
        raise KeyError

    coordinator.cache.plants[0].update = raisekeyerror
    freezer.tick(timedelta(seconds=31))
    async_fire_time_changed(hass)  # noqa: F821
    await hass.async_block_till_done(wait_background_tasks=True)
    for key in sensor_keys:
        state = hass.states.get(f"sensor.sunsynk_{key}")
        assert state.state == "unavailable"
    coordinator.cache.plants[0].update = AsyncMock()
    freezer.tick(timedelta(seconds=31))
    async_fire_time_changed(hass)  # noqa: F821
    entity_registry.async_update_entity(state.entity_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    for key in sensor_keys:
        state = hass.states.get(f"sensor.sunsynk_{key}")
        assert state.state in ("0", "-0", "2")
