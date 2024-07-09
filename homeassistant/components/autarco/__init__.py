"""The Autarco integration."""

from __future__ import annotations

from autarco import Autarco

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .coordinator import AutarcoDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]

type AutarcoConfigEntry = ConfigEntry[AutarcoDataUpdateCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: AutarcoConfigEntry) -> bool:
    """Set up Autarco from a config entry."""
    client = Autarco(
        email=entry.data[CONF_EMAIL],
        password=entry.data[CONF_PASSWORD],
        session=async_get_clientsession(hass),
    )

    coordinator = AutarcoDataUpdateCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: AutarcoConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
