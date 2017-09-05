"""
This component provides HA switch support for Abode Security System.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/switch.abode/
"""
import logging

from homeassistant.components.abode import AbodeDevice, AbodeAutomation, DOMAIN
from homeassistant.components.switch import SwitchDevice


DEPENDENCIES = ['abode']

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up Abode switch devices."""
    import abodepy.helpers.constants as CONST
    import abodepy.helpers.timeline as TIMELINE

    data = hass.data[DOMAIN]

    devices = []

    # Get all regular switches that are not excluded or marked as lights
    for device in data.abode.get_devices(generic_type=CONST.TYPE_SWITCH):
        if (device.device_id not in data.exclude
                and device.device_id not in data.lights):
            devices.append(AbodeSwitch(data, device))

    # Get all Abode automations that can be enabled/disabled
    for automation in data.abode.get_automations(
            generic_type=CONST.TYPE_AUTOMATION):
        devices.append(AbodeAutomationSwitch(
            data, automation, TIMELINE.AUTOMATION_EDIT_GROUP))

    data.devices.extend(devices)

    add_devices(devices)


class AbodeSwitch(AbodeDevice, SwitchDevice):
    """Representation of an Abode switch."""

    def __init__(self, data, device):
        """Initialize the Abode device."""
        AbodeDevice.__init__(self, data, device)

    def turn_on(self, **kwargs):
        """Turn on the device."""
        self._device.switch_on()

    def turn_off(self, **kwargs):
        """Turn off the device."""
        self._device.switch_off()

    @property
    def is_on(self):
        """Return true if device is on."""
        return self._device.is_on


class AbodeAutomationSwitch(AbodeAutomation, SwitchDevice):
    """A switch implementation for Abode automations."""

    def __init__(self, data, automation, event):
        """Initialize the automation switch."""
        AbodeAutomation.__init__(self, data, automation, event)

    def turn_on(self, **kwargs):
        """Turn on the device."""
        self._automation.set_active(True)

    def turn_off(self, **kwargs):
        """Turn off the device."""
        self._automation.set_active(False)

    @property
    def is_on(self):
        """Return True if the binary sensor is on."""
        return self._automation.is_active
