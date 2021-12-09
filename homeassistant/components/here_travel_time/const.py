"""Constants for the HERE Travel Time integration."""
from __future__ import annotations

from typing import TypedDict

from homeassistant.const import (
    CONF_UNIT_SYSTEM,
    CONF_UNIT_SYSTEM_IMPERIAL,
    CONF_UNIT_SYSTEM_METRIC,
)


class HERERoutingData(TypedDict):
    """Routing information calculated from a herepy.RoutingResponse."""

    attribution: str | None
    base_time: float
    traffic_time: float
    distance: float
    route: str
    origin: str
    destination: str
    origin_name: str
    destination_name: str


DOMAIN = "here_travel_time"
DEFAULT_SCAN_INTERVAL = 300

CONF_DESTINATION = "destination"
CONF_ORIGIN = "origin"
CONF_TRAFFIC_MODE = "traffic_mode"
CONF_ROUTE_MODE = "route_mode"
CONF_ARRIVAL = "arrival"
CONF_DEPARTURE = "departure"
CONF_ARRIVAL_TIME = "arrival_time"
CONF_DEPARTURE_TIME = "departure_time"
CONF_TIME_TYPE = "time_type"
CONF_TIME = "time"

ARRIVAL_TIME = "Arrival Time"
DEPARTURE_TIME = "Departure Time"
TIME_TYPES = [ARRIVAL_TIME, DEPARTURE_TIME]

DEFAULT_NAME = "HERE Travel Time"

TRACKABLE_DOMAINS = ["device_tracker", "sensor", "zone", "person"]

TRAVEL_MODE_BICYCLE = "bicycle"
TRAVEL_MODE_CAR = "car"
TRAVEL_MODE_PEDESTRIAN = "pedestrian"
TRAVEL_MODE_PUBLIC = "publicTransport"
TRAVEL_MODE_PUBLIC_TIME_TABLE = "publicTransportTimeTable"
TRAVEL_MODE_TRUCK = "truck"
TRAVEL_MODES = [
    TRAVEL_MODE_BICYCLE,
    TRAVEL_MODE_CAR,
    TRAVEL_MODE_PEDESTRIAN,
    TRAVEL_MODE_PUBLIC,
    TRAVEL_MODE_PUBLIC_TIME_TABLE,
    TRAVEL_MODE_TRUCK,
]

TRAVEL_MODES_PUBLIC = [TRAVEL_MODE_PUBLIC, TRAVEL_MODE_PUBLIC_TIME_TABLE]
TRAVEL_MODES_VEHICLE = [TRAVEL_MODE_CAR, TRAVEL_MODE_TRUCK]

TRAFFIC_MODE_ENABLED = "traffic_enabled"
TRAFFIC_MODE_DISABLED = "traffic_disabled"
TRAFFIC_MODES = [TRAFFIC_MODE_ENABLED, TRAFFIC_MODE_DISABLED]

ROUTE_MODE_FASTEST = "fastest"
ROUTE_MODE_SHORTEST = "shortest"
ROUTE_MODES = [ROUTE_MODE_FASTEST, ROUTE_MODE_SHORTEST]

ICON_BICYCLE = "mdi:bike"
ICON_CAR = "mdi:car"
ICON_PEDESTRIAN = "mdi:walk"
ICON_PUBLIC = "mdi:bus"
ICON_TRUCK = "mdi:truck"

UNITS = [CONF_UNIT_SYSTEM_METRIC, CONF_UNIT_SYSTEM_IMPERIAL]

ATTR_DURATION = "duration"
ATTR_DISTANCE = "distance"
ATTR_ROUTE = "route"
ATTR_ORIGIN = "origin"
ATTR_DESTINATION = "destination"

ATTR_UNIT_SYSTEM = CONF_UNIT_SYSTEM
ATTR_TRAFFIC_MODE = CONF_TRAFFIC_MODE

ATTR_DURATION_IN_TRAFFIC = "duration_in_traffic"
ATTR_ORIGIN_NAME = "origin_name"
ATTR_DESTINATION_NAME = "destination_name"

NO_ROUTE_ERROR_MESSAGE = "HERE could not find a route based on the input"
