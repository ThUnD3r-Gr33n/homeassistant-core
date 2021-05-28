"""The Garmin Connect integration."""
from datetime import date
import logging

from garminconnect_aio import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import Throttle

from .const import DEFAULT_UPDATE_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Garmin Connect from a config entry."""

    websession = async_get_clientsession(hass)
    username: str = entry.data[CONF_USERNAME]
    password: str = entry.data[CONF_PASSWORD]

    garmin_client = Garmin(websession, username, password)

    try:
        await garmin_client.login()
    except (
        GarminConnectAuthenticationError,
        GarminConnectTooManyRequestsError,
    ) as err:
        _LOGGER.error("Error occurred during Garmin Connect login request: %s", err)
        return False
    except (GarminConnectConnectionError) as err:
        _LOGGER.error(
            "Connection error occurred during Garmin Connect login request: %s", err
        )
        raise ConfigEntryNotReady from err
    except Exception:  # pylint: disable=broad-except
        _LOGGER.exception("Unknown error occurred during Garmin Connect login request")
        return False

    garmin_data = GarminConnectData(hass, garmin_client)
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = garmin_data

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


class GarminConnectData:
    """Define an object to hold sensor data."""

    def __init__(self, hass, client):
        """Initialize."""
        self.hass = hass
        self.client = client
        self.data = None

    async def _get_combined_alarms_of_all_devices(self):
        """Combine the list of active alarms from all garmin devices."""
        alarms = []
        devices = await self.client.get_devices()
        for device in devices:
            device_settings = await self.client.get_device_settings(device["deviceId"])
            alarms += device_settings["alarms"]
        return alarms

    @Throttle(DEFAULT_UPDATE_INTERVAL)
    async def async_update(self):
        """Update data via API wrapper."""
        today = date.today()
        summary = None
        body = None

        try:
            summary = await self.client.get_user_summary(today.isoformat())
            body = await self.client.get_body_composition(today.isoformat())

            self.data = {
                **summary,
                **body["totalAverage"],
            }
            self.data["nextAlarm"] = await self._get_combined_alarms_of_all_devices()
        except (
            GarminConnectAuthenticationError,
            GarminConnectTooManyRequestsError,
            GarminConnectConnectionError,
        ) as err:
            _LOGGER.error(
                "Error occurred during Garmin Connect update requests: %s", err
            )
            return
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception(
                "Unknown error occurred during Garmin Connect update requests"
            )
            return
