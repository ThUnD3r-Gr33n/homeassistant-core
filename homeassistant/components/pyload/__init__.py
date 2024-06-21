"""The pyLoad integration."""

from __future__ import annotations

from aiohttp import CookieJar
from pyloadapi.api import PyLoadAPI
from pyloadapi.exceptions import CannotConnect, InvalidAuth, ParserError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SSL,
    CONF_USERNAME,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers.aiohttp_client import async_create_clientsession

PLATFORMS: list[Platform] = [Platform.SENSOR]

type PyLoadConfigEntry = ConfigEntry[PyLoadAPI]  # noqa: F821


async def async_setup_entry(hass: HomeAssistant, entry: PyLoadConfigEntry) -> bool:
    """Set up pyLoad from a config entry."""

    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    protocol = "https" if entry.data[CONF_SSL] else "http"
    url = f"{protocol}://{host}:{port}/"

    session = async_create_clientsession(
        hass,
        verify_ssl=False,
        cookie_jar=CookieJar(unsafe=True),
    )
    pyloadapi = PyLoadAPI(
        session,
        api_url=url,
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
    )

    try:
        await pyloadapi.login()
    except CannotConnect as e:
        raise PlatformNotReady(
            "Unable to connect and retrieve data from pyLoad API"
        ) from e
    except ParserError as e:
        raise PlatformNotReady("Unable to parse data from pyLoad API") from e
    except InvalidAuth as e:
        raise PlatformNotReady(
            f"Authentication failed for {entry.data[CONF_USERNAME]}, check your login credentials"
        ) from e

    entry.runtime_data = pyloadapi

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: PyLoadConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
