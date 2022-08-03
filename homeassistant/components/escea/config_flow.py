"""Config flow for escea."""

import asyncio
from collections.abc import Callable
from contextlib import suppress
import logging

from async_timeout import timeout

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_entry_flow
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import (
    DISPATCH_CONTROLLER_DISCOVERED,
    ESCEA,
    ESCEA_FIREPLACE,
    TIMEOUT_DISCOVERY,
)
from .discovery import async_start_discovery_service, async_stop_discovery_service

_LOGGER = logging.getLogger(__name__)


async def _async_has_devices(hass: HomeAssistant) -> bool:

    controller_ready = asyncio.Event()
    remove_handler: Callable[[], None]

    @callback
    def dispatch_discovered(_):
        controller_ready.set()

    remove_handler = async_dispatcher_connect(
        hass, DISPATCH_CONTROLLER_DISCOVERED, dispatch_discovered
    )

    disco = await async_start_discovery_service(hass)

    with suppress(asyncio.TimeoutError):
        async with timeout(TIMEOUT_DISCOVERY):
            await controller_ready.wait()

    if remove_handler is not None:
        remove_handler()

    if not disco.pi_disco.controllers:
        await async_stop_discovery_service(hass)
        _LOGGER.debug("No controllers found")
        return False

    _LOGGER.debug("Controllers %s", disco.pi_disco.controllers)
    return True


config_entry_flow.register_discovery_flow(ESCEA, ESCEA_FIREPLACE, _async_has_devices)
