"""The Airly component."""
import asyncio
from datetime import timedelta
import logging
from math import ceil

from aiohttp.client_exceptions import ClientConnectorError
from airly import Airly
from airly.exceptions import AirlyError
import async_timeout

from homeassistant.const import CONF_API_KEY, CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import Config, HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    ATTR_API_ADVICE,
    ATTR_API_CAQI,
    ATTR_API_CAQI_DESCRIPTION,
    ATTR_API_CAQI_LEVEL,
    DOMAIN,
    MAX_REQUESTS_PER_DAY,
    NO_AIRLY_SENSORS,
)

PLATFORMS = ["air_quality", "sensor"]

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: Config) -> bool:
    """Set up configured Airly."""
    return True


async def async_setup_entry(hass, config_entry):
    """Set up Airly as config entry."""
    api_key = config_entry.data[CONF_API_KEY]
    latitude = config_entry.data[CONF_LATITUDE]
    longitude = config_entry.data[CONF_LONGITUDE]

    # For backwards compat, set unique ID
    if config_entry.unique_id is None:
        hass.config_entries.async_update_entry(
            config_entry, unique_id=f"{latitude}-{longitude}"
        )

    websession = async_get_clientsession(hass)

    # We check how many Airly config entries are and calculate interval to not
    # exceed allowed numbers of requests.
    instances = len(hass.config_entries.async_entries(DOMAIN))
    update_interval = timedelta(
        minutes=ceil(24 * 60 / MAX_REQUESTS_PER_DAY) * instances
    )

    coordinator = AirlyDataUpdateCoordinator(
        hass, websession, api_key, latitude, longitude, update_interval
    )
    await coordinator.async_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.entry_id] = coordinator

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(config_entry, component)
        )

    # Change update_interval for another Airly instances
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.entry_id != config_entry.entry_id and hass.data.get(DOMAIN).get(
            entry.entry_id
        ):
            hass.data.get(DOMAIN).get(entry.entry_id).update_interval = update_interval

    return True


async def async_unload_entry(hass, config_entry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(config_entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN].pop(config_entry.entry_id)

    # Change update_interval for another Airly instances
    instances = len(hass.config_entries.async_entries(DOMAIN)) - 1
    update_interval = timedelta(
        minutes=ceil(24 * 60 / MAX_REQUESTS_PER_DAY) * instances
    )
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.entry_id != config_entry.entry_id and hass.data.get(DOMAIN).get(
            entry.entry_id
        ):
            hass.data.get(DOMAIN).get(entry.entry_id).update_interval = update_interval

    return unload_ok


class AirlyDataUpdateCoordinator(DataUpdateCoordinator):
    """Define an object to hold Airly data."""

    def __init__(self, hass, session, api_key, latitude, longitude, update_interval):
        """Initialize."""
        self.latitude = latitude
        self.longitude = longitude
        self.airly = Airly(api_key, session)

        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=update_interval)

    async def _async_update_data(self):
        """Update data via library."""
        data = {}
        try:
            with async_timeout.timeout(20):
                measurements = self.airly.create_measurements_session_point(
                    self.latitude, self.longitude
                )
                await measurements.update()

            values = measurements.current["values"]
            index = measurements.current["indexes"][0]
            standards = measurements.current["standards"]

            if index["description"] == NO_AIRLY_SENSORS:
                raise UpdateFailed("Can't retrieve data: no Airly sensors in this area")
            for value in values:
                data[value["name"]] = value["value"]
            for standard in standards:
                data[f"{standard['pollutant']}_LIMIT"] = standard["limit"]
                data[f"{standard['pollutant']}_PERCENT"] = standard["percent"]
            data[ATTR_API_CAQI] = index["value"]
            data[ATTR_API_CAQI_LEVEL] = index["level"].lower().replace("_", " ")
            data[ATTR_API_CAQI_DESCRIPTION] = index["description"]
            data[ATTR_API_ADVICE] = index["advice"]
        except (ValueError, AirlyError, ClientConnectorError) as error:
            raise UpdateFailed(error)
        return data
