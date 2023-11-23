"""Support for geolocation data from Krisinformation."""
from datetime import timedelta

from homeassistant.components.geo_location import GeolocationEvent
from homeassistant.const import UnitOfLength
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import track_time_interval
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import CONF_COUNTY
from .crisis_alerter import CrisisAlerter
from .sensor import _LOGGER

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=120)

SOURCE = "krisinformation"


class KrisInformationGeolocationEvent(GeolocationEvent):
    """Represents a demo geolocation event."""

    _attr_should_poll = False
    _attr_source = SOURCE
    _attr_icon = "mdi:public"

    def __init__(
        self,
        name: str,
        latitude: float,
        longitude: float,
        unit_of_measurement: str,
    ) -> None:
        """Initialize entity with data provided."""
        self._attr_name = name
        self._latitude = latitude
        self._longitude = longitude
        self._unit_of_measurement = unit_of_measurement

    @property
    def source(self) -> str:
        """Return source value of this external event."""
        return SOURCE

    @property
    def latitude(self) -> float | None:
        """Return latitude value of this external event."""
        return self._latitude

    @property
    def longitude(self) -> float | None:
        """Return longitude value of this external event."""
        return self._longitude

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return self._unit_of_measurement


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Demo geolocations."""
    KrisInformationGeolocationManager(
        hass, add_entities, CrisisAlerter(config.get(CONF_COUNTY))
    )


class KrisInformationGeolocationManager:
    """Device manager for demo geolocation events."""

    def __init__(
        self,
        hass: HomeAssistant,
        add_entities: AddEntitiesCallback,
        crisis_alerter: CrisisAlerter,
    ) -> None:
        """Initialise the demo geolocation event manager."""
        self._hass = hass
        self._add_entities = add_entities
        self._events: list[KrisInformationGeolocationEvent] = []
        self._crisis_alerter = crisis_alerter
        self._update()
        self._init_regular_updates()
        _LOGGER.info("INIT KRISINFO MANAGER")

    def _generate_random_event(
        self, headline: str, latitude: float, longitude: float
    ) -> KrisInformationGeolocationEvent:
        """Generate a random event in vicinity of this HA instance."""
        return KrisInformationGeolocationEvent(
            headline, latitude, longitude, UnitOfLength.KILOMETERS
        )

    def _init_regular_updates(self) -> None:
        """Schedule regular updates based on configured time interval."""
        track_time_interval(
            self._hass,
            lambda now: self._update(),
            MIN_TIME_BETWEEN_UPDATES,
            cancel_on_shutdown=True,
        )

    def _update(self, count: int = 1) -> None:
        """Remove events and add new random events."""
        new_events = []
        self._events.clear()
        events = self._crisis_alerter.vmas(is_test=True)
        for event in events:
            new_event = self._generate_random_event(
                event["Headline"],
                event["Area"][0]["GeometryInformation"]["PoleOfInInaccessibility"][
                    "coordinates"
                ][1],
                event["Area"][0]["GeometryInformation"]["PoleOfInInaccessibility"][
                    "coordinates"
                ][0],
            )
            new_events.append(new_event)
            self._events.append(new_event)
        self._add_entities(new_events)
