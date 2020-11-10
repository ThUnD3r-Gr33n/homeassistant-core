"""
Test for Nest cameras platform for the Smart Device Management API.

These tests fake out the subscriber/devicemanager, and are not using a real
pubsub subscriber.
"""

import datetime
from typing import List

from google_nest_sdm.auth import AbstractAuth
from google_nest_sdm.device import Device
from requests import HTTPError

from homeassistant.components import camera
from homeassistant.components.camera import STATE_IDLE
from homeassistant.util.dt import utcnow

from .common import async_setup_sdm_platform

from tests.async_mock import patch
from tests.common import async_fire_time_changed

PLATFORM = "camera"
CAMERA_DEVICE_TYPE = "sdm.devices.types.CAMERA"
DEVICE_ID = "some-device-id"
DEVICE_TRAITS = {
    "sdm.devices.traits.Info": {
        "customName": "My Camera",
    },
    "sdm.devices.traits.CameraLiveStream": {
        "maxVideoResolution": {
            "width": 640,
            "height": 480,
        },
        "videoCodecs": ["H264"],
        "audioCodecs": ["AAC"],
    },
}
DATETIME_FORMAT = "YY-MM-DDTHH:MM:SS"
DOMAIN = "nest"


class FakeResponse:
    """A fake web response used for returning results of commands."""

    def __init__(self, json=None, error=None):
        """Initialize the FakeResponse."""
        self._json = json
        self._error = error

    def raise_for_status(self):
        """Mimics a successful response status."""
        if self._error:
            raise self._error
        pass

    async def json(self):
        """Return a dict with the response."""
        assert self._json
        return self._json


class FakeAuth(AbstractAuth):
    """Fake authentication object that returns fake responses."""

    def __init__(self, responses: List[FakeResponse]):
        """Initialize the FakeAuth."""
        super().__init__(None, "")
        self._responses = responses

    async def async_get_access_token(self):
        """Return a fake access token."""
        return "some-token"

    async def creds(self):
        """Return a fake creds."""
        return None

    async def request(self, method: str, url: str, **kwargs):
        """Pass through the FakeResponse."""
        return self._responses.pop(0)


async def async_setup_camera(hass, traits={}, auth=None):
    """Set up the platform and prerequisites."""
    devices = {}
    if traits:
        devices[DEVICE_ID] = Device.MakeDevice(
            {
                "name": DEVICE_ID,
                "type": CAMERA_DEVICE_TYPE,
                "traits": traits,
            },
            auth=auth,
        )
    return await async_setup_sdm_platform(hass, PLATFORM, devices)


async def test_no_devices(hass):
    """Test configuration that returns no devices."""
    await async_setup_camera(hass)
    assert len(hass.states.async_all()) == 0


async def test_ineligible_device(hass):
    """Test configuration with devices that do not support cameras."""
    await async_setup_camera(
        hass,
        {
            "sdm.devices.traits.Info": {
                "customName": "My Camera",
            },
        },
    )
    assert len(hass.states.async_all()) == 0


async def test_camera_device(hass):
    """Test a basic camera with a live stream."""
    await async_setup_camera(hass, DEVICE_TRAITS)

    assert len(hass.states.async_all()) == 1
    camera = hass.states.get("camera.my_camera")
    assert camera is not None
    assert camera.state == STATE_IDLE

    registry = await hass.helpers.entity_registry.async_get_registry()
    entry = registry.async_get("camera.my_camera")
    assert entry.unique_id == "some-device-id-camera"
    assert entry.original_name == "My Camera"
    assert entry.domain == "camera"

    device_registry = await hass.helpers.device_registry.async_get_registry()
    device = device_registry.async_get(entry.device_id)
    assert device.name == "My Camera"
    assert device.model == "Camera"
    assert device.identifiers == {("nest", DEVICE_ID)}


async def test_camera_stream(hass, aiohttp_client):
    """Test a basic camera and fetch its live stream."""
    now = utcnow()
    expiration = now + datetime.timedelta(seconds=100)
    response = FakeResponse(
        {
            "results": {
                "streamUrls": {"rtspUrl": "rtsp://some/url?auth=g.0.streamingToken"},
                "streamExtensionToken": "g.1.extensionToken",
                "streamToken": "g.0.streamingToken",
                "expiresAt": expiration.isoformat(timespec="seconds"),
            },
        }
    )
    await async_setup_camera(hass, DEVICE_TRAITS, auth=FakeAuth([response]))

    assert len(hass.states.async_all()) == 1
    cam = hass.states.get("camera.my_camera")
    assert cam is not None
    assert cam.state == STATE_IDLE

    stream_source = await camera.async_get_stream_source(hass, "camera.my_camera")
    assert stream_source == "rtsp://some/url?auth=g.0.streamingToken"

    with patch(
        "homeassistant.components.ffmpeg.ImageFrame.get_image",
        autopatch=True,
        return_value=b"image bytes",
    ):
        image = await camera.async_get_image(hass, "camera.my_camera")

    assert image.content == b"image bytes"


async def test_refresh_expired_stream_token(hass, aiohttp_client):
    """Test a camera stream expiration and refresh."""
    now = utcnow()
    expiration = now + datetime.timedelta(seconds=90)
    new_expiration = now + datetime.timedelta(seconds=180)
    responses = [
        FakeResponse(
            {
                "results": {
                    "streamUrls": {
                        "rtspUrl": "rtsp://some/url?auth=g.0.streamingToken"
                    },
                    "streamExtensionToken": "g.1.extensionToken",
                    "streamToken": "g.0.streamingToken",
                    "expiresAt": expiration.isoformat(timespec="seconds"),
                },
            }
        ),
        FakeResponse(
            {
                "results": {
                    "streamExtensionToken": "g.3.extensionToken",
                    "streamToken": "g.2.streamingToken",
                    "expiresAt": new_expiration.isoformat(timespec="seconds"),
                },
            }
        ),
    ]
    await async_setup_camera(
        hass,
        DEVICE_TRAITS,
        auth=FakeAuth(responses),
    )

    assert len(hass.states.async_all()) == 1
    cam = hass.states.get("camera.my_camera")
    assert cam is not None
    assert cam.state == STATE_IDLE

    stream_source = await camera.async_get_stream_source(hass, "camera.my_camera")
    assert stream_source == "rtsp://some/url?auth=g.0.streamingToken"

    # Fire alarm (> refresh interval). The stream has not yet expired, so the
    # url is not refreshed
    next_update = now + datetime.timedelta(seconds=25)
    with patch("homeassistant.util.dt.utcnow", return_value=next_update):
        async_fire_time_changed(hass, next_update)
        await hass.async_block_till_done()
    stream_source = await camera.async_get_stream_source(hass, "camera.my_camera")
    assert stream_source == "rtsp://some/url?auth=g.0.streamingToken"

    # Fire alarm when stream is nearing expiration, causing it to be extended
    next_update = now + datetime.timedelta(seconds=65)
    with patch("homeassistant.util.dt.utcnow", return_value=next_update):
        async_fire_time_changed(hass, next_update)
        await hass.async_block_till_done()
    stream_source = await camera.async_get_stream_source(hass, "camera.my_camera")
    assert stream_source == "rtsp://some/url?auth=g.2.streamingToken"


async def test_camera_removed(hass, aiohttp_client):
    """Test case where entities are removed and stream tokens expired."""
    now = utcnow()
    expiration = now + datetime.timedelta(seconds=100)
    responses = [
        FakeResponse(
            {
                "results": {
                    "streamUrls": {
                        "rtspUrl": "rtsp://some/url?auth=g.0.streamingToken"
                    },
                    "streamExtensionToken": "g.1.extensionToken",
                    "streamToken": "g.0.streamingToken",
                    "expiresAt": expiration.isoformat(timespec="seconds"),
                },
            }
        ),
        FakeResponse({"results": {}}),
    ]
    await async_setup_camera(
        hass,
        DEVICE_TRAITS,
        auth=FakeAuth(responses),
    )

    assert len(hass.states.async_all()) == 1
    cam = hass.states.get("camera.my_camera")
    assert cam is not None
    assert cam.state == STATE_IDLE

    stream_source = await camera.async_get_stream_source(hass, "camera.my_camera")
    assert stream_source == "rtsp://some/url?auth=g.0.streamingToken"

    for config_entry in hass.config_entries.async_entries(DOMAIN):
        await hass.config_entries.async_remove(config_entry.entry_id)
    assert len(hass.states.async_all()) == 0


async def test_refresh_expired_stream_failure(hass, aiohttp_client):
    """Tests a failure when refreshing the stream."""
    now = utcnow()
    expiration = now + datetime.timedelta(seconds=90)
    new_expiration = now + datetime.timedelta(seconds=180)
    responses = [
        FakeResponse(
            {
                "results": {
                    "streamUrls": {
                        "rtspUrl": "rtsp://some/url?auth=g.0.streamingToken"
                    },
                    "streamExtensionToken": "g.1.extensionToken",
                    "streamToken": "g.0.streamingToken",
                    "expiresAt": expiration.isoformat(timespec="seconds"),
                },
            }
        ),
        # Extending the stream fails
        FakeResponse(error=HTTPError(response="Some Error")),
        # Next attempt to get a stream fetches a new url
        FakeResponse(
            {
                "results": {
                    "streamUrls": {
                        "rtspUrl": "rtsp://some/url?auth=g.4.streamingToken"
                    },
                    "streamExtensionToken": "g.5.extensionToken",
                    "streamToken": "g.4.streamingToken",
                    "expiresAt": new_expiration.isoformat(timespec="seconds"),
                },
            }
        ),
    ]
    await async_setup_camera(
        hass,
        DEVICE_TRAITS,
        auth=FakeAuth(responses),
    )

    assert len(hass.states.async_all()) == 1
    cam = hass.states.get("camera.my_camera")
    assert cam is not None
    assert cam.state == STATE_IDLE

    stream_source = await camera.async_get_stream_source(hass, "camera.my_camera")
    assert stream_source == "rtsp://some/url?auth=g.0.streamingToken"

    # Fire alarm when stream is nearing expiration, causing it to be extended.
    # The stream expires.
    next_update = now + datetime.timedelta(seconds=65)
    with patch("homeassistant.util.dt.utcnow", return_value=next_update):
        async_fire_time_changed(hass, next_update)
        await hass.async_block_till_done()

    # The stream is entirely refreshed
    stream_source = await camera.async_get_stream_source(hass, "camera.my_camera")
    assert stream_source == "rtsp://some/url?auth=g.4.streamingToken"
