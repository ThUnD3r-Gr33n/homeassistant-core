"""
Support for Tellstick switches.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/switch.tellstick/
"""


from homeassistant.components.cover import CoverDevice
from homeassistant.components.tellstick import (
    DEFAULT_SIGNAL_REPETITIONS, ATTR_DISCOVER_DEVICES, ATTR_DISCOVER_CONFIG,
    DATA_TELLSTICK, TellstickDevice)


# pylint: disable=unused-argument
def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Tellstick lights."""
    if (discovery_info is None or
            discovery_info[ATTR_DISCOVER_DEVICES] is None):
        return

    signal_repetitions = discovery_info.get(
        ATTR_DISCOVER_CONFIG, DEFAULT_SIGNAL_REPETITIONS)

    add_devices([TellstickCover(hass.data[DATA_TELLSTICK][tellcore_id],
                                signal_repetitions)
                 for tellcore_id in discovery_info[ATTR_DISCOVER_DEVICES]],
                True)


class TellstickCover(TellstickDevice, CoverDevice):
    """Representation of a Tellstick switch."""

    @property
    def is_closed(self):
        """Return the current position of the cover is not possible."""
        return None

    def close_cover(self, **kwargs):
        """Close the cover."""
        self._tellcore_device.down()

    def open_cover(self, **kwargs):
        """Open the cover."""
        self._tellcore_device.up()

    def stop_cover(self, **kwargs):
        """Stop the cover."""
        self._tellcore_device.stop()

    def _parse_tellcore_data(self, tellcore_data):
        """Turn the value received from tellcore into something useful."""
        return None

    def _parse_ha_data(self, kwargs):
        """Turn the value from HA into something useful."""
        return None

    def _update_model(self, new_state, data):
        """Update the device entity state to match the arguments."""
        self._state = new_state
