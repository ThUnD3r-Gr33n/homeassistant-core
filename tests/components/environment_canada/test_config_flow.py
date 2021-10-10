"""Test the Environment Canada (EC) config flow."""
from unittest.mock import MagicMock, Mock, patch
import xml.etree.ElementTree as et

import aiohttp
import pytest

from homeassistant import config_entries, data_entry_flow, setup
from homeassistant.components.environment_canada.const import (
    CONF_LANGUAGE,
    CONF_STATION,
    DOMAIN,
)
from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE

from tests.common import MockConfigEntry

FAKE_CONFIG = {
    CONF_STATION: "ON/s1234567",
    CONF_LANGUAGE: "English",
    CONF_LATITUDE: 42.42,
    CONF_LONGITUDE: -42.42,
}
FAKE_TITLE = "Universal title!"


def mocked_ec(
    station_id=FAKE_CONFIG[CONF_STATION],
    lat=FAKE_CONFIG[CONF_LATITUDE],
    lon=FAKE_CONFIG[CONF_LONGITUDE],
    lang=FAKE_CONFIG[CONF_LANGUAGE],
    update=None,
    metadata={"location": FAKE_TITLE},
):
    """Mock the env_canada library."""
    ec_mock = MagicMock()
    ec_mock.station_id = station_id
    ec_mock.lat = lat
    ec_mock.lon = lon
    ec_mock.language = lang
    ec_mock.metadata = metadata

    if update:
        ec_mock.update = update
    else:
        ec_mock.update = Mock()

    return patch(
        "homeassistant.components.environment_canada.config_flow.ECData",
        return_value=ec_mock,
    )


async def test_form(hass):
    """Test we get the form."""
    await setup.async_setup_component(hass, "persistent_notification", {})

    with mocked_ec(), patch(
        "homeassistant.components.environment_canada.async_setup_entry",
        return_value=True,
    ):
        flow = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert flow["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert flow["errors"] == {}

        result = await hass.config_entries.flow.async_configure(
            flow["flow_id"], FAKE_CONFIG
        )
        await hass.async_block_till_done()
        assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
        assert result["data"] == FAKE_CONFIG
        assert result["title"] == FAKE_TITLE
        assert flow["errors"] == {}


async def test_create_same_entry_twice(hass):
    """Test duplicate entries."""
    await setup.async_setup_component(hass, "persistent_notification", {})

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=FAKE_CONFIG,
        unique_id="ON/s1234567-english",
    )
    entry.add_to_hass(hass)

    with mocked_ec(), patch(
        "homeassistant.components.environment_canada.async_setup_entry",
        return_value=True,
    ):
        flow = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            flow["flow_id"], FAKE_CONFIG
        )
        await hass.async_block_till_done()
        assert result["type"] == data_entry_flow.RESULT_TYPE_ABORT


async def test_too_many_attempts(hass):
    """Test hitting rate limit."""
    await setup.async_setup_component(hass, "persistent_notification", {})

    with mocked_ec(metadata={}), patch(
        "homeassistant.components.environment_canada.async_setup_entry",
        return_value=True,
    ):
        flow = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            flow["flow_id"],
            {},
        )
        await hass.async_block_till_done()
        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["errors"] == {"base": "too_many_attempts"}


@pytest.mark.parametrize(
    "error",
    [
        (aiohttp.ClientResponseError(Mock(), (), status=404), "bad_station_id"),
        (aiohttp.ClientResponseError(Mock(), (), status=400), "error_response"),
        (aiohttp.ClientConnectionError, "cannot_connect"),
        (et.ParseError, "bad_station_id"),
        (ValueError, "unknown"),
    ],
)
async def test_exception_handling(hass, error):
    """Test exception handling."""
    exc, base_error = error
    await setup.async_setup_component(hass, "persistent_notification", {})

    with patch(
        "homeassistant.components.environment_canada.config_flow.ECData",
        side_effect=exc,
    ):
        # with mocked_ec(update=Mock(side_effect=exc)), patch(
        #     "homeassistant.components.environment_canada.async_setup_entry",
        #     return_value=True,
        # ):
        flow = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            flow["flow_id"],
            {},
        )
        await hass.async_block_till_done()
        assert result["type"] == "form"
        assert result["errors"] == {"base": base_error}


async def test_lat_or_lon_not_specified(hass):
    """Test that the import step works."""
    with mocked_ec(), patch(
        "homeassistant.components.environment_canada.async_setup_entry",
        return_value=True,
    ):
        fake_config = dict(FAKE_CONFIG)
        del fake_config[CONF_LATITUDE]
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_IMPORT}, data=fake_config
        )
        await hass.async_block_till_done()
        assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
        assert result["data"] == FAKE_CONFIG
        assert result["title"] == FAKE_TITLE


async def test_async_step_import(hass):
    """Test that the import step works."""
    with mocked_ec(), patch(
        "homeassistant.components.environment_canada.async_setup_entry",
        return_value=True,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_IMPORT}, data=FAKE_CONFIG
        )
        await hass.async_block_till_done()
        assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
        assert result["data"] == FAKE_CONFIG
        assert result["title"] == FAKE_TITLE

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_IMPORT}, data=FAKE_CONFIG
        )
        assert result["type"] == data_entry_flow.RESULT_TYPE_ABORT
