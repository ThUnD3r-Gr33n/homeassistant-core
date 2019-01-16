"""SmartThings Cloud integration for Home Assistant."""

import asyncio
import logging

from aiohttp.client_exceptions import (
    ClientConnectionError, ClientResponseError)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect, async_dispatcher_send)
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.typing import ConfigType, HomeAssistantType

from .config_flow import SmartThingsFlowHandler  # noqa
from .const import (
    CONF_APP_ID, CONF_INSTALLED_APP_ID, DATA_BROKERS, DATA_MANAGER, DOMAIN,
    SIGNAL_SMARTTHINGS_UPDATE, SUPPORTED_PLATFORMS)
from .smartapp import (
    setup_smartapp, setup_smartapp_endpoint, update_app,
    validate_installed_app)

REQUIREMENTS = ['pysmartapp==0.3.0', 'pysmartthings==0.4.1']
DEPENDENCIES = ['http']

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistantType, config: ConfigType):
    """Initialize the SmartThings platform."""
    await setup_smartapp_endpoint(hass)
    return True


async def async_setup_entry(hass: HomeAssistantType, entry: ConfigEntry):
    """Initialize config entry which represents an installed SmartApp."""
    from pysmartthings import SmartThings

    if not hass.config.api.base_url.lower().startswith('https://'):
        _LOGGER.warning("The 'base_url' of the 'http' component must be "
                        "configured and start with 'https://'")
        return False

    api = SmartThings(async_get_clientsession(hass),
                      entry.data[CONF_ACCESS_TOKEN])

    remove_entry = False
    try:
        # See if the app is already setup. This occurs when there are
        # installs in multiple SmartThings locations (valid use-case)
        manager = hass.data[DOMAIN][DATA_MANAGER]
        smart_app = manager.smartapps.get(entry.data[CONF_APP_ID])
        if not smart_app:
            # Validate and setup the app.
            app = await api.app(entry.data[CONF_APP_ID])
            await update_app(hass, app)
            smart_app = setup_smartapp(hass, app)

        # Validate and retrieve the installed app.
        installed_app = await validate_installed_app(
            api, entry.data[CONF_APP_ID],
            entry.data[CONF_INSTALLED_APP_ID])

        # Get devices and their current status
        devices = await api.devices(
            location_ids=[installed_app.location_id])
        await asyncio.gather(*[d.status.refresh() for d in devices])

        # Setup device broker
        broker = DeviceBroker(hass, devices,
                              installed_app.installed_app_id)
        broker.event_handler_disconnect = \
            smart_app.connect_event(broker.event_handler)
        hass.data[DOMAIN][DATA_BROKERS][entry.entry_id] = broker

    except ClientResponseError as ex:
        if ex.status in (400, 401, 403, 422):
            remove_entry = True
        else:
            raise ConfigEntryNotReady from ex
    except (ClientConnectionError, RuntimeWarning) as ex:
        raise ConfigEntryNotReady from ex

    if remove_entry:
        hass.async_create_task(
            hass.config_entries.async_remove(entry.entry_id))
        # only create new flow if there isn't a pending one for SmartThings.
        flows = hass.config_entries.flow.async_progress()
        if not [flow for flow in flows if flow['handler'] == DOMAIN]:
            hass.async_create_task(
                hass.config_entries.flow.async_init(
                    DOMAIN, context={'source': 'import'}))
        return False

    for component in SUPPORTED_PLATFORMS:
        hass.async_create_task(hass.config_entries.async_forward_entry_setup(
            entry, component))
    return True


async def async_unload_entry(hass: HomeAssistantType, entry: ConfigEntry):
    """Unload a config entry."""
    broker = hass.data[DOMAIN][DATA_BROKERS].pop(entry.entry_id, None)
    if broker and broker.event_handler_disconnect:
        broker.event_handler_disconnect()

    for component in SUPPORTED_PLATFORMS:
        hass.async_create_task(hass.config_entries.async_forward_entry_unload(
            entry, component))
    return True


class DeviceBroker:
    """Manages an individual SmartThings config entry."""

    def __init__(self, hass, devices, installed_app_id: str):
        """Create a new instance of the SmartThingsInstalledApp."""
        self.devices = {}
        self._hass = hass
        self._installed_app_id = installed_app_id
        self.event_handler_disconnect = None
        self.switches = []
        self._map_entities(devices)

    def _map_entities(self, devices):
        # determine the device types...
        for device in devices:
            self.devices[device.device_id] = device
            if 'switch' in device.capabilities:
                self.switches.append(device)

    async def event_handler(self, req, resp, app):
        """Broker for incoming events."""
        from pysmartapp.event import EVENT_TYPE_DEVICE

        # Do not process events received from a different installed app
        # under the same parent SmartApp (valid use-scenario)
        if req.installed_app_id != self._installed_app_id:
            return

        updated_devices = set()
        for evt in req.events:
            if evt.event_type != EVENT_TYPE_DEVICE:
                continue
            device = self.devices.get(evt.device_id)
            if not device:
                continue
            device.status.apply_attribute_update(
                evt.component_id, evt.capability, evt.attribute, evt.value)
            updated_devices.add(device.device_id)
        _LOGGER.debug("Update received with %s events and updated %s devices",
                      len(req.events), len(updated_devices))

        async_dispatcher_send(self._hass, SIGNAL_SMARTTHINGS_UPDATE,
                              updated_devices)


class SmartThingsEntity(Entity):
    """Defines a SmartThings entity."""

    def __init__(self, device):
        """Initialize the instance."""
        self._device = device
        self._dispatcher_remove = None

    async def async_added_to_hass(self):
        """Device added to hass."""
        async def async_update_state(devices):
            """Update device state."""
            if self._device.device_id in devices:
                await self.async_update_ha_state(True)

        self._dispatcher_remove = async_dispatcher_connect(
            self.hass, SIGNAL_SMARTTHINGS_UPDATE, async_update_state)

    async def async_will_remove_from_hass(self) -> None:
        """Disconnect the device when removed."""
        if self._dispatcher_remove:
            self._dispatcher_remove()

    @property
    def device_info(self):
        """Get attributes about the device."""
        return {
            'identifiers': {
                (DOMAIN, self._device.device_id)
            },
            'name': self._device.label,
            'model': self._device.device_type_name,
            'manufacturer': 'SmartThings'
        }

    @property
    def name(self) -> str:
        """Return the name of the light if any."""
        return self._device.label

    @property
    def should_poll(self) -> bool:
        """No polling needed for this device."""
        return False

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return self._device.device_id
