"""DataUpdateCoordinator for System Bridge."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Callable

from systembridge import Bridge
from systembridge.client import BridgeClient
from systembridge.exceptions import BridgeConnectionClosedException, BridgeException
from systembridge.objects.events import Event

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_API_KEY,
    CONF_HOST,
    CONF_PORT,
    EVENT_HOMEASSISTANT_STOP,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN


class SystemBridgeDataUpdateCoordinator(DataUpdateCoordinator[Bridge]):
    """Class to manage fetching System Bridge data from single endpoint."""

    def __init__(
        self,
        hass: HomeAssistant,
        LOGGER: logging.Logger,
        *,
        entry: ConfigEntry,
    ) -> None:
        """Initialize global System Bridge data updater."""
        self.bridge = Bridge(
            BridgeClient(async_get_clientsession(hass)),
            f"http://{entry.data[CONF_HOST]}:{entry.data[CONF_PORT]}",
            entry.data[CONF_API_KEY],
        )
        self.host = entry.data[CONF_HOST]
        self.unsub: Callable | None = None

        super().__init__(
            hass, LOGGER, name=DOMAIN, update_interval=timedelta(seconds=30)
        )

    def update_listeners(self) -> None:
        """Call update on all listeners."""
        for update_callback in self._listeners:
            update_callback()

    async def async_handle_event(self, event: Event):
        """Handle System Bridge events from the WebSocket."""
        # No need to update anything, as everything is updated in the caller
        self.logger.debug("New event from System Bridge: %s", event.name)
        self.async_set_updated_data(self.bridge)

    @callback
    async def _setup_websocket(self) -> None:
        """Use WebSocket for updates, instead of polling."""

        try:
            await self.bridge.async_get_information()
            self.logger.debug(
                "Connecting to ws://%s:%s",
                self.host,
                self.bridge.information.websocketPort,
            )
            await self.bridge.async_connect_websocket(
                self.host,
                self.bridge.information.websocketPort,
            )
        except BridgeException as exception:
            self.logger.error(exception)
            if self.unsub:
                self.unsub()
                self.unsub = None
            return

        try:
            asyncio.create_task(
                self.bridge.listen_for_events(callback=self.async_handle_event)
            )
            await self.bridge.async_send_event(
                "get-data",
                [
                    "battery",
                    "cpu",
                    "filesystem",
                    "information",
                    "memory",
                    "network",
                    "os",
                    "processes",
                    "system",
                ],
            )
        except BridgeConnectionClosedException as exception:
            self.last_update_success = False
            self.logger.info(exception)
        except BridgeException as exception:
            self.last_update_success = False
            self.update_listeners()
            self.logger.error(exception)

        async def close_websocket(_) -> None:
            """Close WebSocket connection."""
            await self.bridge.async_close_websocket()

        # Clean disconnect WebSocket on Home Assistant shutdown
        self.unsub = self.hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STOP, close_websocket
        )

    async def _async_update_data(self) -> Bridge:
        """Update System Bridge data from WebSocket."""
        self.logger.debug(
            "_async_update_data - WebSocket Connected: %s",
            self.bridge.websocket_connected,
        )
        if not self.bridge.websocket_connected:
            await self._setup_websocket()

        return self.bridge
