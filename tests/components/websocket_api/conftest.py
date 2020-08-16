"""Fixtures for websocket tests."""
import pytest

from homeassistant.components.websocket_api.auth import TYPE_AUTH_REQUIRED
from homeassistant.components.websocket_api.http import URL
from homeassistant.setup import async_setup_component


@pytest.fixture
async def websocket_client(hass, hass_ws_client):
    """Create a websocket client."""
    return await hass_ws_client(hass)


@pytest.fixture
async def no_auth_websocket_client(hass, aiohttp_client):
    """Websocket connection that requires authentication."""
    assert await async_setup_component(hass, "websocket_api", {})
    await hass.async_block_till_done()

    client = await aiohttp_client(hass.http.app)
    ws = await client.ws_connect(URL)

    auth_ok = await ws.receive_json()
    assert auth_ok["type"] == TYPE_AUTH_REQUIRED

    ws.client = client
    yield ws

    if not ws.closed:
        await ws.close()
