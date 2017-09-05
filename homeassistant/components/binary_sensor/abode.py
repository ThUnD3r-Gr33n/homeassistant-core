"""
This component provides HA binary_sensor support for Abode Security System.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/binary_sensor.abode/
"""
import logging

from homeassistant.components.abode import AbodeDevice, AbodeAutomation, DOMAIN
from homeassistant.components.binary_sensor import BinarySensorDevice


DEPENDENCIES = ['abode']

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up a sensor for an Abode device."""
    import abodepy.helpers.constants as CONST
    import abodepy.helpers.timeline as TIMELINE

    data = hass.data[DOMAIN]

    device_types = [CONST.TYPE_CONNECTIVITY, CONST.TYPE_MOISTURE,
                    CONST.TYPE_MOTION, CONST.TYPE_OCCUPANCY,
                    CONST.TYPE_OPENING]

    devices = []
    for device in data.abode.get_devices(generic_type=device_types):
        if device.device_id not in data.exclude:
            devices.append(AbodeBinarySensor(data, device))

    for automation in data.abode.get_automations(
            generic_type=CONST.TYPE_QUICK_ACTION):
        if automation.automation_id not in data.exclude:
            devices.append(AbodeQuickActionBinarySensor(
                data, automation, TIMELINE.AUTOMATION_EDIT_GROUP))

    data.devices.extend(devices)

    add_devices(devices)


class AbodeBinarySensor(AbodeDevice, BinarySensorDevice):
    """A binary sensor implementation for Abode device."""

    def __init__(self, data, device):
        """Initialize a sensor for Abode device."""
        AbodeDevice.__init__(self, data, device)

    @property
    def is_on(self):
        """Return True if the binary sensor is on."""
        return self._device.is_on

    @property
    def device_class(self):
        """Return the class of the binary sensor."""
        return self._device.generic_type


class AbodeQuickActionBinarySensor(AbodeAutomation, BinarySensorDevice):
    """A binary sensor implementation for Abode quick action automations."""

    def __init__(self, data, automation, event):
        """Initialize the Quick Automation sensor."""
        AbodeAutomation.__init__(self, data, automation, event)

    def trigger(self):
        """Trigger a quick automation."""
        self._automation.trigger()

    @property
    def is_on(self):
        """Return True if the binary sensor is on."""
        return self._automation.is_active
