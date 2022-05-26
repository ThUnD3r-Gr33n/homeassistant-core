"""Denon HEOS Media Player."""
from __future__ import annotations

from collections.abc import Awaitable, Callable, Coroutine
from functools import reduce, wraps
import logging
from operator import ior
from typing import Any

from pyheos import HeosError, const as heos_const
from typing_extensions import ParamSpec

from homeassistant.components import media_source
from homeassistant.components.media_player import (
    MediaPlayerEnqueue,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
)
from homeassistant.components.media_player.browse_media import (
    async_process_play_media_url,
)
from homeassistant.components.media_player.const import (
    ATTR_MEDIA_ENQUEUE,
    DOMAIN,
    MEDIA_TYPE_MUSIC,
    MEDIA_TYPE_PLAYLIST,
    MEDIA_TYPE_URL,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_IDLE, STATE_PAUSED, STATE_PLAYING
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.dt import utcnow

from .const import (
    DATA_ENTITY_ID_MAP,
    DATA_GROUP_MANAGER,
    DATA_SOURCE_MANAGER,
    DOMAIN as HEOS_DOMAIN,
    SIGNAL_HEOS_PLAYER_ADDED,
    SIGNAL_HEOS_UPDATED,
)

_P = ParamSpec("_P")

BASE_SUPPORTED_FEATURES = (
    MediaPlayerEntityFeature.VOLUME_MUTE
    | MediaPlayerEntityFeature.VOLUME_SET
    | MediaPlayerEntityFeature.VOLUME_STEP
    | MediaPlayerEntityFeature.CLEAR_PLAYLIST
    | MediaPlayerEntityFeature.SHUFFLE_SET
    | MediaPlayerEntityFeature.SELECT_SOURCE
    | MediaPlayerEntityFeature.PLAY_MEDIA
    | MediaPlayerEntityFeature.GROUPING
    | MediaPlayerEntityFeature.BROWSE_MEDIA
)

PLAY_STATE_TO_STATE = {
    heos_const.PLAY_STATE_PLAY: STATE_PLAYING,
    heos_const.PLAY_STATE_STOP: STATE_IDLE,
    heos_const.PLAY_STATE_PAUSE: STATE_PAUSED,
}

CONTROL_TO_SUPPORT = {
    heos_const.CONTROL_PLAY: MediaPlayerEntityFeature.PLAY,
    heos_const.CONTROL_PAUSE: MediaPlayerEntityFeature.PAUSE,
    heos_const.CONTROL_STOP: MediaPlayerEntityFeature.STOP,
    heos_const.CONTROL_PLAY_PREVIOUS: MediaPlayerEntityFeature.PREVIOUS_TRACK,
    heos_const.CONTROL_PLAY_NEXT: MediaPlayerEntityFeature.NEXT_TRACK,
}

HA_HEOS_ENQUEUE_MAP = {
    None: heos_const.ADD_QUEUE_REPLACE_AND_PLAY,
    MediaPlayerEnqueue.ADD: heos_const.ADD_QUEUE_ADD_TO_END,
    MediaPlayerEnqueue.REPLACE: heos_const.ADD_QUEUE_REPLACE_AND_PLAY,
    MediaPlayerEnqueue.NEXT: heos_const.ADD_QUEUE_PLAY_NEXT,
    MediaPlayerEnqueue.PLAY: heos_const.ADD_QUEUE_PLAY_NOW,
}

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Add media players for a config entry."""
    players = hass.data[HEOS_DOMAIN][DOMAIN]
    devices = [HeosMediaPlayer(player) for player in players.values()]
    async_add_entities(devices, True)


def log_command_error(
    command: str,
) -> Callable[[Callable[_P, Awaitable[Any]]], Callable[_P, Coroutine[Any, Any, None]]]:
    """Return decorator that logs command failure."""

    def decorator(
        func: Callable[_P, Awaitable[Any]]
    ) -> Callable[_P, Coroutine[Any, Any, None]]:
        @wraps(func)
        async def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> None:
            try:
                await func(*args, **kwargs)
            except (HeosError, ValueError) as ex:
                _LOGGER.error("Unable to %s: %s", command, ex)

        return wrapper

    return decorator


class HeosMediaPlayer(MediaPlayerEntity):
    """The HEOS player."""

    def __init__(self, player):
        """Initialize."""
        self._media_position_updated_at = None
        self._player = player
        self._signals = []
        self._attr_supported_features = BASE_SUPPORTED_FEATURES
        self._source_manager = None
        self._group_manager = None

    async def _player_update(self, player_id, event):
        """Handle player attribute updated."""
        if self._player.player_id != player_id:
            return
        if event == heos_const.EVENT_PLAYER_NOW_PLAYING_PROGRESS:
            self._media_position_updated_at = utcnow()
        await self.async_update_ha_state(True)

    async def _heos_updated(self):
        """Handle sources changed."""
        await self.async_update_ha_state(True)

    async def async_added_to_hass(self):
        """Device added to hass."""
        # Update state when attributes of the player change
        self._signals.append(
            self._player.heos.dispatcher.connect(
                heos_const.SIGNAL_PLAYER_EVENT, self._player_update
            )
        )
        # Update state when heos changes
        self._signals.append(
            async_dispatcher_connect(self.hass, SIGNAL_HEOS_UPDATED, self._heos_updated)
        )
        # Register this player's entity_id so it can be resolved by the group manager
        self.hass.data[HEOS_DOMAIN][DATA_ENTITY_ID_MAP][
            self._player.player_id
        ] = self.entity_id
        async_dispatcher_send(self.hass, SIGNAL_HEOS_PLAYER_ADDED)

    @log_command_error("clear playlist")
    async def async_clear_playlist(self):
        """Clear players playlist."""
        await self._player.clear_queue()

    @log_command_error("join_players")
    async def async_join_players(self, group_members: list[str]) -> None:
        """Join `group_members` as a player group with the current player."""
        await self._group_manager.async_join_players(self.entity_id, group_members)

    @log_command_error("pause")
    async def async_media_pause(self):
        """Send pause command."""
        await self._player.pause()

    @log_command_error("play")
    async def async_media_play(self):
        """Send play command."""
        await self._player.play()

    @log_command_error("move to previous track")
    async def async_media_previous_track(self):
        """Send previous track command."""
        await self._player.play_previous()

    @log_command_error("move to next track")
    async def async_media_next_track(self):
        """Send next track command."""
        await self._player.play_next()

    @log_command_error("stop")
    async def async_media_stop(self):
        """Send stop command."""
        await self._player.stop()

    @log_command_error("set mute")
    async def async_mute_volume(self, mute):
        """Mute the volume."""
        await self._player.set_mute(mute)

    @log_command_error("play media")
    async def async_play_media(self, media_type, media_id, **kwargs):
        """Play a piece of media."""
        if media_source.is_media_source_id(media_id):
            media_type = MEDIA_TYPE_URL
            play_item = await media_source.async_resolve_media(self.hass, media_id)
            media_id = play_item.url

        if media_type in (MEDIA_TYPE_URL, MEDIA_TYPE_MUSIC):
            media_id = async_process_play_media_url(self.hass, media_id)

            await self._player.play_url(media_id)
            return

        if media_type == "quick_select":
            # media_id may be an int or a str
            selects = await self._player.get_quick_selects()
            try:
                index = int(media_id)
            except ValueError:
                # Try finding index by name
                index = next(
                    (index for index, select in selects.items() if select == media_id),
                    None,
                )
            if index is None:
                raise ValueError(f"Invalid quick select '{media_id}'")
            await self._player.play_quick_select(index)
            return

        if media_type == MEDIA_TYPE_PLAYLIST:
            playlists = await self._player.heos.get_playlists()
            playlist = next((p for p in playlists if p.name == media_id), None)
            if not playlist:
                raise ValueError(f"Invalid playlist '{media_id}'")
            add_queue_option = HA_HEOS_ENQUEUE_MAP.get(kwargs.get(ATTR_MEDIA_ENQUEUE))

            await self._player.add_to_queue(playlist, add_queue_option)
            return

        if media_type == "favorite":
            # media_id may be an int or str
            try:
                index = int(media_id)
            except ValueError:
                # Try finding index by name
                index = next(
                    (
                        index
                        for index, favorite in self._source_manager.favorites.items()
                        if favorite.name == media_id
                    ),
                    None,
                )
            if index is None:
                raise ValueError(f"Invalid favorite '{media_id}'")
            await self._player.play_favorite(index)
            return

        raise ValueError(f"Unsupported media type '{media_type}'")

    @log_command_error("select source")
    async def async_select_source(self, source):
        """Select input source."""
        await self._source_manager.play_source(source, self._player)

    @log_command_error("set shuffle")
    async def async_set_shuffle(self, shuffle):
        """Enable/disable shuffle mode."""
        await self._player.set_play_mode(self._player.repeat, shuffle)

    @log_command_error("set volume level")
    async def async_set_volume_level(self, volume):
        """Set volume level, range 0..1."""
        await self._player.set_volume(int(volume * 100))

    async def async_update(self):
        """Update supported features of the player."""
        controls = self._player.now_playing_media.supported_controls
        current_support = [CONTROL_TO_SUPPORT[control] for control in controls]
        self._attr_supported_features = reduce(
            ior, current_support, BASE_SUPPORTED_FEATURES
        )

        if self._group_manager is None:
            self._group_manager = self.hass.data[HEOS_DOMAIN][DATA_GROUP_MANAGER]

        if self._source_manager is None:
            self._source_manager = self.hass.data[HEOS_DOMAIN][DATA_SOURCE_MANAGER]

    @log_command_error("unjoin_player")
    async def async_unjoin_player(self):
        """Remove this player from any group."""
        await self._group_manager.async_unjoin_player(self.entity_id)

    async def async_will_remove_from_hass(self):
        """Disconnect the device when removed."""
        for signal_remove in self._signals:
            signal_remove()
        self._signals.clear()

    @property
    def available(self) -> bool:
        """Return True if the device is available."""
        return self._player.available

    @property
    def device_info(self) -> DeviceInfo:
        """Get attributes about the device."""
        return DeviceInfo(
            identifiers={(HEOS_DOMAIN, self._player.player_id)},
            manufacturer="HEOS",
            model=self._player.model,
            name=self._player.name,
            sw_version=self._player.version,
        )

    @property
    def extra_state_attributes(self) -> dict:
        """Get additional attribute about the state."""
        return {
            "media_album_id": self._player.now_playing_media.album_id,
            "media_queue_id": self._player.now_playing_media.queue_id,
            "media_source_id": self._player.now_playing_media.source_id,
            "media_station": self._player.now_playing_media.station,
            "media_type": self._player.now_playing_media.type,
        }

    @property
    def group_members(self) -> list[str]:
        """List of players which are grouped together."""
        return self._group_manager.group_membership.get(self.entity_id, [])

    @property
    def is_volume_muted(self) -> bool:
        """Boolean if volume is currently muted."""
        return self._player.is_muted

    @property
    def media_album_name(self) -> str:
        """Album name of current playing media, music track only."""
        return self._player.now_playing_media.album

    @property
    def media_artist(self) -> str:
        """Artist of current playing media, music track only."""
        return self._player.now_playing_media.artist

    @property
    def media_content_id(self) -> str:
        """Content ID of current playing media."""
        return self._player.now_playing_media.media_id

    @property
    def media_content_type(self) -> str:
        """Content type of current playing media."""
        return MEDIA_TYPE_MUSIC

    @property
    def media_duration(self):
        """Duration of current playing media in seconds."""
        duration = self._player.now_playing_media.duration
        if isinstance(duration, int):
            return duration / 1000
        return None

    @property
    def media_position(self):
        """Position of current playing media in seconds."""
        # Some media doesn't have duration but reports position, return None
        if not self._player.now_playing_media.duration:
            return None
        return self._player.now_playing_media.current_position / 1000

    @property
    def media_position_updated_at(self):
        """When was the position of the current playing media valid."""
        # Some media doesn't have duration but reports position, return None
        if not self._player.now_playing_media.duration:
            return None
        return self._media_position_updated_at

    @property
    def media_image_remotely_accessible(self) -> bool:
        """If the image url is remotely accessible."""
        return True

    @property
    def media_image_url(self) -> str:
        """Image url of current playing media."""
        # May be an empty string, if so, return None
        image_url = self._player.now_playing_media.image_url
        return image_url if image_url else None

    @property
    def media_title(self) -> str:
        """Title of current playing media."""
        return self._player.now_playing_media.song

    @property
    def name(self) -> str:
        """Return the name of the device."""
        return self._player.name

    @property
    def should_poll(self) -> bool:
        """No polling needed for this device."""
        return False

    @property
    def shuffle(self) -> bool:
        """Boolean if shuffle is enabled."""
        return self._player.shuffle

    @property
    def source(self) -> str:
        """Name of the current input source."""
        return self._source_manager.get_current_source(self._player.now_playing_media)

    @property
    def source_list(self) -> list[str]:
        """List of available input sources."""
        return self._source_manager.source_list

    @property
    def state(self) -> str:
        """State of the player."""
        return PLAY_STATE_TO_STATE[self._player.state]

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return str(self._player.player_id)

    @property
    def volume_level(self) -> float:
        """Volume level of the media player (0..1)."""
        return self._player.volume / 100

    async def async_browse_media(self, media_content_type=None, media_content_id=None):
        """Implement the websocket media browsing helper."""
        return await media_source.async_browse_media(
            self.hass,
            media_content_id,
            content_filter=lambda item: item.media_content_type.startswith("audio/"),
        )
