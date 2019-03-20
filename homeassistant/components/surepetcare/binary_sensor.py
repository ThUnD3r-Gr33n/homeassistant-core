"""Support for Sure PetCare Flaps binary sensors."""
import logging

import homeassistant.helpers.device_registry as dr
from homeassistant.components.binary_sensor import BinarySensorDevice
from homeassistant.const import CONF_ID, CONF_NAME, CONF_TYPE
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import (CONF_HOUSEHOLD_ID, DATA_SURE_PETCARE, DEFAULT_DEVICE_CLASS,
                    DEFAULT_ICON, SURE_IDS, TOPIC_UPDATE,
                    SureLocationID, SureLockStateID, SureProductID,
                    SureThingType)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Sure PetCare Flaps sensors based on a config entry."""
    hass.data[DATA_SURE_PETCARE][CONF_HOUSEHOLD_ID] = entry.data[
        CONF_HOUSEHOLD_ID]
    hass.data[DATA_SURE_PETCARE][SureThingType.FLAP.name] = dict()
    hass.data[DATA_SURE_PETCARE][SureThingType.PET.name] = dict()

    entities = list()

    for thing in hass.data[DATA_SURE_PETCARE][SURE_IDS]:
        sure_id = thing[CONF_ID]
        sure_type = thing[CONF_TYPE]

        if sure_id not in hass.data[DATA_SURE_PETCARE][sure_type]:
            hass.data[DATA_SURE_PETCARE][sure_type][sure_id] = None

        if sure_type == SureThingType.FLAP.name:
            entities.append(Flap(sure_id, thing[CONF_NAME], hass=hass))
        elif sure_type == SureThingType.PET.name:
            entities.append(Pet(sure_id, thing[CONF_NAME], hass=hass))

    async_add_entities(entities, True)


class SurePetcareBinarySensor(BinarySensorDevice):
    """A binary sensor implementation for Sure Petcare Entities."""

    def __init__(self, _id: int, name: int, icon=None, device_class=None, sure_type=None, hass=None):
        self._hass = hass

        self._household_id = hass.data[DATA_SURE_PETCARE][CONF_HOUSEHOLD_ID]
        self._id: int = _id
        self._type = sure_type
        self._name = name

        self._data = None
        self._state = dict()

        self._icon = icon
        self._device_class = device_class

    @property
    def is_on(self):
        """Return true if light is on."""
        # return self._state
        # pass

    @property
    def should_poll(self):
        """Return true."""
        return False

    @property
    def name(self):
        """Return the name of the device if any."""
        return self._name

    @property
    def device_info(self):
        """Return information about the device."""
        return {
            "name": self._name,
            "model": SureProductID.PET_FLAP,
            "manufacturer": 'Sure Petcare',
            "connections": {
                (dr.CONNECTION_NETWORK_MAC, "38B9A8FEF31180D8")
            },
            "sw_version": 0,
        }

    @property
    def device_state_attributes(self):
        """Return the state attributes of the device."""
        return self._state

    @property
    def device_class(self):
        """Return the device class."""
        return (DEFAULT_DEVICE_CLASS
                if not self._device_class
                else self._device_class)

    @property
    def icon(self):
        """Return the device class."""
        return DEFAULT_ICON if not self._icon else self._icon

    @property
    def unique_id(self):
        """Return an unique ID."""
        return "{}-{}".format(self._household_id, self._id)

    async def async_update(self):
        """Get the latest data and update the state."""
        try:
            self._state = self._data[self._id]
        except (AttributeError, KeyError, TypeError):
            pass

    async def async_added_to_hass(self):
        """Register callbacks."""
        @callback
        def update():
            """Update the state."""
            self.async_schedule_update_ha_state(True)

        # noinspection W0201
        self._async_unsub_dispatcher_connect = async_dispatcher_connect(
            self._hass, TOPIC_UPDATE, update)

    async def async_will_remove_from_hass(self):
        """Disconnect dispatcher listener when removed."""
        if self._async_unsub_dispatcher_connect:
            self._async_unsub_dispatcher_connect()


class Flap(SurePetcareBinarySensor):
    """Sure Petcare Flap."""

    def __init__(self, _id: int, name: int, hass=None):
        super().__init__(
            _id,
            f"Flap {name.capitalize()}",
            icon="mdi:lock",
            device_class="lock",
            sure_type=hass.data[DATA_SURE_PETCARE][SureThingType.FLAP.name],
            hass=hass,
        )

    @property
    def is_on(self):
        """Return true if light is on."""
        try:
            return bool(self._state["locking"]["mode"] == SureLockStateID.UNLOCKED)
        except (KeyError, TypeError):
            # return False
            return "unknown"

    @property
    def device_info(self):
        """Return information about the device."""
        return {
            "name": self._name,
            "model": SureProductID.PET_FLAP,
            "manufacturer": 'Sure Petcare',
            "connections": {
                (dr.CONNECTION_NETWORK_MAC, "38B953FEFF3980D8")
            },
            "sw_version": 0,
        }

    @property
    def device_state_attributes(self):
        """Return the state attributes of the device."""
        attributes = None
        if self._state:
            attributes = dict(
                battery_voltage=self._state["battery"] / 4,
                locking_mode=self._state["locking"]["mode"],
                device_rssi=self._state["signal"]["device_rssi"],
                hub_rssi=self._state["signal"]["hub_rssi"],
                device_hardware_version=self._state["version"]["device"]["hardware"],
                device_firmware_version=self._state["version"]["device"]["firmware"],
                lcd_hardware_version=self._state["version"]["lcd"]["hardware"],
                lcd_firmware_version=self._state["version"]["lcd"]["firmware"],
                rf_hardware_version=self._state["version"]["rf"]["hardware"],
                rf_firmware_version=self._state["version"]["rf"]["firmware"],
            )
        else:
            attributes = dict(error=self._state)

        return attributes


class Pet(SurePetcareBinarySensor):
    """Sure Petcare Pet."""

    def __init__(self, _id: int, name: int, hass=None):
        super().__init__(
            _id,
            f"Pet {name.capitalize()}",
            icon="mdi:cat",
            device_class="presence",
            hass=hass,
        )

    @property
    def is_on(self):
        """Return true if light is on."""
        try:
            return bool(self._state["where"] == SureLocationID.INSIDE)
        except (KeyError, TypeError):
            return False
