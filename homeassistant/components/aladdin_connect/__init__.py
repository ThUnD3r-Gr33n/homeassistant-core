"""The aladdin_connect component."""
from datetime import timedelta
import logging
from typing import Final

from AIOAladdinConnect import AladdinConnectClient
import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from .const import DOMAIN

_LOGGER: Final = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.COVER]
SCAN_INTERVAL = timedelta(seconds=120)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up platform from a ConfigEntry."""
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    acc = AladdinConnectClient(username, password, None)
    try:
        if not await acc.login():
            raise ConfigEntryAuthFailed("Incorrect Password")
    except aiohttp.ClientConnectionError as ex:
        raise ConfigEntryNotReady("Can not Connect to host") from ex

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = acc
    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
