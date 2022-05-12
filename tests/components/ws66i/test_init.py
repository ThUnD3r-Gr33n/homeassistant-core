"""Test the WS66i 6-Zone Amplifier init file."""
from unittest.mock import patch

from homeassistant.components.ws66i.const import DOMAIN
from homeassistant.const import CONF_IP_ADDRESS

from .test_media_player import MOCK_CONFIG, MOCK_DEFAULT_OPTIONS, MockWs66i

from tests.common import MockConfigEntry

CONFIG = {CONF_IP_ADDRESS: "1.1.1.1"}

ZONE_1_ID = "media_player.zone_11"


async def test_cannot_connect(hass):
    """Test connection error."""
    with patch(
        "homeassistant.components.ws66i.get_ws66i",
        new=lambda *a: MockWs66i(fail_open=True),
    ):
        config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG)
        config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
        assert hass.states.get(ZONE_1_ID) is None


async def test_cannot_connect_2(hass):
    """Test connection error pt 2."""
    # Another way to test same case as test_cannot_connect
    ws66i = MockWs66i()

    with patch.object(MockWs66i, "open", side_effect=ConnectionError):
        with patch(
            "homeassistant.components.ws66i.get_ws66i",
            new=lambda *a: ws66i,
        ):
            config_entry = MockConfigEntry(
                domain=DOMAIN, data=MOCK_CONFIG, options=MOCK_DEFAULT_OPTIONS
            )
            config_entry.add_to_hass(hass)
            await hass.config_entries.async_setup(config_entry.entry_id)
            await hass.async_block_till_done()

        assert hass.states.get(ZONE_1_ID) is None
