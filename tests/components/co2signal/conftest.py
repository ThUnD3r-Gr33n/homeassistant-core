"""Fixtures for Electricity maps integration tests."""
from collections.abc import Generator
from unittest.mock import AsyncMock, patch

from aioelectricitymaps import ElectricityMaps
import pytest

from homeassistant.components.co2signal import DOMAIN
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from tests.common import MockConfigEntry
from tests.components.co2signal import VALID_RESPONSE


@pytest.fixture(name="electricity_maps")
def mock_electricity_maps() -> Generator[AsyncMock, None, None]:
    """Mock the ElectricityMaps client."""
    mock = AsyncMock(
        __aenter__=AsyncMock(
            return_value=AsyncMock(
                spec=ElectricityMaps,
                latest_carbon_intensity_by_coordinates=AsyncMock(
                    return_value=VALID_RESPONSE
                ),
                latest_carbon_intensity_by_country_code=AsyncMock(
                    return_value=VALID_RESPONSE
                ),
            )
        ),
        __aexit__=AsyncMock(return_value=None),
    )

    with patch(
        "homeassistant.components.co2signal.ElectricityMaps",
        return_value=mock,
    ):
        yield mock


@pytest.fixture(name="config_entry")
async def mock_config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Return a MockConfigEntry for testing."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={CONF_API_KEY: "api_key", "location": ""},
        entry_id="904a74160aa6f335526706bee85dfb83",
    )


@pytest.fixture(name="setup_integration")
async def mock_setup_integration(
    hass: HomeAssistant, config_entry: MockConfigEntry, electricity_maps: AsyncMock
) -> None:
    """Fixture for setting up the component."""
    config_entry.add_to_hass(hass)

    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
