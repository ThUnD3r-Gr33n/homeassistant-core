"""Common opentherm_gw entity properties."""

from dataclasses import dataclass
import logging

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, TRANSLATE_SOURCE

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class OpenThermEntityDescriptionMixin:
    """Mixin for common opentherm_gw entity properties."""

    friendly_name_format: str


class OpenThermEntity(Entity):
    """Represent an OpenTherm Gateway entity."""

    _attr_should_poll = False
    _attr_entity_registry_enabled_default = False
    _attr_available = False

    def __init__(self, gw_dev, source, description):
        """Initialize the entity."""
        self.entity_description = description
        self._gateway = gw_dev
        self._source = source
        friendly_name_format = (
            f"{description.friendly_name_format} ({TRANSLATE_SOURCE[source]})"
            if TRANSLATE_SOURCE[source] is not None
            else description.friendly_name_format
        )
        self._attr_name = friendly_name_format.format(gw_dev.name)
        self._unsub_updates = None
        self._attr_unique_id = f"{gw_dev.gw_id}-{source}-{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, gw_dev.gw_id)},
            manufacturer="Schelte Bron",
            model="OpenTherm Gateway",
            name=gw_dev.name,
            sw_version=gw_dev.gw_version,
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to updates from the component."""
        _LOGGER.debug("Added OpenTherm Gateway entity %s", self._attr_name)
        self._unsub_updates = async_dispatcher_connect(
            self.hass, self._gateway.update_signal, self.receive_report
        )

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe from updates from the component."""
        _LOGGER.debug("Removing OpenTherm Gateway binary sensor %s", self._attr_name)
        self._unsub_updates()

    @callback
    def receive_report(self, status):
        """Handle status updates from the component."""
        # Must be implemented at the platform level.
        raise NotImplementedError
