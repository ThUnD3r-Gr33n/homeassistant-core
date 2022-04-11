"""The yolink integration."""
from __future__ import annotations

from datetime import timedelta
import logging

import async_timeout
import voluptuous as vol
from yolink_client.const import OAUTH2_AUTHORIZE, OAUTH2_TOKEN
from yolink_client.yolink_client import YoLinkClient
from yolink_client.yolink_exception import YoLinkAPIError
from yolink_client.yolink_mqtt_client import HomeEventMqttSub, MqttClient

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_CLIENT_ID, CONF_CLIENT_SECRET, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    aiohttp_client,
    config_entry_oauth2_flow,
    config_validation as cv,
)
from homeassistant.helpers.typing import ConfigType

from . import api, config_flow
from .const import DOMAIN, HOME_ID, HOME_SUBSCRIPTION

SCAN_INTERVAL = timedelta(minutes=5)

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

PLATFORMS = [Platform.SENSOR]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the yolink component."""
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


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up yolink from a config entry."""
    implementation = (
        await config_entry_oauth2_flow.async_get_config_entry_implementation(
            hass, entry
        )
    )

    session = config_entry_oauth2_flow.OAuth2Session(hass, entry, implementation)
    auth_mgr = api.ConfigEntryAuth(
        hass, aiohttp_client.async_get_clientsession(hass), session
    )
    yolink_http_client = YoLinkClient(auth_mgr)
    yolink_mqtt_client = MqttClient(auth_mgr)

    hass.data[DOMAIN][entry.entry_id] = {
        "client": yolink_http_client,
        "mqttClient": yolink_mqtt_client,
        "devices": [],
    }

    try:
        async with async_timeout.timeout(5):
            home_response = await yolink_http_client.get_general_info()
            if not (home_response.data["id"] is None):
                hass.data[DOMAIN][entry.entry_id][HOME_ID] = home_response.data["id"]
                hass.data[DOMAIN][entry.entry_id][HOME_SUBSCRIPTION] = HomeEventMqttSub(
                    home_response.data["id"]
                )
                yolink_mqtt_client.subHome(
                    hass.data[DOMAIN][entry.entry_id][HOME_SUBSCRIPTION]
                )
        async with async_timeout.timeout(5):
            devices_response = await yolink_http_client.get_auth_devices()
            if not (devices_response.data["devices"] is None):
                hass.data[DOMAIN][entry.entry_id]["devices"] = devices_response.data[
                    "devices"
                ]
        await yolink_mqtt_client.async_connect()

    except YoLinkAPIError as yl_err:
        _LOGGER.warning("Call yolink api failed: %s", yl_err)
        return False

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
