"""Component for wiffi support."""
import asyncio
from datetime import datetime, timedelta
import errno
import logging

from wiffi import WiffiTcpServer

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PORT
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    CHECK_ENTITIES_SIGNAL,
    CREATE_ENTITY_SIGNAL,
    DOMAIN,
    UPDATE_ENTITY_SIGNAL,
)

_LOGGER = logging.getLogger(__name__)


PLATFORMS = ["sensor", "binary_sensor"]


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the wiffi component. config contains data from configuration.yaml."""
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Set up wiffi from a config entry, config_entry contains data from config entry database."""
    # create api object
    api = WiffiIntegrationApi(hass)
    api.setup(config_entry)

    # store api object
    hass.data.setdefault(DOMAIN, {})[config_entry.entry_id] = api

    try:
        await api.server.start_server()
    except OSError as exc:
        if exc.errno != errno.EADDRINUSE:
            _LOGGER.error(f"start_server failed, errno: {exc.errno}")
            return False
        _LOGGER.error("port %s already in use", config_entry.data[CONF_PORT])
        raise ConfigEntryNotReady from exc

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(config_entry, component)
        )

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Unload a config entry."""
    api: "WiffiIntegrationApi" = hass.data[DOMAIN][config_entry.entry_id]
    await api.server.close_server()

    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(config_entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if unload_ok:
        api = hass.data[DOMAIN].pop(config_entry.entry_id)
        api.shutdown()

    return unload_ok


def generateUniqueId(device, metric):
    """Generate a unique string for the entity."""
    return f"{device.mac_address.replace(':', '')}-{metric.name}"


class WiffiIntegrationApi:
    """API object for wiffi handling. Stored in hass.data."""

    def __init__(self, hass):
        """Initialize the instance."""
        self._hass = hass
        self._server = None
        self._known_devices = {}
        self._async_add_entities = {}
        self._periodic_callback = None

    def setup(self, config_entry):
        """Set up api instance."""
        self._server = WiffiTcpServer(config_entry.data[CONF_PORT], self)
        self._periodic_callback = async_track_time_interval(
            self._hass, self._periodic_tick, timedelta(seconds=10)
        )

    def shutdown(self):
        """Shutdown wiffi api.

        Remove listener for periodic callbacks.
        """
        remove_listener = self._periodic_callback
        if remove_listener is not None:
            remove_listener()

    async def __call__(self, device, metrics):
        """Process callback from TCP server if new data arrives from a device."""
        if device.mac_address not in self._known_devices:
            # add empty set for new device
            self._known_devices[device.mac_address] = set()

        for metric in metrics:
            if metric.id not in self._known_devices[device.mac_address]:
                self._known_devices[device.mac_address].add(metric.id)
                async_dispatcher_send(
                    self._hass, CREATE_ENTITY_SIGNAL, self, device, metric
                )
            else:
                async_dispatcher_send(
                    self._hass,
                    UPDATE_ENTITY_SIGNAL + generateUniqueId(device, metric),
                    device,
                    metric,
                )

    @property
    def server(self):
        """Return TCP server instance for start + close."""
        return self._server

    @property
    def async_add_entities(self):
        """Return dict with add_entities functions for every platform."""
        return self._async_add_entities

    @callback
    def _periodic_tick(self, now=None):
        """Check if any entity has timed out because it has not been updated."""
        async_dispatcher_send(self._hass, CHECK_ENTITIES_SIGNAL)


class WiffiEntity(Entity):
    """Common functionality for all wiffi entities."""

    def __init__(self, device, metric):
        """Initialize the base elements of a wiffi entity."""
        self._id = generateUniqueId(device, metric)
        self._device_info = {
            "connections": {
                (device_registry.CONNECTION_NETWORK_MAC, device.mac_address)
            },
            "identifiers": {(DOMAIN, device.mac_address)},
            "manufacturer": "stall.biz",
            "name": f"{device.moduletype} {device.mac_address}",
            "model": device.moduletype,
            "sw_version": device.sw_version,
        }
        self._name = metric.description
        self._expiration_date = None
        self._value = None

    async def async_added_to_hass(self):
        """Entity has been added to hass."""
        async_dispatcher_connect(
            self.hass, UPDATE_ENTITY_SIGNAL + self._id, self._update_value_callback
        )
        async_dispatcher_connect(
            self.hass, CHECK_ENTITIES_SIGNAL, self._check_expiration_date
        )

    @property
    def should_poll(self):
        """Disable polling because data driven ."""
        return False

    @property
    def device_info(self):
        """Return wiffi device info which is shared between all entities of a device."""
        return self._device_info

    @property
    def unique_id(self):
        """Return unique id for entity."""
        return self._id

    @property
    def name(self):
        """Return entity name."""
        return self._name

    @property
    def available(self):
        """Return true if value is valid."""
        return self._value is not None

    def reset_expiration_date(self):
        """Reset value expiration date.

        Will be called by derived classes after a value update has been received.
        """
        self._expiration_date = datetime.now() + timedelta(minutes=3)

    @callback
    def _update_value_callback(self, device, metric):
        """Check if the update belongs to us and update value."""
        if self._id == f"{device.mac_address.replace(':', '')}-{metric.name}":
            self._update_value(metric)

    @callback
    def _check_expiration_date(self):
        """Periodically check if entity value has been updated.

        If there are no more updates from the wiffi device, the value will be
        set to unavailable.
        """
        if (
            self._value is not None
            and self._expiration_date is not None
            and datetime.now() > self._expiration_date
        ):
            self._value = None
            self.async_write_ha_state()
