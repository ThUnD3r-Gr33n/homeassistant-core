"""The tests for the DirecTV Media player platform."""
from datetime import datetime, timedelta
from typing import Optional

from asynctest import patch
from pytest import fixture

from homeassistant.components.directv.media_player import (
    ATTR_MEDIA_CURRENTLY_RECORDING,
    ATTR_MEDIA_RATING,
    ATTR_MEDIA_RECORDED,
    ATTR_MEDIA_START_TIME,
)
from homeassistant.components.media_player.const import (
    ATTR_INPUT_SOURCE,
    ATTR_MEDIA_CHANNEL,
    ATTR_MEDIA_CONTENT_ID,
    ATTR_MEDIA_CONTENT_TYPE,
    ATTR_MEDIA_DURATION,
    ATTR_MEDIA_ENQUEUE,
    ATTR_MEDIA_POSITION,
    ATTR_MEDIA_POSITION_UPDATED_AT,
    ATTR_MEDIA_SERIES_TITLE,
    ATTR_MEDIA_TITLE,
    DOMAIN as MP_DOMAIN,
    MEDIA_TYPE_MOVIE,
    MEDIA_TYPE_TVSHOW,
    SUPPORT_NEXT_TRACK,
    SUPPORT_PAUSE,
    SUPPORT_PLAY,
    SUPPORT_PLAY_MEDIA,
    SUPPORT_PREVIOUS_TRACK,
    SUPPORT_STOP,
    SUPPORT_TURN_OFF,
    SUPPORT_TURN_ON,
)
from homeassistant.const import (
    STATE_PAUSED,
    STATE_PLAYING,
    STATE_UNAVAILABLE,
)
from homeassistant.helpers.typing import HomeAssistantType
from homeassistant.util import dt as dt_util

from tests.components.directv import setup_integration
from tests.components.media_player import common
from tests.test_util.aiohttp import AiohttpClientMocker

ATTR_UNIQUE_ID = "unique_id"
CLIENT_ENTITY_ID = f"{MP_DOMAIN}.client"
MAIN_ENTITY_ID = f"{MP_DOMAIN}.host"
UNAVAILABLE_ENTITY_ID = f"{MP_DOMAIN}.unavailable_client"

# pylint: disable=redefined-outer-name


@fixture
def mock_now() -> datetime:
    """Fixture for dtutil.now."""
    return dt_util.utcnow()


async def test_setup(
    hass: HomeAssistantType, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test setup with basic config."""
    await setup_integration(hass, aioclient_mock)
    assert hass.states.get(MAIN_ENTITY_ID)
    assert hass.states.get(CLIENT_ENTITY_ID)
    assert hass.states.get(UNAVAILABLE_ENTITY_ID)


async def test_unique_id(
    hass: HomeAssistantType, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test unique id."""
    await setup_integration(hass, aioclient_mock)

    entity_registry = await hass.helpers.entity_registry.async_get_registry()

    main = entity_registry.async_get(MAIN_ENTITY_ID)
    assert main.unique_id == "028877455858"

    client = entity_registry.async_get(CLIENT_ENTITY_ID)
    assert client.unique_id == "2CA17D1CD30X"

    unavailable_client = entity_registry.async_get(UNAVAILABLE_ENTITY_ID)
    assert unavailable_client.unique_id == "9XXXXXXXXXX9"


async def test_supported_features(
    hass: HomeAssistantType, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test supported features."""
    await setup_integration(hass, aioclient_mock)

    # Features supported for main DVR
    state = hass.states.get(MAIN_ENTITY_ID)
    assert (
        SUPPORT_PAUSE
        | SUPPORT_TURN_ON
        | SUPPORT_TURN_OFF
        | SUPPORT_PLAY_MEDIA
        | SUPPORT_STOP
        | SUPPORT_NEXT_TRACK
        | SUPPORT_PREVIOUS_TRACK
        | SUPPORT_PLAY
        == state.attributes.get("supported_features")
    )

    # Feature supported for clients.
    state = hass.states.get(CLIENT_ENTITY_ID)
    assert (
        SUPPORT_PAUSE
        | SUPPORT_PLAY_MEDIA
        | SUPPORT_STOP
        | SUPPORT_NEXT_TRACK
        | SUPPORT_PREVIOUS_TRACK
        | SUPPORT_PLAY
        == state.attributes.get("supported_features")
    )


async def test_check_attributes(
    hass: HomeAssistantType,
    mock_now: dt_util.dt.datetime,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test attributes."""
    await setup_integration(hass, aioclient_mock)

    state = hass.states.get(MAIN_ENTITY_ID)
    assert state.state == STATE_PLAYING

    assert state.attributes.get(ATTR_MEDIA_CONTENT_ID) == "17016356"
    assert state.attributes.get(ATTR_MEDIA_CONTENT_TYPE) == MEDIA_TYPE_MOVIE
    assert state.attributes.get(ATTR_MEDIA_DURATION) == 7200
    assert state.attributes.get(ATTR_MEDIA_POSITION) == 4437
    assert state.attributes.get(ATTR_MEDIA_POSITION_UPDATED_AT)
    assert state.attributes.get(ATTR_MEDIA_TITLE) == "Snow Bride"
    assert state.attributes.get(ATTR_MEDIA_SERIES_TITLE) is None
    assert state.attributes.get(ATTR_MEDIA_CHANNEL) == "{} ({})".format("HALLHD", "312")
    assert state.attributes.get(ATTR_INPUT_SOURCE) == "312"
    assert not state.attributes.get(ATTR_MEDIA_CURRENTLY_RECORDING)
    assert state.attributes.get(ATTR_MEDIA_RATING) == "TV-G"
    assert not state.attributes.get(ATTR_MEDIA_RECORDED)
    assert state.attributes.get(ATTR_MEDIA_START_TIME) == datetime(
        2020, 3, 21, 13, 0, tzinfo=dt_util.UTC
    )

    state = hass.states.get(CLIENT_ENTITY_ID)
    assert state.state == STATE_PLAYING

    assert state.attributes.get(ATTR_MEDIA_CONTENT_ID) == "4405732"
    assert state.attributes.get(ATTR_MEDIA_CONTENT_TYPE) == MEDIA_TYPE_TVSHOW
    assert state.attributes.get(ATTR_MEDIA_DURATION) == 1791
    assert state.attributes.get(ATTR_MEDIA_POSITION) == 263
    assert state.attributes.get(ATTR_MEDIA_POSITION_UPDATED_AT)
    assert state.attributes.get(ATTR_MEDIA_TITLE) == "Tyler's Ultimate"
    assert state.attributes.get(ATTR_MEDIA_SERIES_TITLE) == "Spaghetti and Clam Sauce"
    assert state.attributes.get(ATTR_MEDIA_CHANNEL) == "{} ({})".format("FOODHD", "231")
    assert state.attributes.get(ATTR_INPUT_SOURCE) == "231"
    assert not state.attributes.get(ATTR_MEDIA_CURRENTLY_RECORDING)
    assert state.attributes.get(ATTR_MEDIA_RATING) == "No Rating"
    assert state.attributes.get(ATTR_MEDIA_RECORDED)
    assert state.attributes.get(ATTR_MEDIA_START_TIME) == datetime(
        2010, 7, 5, 15, 0, 8, tzinfo=dt_util.UTC
    )

    state = hass.states.get(UNAVAILABLE_ENTITY_ID)
    assert state.state == STATE_UNAVAILABLE


async def test_attributes_paused(
    hass: HomeAssistantType,
    mock_now: dt_util.dt.datetime,
    aioclient_mock: AiohttpClientMocker,
):
    """Test attributes while paused."""
    await setup_integration(hass, aioclient_mock)

    state = hass.states.get(CLIENT_ENTITY_ID)
    last_updated = state.attributes.get(ATTR_MEDIA_POSITION_UPDATED_AT)

    # Test to make sure that ATTR_MEDIA_POSITION_UPDATED_AT is not
    # updated if TV is paused.
    with patch(
        "homeassistant.util.dt.utcnow", return_value=mock_now + timedelta(minutes=5)
    ):
        await common.async_media_pause(hass, CLIENT_ENTITY_ID)

    state = hass.states.get(CLIENT_ENTITY_ID)
    assert state.state == STATE_PAUSED
    assert state.attributes.get(ATTR_MEDIA_POSITION_UPDATED_AT) == last_updated


async def test_main_services(
    hass: HomeAssistantType,
    mock_now: dt_util.dt.datetime,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test the different services."""
    await setup_integration(hass, aioclient_mock)

    with patch("directv.DIRECTV.remote") as remote_mock:
        await common.async_turn_off(hass, MAIN_ENTITY_ID)
        remote_mock.assert_called_once_with("poweroff", "0")

    with patch("directv.DIRECTV.remote") as remote_mock:
        await common.async_turn_on(hass, MAIN_ENTITY_ID)
        remote_mock.assert_called_once_with("poweron", "0")

    with patch("directv.DIRECTV.remote") as remote_mock:
        await common.async_media_pause(hass, MAIN_ENTITY_ID)
        remote_mock.assert_called_once_with("pause", "0")

    with patch("directv.DIRECTV.remote") as remote_mock:
        await remote.async_media_play(hass, MAIN_ENTITY_ID)
        remote_mock.assert_called_once_with("play", "0")

    with patch("directv.DIRECTV.remote") as remote_mock:
        await common.async_media_next_track(hass, MAIN_ENTITY_ID)
        remote_mock.assert_called_once_with("ffwd", "0")

    with patch("directv.DIRECTV.remote") as remote_mock:
        await common.async_media_previous_track(hass, MAIN_ENTITY_ID)
        remote_mock.assert_called_once_with("rew", "0")

    with patch("directv.DIRECTV.remote") as remote_mock:
        await common.async_media_stop(hass, MAIN_ENTITY_ID)
        remote_mock.assert_called_once_with("stop", "0")

    with patch("directv.DIRECTV.tune") as tune_mock:
        await common.async_play_media(hass, "channel", 312, MAIN_ENTITY_ID)
        tune_mock.assert_called_once_with("312", "0")
