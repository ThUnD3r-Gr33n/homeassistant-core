"""Support for MQTT notify."""
from __future__ import annotations

import functools
import logging
from typing import Any

import voluptuous as vol

from homeassistant.components import notify
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)
from homeassistant.helpers.reload import async_setup_reload_service
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.util import slugify

from . import PLATFORMS, MqttCommandTemplate
from .. import mqtt
from .const import (
    ATTR_DISCOVERY_HASH,
    ATTR_DISCOVERY_PAYLOAD,
    CONF_COMMAND_TOPIC,
    CONF_ENCODING,
    CONF_QOS,
    CONF_RETAIN,
    DOMAIN,
)
from .discovery import MQTT_DISCOVERY_DONE, MQTT_DISCOVERY_UPDATED, clear_discovery_hash
from .mixins import async_setup_entry_helper

CONF_COMMAND_TEMPLATE = "command_template"
CONF_PAYLOAD_TITLE = "Notification"
CONF_TITLE = "title"

MQTT_EVENT_RELOADED = "event_{}_reloaded"

MQTT_NOTIFY_TARGET_CONFIG = "mqtt_notify_target_config"

PLATFORM_SCHEMA = mqtt.MQTT_BASE_PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_COMMAND_TOPIC): mqtt.valid_publish_topic,
        vol.Optional(CONF_COMMAND_TEMPLATE): cv.template,
        vol.Optional(CONF_NAME): cv.string,
        vol.Optional(CONF_TITLE, default=notify.ATTR_TITLE_DEFAULT): cv.string,
        vol.Optional(CONF_RETAIN, default=mqtt.DEFAULT_RETAIN): cv.boolean,
    }
)

DISCOVERY_SCHEMA = PLATFORM_SCHEMA.extend({}, extra=vol.REMOVE_EXTRA)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> None:
    """Set up MQTT climate device dynamically through MQTT discovery."""
    await async_setup_reload_service(hass, DOMAIN, PLATFORMS)
    setup = functools.partial(_async_setup_notify, hass, config_entry=config_entry)
    await async_setup_entry_helper(hass, notify.DOMAIN, setup, DISCOVERY_SCHEMA)


async def _async_setup_notify(
    hass,
    legacy_config: ConfigType,
    config_entry: ConfigEntry,
    discovery_data: dict[str, Any],
):
    """Set up the MQTT notify service with auto discovery."""
    config = DISCOVERY_SCHEMA(discovery_data[ATTR_DISCOVERY_PAYLOAD])
    discovery_hash = discovery_data[ATTR_DISCOVERY_HASH]
    service = MqttNotificationService(
        hass,
        config[CONF_COMMAND_TOPIC],
        MqttCommandTemplate(config.get(CONF_COMMAND_TEMPLATE), hass=hass),
        config[CONF_ENCODING],
        config.get(CONF_NAME),
        config[CONF_QOS],
        config[CONF_RETAIN],
        config[CONF_TITLE],
        discovery_hash=discovery_hash,
    )
    await service.async_setup(
        hass, slugify(config.get(CONF_NAME, config[CONF_COMMAND_TOPIC])), ""
    )
    await service.async_register_services()


async def async_get_service(
    hass: HomeAssistant,
    config: ConfigType,
    discovery_info: DiscoveryInfoType | None = None,
) -> MqttNotificationService | None:
    """Prepare the MQTT notification service through configuration.yaml."""
    await async_setup_reload_service(hass, DOMAIN, PLATFORMS)
    return MqttNotificationService(
        hass,
        config[CONF_COMMAND_TOPIC],
        MqttCommandTemplate(config.get(CONF_COMMAND_TEMPLATE), hass=hass),
        config[CONF_ENCODING],
        config.get(CONF_NAME),
        config[CONF_QOS],
        config[CONF_RETAIN],
        config[CONF_TITLE],
    )


class MqttNotificationServiceUpdater:
    """Add support for auto discovery updates."""

    def __init__(self, hass: HomeAssistant, service: MqttNotificationService) -> None:
        """Initialize the update service."""

        async def async_discovery_update(
            discovery_payload: DiscoveryInfoType | None,
        ) -> None:
            """Handle discovery update."""
            async_dispatcher_send(
                hass, MQTT_DISCOVERY_DONE.format(service.discovery_hash), None
            )
            if not discovery_payload:
                # unregister notify service through auto discovery
                clear_discovery_hash(hass, service.discovery_hash)
                self._remove_discovery()
                await service.async_unregister_services()
                _LOGGER.info(
                    "Notify service %s has been removed",
                    service.discovery_hash,
                )
                del self._service
                return

            # update notify service through auto discovery
            await service.async_update_service(discovery_payload)
            _LOGGER.debug(
                "Notify service %s has been updated",
                service.discovery_hash,
            )

        self._service = service
        self._remove_discovery = async_dispatcher_connect(
            hass,
            MQTT_DISCOVERY_UPDATED.format(service.discovery_hash),
            async_discovery_update,
        )
        async_dispatcher_send(
            hass, MQTT_DISCOVERY_DONE.format(service.discovery_hash), None
        )
        _LOGGER.info(
            "Notify service %s has been initialized",
            service.discovery_hash,
        )


class MqttNotificationService(notify.BaseNotificationService):
    """Implement the notification service for MQTT."""

    def __init__(
        self,
        hass: HomeAssistant,
        command_topic: str,
        command_template: MqttCommandTemplate,
        encoding: str,
        name: str | None,
        qos: int,
        retain: bool,
        title: str | None,
        discovery_hash: tuple | None = None,
    ) -> None:
        """Initialize the service."""
        self.hass = hass
        self._command_topic = command_topic
        self._command_template = command_template
        self._encoding = encoding
        self._name = name
        self._qos = qos
        self._retain = retain
        self._title = title
        self._discovery_hash = discovery_hash
        self._service_name = slugify(name or command_topic)

        self._updater = (
            MqttNotificationServiceUpdater(hass, self) if discovery_hash else None
        )

    @property
    def discovery_hash(self) -> tuple | None:
        """Return the discovery hash."""
        return self._discovery_hash

    async def async_update_service(
        self,
        discovery_payload: DiscoveryInfoType,
    ) -> None:
        """Update the notify service through auto discovery."""
        config = DISCOVERY_SCHEMA(discovery_payload)
        self._command_topic = config[CONF_COMMAND_TOPIC]
        if config.get(CONF_COMMAND_TEMPLATE) is not None:
            template = config[CONF_COMMAND_TEMPLATE]
            template.hass = self.hass
            self._command_template._attr_command_template = template
        else:
            self._command_template._attr_command_template = None
        self._encoding = config[CONF_ENCODING]
        self._name = config.get(CONF_NAME)
        self._qos = config[CONF_QOS]
        self._retain = config[CONF_RETAIN]
        self._title = config[CONF_TITLE]
        new_service_name = slugify(config.get(CONF_NAME, config[CONF_COMMAND_TOPIC]))
        if new_service_name != self._service_name:
            await self.async_unregister_services()
            self._service_name = new_service_name
            await self.async_register_services()

    async def async_send_message(self, message: str = "", **kwargs):
        """Build and send a MQTT message."""
        payload = self._command_template.async_render(
            message,
            variables={
                "data": kwargs.get(notify.ATTR_DATA),
                "message": message,
                "name": self._name,
                "service": self._service_name,
                "title": kwargs.get(notify.ATTR_TITLE, self._title),
            },
        )
        await mqtt.async_publish(
            self.hass,
            self._command_topic,
            payload,
            self._qos,
            self._retain,
            self._encoding,
        )
