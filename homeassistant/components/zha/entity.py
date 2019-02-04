"""
Entity for Zigbee Home Automation.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/zha/
"""

import logging

from homeassistant.helpers import entity
from homeassistant.helpers.device_registry import CONNECTION_ZIGBEE
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.util import slugify

from .core.const import (
    DOMAIN, ATTR_MANUFACTURER, DATA_ZHA, DATA_ZHA_BRIDGE_ID, MODEL, NAME
)

_LOGGER = logging.getLogger(__name__)

ENTITY_SUFFIX = 'entity_suffix'


class ZhaEntity(entity.Entity):
    """A base class for ZHA entities."""

    _domain = None  # Must be overridden by subclasses

    def __init__(self, unique_id, zha_device, listeners,
                 skip_entity_id=False, **kwargs):
        """Init ZHA entity."""
        self._force_update = False
        self._should_poll = False
        self._unique_id = unique_id
        self._name = None
        if zha_device.manufacturer and zha_device.model is not None:
            self._name = "{} {}".format(
                zha_device.manufacturer,
                zha_device.model
            )
        if not skip_entity_id:
            ieee = zha_device.ieee
            ieeetail = ''.join(['%02x' % (o, ) for o in ieee[-4:]])
            if zha_device.manufacturer and zha_device.model is not None:
                self.entity_id = "{}.{}_{}_{}_{}{}".format(
                    self._domain,
                    slugify(zha_device.manufacturer),
                    slugify(zha_device.model),
                    ieeetail,
                    listeners[0].cluster.endpoint.endpoint_id,
                    kwargs.get(ENTITY_SUFFIX, ''),
                )
            else:
                self.entity_id = "{}.zha_{}_{}{}".format(
                    self._domain,
                    ieeetail,
                    listeners[0].cluster.endpoint.endpoint_id,
                    kwargs.get(ENTITY_SUFFIX, ''),
                )
        self._state = None
        self._device_state_attributes = {}
        self._zha_device = zha_device
        self._cluster_listeners = {}
        self._available = False
        self._component = kwargs['component']
        self._unsubs = []
        for listener in listeners:
            self._cluster_listeners[listener.name] = listener

    @property
    def name(self):
        """Return Entity's default name."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return self._unique_id

    @property
    def zha_device(self):
        """Return the zha device this entity is attached to."""
        return self._zha_device

    @property
    def device_state_attributes(self):
        """Return device specific state attributes."""
        return self._device_state_attributes

    @property
    def force_update(self) -> bool:
        """Force update this entity."""
        return self._force_update

    @property
    def should_poll(self) -> bool:
        """Poll state from device."""
        return self._should_poll

    @force_update.setter
    def force_update(self, force_update):
        """Set force update."""
        self._force_update = force_update

    @should_poll.setter
    def should_poll(self, should_poll):
        """Set should poll."""
        self._should_poll = should_poll

    @property
    def cluster_listeners(self):
        """Return cluster listeners for entity."""
        return self._cluster_listeners.values()

    @property
    def device_info(self):
        """Return a device description for device registry."""
        zha_device_info = self._zha_device.device_info
        ieee = zha_device_info['ieee']
        return {
            'connections': {(CONNECTION_ZIGBEE, ieee)},
            'identifiers': {(DOMAIN, ieee)},
            ATTR_MANUFACTURER: zha_device_info[ATTR_MANUFACTURER],
            MODEL: zha_device_info[MODEL],
            NAME: zha_device_info[NAME],
            'via_hub': (DOMAIN, self.hass.data[DATA_ZHA][DATA_ZHA_BRIDGE_ID]),
        }

    @property
    def available(self):
        """Return entity availability."""
        return self._available

    def set_available(self, available):
        """Set entity availability."""
        self._available = available
        self.async_schedule_update_ha_state()

    def get_listener(self, name):
        """Get listener by listener name."""
        return self._cluster_listeners.get(name, None)

    def update_state_attribute(self, key, value):
        """Update a single device state attribute."""
        self._device_state_attributes.update({
            key: value
        })
        self.async_schedule_update_ha_state()

    def set_state(self, state):
        """Set the entity state."""
        pass

    async def async_added_to_hass(self):
        """Run when about to be added to hass."""
        await super().async_added_to_hass()
        await self.async_accept_signal(
            None, "{}_{}".format(self.zha_device.available_signal, 'entity'),
            self.set_available,
            signal_override=True)
        self._zha_device.gateway.register_entity(self._zha_device.ieee, self)

    async def async_will_remove_from_hass(self) -> None:
        """Disconnect entity object when removed."""
        for unsub in self._unsubs:
            unsub()

    async def async_update(self):
        """Retrieve latest state."""
        for listener in self.cluster_listeners:
            if hasattr(listener, 'async_update'):
                await listener.async_update()

    async def async_accept_signal(self, listener, signal, func,
                                  signal_override=False):
        """Accept a signal from a listener."""
        unsub = None
        if signal_override:
            unsub = async_dispatcher_connect(
                self.hass,
                signal,
                func
            )
        else:
            unsub = async_dispatcher_connect(
                self.hass,
                "{}_{}".format(listener.unique_id, signal),
                func
            )
        self._unsubs.append(unsub)
