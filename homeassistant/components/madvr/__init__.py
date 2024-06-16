"""The madvr-envy integration."""

from __future__ import annotations

import logging

from madvr.madvr import Madvr

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import MadVRCoordinator
from .utils import cancel_tasks

# For your initial PR, limit it to 1 platform.
PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.REMOTE, Platform.SENSOR]

# Alias name should be prefixed by integration name
type MadVRConfigEntry = ConfigEntry[MadVRCoordinator]  # noqa: F821

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: MadVRConfigEntry) -> bool:
    """Set up the integration from a config entry."""
    name = entry.data["name"]
    madVRClient = Madvr(
        host=entry.data["host"],
        logger=_LOGGER,
        port=entry.data.get("port", 44077),
        connect_timeout=10,
    )
    coordinator = MadVRCoordinator(
        hass,
        entry,
        madVRClient,
        mac=entry.data.get("mac", ""),
        name=name,
    )
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator
    hass.data[DOMAIN]["entry_id"] = entry.entry_id

    await coordinator.async_config_entry_first_refresh()

    # Forward the entry setup to the platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: MadVRConfigEntry) -> bool:
    """Unload a config entry."""
    await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    coordinator: MadVRCoordinator = hass.data[DOMAIN][entry.entry_id]
    # cancel all tasks
    await cancel_tasks(coordinator.my_api)

    hass.data[DOMAIN].pop(entry.entry_id)
    return True


async def async_reload_entry(hass: HomeAssistant, entry: MadVRConfigEntry) -> None:
    """Reload a config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
