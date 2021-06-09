"""Tests for the Ambee integration."""
from unittest.mock import AsyncMock, MagicMock, patch

from ambee import AmbeeConnectionError

from homeassistant.components.ambee.const import DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry


async def test_load_unload_config_entry(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_ambee: AsyncMock,
) -> None:
    """Test the Ambee configuration entry loading/unloading."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED

    await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert not hass.data.get(DOMAIN)


@patch(
    "homeassistant.components.ambee.Ambee.air_quality",
    side_effect=AmbeeConnectionError,
)
async def test_config_entry_not_ready(
    mock_air_quality: MagicMock,
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test the Ambee configuration entry not ready."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_air_quality.call_count == 1
    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY
