"""Generic Z-Wave Entity Class."""

import logging
from typing import List, Optional, Tuple, Union

from zwave_js_server.client import Client as ZwaveClient
from zwave_js_server.model.node import Node as ZwaveNode
from zwave_js_server.model.value import Value as ZwaveValue, get_value_id

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.helpers.entity import Entity

from .const import DOMAIN
from .discovery import ZwaveDiscoveryInfo

LOGGER = logging.getLogger(__name__)

EVENT_VALUE_UPDATED = "value updated"


@callback
def get_device_id(client: ZwaveClient, node: ZwaveNode) -> Tuple[str, str]:
    """Get device registry identifier for Z-Wave node."""
    return (DOMAIN, f"{client.driver.controller.home_id}-{node.node_id}")


class ZWaveBaseEntity(Entity):
    """Generic Entity Class for a Z-Wave Device."""

    def __init__(
        self, config_entry: ConfigEntry, client: ZwaveClient, info: ZwaveDiscoveryInfo
    ) -> None:
        """Initialize a generic Z-Wave device entity."""
        self.config_entry = config_entry
        self.client = client
        self.info = info
        self._name = self.generate_name()
        # entities requiring additional values, can add extra ids to this list
        self.watched_value_ids = {self.info.primary_value.value_id}

    @callback
    def on_value_update(self) -> None:
        """Call when one of the watched values change.

        To be overridden by platforms needing this event.
        """

    async def async_added_to_hass(self) -> None:
        """Call when entity is added."""
        assert self.hass  # typing
        # Add value_changed callbacks.
        self.async_on_remove(
            self.info.node.on(EVENT_VALUE_UPDATED, self._value_changed)
        )

    @property
    def device_info(self) -> dict:
        """Return device information for the device registry."""
        # device is precreated in main handler
        return {
            "identifiers": {get_device_id(self.client, self.info.node)},
        }

    def generate_name(
        self,
        include_value_name: bool = False,
        alternate_value_name: Optional[str] = None,
        additional_info: Optional[List[str]] = None,
    ) -> str:
        """Generate entity name."""
        if additional_info is None:
            additional_info = []
        name: str = self.info.node.name or self.info.node.device_config.description
        if include_value_name:
            value_name = (
                alternate_value_name
                or self.info.primary_value.metadata.label
                or self.info.primary_value.property_key_name
                or self.info.primary_value.property_name
            )
            name = f"{name}: {value_name}"
        for item in additional_info:
            if item:
                name += f" - {item}"
        # append endpoint if > 1
        if self.info.primary_value.endpoint > 1:
            name += f" ({self.info.primary_value.endpoint})"

        return name

    @property
    def name(self) -> str:
        """Return default name from device name and value name combination."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return the unique_id of the entity."""
        return f"{self.client.driver.controller.home_id}.{self.info.value_id}"

    @property
    def available(self) -> bool:
        """Return entity availability."""
        return self.client.connected and bool(self.info.node.ready)

    @callback
    def _value_changed(self, event_data: dict) -> None:
        """Call when (one of) our watched values changes.

        Should not be overridden by subclasses.
        """
        value_id = event_data["value"].value_id

        if value_id not in self.watched_value_ids:
            return

        value = self.info.node.values[value_id]

        LOGGER.debug(
            "[%s] Value %s/%s changed to: %s",
            self.entity_id,
            value.property_,
            value.property_key_name,
            value.value,
        )

        self.on_value_update()
        self.async_write_ha_state()

    @callback
    def get_zwave_value(
        self,
        value_property: Union[str, int],
        command_class: Optional[int] = None,
        endpoint: Optional[int] = None,
        value_property_key: Optional[int] = None,
        value_property_key_name: Optional[str] = None,
        add_to_watched_value_ids: bool = True,
        check_all_endpoints: bool = False,
    ) -> Optional[ZwaveValue]:
        """Return specific ZwaveValue on this ZwaveNode."""
        # use commandclass and endpoint from primary value if omitted
        return_value = None
        if command_class is None:
            command_class = self.info.primary_value.command_class
        if endpoint is None:
            endpoint = self.info.primary_value.endpoint

        # lookup value by value_id
        value_id = get_value_id(
            self.info.node,
            command_class,
            value_property,
            endpoint=endpoint,
            property_key=value_property_key,
            property_key_name=value_property_key_name,
        )
        return_value = self.info.node.values.get(value_id)

        # If we haven't found a value and check_all_endpoints is True, we should
        # return the first value we can find on any other endpoint
        if return_value is None and check_all_endpoints:
            for endpoint_ in self.info.node.endpoints:
                if endpoint_.index != self.info.primary_value.endpoint:
                    value_id = get_value_id(
                        self.info.node,
                        command_class,
                        value_property,
                        endpoint_.index,
                        value_property_key,
                        value_property_key_name,
                    )
                    return_value = self.info.node.values.get(value_id)
                    if return_value:
                        break

        # add to watched_ids list so we will be triggered when the value updates
        if (
            return_value
            and return_value.value_id not in self.watched_value_ids
            and add_to_watched_value_ids
        ):
            self.watched_value_ids.add(return_value.value_id)
        return return_value

    @property
    def should_poll(self) -> bool:
        """No polling needed."""
        return False
