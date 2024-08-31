"""Tests for the BSB-Lan climate platform."""

from unittest.mock import AsyncMock

from syrupy.assertion import SnapshotAssertion

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
import homeassistant.helpers.entity_registry as er

from . import setup_with_selected_platforms

from tests.common import MockConfigEntry, snapshot_platform


async def test_climate_entity(
    hass: HomeAssistant,
    mock_bsblan: AsyncMock,
    mock_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test the initial parameters."""
    await setup_with_selected_platforms(hass, mock_config_entry, [Platform.CLIMATE])

    await snapshot_platform(hass, entity_registry, snapshot, mock_config_entry.entry_id)

    # Spoof the current_temperature value to "---"
    mock_bsblan.set_current_temperature("---")

    # Update the state in Home Assistant
    await hass.helpers.entity_component.async_update_entity("climate.bsb_lan")

    # Get the state of the climate entity
    state = hass.states.get("climate.bsb_lan")

    # Assert that the current_temperature attribute is None
    assert state.attributes["current_temperature"] is None
