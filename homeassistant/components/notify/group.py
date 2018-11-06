"""
Group platform for notify component.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/notify.group/
"""
import asyncio
from collections.abc import Mapping
from copy import deepcopy
import logging
import voluptuous as vol

from build.lib.homeassistant.helpers.service import CONF_SERVICE_TEMPLATE
from homeassistant.const import ATTR_SERVICE
from homeassistant.components.notify import (
    DOMAIN, ATTR_MESSAGE, ATTR_DATA, PLATFORM_SCHEMA, BaseNotificationService)
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

CONF_SERVICES = 'services'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_SERVICES): vol.All(cv.ensure_list, [{
        vol.Optional(ATTR_SERVICE): cv.slug,
        vol.Optional(CONF_SERVICE_TEMPLATE): cv.template,
        vol.Optional(ATTR_DATA): dict,
    }])
})


def update(input_dict, update_source):
    """Deep update a dictionary.

    Async friendly.
    """
    for key, val in update_source.items():
        if isinstance(val, Mapping):
            recurse = update(input_dict.get(key, {}), val)
            input_dict[key] = recurse
        else:
            input_dict[key] = update_source[key]
    return input_dict


async def async_get_service(hass, config, discovery_info=None):
    """Get the Group notification service."""
    return GroupNotifyPlatform(hass, config.get(CONF_SERVICES))


class GroupNotifyPlatform(BaseNotificationService):
    """Implement the notification service for the group notify platform."""

    def __init__(self, hass, entities):
        """Initialize the service."""
        self.hass = hass
        self.entities = entities

    async def async_send_message(self, message="", **kwargs):
        """Send message to all entities in the group."""
        payload = {ATTR_MESSAGE: message}
        payload.update({key: val for key, val in kwargs.items() if val})

        tasks = []
        for entity in self.entities:
            service_template = entity.get(CONF_SERVICE_TEMPLATE)
            if service_template is not None:
                service = service_template.render()
            else:
                service = entity.get(ATTR_DATA)

            sending_payload = deepcopy(payload.copy())
            if service is not None:
                update(sending_payload, service)
            tasks.append(self.hass.services.async_call(
                DOMAIN, service, sending_payload))

        if tasks:
            await asyncio.wait(tasks, loop=self.hass.loop)
