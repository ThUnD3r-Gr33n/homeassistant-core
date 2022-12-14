"""Summary binary data from Nextcloud."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from const import BINARY_SENSORS, DOMAIN

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Nextcloud sensors."""
    binary_sensors = []
    for name in hass.data[DOMAIN]:
        if name in BINARY_SENSORS:
            binary_sensors.append(NextcloudBinarySensor(name))

    async_add_entities(
        binary_sensors,
        update_before_add=True,
    )

class NextcloudBinarySensor(BinarySensorEntity):
    """Represents a Nextcloud binary sensor."""

    def __init__(self, item):
        """Initialize the Nextcloud binary sensor."""
        self._name = item
        self._is_on = None

    @property
    def icon(self):
        """Return the icon for this binary sensor."""
        return "mdi:cloud"

    @property
    def name(self):
        """Return the name for this binary sensor."""
        return self._name

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        return self._is_on == "yes"

    @property
    def unique_id(self):
        """Return the unique ID for this binary sensor."""
        return f"{self.hass.data[DOMAIN]['instance']}#{self._name}"

    def update(self) -> None:
        """Update the binary sensor."""
        self._is_on = self.hass.data[DOMAIN][self._name]
