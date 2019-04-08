"""Support for Android push notifications."""
from datetime import datetime, timezone
import logging

import requests

from homeassistant.components import android
from homeassistant.components.notify import (
    ATTR_DATA, ATTR_MESSAGE, ATTR_TARGET, ATTR_TITLE, ATTR_TITLE_DEFAULT,
    BaseNotificationService)
import homeassistant.util.dt as dt_util

_LOGGER = logging.getLogger(__name__)

PUSH_URL = "https://android-push.home-assistant.io/push"

DEPENDENCIES = ["android"]


# pylint: disable=invalid-name
def log_rate_limits(hass, target, resp, level=20):
    """Output rate limit log line at given level."""
    rate_limits = resp["rateLimits"]
    resetsAt = dt_util.parse_datetime(rate_limits["resetsAt"])
    resetsAtTime = resetsAt - datetime.now(timezone.utc)
    rate_limit_msg = ("Android push notification rate limits for %s: "
                      "%d sent, %d allowed, %d errors, "
                      "resets in %s")
    _LOGGER.log(level, rate_limit_msg,
                android.device_name_for_push_id(hass, target),
                rate_limits["successful"],
                rate_limits["maximum"], rate_limits["errors"],
                str(resetsAtTime).split(".")[0])


def get_service(hass, config, discovery_info=None):
    """Get the Android notification service."""
    if "notify.android" not in hass.config.components:
        # Need this to enable requirements checking in the app.
        hass.config.components.add("notify.android")

    if not android.devices_with_push(hass):
        _LOGGER.error("The notify.android platform was loaded but no "
                      "devices exist! Please check the documentation at "
                      "https://home-assistant.io/ecosystem/android/notifications"
                      "/ for more information")
        return None

    return AndroidNotificationService()


class AndroidNotificationService(BaseNotificationService):
    """Implement the notification service for Android."""

    def __init__(self):
        """Initialize the service."""

    @property
    def targets(self):
        """Return a dictionary of registered targets."""
        return android.devices_with_push(self.hass)

    def send_message(self, message="", **kwargs):
        """Send a message to the Lambda APNS gateway."""
        data = {ATTR_MESSAGE: message}

        if kwargs.get(ATTR_TITLE) is not None:
            # Remove default title from notifications.
            if kwargs.get(ATTR_TITLE) != ATTR_TITLE_DEFAULT:
                data[ATTR_TITLE] = kwargs.get(ATTR_TITLE)

        targets = kwargs.get(ATTR_TARGET)

        if not targets:
            targets = android.enabled_push_ids(self.hass)

        if kwargs.get(ATTR_DATA) is not None:
            data[ATTR_DATA] = kwargs.get(ATTR_DATA)

        for target in targets:
            if target not in android.enabled_push_ids(self.hass):
                _LOGGER.error("The target (%s) does not exist in .android.conf",
                              targets)
                return

            data[ATTR_TARGET] = target

            req = requests.post(PUSH_URL, json=data, timeout=10)

            if req.status_code != 201:
                fallback_error = req.json().get("errorMessage",
                                                "Unknown error")
                fallback_message = ("Internal server error, "
                                    "please try again later: "
                                    "{}").format(fallback_error)
                message = req.json().get("message", fallback_message)
                if req.status_code == 429:
                    _LOGGER.warning(message)
                    log_rate_limits(self.hass, target, req.json(), 30)
                else:
                    _LOGGER.error(message)
            else:
                log_rate_limits(self.hass, target, req.json())
