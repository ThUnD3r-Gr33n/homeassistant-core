"""Define tests for the Awair config flow."""

from unittest.mock import patch

from python_awair.exceptions import AuthError, AwairError

from homeassistant import data_entry_flow
from homeassistant.components.awair.const import DOMAIN
from homeassistant.config_entries import SOURCE_REAUTH, SOURCE_USER
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_HOST
from homeassistant.core import HomeAssistant

from .const import (
    CLOUD_CONFIG,
    CLOUD_DEVICES_FIXTURE,
    CLOUD_UNIQUE_ID,
    LOCAL_CONFIG,
    LOCAL_DEVICES_FIXTURE,
    LOCAL_UNIQUE_ID,
    NO_DEVICES_FIXTURE,
    USER_FIXTURE,
)

from tests.common import MockConfigEntry


async def test_show_form(hass: HomeAssistant):
    """Test that the form is served with no input."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] == data_entry_flow.FlowResultType.MENU
    assert result["step_id"] == SOURCE_USER


async def test_invalid_access_token(hass: HomeAssistant):
    """Test that errors are shown when the access token is invalid."""

    with patch("python_awair.AwairClient.query", side_effect=AuthError()):
        menu_step = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=CLOUD_CONFIG
        )

        form_step = await hass.config_entries.flow.async_configure(
            menu_step["flow_id"],
            {"next_step_id": "cloud"},
        )

        result = await hass.config_entries.flow.async_configure(
            form_step["flow_id"],
            CLOUD_CONFIG,
        )

        assert result["errors"] == {CONF_ACCESS_TOKEN: "invalid_access_token"}


async def test_unexpected_api_error(hass: HomeAssistant):
    """Test that we abort on generic errors."""

    with patch("python_awair.AwairClient.query", side_effect=AwairError()):
        menu_step = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=CLOUD_CONFIG
        )

        form_step = await hass.config_entries.flow.async_configure(
            menu_step["flow_id"],
            {"next_step_id": "cloud"},
        )

        result = await hass.config_entries.flow.async_configure(
            form_step["flow_id"],
            CLOUD_CONFIG,
        )

        assert result["type"] == "abort"
        assert result["reason"] == "unknown"


async def test_duplicate_error(hass: HomeAssistant):
    """Test that errors are shown when adding a duplicate config."""

    with patch(
        "python_awair.AwairClient.query",
        side_effect=[USER_FIXTURE, CLOUD_DEVICES_FIXTURE],
    ), patch(
        "homeassistant.components.awair.sensor.async_setup_entry",
        return_value=True,
    ):
        MockConfigEntry(
            domain=DOMAIN, unique_id=CLOUD_UNIQUE_ID, data=CLOUD_CONFIG
        ).add_to_hass(hass)

        menu_step = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=CLOUD_CONFIG
        )

        form_step = await hass.config_entries.flow.async_configure(
            menu_step["flow_id"],
            {"next_step_id": "cloud"},
        )

        result = await hass.config_entries.flow.async_configure(
            form_step["flow_id"],
            CLOUD_CONFIG,
        )

        assert result["type"] == "abort"
        assert result["reason"] == "already_configured_account"


async def test_no_devices_error(hass: HomeAssistant):
    """Test that errors are shown when the API returns no devices."""

    with patch(
        "python_awair.AwairClient.query", side_effect=[USER_FIXTURE, NO_DEVICES_FIXTURE]
    ):
        menu_step = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=CLOUD_CONFIG
        )

        form_step = await hass.config_entries.flow.async_configure(
            menu_step["flow_id"],
            {"next_step_id": "cloud"},
        )

        result = await hass.config_entries.flow.async_configure(
            form_step["flow_id"],
            CLOUD_CONFIG,
        )

        assert result["type"] == "abort"
        assert result["reason"] == "no_devices_found"


async def test_reauth(hass: HomeAssistant) -> None:
    """Test reauth flow."""
    mock_config = MockConfigEntry(
        domain=DOMAIN,
        unique_id=CLOUD_UNIQUE_ID,
        data={**CLOUD_CONFIG, CONF_ACCESS_TOKEN: "blah"},
    )
    mock_config.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_REAUTH, "unique_id": CLOUD_UNIQUE_ID},
        data={**CLOUD_CONFIG, CONF_ACCESS_TOKEN: "blah"},
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"
    assert result["errors"] == {}

    with patch("python_awair.AwairClient.query", side_effect=AuthError()):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=CLOUD_CONFIG,
        )

        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "reauth_confirm"
        assert result["errors"] == {CONF_ACCESS_TOKEN: "invalid_access_token"}

    with patch(
        "python_awair.AwairClient.query",
        side_effect=[USER_FIXTURE, CLOUD_DEVICES_FIXTURE],
    ), patch("homeassistant.components.awair.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=CLOUD_CONFIG,
        )

        assert result["type"] == data_entry_flow.FlowResultType.ABORT
        assert result["reason"] == "reauth_successful"


async def test_reauth_error(hass: HomeAssistant) -> None:
    """Test reauth flow."""
    mock_config = MockConfigEntry(
        domain=DOMAIN,
        unique_id=CLOUD_UNIQUE_ID,
        data={**CLOUD_CONFIG, CONF_ACCESS_TOKEN: "blah"},
    )
    mock_config.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_REAUTH, "unique_id": CLOUD_UNIQUE_ID},
        data={**CLOUD_CONFIG, CONF_ACCESS_TOKEN: "blah"},
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"
    assert result["errors"] == {}

    with patch("python_awair.AwairClient.query", side_effect=AwairError()):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=CLOUD_CONFIG,
        )

        assert result["type"] == data_entry_flow.FlowResultType.ABORT
        assert result["reason"] == "unknown"


async def test_create_cloud_entry(hass: HomeAssistant):
    """Test overall flow."""

    with patch(
        "python_awair.AwairClient.query",
        side_effect=[USER_FIXTURE, CLOUD_DEVICES_FIXTURE],
    ), patch(
        "homeassistant.components.awair.sensor.async_setup_entry",
        return_value=True,
    ):
        menu_step = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=CLOUD_CONFIG
        )

        form_step = await hass.config_entries.flow.async_configure(
            menu_step["flow_id"],
            {"next_step_id": "cloud"},
        )

        result = await hass.config_entries.flow.async_configure(
            form_step["flow_id"],
            CLOUD_CONFIG,
        )

        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result["title"] == "foo@bar.com"
        assert result["data"][CONF_ACCESS_TOKEN] == CLOUD_CONFIG[CONF_ACCESS_TOKEN]
        assert result["result"].unique_id == CLOUD_UNIQUE_ID


async def test_create_local_entry(hass: HomeAssistant):
    """Test overall flow."""

    with patch(
        "python_awair.AwairClient.query", side_effect=[LOCAL_DEVICES_FIXTURE]
    ), patch(
        "homeassistant.components.awair.sensor.async_setup_entry",
        return_value=True,
    ):
        menu_step = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=LOCAL_CONFIG
        )

        form_step = await hass.config_entries.flow.async_configure(
            menu_step["flow_id"],
            {"next_step_id": "local"},
        )

        result = await hass.config_entries.flow.async_configure(
            form_step["flow_id"],
            LOCAL_CONFIG,
        )

        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result["title"] == "Awair Element (24947)"
        assert result["data"][CONF_HOST] == LOCAL_CONFIG[CONF_HOST]
        assert result["result"].unique_id == LOCAL_UNIQUE_ID
