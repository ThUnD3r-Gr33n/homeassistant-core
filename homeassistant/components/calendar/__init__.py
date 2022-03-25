"""Support for Google Calendar event device sensors."""
from __future__ import annotations

import datetime
from http import HTTPStatus
import logging
import re
from typing import Any, cast, final

from aiohttp import web

from homeassistant.components import frontend, http
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.config_validation import (  # noqa: F401
    PLATFORM_SCHEMA,
    PLATFORM_SCHEMA_BASE,
    time_period_str,
)
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.template import DATE_STR_FORMAT
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt

# mypy: allow-untyped-defs, no-check-untyped-defs

_LOGGER = logging.getLogger(__name__)

DOMAIN = "calendar"
ENTITY_ID_FORMAT = DOMAIN + ".{}"
SCAN_INTERVAL = datetime.timedelta(seconds=60)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Track states and offer events for calendars."""
    component = hass.data[DOMAIN] = EntityComponent(
        _LOGGER, DOMAIN, hass, SCAN_INTERVAL
    )

    hass.http.register_view(CalendarListView(component))
    hass.http.register_view(CalendarEventView(component))

    frontend.async_register_built_in_panel(
        hass, "calendar", "calendar", "hass:calendar"
    )

    await component.async_setup(config)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a config entry."""
    component: EntityComponent = hass.data[DOMAIN]
    return await component.async_setup_entry(entry)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    component: EntityComponent = hass.data[DOMAIN]
    return await component.async_unload_entry(entry)


def get_date(date: dict[str, Any]) -> datetime.datetime:
    """Get the dateTime from date or dateTime as a local."""
    if "date" in date:
        parsed_date = dt.parse_date(date["date"])
        assert parsed_date
        return dt.start_of_local_day(
            datetime.datetime.combine(parsed_date, datetime.time.min)
        )
    parsed_datetime = dt.parse_datetime(date["dateTime"])
    assert parsed_datetime
    return dt.as_local(parsed_datetime)


def normalize_event(event: dict[str, Any]) -> dict[str, Any]:
    """Normalize a calendar event."""
    normalized_event: dict[str, Any] = {}

    start = event.get("start")
    end = event.get("end")
    start = get_date(start) if start is not None else None
    end = get_date(end) if end is not None else None
    normalized_event["dt_start"] = start
    normalized_event["dt_end"] = end

    start = start.strftime(DATE_STR_FORMAT) if start is not None else None
    end = end.strftime(DATE_STR_FORMAT) if end is not None else None
    normalized_event["start"] = start
    normalized_event["end"] = end

    # cleanup the string so we don't have a bunch of double+ spaces
    summary = event.get("summary", "")
    normalized_event["message"] = re.sub("  +", "", summary).strip()
    normalized_event["location"] = event.get("location", "")
    normalized_event["description"] = event.get("description", "")
    normalized_event["all_day"] = "date" in event["start"]

    return normalized_event


def calculate_offset(event: dict[str, Any], offset: str) -> dict[str, Any]:
    """Calculate event offset.

    Return the updated event with the offset_time included.
    """
    summary = event.get("summary", "")
    # check if we have an offset tag in the message
    # time is HH:MM or MM
    reg = f"{offset}([+-]?[0-9]{{0,2}}(:[0-9]{{0,2}})?)"
    search = re.search(reg, summary)
    if search and search.group(1):
        time = search.group(1)
        if ":" not in time:
            if time[0] == "+" or time[0] == "-":
                time = f"{time[0]}0:{time[1:]}"
            else:
                time = f"0:{time}"

        offset_time = time_period_str(time)
        summary = (summary[: search.start()] + summary[search.end() :]).strip()
        event["summary"] = summary
    else:
        offset_time = datetime.timedelta()  # default it

    event["offset_time"] = offset_time
    return event


def is_offset_reached(event: dict[str, Any]) -> bool:
    """Have we reached the offset time specified in the event title."""
    start = get_date(event["start"])
    offset_time: datetime.timedelta = event["offset_time"]
    if start is None or offset_time == datetime.timedelta():
        return False

    return start + offset_time <= dt.now(start.tzinfo)


class CalendarEventDevice(Entity):
    """Base class for calendar event entities."""

    @property
    def event(self) -> dict[str, Any] | None:
        """Return the next upcoming event."""
        raise NotImplementedError()

    @final
    @property
    def state_attributes(self) -> dict[str, Any] | None:
        """Return the entity state attributes."""
        if (event := self.event) is None:
            return None

        event = normalize_event(event)
        return {
            "message": event["message"],
            "all_day": event["all_day"],
            "start_time": event["start"],
            "end_time": event["end"],
            "location": event["location"],
            "description": event["description"],
        }

    @property
    def state(self) -> str:
        """Return the state of the calendar event."""
        if (event := self.event) is None:
            return STATE_OFF

        event = normalize_event(event)
        start = event["dt_start"]
        end = event["dt_end"]

        if start is None or end is None:
            return STATE_OFF

        now = dt.now()

        if start <= now < end:
            return STATE_ON

        return STATE_OFF

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[dict[str, Any]]:
        """Return calendar events within a datetime range."""
        raise NotImplementedError()


class CalendarEventView(http.HomeAssistantView):
    """View to retrieve calendar content."""

    url = "/api/calendars/{entity_id}"
    name = "api:calendars:calendar"

    def __init__(self, component: EntityComponent) -> None:
        """Initialize calendar view."""
        self.component = component

    async def get(self, request: web.Request, entity_id: str) -> web.Response:
        """Return calendar events."""
        entity = self.component.get_entity(entity_id)
        start = request.query.get("start")
        end = request.query.get("end")
        if start is None or end is None or entity is None:
            return web.Response(status=HTTPStatus.BAD_REQUEST)
        assert isinstance(entity, CalendarEventDevice)
        try:
            start_date = dt.parse_datetime(start)
            end_date = dt.parse_datetime(end)
        except (ValueError, AttributeError):
            return web.Response(status=HTTPStatus.BAD_REQUEST)
        assert start_date
        assert end_date
        event_list = await entity.async_get_events(
            request.app["hass"], start_date, end_date
        )
        return self.json(event_list)


class CalendarListView(http.HomeAssistantView):
    """View to retrieve calendar list."""

    url = "/api/calendars"
    name = "api:calendars"

    def __init__(self, component: EntityComponent) -> None:
        """Initialize calendar view."""
        self.component = component

    async def get(self, request: web.Request) -> web.Response:
        """Retrieve calendar list."""
        hass = request.app["hass"]
        calendar_list: list[dict[str, str]] = []

        for entity in self.component.entities:
            state = hass.states.get(entity.entity_id)
            calendar_list.append({"name": state.name, "entity_id": entity.entity_id})

        return self.json(sorted(calendar_list, key=lambda x: cast(str, x["name"])))
