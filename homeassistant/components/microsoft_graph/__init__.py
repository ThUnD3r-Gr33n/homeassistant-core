"""The Microsoft Graph integration."""
import asyncio
from dataclasses import dataclass
from typing import Dict, Optional
from datetime import timedelta
import logging

import voluptuous as vol
from hagraph.api.client import GraphApiClient
from hagraph.api.provider.presence.models import PresenceResponse

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_CLIENT_ID, CONF_CLIENT_SECRET
from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    aiohttp_client,
    config_entry_oauth2_flow,
    config_validation as cv,
)
from homeassistant.helpers.typing import HomeAssistantType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from . import api, config_flow
from .const import DOMAIN, OAUTH2_AUTHORIZE, OAUTH2_TOKEN

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_CLIENT_ID): cv.string,
                vol.Required(CONF_CLIENT_SECRET): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

PLATFORMS = ["sensor"]


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Microsoft Graph component."""
    hass.data[DOMAIN] = {}

    if DOMAIN not in config:
        return True

    config_flow.OAuth2FlowHandler.async_register_implementation(
        hass,
        config_entry_oauth2_flow.LocalOAuth2Implementation(
            hass,
            DOMAIN,
            config[DOMAIN][CONF_CLIENT_ID],
            config[DOMAIN][CONF_CLIENT_SECRET],
            OAUTH2_AUTHORIZE,
            OAUTH2_TOKEN,
        ),
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Microsoft Graph from a config entry."""
    implementation = (
        await config_entry_oauth2_flow.async_get_config_entry_implementation(
            hass, entry
        )
    )

    session = config_entry_oauth2_flow.OAuth2Session(hass, entry, implementation)
    auth = api.AsyncConfigEntryAuth(
        aiohttp_client.async_get_clientsession(hass), session
    )

    client = GraphApiClient(auth)

    coordinator = GraphUpdateCoordinator(hass, client)
    await coordinator.async_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "client": GraphApiClient(auth),
        "coordinator": coordinator,
    }

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN][entry.entry_id]["sensor_unsub"]()
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

@dataclass
class PresenceData:
    """Microsoft Graph user presence data."""

    uuid: str
    availability: str
    activity: str

@dataclass
class GraphData:
    """Graph dataclass for update coordinator."""

    presence: Dict[str, PresenceData]


class GraphUpdateCoordinator(DataUpdateCoordinator):
    """Store Graph Status."""

    def __init__(
        self,
        hass: HomeAssistantType,
        client: GraphApiClient,
    ) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=5),
        )
        self.data: GraphData = GraphData({})
        self.client: GraphApiClient = client

    async def _async_update_data(self) -> GraphData:
        """Fetch the latest data."""

        # Update user presence
        presence_data = {}
        me = await self.client.presence.get_presence()
        presence_data[me.id] = _build_presence_data(me)

        _LOGGER.debug(
            "Microsoft Graph presence_data: %s",
            presence_data
        )

        return GraphData(presence_data)


def _build_presence_data(person: PresenceResponse) -> PresenceData:
    """Build presence data from a person."""

    return PresenceData(
        uuid=person.id,
        availability=person.availability,
        activity=person.activity,
    )