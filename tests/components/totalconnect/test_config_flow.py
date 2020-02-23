"""Tests for the iCloud config flow."""
from unittest.mock import MagicMock

from homeassistant import data_entry_flow
from homeassistant.components.totalconnect.const import DOMAIN
from homeassistant.config_entries import SOURCE_IMPORT, SOURCE_USER
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.typing import HomeAssistantType

from tests.common import MockConfigEntry

USERNAME = "username@me.com"
USERNAME_2 = "second_username@icloud.com"
PASSWORD = "password"


async def test_user(hass: HomeAssistantType, service: MagicMock):
    """Test user config."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data=None
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "user"

    # test with all provided
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD},
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM


#    assert result["step_id"] == CONF_TRUSTED_DEVICE


async def test_import(hass: HomeAssistantType, service: MagicMock):
    """Test import step."""
    # import with username and password
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_IMPORT},
        data={CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD},
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM


#   assert result["step_id"] == "trusted_device"


async def test_abort_if_already_setup(hass: HomeAssistantType):
    """Test we abort if the account is already setup."""
    MockConfigEntry(
        domain=DOMAIN,
        data={CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD},
        unique_id=USERNAME,
    ).add_to_hass(hass)

    # Should fail, same USERNAME (import)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_IMPORT},
        data={CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD},
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_ABORT
    assert result["reason"] == "already_configured"

    # Should fail, same USERNAME (flow)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD},
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_ABORT
    assert result["reason"] == "already_configured"


async def test_login_failed(hass: HomeAssistantType):
    """Test when we have errors during login."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD},
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["errors"] == {CONF_USERNAME: "login"}
