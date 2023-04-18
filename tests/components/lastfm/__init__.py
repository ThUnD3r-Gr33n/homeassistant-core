"""The tests for lastfm."""
from datetime import datetime
from unittest.mock import patch

from pylast import Album, PlayedTrack, TopItem, Track

from homeassistant.components.lastfm.const import CONF_USERS, DOMAIN
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry

API_KEY = "asdasdasdasdasd"
USERNAME_1 = "testaccount1"

CONF_USER_INPUT = {CONF_API_KEY: API_KEY, CONF_USERS: USERNAME_1}

CONF_DATA = {**CONF_USER_INPUT, CONF_USERS: [CONF_USER_INPUT[CONF_USERS]]}


class MockNetwork:
    """Mock _Network object for pylast."""

    def __init__(self, username: str) -> None:
        """Initialize the mock."""
        self.username = username


MOCK_TRACK = Track(
    artist="Goldband", title="Noodgeval", network=MockNetwork(USERNAME_1)
)

MOCK_ALBUM = Album(
    artist="Goldband", title="Betaalbare Romantiek", network=MockNetwork(USERNAME_1)
)

MOCK_PLAYED_TRACK = PlayedTrack(
    track=MOCK_TRACK,
    album=MOCK_ALBUM,
    playback_date=datetime.now(),
    timestamp=datetime.now(),
)

MOCK_TOP_ITEM = TopItem(item=MOCK_TRACK, weight=69)


def create_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Add config entry in Home Assistant."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=CONF_DATA,
        unique_id=USERNAME_1,
    )
    entry.add_to_hass(hass)
    return entry


class MockUser:
    """Mock User object for pylast."""

    def __init__(self, now_playing: Track | None = None) -> None:
        """Initialize the mock."""
        self.now_playing = now_playing

    def get_playcount(self) -> int | float:
        """Get mock play count."""
        return 1

    def get_image(self, size: int) -> str:
        """Get mock image."""
        return "yes"

    def get_recent_tracks(self, limit: int) -> list[PlayedTrack]:
        """Get mock recent tracks."""
        return [MOCK_PLAYED_TRACK]

    def get_top_tracks(self, limit: int) -> list[TopItem]:
        """Get mock top tracks."""
        return [MOCK_TOP_ITEM]

    def get_now_playing(self) -> Track | None:
        """Get mock now playing."""
        return self.now_playing


def patch_interface(now_playing: Track | None = None) -> MockUser:
    """Patch interface."""
    return patch("pylast.User", return_value=MockUser(now_playing))
