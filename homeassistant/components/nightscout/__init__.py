"""The NightScout integration."""
import asyncio
from asyncio import TimeoutError as AsyncIOTimeoutError
import logging

from aiohttp import ClientError, ClientTimeout
from py_nightscout import Api as NightScoutAPI

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import SLOW_UPDATE_WARNING

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor"]
_API_TIMEOUT = SLOW_UPDATE_WARNING - 1


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the NightScout component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up NightScout from a config entry."""
    host = entry.data[CONF_HOST]

    api = NightScoutAPI(host)
    status = await api.get_server_status()

    hass.data[DOMAIN][entry.entry_id] = api

    device_registry = await dr.async_get_registry(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, status.name)},
        manufacturer="NighScout",
        name=status.name,
        sw_version=status.version,
    )

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
