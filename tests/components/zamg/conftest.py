"""Fixtures for Zamg integration tests."""
from collections.abc import Generator
import json
from unittest.mock import MagicMock, patch

import pytest

from homeassistant.components.zamg.const import CONF_STATION_ID, DOMAIN
from homeassistant.components.zamg.sensor import ZamgData as ZamgDevice
from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry, load_fixture

TEST_STATION_ID = "11240"
TEST_STATION_NAME = "Graz/Flughafen"


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return the default mocked config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={CONF_STATION_ID: TEST_STATION_ID},
        unique_id=TEST_STATION_ID,
    )


@pytest.fixture
def mock_setup_entry() -> Generator[None, None, None]:
    """Mock setting up a config entry."""
    with patch("homeassistant.components.zamg.async_setup_entry", return_value=True):
        yield


@pytest.fixture
def mock_zamg_config_flow(
    request: pytest.FixtureRequest,
) -> Generator[None, MagicMock, None]:
    """Return a mocked Zamg client."""
    with patch(
        "homeassistant.components.zamg.sensor.ZamgData", autospec=True
    ) as zamg_mock:
        zamg = zamg_mock.return_value
        zamg.update.return_value = ZamgDevice(
            json.loads(load_fixture("zamg/data.json"))
        )
        zamg.get_data.return_value = zamg.get_data(TEST_STATION_ID)
        yield zamg


@pytest.fixture
def mock_zamg(request: pytest.FixtureRequest) -> Generator[None, MagicMock, None]:
    """Return a mocked Zamg client."""
    fixture: str = "zamg/data.json"
    if hasattr(request, "param") and request.param:
        fixture = request.param

    device = ZamgDevice(json.loads(load_fixture(fixture)))
    with patch(
        "homeassistant.components.zamg.sensor.ZamgData", autospec=True
    ) as zamg_mock:
        zamg = zamg_mock.return_value
        zamg.update.return_value = device
        zamg.get_data.return_value = device.get_data(TEST_STATION_ID)
        zamg.current_observations.return_value = ValueError()
        yield zamg


@pytest.fixture
def mock_closest_station(
    request: pytest.FixtureRequest,
) -> Generator[None, MagicMock, None]:
    """Return a mocked Zamg client."""
    with patch(
        "homeassistant.components.zamg.sensor.closest_station", autospec=True
    ) as zamg_mock:
        zamg = zamg_mock.return_value
        zamg.update.return_value = TEST_STATION_ID
        yield zamg


@pytest.fixture
async def init_integration(
    #    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_zamg: MagicMock
    hass: HomeAssistant,
) -> MockConfigEntry:
    """Set up the Zamg integration for testing."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    return mock_config_entry
