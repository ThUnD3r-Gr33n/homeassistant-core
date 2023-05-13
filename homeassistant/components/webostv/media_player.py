"""Support for interface with an LG webOS Smart TV."""
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Coroutine
from contextlib import suppress
import datetime as datetime2
from datetime import datetime, timedelta
from functools import wraps
from http import HTTPStatus
import logging
from ssl import SSLContext
from typing import Any, Concatenate, ParamSpec, TypeVar, cast

from aiowebostv import WebOsClient, WebOsTvPairError
import async_timeout

from homeassistant import util
from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_SUPPORTED_FEATURES,
    ENTITY_MATCH_ALL,
    ENTITY_MATCH_NONE,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.trigger import PluggableAction
import homeassistant.util.dt as dt_util

from . import update_client_key
from .const import (
    ATTR_PAYLOAD,
    ATTR_SOUND_OUTPUT,
    CONF_SOURCES,
    DATA_CONFIG_ENTRY,
    DOMAIN,
    LIVE_TV_APP_ID,
    WEBOSTV_EXCEPTIONS,
)
from .triggers.turn_on import async_get_turn_on_trigger

_LOGGER = logging.getLogger(__name__)

SUPPORT_WEBOSTV = (
    MediaPlayerEntityFeature.TURN_OFF
    | MediaPlayerEntityFeature.NEXT_TRACK
    | MediaPlayerEntityFeature.PAUSE
    | MediaPlayerEntityFeature.PREVIOUS_TRACK
    | MediaPlayerEntityFeature.SELECT_SOURCE
    | MediaPlayerEntityFeature.PLAY_MEDIA
    | MediaPlayerEntityFeature.PLAY
    | MediaPlayerEntityFeature.STOP
)

SUPPORT_WEBOSTV_VOLUME = (
    MediaPlayerEntityFeature.VOLUME_MUTE | MediaPlayerEntityFeature.VOLUME_STEP
)

MIN_TIME_BETWEEN_SCANS = timedelta(seconds=10)
MIN_TIME_BETWEEN_FORCED_SCANS = timedelta(seconds=1)
SCAN_INTERVAL = timedelta(seconds=10)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the LG webOS Smart TV platform."""
    client = hass.data[DOMAIN][DATA_CONFIG_ENTRY][entry.entry_id]
    async_add_entities([LgWebOSMediaPlayerEntity(entry, client)])


_T = TypeVar("_T", bound="LgWebOSMediaPlayerEntity")
_P = ParamSpec("_P")


def cmd(
    func: Callable[Concatenate[_T, _P], Awaitable[None]]
) -> Callable[Concatenate[_T, _P], Coroutine[Any, Any, None]]:
    """Catch command exceptions."""

    @wraps(func)
    async def cmd_wrapper(self: _T, *args: _P.args, **kwargs: _P.kwargs) -> None:
        """Wrap all command methods."""
        try:
            await func(self, *args, **kwargs)
        except WEBOSTV_EXCEPTIONS as exc:
            if self.state != MediaPlayerState.OFF:
                raise HomeAssistantError(
                    f"Error calling {func.__name__} on entity {self.entity_id},"
                    f" state:{self.state}"
                ) from exc
            _LOGGER.warning(
                "Error calling %s on entity %s, state:%s, error: %r",
                func.__name__,
                self.entity_id,
                self.state,
                exc,
            )

    return cmd_wrapper


class LgWebOSMediaPlayerEntity(RestoreEntity, MediaPlayerEntity):
    """Representation of a LG webOS Smart TV."""

    _attr_device_class = MediaPlayerDeviceClass.TV
    language_code: str = ""

    def __init__(self, entry: ConfigEntry, client: WebOsClient) -> None:
        """Initialize the webos device."""
        self._entry = entry
        self._client = client
        self._attr_assumed_state = True
        self._attr_name = entry.title
        self._attr_unique_id = entry.unique_id
        self._sources = entry.options.get(CONF_SOURCES)

        # Assume that the TV is not paused
        self._paused = False
        self._turn_on = PluggableAction(self.async_write_ha_state)
        self._current_source = None
        self._source_list: dict = {}

        self._supported_features = MediaPlayerEntityFeature(0)
        self._update_states()

    async def async_added_to_hass(self) -> None:
        """Connect and subscribe to dispatcher signals and state updates."""
        await super().async_added_to_hass()

        if (entry := self.registry_entry) and entry.device_id:
            self.async_on_remove(
                self._turn_on.async_register(
                    self.hass, async_get_turn_on_trigger(entry.device_id)
                )
            )

        self.async_on_remove(
            async_dispatcher_connect(self.hass, DOMAIN, self.async_signal_handler)
        )

        await self._client.register_state_update_callback(
            self.async_handle_state_update
        )

        if (
            self.state == MediaPlayerState.OFF
            and (state := await self.async_get_last_state()) is not None
        ):
            self._supported_features = (
                state.attributes.get(
                    ATTR_SUPPORTED_FEATURES, MediaPlayerEntityFeature(0)
                )
                & ~MediaPlayerEntityFeature.TURN_ON
            )

    async def async_will_remove_from_hass(self) -> None:
        """Call disconnect on removal."""
        self._client.unregister_state_update_callback(self.async_handle_state_update)

    async def async_signal_handler(self, data: dict[str, Any]) -> None:
        """Handle domain-specific signal by calling appropriate method."""
        if (entity_ids := data[ATTR_ENTITY_ID]) == ENTITY_MATCH_NONE:
            return

        if entity_ids == ENTITY_MATCH_ALL or self.entity_id in entity_ids:
            params = {
                key: value
                for key, value in data.items()
                if key not in ["entity_id", "method"]
            }
            await getattr(self, data["method"])(**params)

    async def async_handle_state_update(self, _client: WebOsClient) -> None:
        """Update state from WebOsClient."""
        self._update_states()
        self.async_write_ha_state()

    def _update_states_livetv(self) -> None:
        if (self.state == MediaPlayerState.OFF) or (not self._client.is_on):
            return
        channel_name: str | None = (
            cast(str, self._client.current_channel.get("channelName"))
            if (self._client.current_channel["channelName"] is not None)
            else None
        )
        self._attr_media_channel = channel_name
        channel_id: str | None = (
            cast(str, self._client.current_channel.get("channelId"))
            if (self._client.current_channel["channelId"] is not None)
            else None
        )
        channel_type_name: str | None = (
            cast(str, self._client.current_channel.get("channelTypeName"))
            if (self._client.current_channel.get("channelTypeName") is not None)
            else None
        )
        if channel_type_name is not None:
            self._attr_extra_state_attributes.update(
                {"channel_type_name": channel_type_name}
            )
        channel_mode_name: str | None = (
            cast(str, self._client.current_channel.get("channelModeName"))
            if (self._client.current_channel.get("channelModeName") is not None)
            else None
        )
        if channel_mode_name is not None:
            self._attr_extra_state_attributes.update(
                {"channel_mode_name": channel_mode_name}
            )
        is_hevc_channel: bool | None = (
            cast(bool, self._client.current_channel.get("isHEVCChannel"))
            if (self._client.current_channel.get("isHEVCChannel") is not None)
            else None
        )
        if is_hevc_channel is not None:
            self._attr_extra_state_attributes.update(
                {"is_hevc_channel": is_hevc_channel}
            )
        hybrid_tv_type: str | None = (
            cast(str, self._client.current_channel.get("hybridtvType"))
            if (self._client.current_channel.get("hybridtvType") is not None)
            else None
        )
        if hybrid_tv_type is not None:
            self._attr_extra_state_attributes.update({"hybrid_tv_type": hybrid_tv_type})
        is_tv: bool = True
        is_radio: bool = False
        if channel_id is not None:
            has_adult_flag: bool = False
            for channel in self._client.channels:
                if channel_id == channel["channelId"]:
                    is_tv = cast(bool, channel.get("TV"))
                    is_radio = cast(bool, channel.get("Radio"))
                    # channel_logo_size = cast(str, channel["channelLogoSize"])         #i.e: "H133x100"
                    img_url: str = cast(str, channel.get("imgUrl"))
                    if (
                        (img_url is not None)
                        and (len(img_url) > 3)
                        and (img_url.startswith("http"))
                    ):
                        self._attr_media_image_url = img_url
                    break
        self._attr_extra_state_attributes.update({"is_radio": is_radio, "is_tv": is_tv})
        if is_tv:
            strtime_pattern: str | None = None  # "%Y,%d,%m,%-I,%M,%S"    <-- for non-Italians? need someone to test it
            if self.language_code in ["it-IT"]:
                strtime_pattern = "%Y,%m,%d,%H,%M,%S"
            channel = (
                (self._client.channel_info.get("channel"))
                if (self._client.channel_info.get("channel") is not None)
                else None
            )
            if (
                (channel is not None)
                and (channel["adultFlag"] is not None)
                and (channel["adultFlag"] > 0)
            ):
                has_adult_flag = cast(str, channel.get("adultFlag")) != "0"
                self._attr_extra_state_attributes.update(
                    {"has_adult_flag": has_adult_flag}
                )
            programs: list = (
                self._client.channel_info.get("programList")
                if (self._client.channel_info.get("programList") is not None)
                else None
            )
            if (programs is not None) and (strtime_pattern is not None):
                for program in programs:
                    # datetime in "2023,05,13,23,50,06" format (<-- this specific sample is for "it-IT")
                    start_time: str = cast(str, program["startTime"])
                    end_time: str = cast(str, program["endTime"])
                    cast(str, program["localStartTime"])
                    cast(str, program["localEndTime"])
                    date_start_time = datetime2.datetime.strptime(
                        start_time, strtime_pattern
                    )
                    date_end_time = datetime2.datetime.strptime(
                        end_time, strtime_pattern
                    )
                    current_datetime = datetime.utcnow()
                    # don't know why but it could be possible that received Datetimes are shifted by 1 or more days,
                    # so it should be fixed before comparison
                    diff = current_datetime - date_start_time
                    current_datetime = current_datetime + timedelta(days=-diff.days)

                    if (current_datetime > date_end_time) or (
                        current_datetime < date_start_time
                    ):
                        continue

                    seconds_start_current_diff: int = (
                        current_datetime - date_start_time
                    ).seconds
                    self._attr_media_position_updated_at = dt_util.utcnow()
                    self._attr_media_position = seconds_start_current_diff

                    if program["duration"] is not None:
                        self._attr_media_duration = cast(
                            int, program["duration"]
                        )  # in seconds
                    program_name: str = cast(str, program["programName"])
                    if (program_name is not None) and (len(program_name) > 0):
                        self._attr_media_title = program_name
                    program_id: str = cast(str, program["programId"])
                    if (program_id is not None) and (len(program_id) > 0):
                        self._attr_media_content_id = program_id

                    genre = cast(str, program["genre"])
                    if (genre is not None) and (len(genre) > 0):
                        self._attr_media_genre = genre

                    self._attr_state = MediaPlayerState.PLAYING

            if (self._attr_media_title is None) or (len(self._attr_media_title) <= 0):
                self._attr_media_title = self._attr_media_channel

    def _update_states(self) -> None:
        """Update entity state attributes."""
        self._update_sources()
        supported = SUPPORT_WEBOSTV
        self._attr_extra_state_attributes = {}
        self._attr_state = (
            MediaPlayerState.ON if self._client.is_on else MediaPlayerState.OFF
        )
        self._attr_is_volume_muted = cast(bool, self._client.muted)

        self._attr_volume_level = None
        if self._client.volume is not None:
            self._attr_volume_level = cast(float, self._client.volume / 100.0)

        self._attr_source = self._current_source
        self._attr_source_list = sorted(self._source_list)

        if (
            (self.language_code == "")
            and (self._client.software_info is not None)
            and (self._client.software_info.get("language_code") is not None)
            and (len(self._client.software_info.get("language_code")) > 4)
        ):
            self.language_code = cast(
                str, self._client.software_info.get("language_code")
            )

        self._attr_media_content_type = None
        if self._client.current_app_id == LIVE_TV_APP_ID:
            self._attr_media_content_type = MediaType.CHANNEL
        else:
            self._attr_state = MediaPlayerState.STANDBY

        self._attr_media_title = None
        self._attr_media_channel = None
        self._attr_media_image_url = None
        self._attr_media_position = 0
        self._attr_media_duration = 0
        self._attr_media_genre = None
        if (self._client.current_app_id == LIVE_TV_APP_ID) and (
            self._client.current_channel is not None
        ):
            self._attr_media_title = cast(
                str, self._client.current_channel.get("channelName")
            )
            self._update_states_livetv()
            if self._attr_extra_state_attributes.get("is_tv"):
                supported &= ~MediaPlayerEntityFeature.STOP
                supported &= ~MediaPlayerEntityFeature.PAUSE
                supported &= ~MediaPlayerEntityFeature.PLAY
                supported &= ~MediaPlayerEntityFeature.PLAY_MEDIA

        self._attr_media_image_url = None
        if self._client.current_app_id in self._client.apps:
            icon: str = self._client.apps[self._client.current_app_id]["largeIcon"]
            if not icon.startswith("http"):
                icon = self._client.apps[self._client.current_app_id]["icon"]
            self._attr_media_image_url = icon

        if self.state != MediaPlayerState.OFF or not self._supported_features:
            if self._client.sound_output in ("external_arc", "external_speaker"):
                supported |= SUPPORT_WEBOSTV_VOLUME
            elif self._client.sound_output != "lineout":
                supported |= (
                    SUPPORT_WEBOSTV_VOLUME | MediaPlayerEntityFeature.VOLUME_SET
                )

            self._supported_features = supported

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, cast(str, self.unique_id))},
            manufacturer="LG",
            name=self.name,
        )

        if (
            (self._client.system_info is not None)
            and (self._client.software_info is not None)
            and (self.state != MediaPlayerState.OFF)
        ):
            maj_v = self._client.software_info.get("major_ver")
            min_v = self._client.software_info.get("minor_ver")
            if maj_v and min_v:
                self._attr_device_info["sw_version"] = f"{maj_v}.{min_v}"

            if model := self._client.system_info.get("modelName"):
                self._attr_device_info["model"] = model

        if (self._client.sound_output is not None) and (
            self.state != MediaPlayerState.OFF
        ):
            self._attr_extra_state_attributes.update(
                {ATTR_SOUND_OUTPUT: self._client.sound_output}
            )

    def _update_sources(self) -> None:
        """Update list of sources from current source, apps, inputs and configured list."""
        source_list = self._source_list
        self._source_list = {}
        conf_sources = self._sources

        found_live_tv = False
        for app in self._client.apps.values():
            if app["id"] == LIVE_TV_APP_ID:
                found_live_tv = True
            if app["id"] == self._client.current_app_id:
                self._current_source = app["title"]
                self._source_list[app["title"]] = app
            elif (
                not conf_sources
                or app["id"] in conf_sources
                or any(word in app["title"] for word in conf_sources)
                or any(word in app["id"] for word in conf_sources)
            ):
                self._source_list[app["title"]] = app

        for source in self._client.inputs.values():
            if source["appId"] == LIVE_TV_APP_ID:
                found_live_tv = True
            if source["appId"] == self._client.current_app_id:
                self._current_source = source["label"]
                self._source_list[source["label"]] = source
            elif (
                not conf_sources
                or source["label"] in conf_sources
                or any(source["label"].find(word) != -1 for word in conf_sources)
            ):
                self._source_list[source["label"]] = source

        # empty list, TV may be off, keep previous list
        if not self._source_list and source_list:
            self._source_list = source_list
        # special handling of live tv since this might
        # not appear in the app or input lists in some cases
        elif not found_live_tv:
            app = {"id": LIVE_TV_APP_ID, "title": "Live TV"}
            if self._client.current_app_id == LIVE_TV_APP_ID:
                self._current_source = app["title"]
                self._source_list["Live TV"] = app
            elif (
                not conf_sources
                or app["id"] in conf_sources
                or any(word in app["title"] for word in conf_sources)
                or any(word in app["id"] for word in conf_sources)
            ):
                self._source_list["Live TV"] = app

    @util.Throttle(MIN_TIME_BETWEEN_SCANS, MIN_TIME_BETWEEN_FORCED_SCANS)
    async def async_update(self) -> None:
        """Connect."""
        if self._client.is_connected():
            return

        with suppress(*WEBOSTV_EXCEPTIONS, WebOsTvPairError):
            try:
                await self._client.connect()
            except WebOsTvPairError:
                self._entry.async_start_reauth(self.hass)
            else:
                update_client_key(self.hass, self._entry, self._client)

    @property
    def supported_features(self) -> MediaPlayerEntityFeature:
        """Flag media player features that are supported."""
        if self._turn_on:
            return self._supported_features | MediaPlayerEntityFeature.TURN_ON

        return self._supported_features

    @cmd
    async def async_turn_off(self) -> None:
        """Turn off media player."""
        await self._client.power_off()

    async def async_turn_on(self) -> None:
        """Turn on media player."""
        await self._turn_on.async_run(self.hass, self._context)

    @cmd
    async def async_volume_up(self) -> None:
        """Volume up the media player."""
        await self._client.volume_up()

    @cmd
    async def async_volume_down(self) -> None:
        """Volume down media player."""
        await self._client.volume_down()

    @cmd
    async def async_set_volume_level(self, volume: float) -> None:
        """Set volume level, range 0..1."""
        tv_volume = int(round(volume * 100))
        await self._client.set_volume(tv_volume)

    @cmd
    async def async_mute_volume(self, mute: bool) -> None:
        """Send mute command."""
        await self._client.set_mute(mute)

    @cmd
    async def async_select_sound_output(self, sound_output: str) -> None:
        """Select the sound output."""
        await self._client.change_sound_output(sound_output)

    @cmd
    async def async_media_play_pause(self) -> None:
        """Simulate play pause media player."""
        if self._paused:
            await self.async_media_play()
        else:
            await self.async_media_pause()

    @cmd
    async def async_select_source(self, source: str) -> None:
        """Select input source."""
        if (source_dict := self._source_list.get(source)) is None:
            _LOGGER.warning("Source %s not found for %s", source, self.name)
            return
        if source_dict.get("title"):
            await self._client.launch_app(source_dict["id"])
        elif source_dict.get("label"):
            await self._client.set_input(source_dict["id"])

    @cmd
    async def async_play_media(
        self, media_type: MediaType | str, media_id: str, **kwargs: Any
    ) -> None:
        """Play a piece of media."""
        _LOGGER.debug("Call play media type <%s>, Id <%s>", media_type, media_id)

        if media_type == MediaType.CHANNEL:
            _LOGGER.debug("Searching channel")
            partial_match_channel_id = None
            perfect_match_channel_id = None

            for channel in self._client.channels:
                if media_id == channel["channelNumber"]:
                    perfect_match_channel_id = channel["channelId"]
                    continue

                if media_id.lower() == channel["channelName"].lower():
                    perfect_match_channel_id = channel["channelId"]
                    continue

                if media_id.lower() in channel["channelName"].lower():
                    partial_match_channel_id = channel["channelId"]

            if perfect_match_channel_id is not None:
                _LOGGER.info(
                    "Switching to channel <%s> with perfect match",
                    perfect_match_channel_id,
                )
                await self._client.set_channel(perfect_match_channel_id)
            elif partial_match_channel_id is not None:
                _LOGGER.info(
                    "Switching to channel <%s> with partial match",
                    partial_match_channel_id,
                )
                await self._client.set_channel(partial_match_channel_id)

    @cmd
    async def async_media_play(self) -> None:
        """Send play command."""
        self._paused = False
        await self._client.play()

    @cmd
    async def async_media_pause(self) -> None:
        """Send media pause command to media player."""
        self._paused = True
        await self._client.pause()

    @cmd
    async def async_media_stop(self) -> None:
        """Send stop command to media player."""
        await self._client.stop()

    @cmd
    async def async_media_next_track(self) -> None:
        """Send next track command."""
        if self._client.current_app_id == LIVE_TV_APP_ID:
            await self._client.channel_up()
        else:
            await self._client.fast_forward()

    @cmd
    async def async_media_previous_track(self) -> None:
        """Send the previous track command."""
        if self._client.current_app_id == LIVE_TV_APP_ID:
            await self._client.channel_down()
        else:
            await self._client.rewind()

    @cmd
    async def async_button(self, button: str) -> None:
        """Send a button press."""
        await self._client.button(button)

    @cmd
    async def async_command(self, command: str, **kwargs: Any) -> None:
        """Send a command."""
        await self._client.request(command, payload=kwargs.get(ATTR_PAYLOAD))

    async def _async_fetch_image(self, url: str) -> tuple[bytes | None, str | None]:
        """Retrieve an image.

        webOS uses self-signed certificates, thus we need to use an empty
        SSLContext to bypass validation errors if url starts with https.
        """
        content = None
        ssl_context = None
        if url.startswith("https"):
            ssl_context = SSLContext()

        websession = async_get_clientsession(self.hass)
        with suppress(asyncio.TimeoutError), async_timeout.timeout(10):
            response = await websession.get(url, ssl=ssl_context)
            if response.status == HTTPStatus.OK:
                content = await response.read()

        if content is None:
            _LOGGER.warning("Error retrieving proxied image from %s", url)

        return content, None
