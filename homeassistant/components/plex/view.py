"""Implement a view to provide proxied Plex thumbnails to the media browser."""
from __future__ import annotations

from http import HTTPStatus
import logging

from aiohttp import web
from aiohttp.hdrs import CACHE_CONTROL
from aiohttp.typedefs import LooseHeaders

from homeassistant.components.http import KEY_AUTHENTICATED, HomeAssistantView
from homeassistant.components.media_player import async_fetch_image

from .const import DOMAIN as PLEX_DOMAIN, SERVERS

_LOGGER = logging.getLogger(__name__)


class PlexImageView(HomeAssistantView):
    """Media player view to serve a Plex image."""

    name = "api:plex:image"
    url = "/api/plex_image_proxy/{server_id}/{media_content_id}"

    async def get(  # pylint: disable=no-self-use
        self,
        request: web.Request,
        media_content_id: str,
        server_id: str | None = None,
    ) -> web.Response:
        """Start a get request."""
        if not request[KEY_AUTHENTICATED]:
            return web.Response(status=HTTPStatus.UNAUTHORIZED)

        hass = request.app["hass"]
        if (server := hass.data[PLEX_DOMAIN][SERVERS].get(server_id)) is None:
            _LOGGER.error("Plex server_id %s not known", server_id)
            return web.Response(status=HTTPStatus.NOT_FOUND)

        if (image_url := server.thumbnail_cache.get(media_content_id)) is None:
            _LOGGER.debug("Thumbnail URL for %s not found in cache", media_content_id)
            return web.Response(status=HTTPStatus.NOT_FOUND)
        data, content_type = await async_fetch_image(_LOGGER, hass, image_url)

        if data is None:
            return web.Response(status=HTTPStatus.INTERNAL_SERVER_ERROR)

        headers: LooseHeaders = {CACHE_CONTROL: "max-age=3600"}
        return web.Response(body=data, content_type=content_type, headers=headers)
