"""Huawei LTE router platform for notify component.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/notify.huawei_lte/
"""

import logging

import voluptuous as vol
import attr

from homeassistant.components.notify import (
    BaseNotificationService, ATTR_TARGET, PLATFORM_SCHEMA)
from homeassistant.const import CONF_URL
import homeassistant.helpers.config_validation as cv

from ..huawei_lte import DATA_KEY


DEPENDENCIES = ['huawei_lte']

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_URL): cv.url,
    vol.Required(ATTR_TARGET): vol.All(cv.ensure_list, [cv.string]),
})


async def async_get_service(hass, config, discovery_info=None):
    """Get the notification service."""
    return HuaweiLteSmsNotificationService(hass, config)


@attr.s
class HuaweiLteSmsNotificationService(BaseNotificationService):
    """Huawei LTE router SMS notification service."""

    hass = attr.ib()
    config = attr.ib()

    def send_message(self, message="", **kwargs):
        """Send message to target numbers."""
        from huawei_lte_api.exceptions import ResponseErrorException

        targets = kwargs.get(ATTR_TARGET, self.config.get(ATTR_TARGET))
        if not targets or not message:
            return

        data = self.hass.data[DATA_KEY].get_data(self.config)
        if not data:
            _LOGGER.error("Router not available")
            return

        try:
            resp = data.client.sms.send_sms(
                phone_numbers=targets, message=message)
            _LOGGER.debug("Sent to %s: %s", targets, resp)
        except ResponseErrorException as ex:
            _LOGGER.error("Could not send to %s: %s", targets, ex)
