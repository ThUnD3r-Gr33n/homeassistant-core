"""Common fixtures for the Wyoming tests."""
from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.components.wyoming import DOMAIN, WyomingService
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from . import STT_INFO

from tests.common import MockConfigEntry


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock, None, None]:
    """Override async_setup_entry."""
    with patch(
        "homeassistant.components.wyoming.async_setup_entry", return_value=True
    ) as mock_setup_entry:
        yield mock_setup_entry


@pytest.fixture
def config_entry(hass: HomeAssistant) -> ConfigEntry:
    """Create a config entry."""
    entry = MockConfigEntry(
        domain="wyoming",
        data={
            "host": "1.2.3.4",
            "port": 1234,
        },
        title="Test ASR",
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
async def init_wyoming(hass: HomeAssistant, config_entry: ConfigEntry):
    """Initialize Wyoming."""
    with patch(
        "homeassistant.components.wyoming.config_flow.load_wyoming_info",
        return_value=STT_INFO,
    ):
        await hass.config_entries.async_setup(config_entry.entry_id)


@pytest.fixture
def wyoming_service(hass, config_entry, init_wyoming) -> WyomingService:
    """Return a WyomingService."""
    return hass.data[DOMAIN][config_entry.entry_id]
