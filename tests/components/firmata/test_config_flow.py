"""Test the Firmata config flow."""
from homeassistant import config_entries, setup
from homeassistant.components.firmata.const import CONF_SERIAL_PORT, DOMAIN
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant

from tests.async_mock import patch


async def test_import_cannot_connect(hass: HomeAssistant) -> None:
    """Test we fail with an invalid board."""
    await setup.async_setup_component(hass, "persistent_notification", {})

    with patch(
        "homeassistant.components.firmata.board.PymataExpress.start_aio",
        side_effect=RuntimeError,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data={CONF_SERIAL_PORT: "/dev/nonExistent"},
        )

    assert result["type"] == "abort"
    assert result["reason"] == "cannot_connect"
    await hass.async_block_till_done()


async def test_import(hass: HomeAssistant) -> None:
    """Test we create an entry from config."""
    await setup.async_setup_component(hass, "persistent_notification", {})

    with patch(
        "homeassistant.components.firmata.board.PymataExpress", autospec=True
    ), patch(
        "homeassistant.components.firmata.async_setup", return_value=True
    ) as mock_setup, patch(
        "homeassistant.components.firmata.async_setup_entry", return_value=True
    ) as mock_setup_entry:

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data={CONF_SERIAL_PORT: "/dev/nonExistent"},
        )

        assert result["type"] == "create_entry"
        assert result["title"] == "serial-/dev/nonExistent"
        assert result["data"] == {
            CONF_NAME: "serial-/dev/nonExistent",
            CONF_SERIAL_PORT: "/dev/nonExistent",
        }
        await hass.async_block_till_done()
        assert len(mock_setup.mock_calls) == 1
        assert len(mock_setup_entry.mock_calls) == 1
