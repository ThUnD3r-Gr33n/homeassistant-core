"""Test Schlage select."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


async def test_select(
    hass: HomeAssistant, mock_added_config_entry: ConfigEntry
) -> None:
    """Test the battery sensor."""
    select = hass.states.get("select.vault_door_auto_lock_time")
    assert select is not None
    assert select.state == "15 seconds"
