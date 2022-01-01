"""The tests for generic camera component."""
import asyncio
from http import HTTPStatus
from io import BytesIO
from unittest.mock import patch

from PIL import Image
import aiohttp
import httpx
import pytest
import respx

from homeassistant import config as hass_config
from homeassistant.components.generic import DOMAIN
from homeassistant.components.generic.camera import GenericCamera
from homeassistant.components.websocket_api.const import TYPE_RESULT
from homeassistant.const import SERVICE_RELOAD
from homeassistant.helpers import config_validation as cv
from homeassistant.setup import async_setup_component

from tests.common import AsyncMock, Mock, get_fixture_path

buf = BytesIO()  # fake image in ram for testing.
Image.new("RGB", (1, 1)).save(buf, format="PNG")
fakeimgbytes_png = bytes(buf.getbuffer())
Image.new("RGB", (1, 1)).save(buf, format="jpeg")
fakeimgbytes_jpg = bytes(buf.getbuffer())
fakeimgbytes_svg = bytes(
    '<svg xmlns="http://www.w3.org/2000/svg"><circle r="50"/></svg>', encoding="utf-8"
)


@respx.mock
async def test_fetching_url(hass, hass_client):
    """Test that it fetches the given url."""
    respx.get("http://example.com").respond(stream=fakeimgbytes_png)

    await async_setup_component(
        hass,
        "camera",
        {
            "camera": {
                "name": "config_test",
                "platform": "generic",
                "still_image_url": "http://example.com",
                "username": "user",
                "password": "pass",
            }
        },
    )
    await hass.async_block_till_done()

    client = await hass_client()

    resp = await client.get("/api/camera_proxy/camera.config_test")

    assert resp.status == HTTPStatus.OK
    assert respx.calls.call_count == 1
    body = await resp.read()
    assert body == fakeimgbytes_png

    resp = await client.get("/api/camera_proxy/camera.config_test")
    assert respx.calls.call_count == 2


@respx.mock
async def test_fetching_without_verify_ssl(hass, hass_client):
    """Test that it fetches the given url when ssl verify is off."""
    respx.get("https://example.com").respond(stream=fakeimgbytes_png)

    with patch(
        "homeassistant.components.generic.camera.GenericCamera.async_camera_image",
        return_value=fakeimgbytes_png,
    ):
        await async_setup_component(
            hass,
            "camera",
            {
                "camera": {
                    "name": "config_test",
                    "platform": "generic",
                    "still_image_url": "https://example.com",
                    "username": "user",
                    "password": "pass",
                    "verify_ssl": "false",
                }
            },
        )
        await hass.async_block_till_done()

    client = await hass_client()

    resp = await client.get("/api/camera_proxy/camera.config_test")

    assert resp.status == HTTPStatus.OK


@respx.mock
async def test_fetching_url_with_verify_ssl(hass, hass_client):
    """Test that it fetches the given url when ssl verify is explicitly on."""
    respx.get("https://example.com").respond(stream=fakeimgbytes_png)

    with patch(
        "homeassistant.components.generic.camera.GenericCamera.async_camera_image",
        return_value=fakeimgbytes_png,
    ):
        await async_setup_component(
            hass,
            "camera",
            {
                "camera": {
                    "name": "config_test",
                    "platform": "generic",
                    "still_image_url": "https://example.com",
                    "username": "user",
                    "password": "pass",
                    "verify_ssl": "true",
                }
            },
        )
        await hass.async_block_till_done()

    client = await hass_client()

    resp = await client.get("/api/camera_proxy/camera.config_test")

    assert resp.status == HTTPStatus.OK


@respx.mock
async def test_limit_refetch(hass, hass_client):
    """Test that it fetches the given url."""
    respx.get("http://example.com/5a").respond(stream=fakeimgbytes_png)
    respx.get("http://example.com/10a").respond(stream=fakeimgbytes_png)
    respx.get("http://example.com/15a").respond(stream=fakeimgbytes_jpg)
    respx.get("http://example.com/20a").respond(status_code=HTTPStatus.NOT_FOUND)

    with patch(
        "homeassistant.components.generic.camera.GenericCamera.async_camera_image",
        return_value=fakeimgbytes_png,
    ):
        await async_setup_component(
            hass,
            "camera",
            {
                "camera": {
                    "name": "config_test",
                    "platform": "generic",
                    "still_image_url": 'http://example.com/{{ states.sensor.temp.state + "a" }}',
                    "limit_refetch_to_url_change": True,
                }
            },
        )
        await hass.async_block_till_done()

    client = await hass_client()

    resp = await client.get("/api/camera_proxy/camera.config_test")

    hass.states.async_set("sensor.temp", "5")

    with pytest.raises(aiohttp.ServerTimeoutError), patch(
        "async_timeout.timeout", side_effect=asyncio.TimeoutError()
    ):
        resp = await client.get("/api/camera_proxy/camera.config_test")

    assert respx.calls.call_count == 0
    assert resp.status == HTTPStatus.INTERNAL_SERVER_ERROR

    hass.states.async_set("sensor.temp", "10")

    resp = await client.get("/api/camera_proxy/camera.config_test")
    assert respx.calls.call_count == 1
    assert resp.status == HTTPStatus.OK
    body = await resp.read()
    assert body == fakeimgbytes_png

    resp = await client.get("/api/camera_proxy/camera.config_test")
    assert respx.calls.call_count == 1
    assert resp.status == HTTPStatus.OK
    body = await resp.read()
    assert body == fakeimgbytes_png

    hass.states.async_set("sensor.temp", "15")

    # Url change = fetch new image
    resp = await client.get("/api/camera_proxy/camera.config_test")
    assert respx.calls.call_count == 2
    assert resp.status == HTTPStatus.OK
    body = await resp.read()
    assert body == fakeimgbytes_jpg

    # Cause a template render error
    hass.states.async_remove("sensor.temp")
    resp = await client.get("/api/camera_proxy/camera.config_test")
    assert respx.calls.call_count == 2
    assert resp.status == HTTPStatus.OK
    body = await resp.read()
    assert body == fakeimgbytes_jpg


async def test_stream_source(hass, hass_client, hass_ws_client):
    """Test that the stream source is rendered."""
    with patch(
        "homeassistant.components.generic.camera.GenericCamera.async_camera_image",
        return_value=fakeimgbytes_png,
    ):
        assert await async_setup_component(
            hass,
            "camera",
            {
                "camera": {
                    "name": "config_test",
                    "platform": "generic",
                    "still_image_url": "https://example.com",
                    "stream_source": 'http://example.com/{{ states.sensor.temp.state + "a" }}',
                    "limit_refetch_to_url_change": True,
                },
            },
        )
        assert await async_setup_component(hass, "stream", {})
        await hass.async_block_till_done()

    hass.states.async_set("sensor.temp", "5")

    with patch(
        "homeassistant.components.camera.Stream.endpoint_url",
        return_value="http://home.assistant/playlist.m3u8",
    ) as mock_stream_url:
        # Request playlist through WebSocket
        client = await hass_ws_client(hass)

        await client.send_json(
            {"id": 1, "type": "camera/stream", "entity_id": "camera.config_test"}
        )
        msg = await client.receive_json()

        # Assert WebSocket response
        assert mock_stream_url.call_count == 1
        assert msg["id"] == 1
        assert msg["type"] == TYPE_RESULT
        assert msg["success"]
        assert msg["result"]["url"][-13:] == "playlist.m3u8"


async def test_stream_source_error(hass, hass_client, hass_ws_client):
    """Test that the stream source has an error."""
    with patch(
        "homeassistant.components.generic.camera.GenericCamera.async_camera_image",
        return_value=fakeimgbytes_png,
    ):
        assert await async_setup_component(
            hass,
            "camera",
            {
                "camera": {
                    "name": "config_test",
                    "platform": "generic",
                    "still_image_url": "https://example.com",
                    # Does not exist
                    "stream_source": 'http://example.com/{{ states.sensor.temp.state + "a" }}',
                    "limit_refetch_to_url_change": True,
                },
            },
        )
        assert await async_setup_component(hass, "stream", {})
        await hass.async_block_till_done()

    with patch(
        "homeassistant.components.camera.Stream.endpoint_url",
        return_value="http://home.assistant/playlist.m3u8",
    ) as mock_stream_url:
        # Request playlist through WebSocket
        client = await hass_ws_client(hass)

        await client.send_json(
            {"id": 1, "type": "camera/stream", "entity_id": "camera.config_test"}
        )
        msg = await client.receive_json()

        # Assert WebSocket response
        assert mock_stream_url.call_count == 0
        assert msg["id"] == 1
        assert msg["type"] == TYPE_RESULT
        assert msg["success"] is False
        assert msg["error"] == {
            "code": "start_stream_failed",
            "message": "camera.config_test does not support play stream service",
        }


async def test_setup_alternative_options(hass, hass_ws_client):
    """Test that the stream source is setup with different config options."""
    assert await async_setup_component(
        hass,
        "camera",
        {
            "camera": {
                "name": "config_test",
                "platform": "generic",
                "still_image_url": "https://example.com",
                "authentication": "digest",
                "username": "user",
                "password": "pass",
                "stream_source": "rtsp://example.com:554/rtsp/",
                "rtsp_transport": "udp",
            },
        },
    )
    await hass.async_block_till_done()
    assert hass.data["camera"].get_entity("camera.config_test")


async def test_no_stream_source(hass, hass_client, hass_ws_client):
    """Test a stream request without stream source option set."""
    with patch(
        "homeassistant.components.generic.camera.GenericCamera.async_camera_image",
        return_value=fakeimgbytes_png,
    ):
        assert await async_setup_component(
            hass,
            "camera",
            {
                "camera": {
                    "name": "config_test",
                    "platform": "generic",
                    "still_image_url": "https://example.com",
                    "limit_refetch_to_url_change": True,
                }
            },
        )
        await hass.async_block_till_done()

    with patch(
        "homeassistant.components.camera.Stream.endpoint_url",
        return_value="http://home.assistant/playlist.m3u8",
    ) as mock_request_stream:
        # Request playlist through WebSocket
        client = await hass_ws_client(hass)

        await client.send_json(
            {"id": 3, "type": "camera/stream", "entity_id": "camera.config_test"}
        )
        msg = await client.receive_json()

        # Assert the websocket error message
        assert mock_request_stream.call_count == 0
        assert msg["id"] == 3
        assert msg["type"] == TYPE_RESULT
        assert msg["success"] is False
        assert msg["error"] == {
            "code": "start_stream_failed",
            "message": "camera.config_test does not support play stream service",
        }


@respx.mock
async def test_camera_content_type(hass, hass_client):
    """Test generic camera with custom content_type."""
    urlsvg = "https://upload.wikimedia.org/wikipedia/commons/0/02/SVG_logo.svg"
    respx.get(urlsvg).respond(stream=fakeimgbytes_svg)
    urljpg = "https://upload.wikimedia.org/wikipedia/commons/0/0e/Felis_silvestris_silvestris.jpg"
    respx.get(urljpg).respond(stream=fakeimgbytes_jpg)
    cam_config_svg = {
        "name": "config_test_svg",
        "platform": "generic",
        "still_image_url": urlsvg,
        "content_type": "image/svg+xml",
    }
    cam_config_normal = cam_config_svg.copy()
    cam_config_normal["content_type"] = "image/jpeg"
    cam_config_normal["name"] = "config_test_jpg"
    cam_config_normal["still_image_url"] = urljpg

    await async_setup_component(
        hass, "camera", {"camera": [cam_config_svg, cam_config_normal]}
    )
    await hass.async_block_till_done()

    client = await hass_client()

    resp_1 = await client.get("/api/camera_proxy/camera.config_test_svg")
    assert respx.calls.call_count == 1
    assert resp_1.status == HTTPStatus.OK
    assert resp_1.content_type == "image/svg+xml"
    body = await resp_1.read()
    assert body == fakeimgbytes_svg

    resp_2 = await client.get("/api/camera_proxy/camera.config_test_jpg")
    assert respx.calls.call_count == 2
    assert resp_2.status == HTTPStatus.OK
    assert resp_2.content_type == "image/jpeg"
    body = await resp_2.read()
    assert body == fakeimgbytes_jpg


@respx.mock
async def test_reloading(hass, hass_client):
    """Test we can cleanly reload."""
    respx.get("http://example.com").respond(text="hello world")

    await async_setup_component(
        hass,
        "camera",
        {
            "camera": {
                "name": "config_test",
                "platform": "generic",
                "still_image_url": "http://example.com",
                "username": "user",
                "password": "pass",
            }
        },
    )
    await hass.async_block_till_done()

    client = await hass_client()

    resp = await client.get("/api/camera_proxy/camera.config_test")

    assert resp.status == HTTPStatus.OK
    assert respx.calls.call_count == 1
    body = await resp.text()
    assert body == "hello world"

    yaml_path = get_fixture_path("configuration.yaml", "generic")

    with patch.object(hass_config, "YAML_CONFIG_FILE", yaml_path):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_RELOAD,
            {},
            blocking=True,
        )
        await hass.async_block_till_done()

    assert len(hass.states.async_all()) == 1

    resp = await client.get("/api/camera_proxy/camera.config_test")

    assert resp.status == HTTPStatus.NOT_FOUND

    resp = await client.get("/api/camera_proxy/camera.reload")

    assert resp.status == HTTPStatus.OK
    assert respx.calls.call_count == 2
    body = await resp.text()
    assert body == "hello world"


@respx.mock
async def test_timeout_cancelled(hass, hass_client):
    """Test that timeouts and cancellations return last image."""

    respx.get("http://example.com").respond(stream=fakeimgbytes_png)

    await async_setup_component(
        hass,
        "camera",
        {
            "camera": {
                "name": "config_test",
                "platform": "generic",
                "still_image_url": "http://example.com",
                "username": "user",
                "password": "pass",
            }
        },
    )
    await hass.async_block_till_done()

    client = await hass_client()

    resp = await client.get("/api/camera_proxy/camera.config_test")

    assert resp.status == HTTPStatus.OK
    assert respx.calls.call_count == 1
    assert await resp.read() == fakeimgbytes_png

    respx.get("http://example.com").respond(stream=fakeimgbytes_jpg)

    with patch(
        "homeassistant.components.generic.camera.GenericCamera.async_camera_image",
        side_effect=asyncio.CancelledError(),
    ):
        resp = await client.get("/api/camera_proxy/camera.config_test")
        assert respx.calls.call_count == 1
        assert resp.status == HTTPStatus.INTERNAL_SERVER_ERROR

    respx.get("http://example.com").side_effect = [
        httpx.RequestError,
        httpx.TimeoutException,
    ]

    for total_calls in range(2, 3):
        resp = await client.get("/api/camera_proxy/camera.config_test")
        assert respx.calls.call_count == total_calls
        assert resp.status == HTTPStatus.OK
        assert await resp.read() == fakeimgbytes_png

async def test_no_still_image_url(hass, hass_client):
    """Test that the component can grab images from stream with no still_image_url."""
    assert await async_setup_component(
        hass,
        "camera",
        {
            "camera": {
                "name": "config_test",
                "platform": "generic",
                "stream_source": "rtsp://example.com:554/rtsp/",
            },
        },
    )
    await hass.async_block_till_done()

    client = await hass_client()

    with patch(
        "homeassistant.components.generic.camera.GenericCamera.stream_source",
        return_value=None,
    ) as mock_stream_source:

        # First test when there is no stream_source should fail
        resp = await client.get("/api/camera_proxy/camera.config_test")
        await hass.async_block_till_done()
        mock_stream_source.assert_called_once()
        assert resp.status == HTTPStatus.INTERNAL_SERVER_ERROR

    with patch("homeassistant.components.camera.create_stream") as mock_create_stream:

        # Now test when creating the stream succeeds
        mock_stream = Mock()
        mock_stream.async_get_image = AsyncMock()
        mock_stream.async_get_image.return_value = b"stream_keyframe_image"
        mock_create_stream.return_value = mock_stream

        # should start the stream and get the image
        resp = await client.get("/api/camera_proxy/camera.config_test")
        await hass.async_block_till_done()
        mock_create_stream.assert_called_once()
        mock_stream.async_get_image.assert_called_once()
        assert resp.status == HTTPStatus.OK
        assert await resp.read() == b"stream_keyframe_image"


def test_frame_interval_property(hass):
    """Test that the frame interval is calculated and returned correctly."""
    cam = GenericCamera(
        hass,
        {
            "name": "config_test",
            "platform": "generic",
            "still_image_url": cv.template("http://example.com"),
            "username": "user",
            "password": "pass",
            "framerate": 5,
            "limit_refetch_to_url_change": True,
            "content_type": "image/jpeg",
            "verify_ssl": True,
        },
    )
    assert cam.frame_interval == pytest.approx(0.2)

