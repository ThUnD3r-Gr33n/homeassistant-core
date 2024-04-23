"""The QBittorrent coordinator."""

from __future__ import annotations

from datetime import timedelta
import logging

from qbittorrentapi import (
    APIConnectionError,
    Client,
    Forbidden403Error,
    LoginFailed,
    SyncMainDataDictionary,
    TorrentInfoList,
)

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class QBittorrentDataCoordinator(DataUpdateCoordinator[SyncMainDataDictionary]):
    """Coordinator for updating QBittorrent data."""

    def __init__(self, hass: HomeAssistant, client: Client) -> None:
        """Initialize coordinator."""
        self.client = client
        # self.main_data: dict[str, int] = {}
        self.total_torrents: dict[str, int] = {}
        self.active_torrents: dict[str, int] = {}
        self.inactive_torrents: dict[str, int] = {}
        self.paused_torrents: dict[str, int] = {}
        self.seeding_torrents: dict[str, int] = {}
        self.started_torrents: dict[str, int] = {}

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
        )

    async def _async_update_data(self) -> SyncMainDataDictionary:
        try:
            return await self.hass.async_add_executor_job(self.client.sync_maindata)
        except (LoginFailed, Forbidden403Error) as exc:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="login_error"
            ) from exc
        except APIConnectionError as exc:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="cannot_connect"
            ) from exc

    async def get_torrents(self, torrent_filter: str) -> TorrentInfoList:
        """Async method to get QBittorrent torrents."""
        try:
            torrents = await self.hass.async_add_executor_job(
                lambda: self.client.torrents_info(torrent_filter)  # type: ignore[arg-type]
            )
        except (LoginFailed, Forbidden403Error) as exc:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="login_error"
            ) from exc
        except APIConnectionError as exc:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="cannot_connect"
            ) from exc

        return torrents
