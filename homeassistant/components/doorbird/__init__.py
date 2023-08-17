"""Support for DoorBird devices."""
from __future__ import annotations

from http import HTTPStatus
import logging
from typing import Any

from aiohttp import web
from doorbirdpy import DoorBird
import requests
import voluptuous as vol

from homeassistant.components import persistent_notification
from homeassistant.components.http import HomeAssistantView
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_TOKEN,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import (
    API_URL,
    CONF_EVENTS,
    DOMAIN,
    DOOR_STATION,
    DOOR_STATION_EVENT_ENTITY_IDS,
    DOOR_STATION_INFO,
    PLATFORMS,
    UNDO_UPDATE_LISTENER,
)
from .device import ConfiguredDoorBird
from .util import get_doorstation_by_token

_LOGGER = logging.getLogger(__name__)

CONF_CUSTOM_URL = "hass_url_override"

RESET_DEVICE_FAVORITES = "doorbird_reset_favorites"

DEVICE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_TOKEN): cv.string,
        vol.Optional(CONF_EVENTS, default=[]): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional(CONF_CUSTOM_URL): cv.string,
        vol.Optional(CONF_NAME): cv.string,
    }
)

CONFIG_SCHEMA = cv.removed(DOMAIN, raise_if_present=False)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the DoorBird component."""
    hass.data.setdefault(DOMAIN, {})

    # Provide an endpoint for the doorstations to call to trigger events
    hass.http.register_view(DoorBirdRequestView)

    def _reset_device_favorites_handler(event):
        """Handle clearing favorites on device."""
        if (token := event.data.get("token")) is None:
            return

        doorstation = get_doorstation_by_token(hass, token)

        if doorstation is None:
            _LOGGER.error("Device not found for provided token")
            return

        # Clear webhooks
        favorites = doorstation.device.favorites()

        for favorite_type in favorites:
            for favorite_id in favorites[favorite_type]:
                doorstation.device.delete_favorite(favorite_type, favorite_id)

    hass.bus.async_listen(RESET_DEVICE_FAVORITES, _reset_device_favorites_handler)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up DoorBird from a config entry."""

    _async_import_options_from_data_if_missing(hass, entry)

    doorstation_config = entry.data
    doorstation_options = entry.options
    config_entry_id = entry.entry_id

    device_ip = doorstation_config[CONF_HOST]
    username = doorstation_config[CONF_USERNAME]
    password = doorstation_config[CONF_PASSWORD]

    device = DoorBird(device_ip, username, password)
    try:
        status, info = await hass.async_add_executor_job(_init_doorbird_device, device)
    except requests.exceptions.HTTPError as err:
        if err.response.status_code == HTTPStatus.UNAUTHORIZED:
            _LOGGER.error(
                "Authorization rejected by DoorBird for %s@%s", username, device_ip
            )
            return False
        raise ConfigEntryNotReady from err
    except OSError as oserr:
        _LOGGER.error("Failed to setup doorbird at %s: %s", device_ip, oserr)
        raise ConfigEntryNotReady from oserr

    if not status[0]:
        _LOGGER.error(
            "Could not connect to DoorBird as %s@%s: Error %s",
            username,
            device_ip,
            str(status[1]),
        )
        raise ConfigEntryNotReady

    token: str = doorstation_config.get(CONF_TOKEN, config_entry_id)
    custom_url: str | None = doorstation_config.get(CONF_CUSTOM_URL)
    name: str | None = doorstation_config.get(CONF_NAME)
    events = doorstation_options.get(CONF_EVENTS, [])
    doorstation = ConfiguredDoorBird(device, name, custom_url, token)
    doorstation.update_events(events)
    # Subscribe to doorbell or motion events
    if not await _async_register_events(hass, doorstation):
        raise ConfigEntryNotReady

    undo_listener = entry.add_update_listener(_update_listener)

    hass.data[DOMAIN][config_entry_id] = {
        DOOR_STATION: doorstation,
        DOOR_STATION_INFO: info,
        UNDO_UPDATE_LISTENER: undo_listener,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


def _init_doorbird_device(device: DoorBird) -> tuple[tuple[bool, int], dict[str, Any]]:
    return device.ready(), device.info()


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    hass.data[DOMAIN][entry.entry_id][UNDO_UPDATE_LISTENER]()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def _async_register_events(
    hass: HomeAssistant, doorstation: ConfiguredDoorBird
) -> bool:
    try:
        await hass.async_add_executor_job(doorstation.register_events, hass)
    except requests.exceptions.HTTPError:
        persistent_notification.async_create(
            hass,
            (
                "Doorbird configuration failed.  Please verify that API "
                "Operator permission is enabled for the Doorbird user. "
                "A restart will be required once permissions have been "
                "verified."
            ),
            title="Doorbird Configuration Failure",
            notification_id="doorbird_schedule_error",
        )
        return False

    return True


async def _update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    config_entry_id = entry.entry_id
    doorstation = hass.data[DOMAIN][config_entry_id][DOOR_STATION]
    doorstation.update_events(entry.options[CONF_EVENTS])
    # Subscribe to doorbell or motion events
    await _async_register_events(hass, doorstation)


@callback
def _async_import_options_from_data_if_missing(hass: HomeAssistant, entry: ConfigEntry):
    options = dict(entry.options)
    modified = False
    for importable_option in (CONF_EVENTS,):
        if importable_option not in entry.options and importable_option in entry.data:
            options[importable_option] = entry.data[importable_option]
            modified = True

    if modified:
        hass.config_entries.async_update_entry(entry, options=options)


class DoorBirdRequestView(HomeAssistantView):
    """Provide a page for the device to call."""

    requires_auth = False
    url = API_URL
    name = API_URL[1:].replace("/", ":")
    extra_urls = [API_URL + "/{event}"]

    async def get(self, request, event):
        """Respond to requests from the device."""
        hass = request.app["hass"]

        token = request.query.get("token")

        device = get_doorstation_by_token(hass, token)

        if device is None:
            return web.Response(
                status=HTTPStatus.UNAUTHORIZED, text="Invalid token provided."
            )

        if device:
            event_data = device.get_event_data()
        else:
            event_data = {}

        if event == "clear":
            hass.bus.async_fire(RESET_DEVICE_FAVORITES, {"token": token})

            message = f"HTTP Favorites cleared for {device.slug}"
            return web.Response(text=message)

        event_data[ATTR_ENTITY_ID] = hass.data[DOMAIN][
            DOOR_STATION_EVENT_ENTITY_IDS
        ].get(event)

        hass.bus.async_fire(f"{DOMAIN}_{event}", event_data)

        return web.Response(text="OK")
