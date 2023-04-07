"""Tests for Deutscher Wetterdienst (DWD) Weather Warnings config flow."""

from typing import Final

import pytest

from homeassistant.components.dwd_weather_warnings.const import (
    ADVANCE_WARNING_SENSOR,
    CONF_OLD_REGION_NAME,
    CONF_REGION_IDENTIFIER,
    CURRENT_WARNING_SENSOR,
    DEFAULT_NAME,
    DOMAIN,
)
from homeassistant.config_entries import SOURCE_IMPORT, SOURCE_USER
from homeassistant.const import CONF_MONITORED_CONDITIONS, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry

DEMO_CONFIG_ENTRY: Final = {
    CONF_NAME: "Unit Test",
    CONF_REGION_IDENTIFIER: "807111000",
    CONF_MONITORED_CONDITIONS: [CURRENT_WARNING_SENSOR, ADVANCE_WARNING_SENSOR],
}

DEMO_YAML_CONFIGURATION: Final = {
    CONF_NAME: "Unit Test",
    CONF_OLD_REGION_NAME: "807111000",
    CONF_MONITORED_CONDITIONS: [CURRENT_WARNING_SENSOR, ADVANCE_WARNING_SENSOR],
}

pytestmark = pytest.mark.usefixtures("mock_setup_entry")


async def test_create_entry_with_region_identifier(hass: HomeAssistant) -> None:
    """Test that the user step works with a region identifier set."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], DEMO_CONFIG_ENTRY
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == DEMO_CONFIG_ENTRY[CONF_NAME]
    assert result["data"] == {
        CONF_NAME: DEMO_CONFIG_ENTRY[CONF_NAME],
        CONF_REGION_IDENTIFIER: DEMO_CONFIG_ENTRY[CONF_REGION_IDENTIFIER],
        CONF_MONITORED_CONDITIONS: DEMO_CONFIG_ENTRY[CONF_MONITORED_CONDITIONS],
    }


async def test_user_no_identifier(hass: HomeAssistant) -> None:
    """Test that error is shown when no region_identifier is set."""
    data: dict = DEMO_CONFIG_ENTRY.copy()
    data.pop(CONF_REGION_IDENTIFIER)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data=data
    )

    assert result["errors"] == {"base": "no_identifier"}


async def test_import_flow_full_data(hass: HomeAssistant) -> None:
    """Test a successful import of a full YAML configuration."""
    data = DEMO_YAML_CONFIGURATION.copy()

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_IMPORT}, data=data
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == DEMO_YAML_CONFIGURATION[CONF_NAME]

    result_data = DEMO_YAML_CONFIGURATION.copy()
    result_data[CONF_REGION_IDENTIFIER] = result_data[CONF_OLD_REGION_NAME]
    result_data.pop(CONF_OLD_REGION_NAME)

    assert result["data"] == result_data


async def test_import_flow_no_name(hass: HomeAssistant) -> None:
    """Test a successful import of a YAML configuration with no name set."""
    data = DEMO_YAML_CONFIGURATION.copy()
    data.pop(CONF_NAME)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_IMPORT}, data=data
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == DEFAULT_NAME

    result_data = DEMO_YAML_CONFIGURATION.copy()
    result_data[CONF_NAME] = DEFAULT_NAME
    result_data[CONF_REGION_IDENTIFIER] = result_data[CONF_OLD_REGION_NAME]
    result_data.pop(CONF_OLD_REGION_NAME)

    assert result["data"] == result_data


async def test_import_flow_only_required(hass: HomeAssistant) -> None:
    """Test a successful import of a YAML configuration with only required properties."""
    data = DEMO_YAML_CONFIGURATION.copy()
    data.pop(CONF_NAME)
    data.pop(CONF_MONITORED_CONDITIONS)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_IMPORT}, data=data
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == DEFAULT_NAME

    result_data = DEMO_YAML_CONFIGURATION.copy()
    result_data[CONF_NAME] = DEFAULT_NAME
    result_data[CONF_REGION_IDENTIFIER] = result_data[CONF_OLD_REGION_NAME]
    result_data.pop(CONF_OLD_REGION_NAME)

    assert result["data"] == result_data


async def test_import_flow_device_already_configured(hass: HomeAssistant) -> None:
    """Test aborting, if the device is already configured during the import."""
    entry = MockConfigEntry(domain=DOMAIN, data=DEMO_CONFIG_ENTRY.copy())
    entry.add_to_hass(hass)

    yaml_data = DEMO_YAML_CONFIGURATION.copy()
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_IMPORT}, data=yaml_data
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_config_flow_device_already_configured(hass: HomeAssistant) -> None:
    """Test aborting, if the device is already configured during the config."""
    entry = MockConfigEntry(domain=DOMAIN, data=DEMO_CONFIG_ENTRY.copy())
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: DEMO_CONFIG_ENTRY[CONF_NAME],
            CONF_REGION_IDENTIFIER: DEMO_CONFIG_ENTRY[CONF_REGION_IDENTIFIER],
            CONF_MONITORED_CONDITIONS: DEMO_CONFIG_ENTRY[CONF_MONITORED_CONDITIONS],
        },
    )
    await hass.async_block_till_done()

    assert result2["type"] == FlowResultType.ABORT
    assert result2["reason"] == "already_configured"
