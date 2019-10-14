"""Code to handle a Dynalite bridge."""
import pprint

from dynalite_devices_lib import DynaliteDevices
from dynalite_lib import CONF_ALL

from homeassistant.core import callback
from homeassistant.const import CONF_HOST

from .const import DOMAIN, DATA_CONFIGS, LOGGER
from .light import DynaliteLight


class BridgeError(Exception):
    """Class to throw exceptions from DynaliteBridge."""

    def __init__(self, message):
        """Initialize the exception."""
        super().__init__()
        self.message = message


class DynaliteBridge:
    """Manages a single Dynalite bridge."""

    def __init__(self, hass, config_entry):
        """Initialize the system."""
        self.config_entry = config_entry
        self.hass = hass
        self.area = {}
        self.async_add_entities = None
        self.waiting_entities = []
        self.all_entities = {}
        self._dynalite_devices = None
        self.config = None

    @property
    def host(self):
        """Return the host of this bridge."""
        return self.config_entry.data[CONF_HOST]

    async def async_setup(self, tries=0):
        """Set up a Dynalite bridge based on host parameter."""
        host = self.host
        hass = self.hass
        LOGGER.debug(
            "component bridge async_setup - %s", pprint.pformat(self.config_entry.data)
        )
        if host not in hass.data[DOMAIN][DATA_CONFIGS]:
            LOGGER.info("invalid host - %s", host)
            return False

        self.config = hass.data[DOMAIN][DATA_CONFIGS][host]

        # Configure the dynalite devices
        self._dynalite_devices = DynaliteDevices(
            config=self.config,
            loop=hass.loop,
            newDeviceFunc=self.add_devices,
            updateDeviceFunc=self.update_device,
        )
        await self._dynalite_devices.async_setup()

        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(self.config_entry, "light")
        )

        return True

    @callback
    def add_devices(self, devices):
        """Call when devices should be added to home assistant."""
        added_entities = []

        for device in devices:
            if device.category == "light":
                entity = DynaliteLight(device, self)
            else:
                LOGGER.debug("Illegal device category %s", device.category)
                continue
            added_entities.append(entity)
            self.all_entities[entity.unique_id] = entity

        if added_entities:
            self.add_entities_when_registered(added_entities)

    @callback
    def update_device(self, device):
        """Call when a device or all devices should be updated."""
        if device == CONF_ALL:
            # This is used to signal connection or disconnection, so all devices may become available or not.
            if self._dynalite_devices.available:
                LOGGER.info("Connected to dynalite host")
            else:
                LOGGER.info("Disconnected from dynalite host")
            for uid in self.all_entities:
                self.all_entities[uid].try_schedule_ha()
        else:
            uid = device.unique_id
            if uid in self.all_entities:
                self.all_entities[uid].try_schedule_ha()

    @callback
    def register_add_entities(self, async_add_entities):
        """Add an async_add_entities for a category."""
        self.async_add_entities = async_add_entities
        if self.waiting_entities:
            self.async_add_entities(self.waiting_entities)

    def add_entities_when_registered(self, entities):
        """Add the entities to HA if async_add_entities was registered, otherwise queue until it is."""
        if not entities:
            return
        if self.async_add_entities:
            self.async_add_entities(entities)
        else:  # handle it later when it is registered
            self.waiting_entities.extend(entities)

    async def async_reset(self):
        """Reset this bridge to default state.

        Will cancel any scheduled setup retry and will unload
        the config entry.
        """
        result = await self.hass.config_entries.async_forward_entry_unload(
            self.config_entry, "light"
        )
        # None and True are OK
        return result
