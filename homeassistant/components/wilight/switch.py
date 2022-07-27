"""Support for WiLight switches."""
from __future__ import annotations

from typing import Any

from pywilight.const import ITEM_SWITCH, SWITCH_PAUSE_VALVE, SWITCH_VALVE
import voluptuous as vol

from homeassistant.components.switch import ToggleEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN, WiLightDevice
from .support import wilight_to_hass_trigger, wilight_trigger as wl_trigger

# Attr of features supported by the valve switch entities
ATTR_WATERING_TIME = "watering_time"
ATTR_PAUSE_TIME = "pause_time"
ATTR_TRIGGER_1 = "trigger_1"
ATTR_TRIGGER_2 = "trigger_2"
ATTR_TRIGGER_3 = "trigger_3"
ATTR_TRIGGER_4 = "trigger_4"
ATTR_TRIGGER_1_DESC = "trigger_1_description"
ATTR_TRIGGER_2_DESC = "trigger_2_description"
ATTR_TRIGGER_3_DESC = "trigger_3_description"
ATTR_TRIGGER_4_DESC = "trigger_4_description"

# Attr of services data supported by the valve switch entities
ATTR_TRIGGER = "trigger"
ATTR_TRIGGER_INDEX = "trigger_index"

# Service of features supported by the valve switch entities
SERVICE_SET_WATERING_TIME = "set_watering_time"
SERVICE_SET_PAUSE_TIME = "set_pause_time"
SERVICE_SET_TRIGGER = "set_trigger"

# Range of features supported by the valve switch entities
RANGE_WATERING_TIME = 1800
RANGE_PAUSE_TIME = 24
RANGE_TRIGGER_INDEX = 4

# Service call validation schemas
VALID_WATERING_TIME = vol.All(
    vol.Coerce(int), vol.Range(min=1, max=RANGE_WATERING_TIME)
)
VALID_PAUSE_TIME = vol.All(vol.Coerce(int), vol.Range(min=1, max=RANGE_PAUSE_TIME))
VALID_TRIGGER = wl_trigger
VALID_TRIGGER_INDEX = vol.All(
    vol.Coerce(int), vol.Range(min=1, max=RANGE_TRIGGER_INDEX)
)

# Service schemas
SERVICE_SCHEMA_WATERING_TIME = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): cv.entity_id,
        vol.Required(ATTR_WATERING_TIME): VALID_WATERING_TIME,
    }
)
SERVICE_SCHEMA_PAUSE_TIME = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): cv.entity_id,
        vol.Required(ATTR_PAUSE_TIME): VALID_PAUSE_TIME,
    }
)
SERVICE_SCHEMA_TRIGGER = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): cv.entity_id,
        vol.Required(ATTR_TRIGGER_INDEX): VALID_TRIGGER_INDEX,
        vol.Required(ATTR_TRIGGER): VALID_TRIGGER,
    }
)

# Descriptions of the valve switch entities
DESC_WATERING = "watering"
DESC_PAUSE = "pause"

# Icons of the valve switch entities
ICON_WATERING = "mdi:water"
ICON_PAUSE = "mdi:pause-circle-outline"


def entities_from_discovered_wilight(api_device: Any) -> tuple[Any]:
    """Parse configuration and add WiLight switch entities."""
    entities: Any = []
    for item in api_device.items:
        if item["type"] == ITEM_SWITCH:
            index = item["index"]
            item_name = item["name"]
            if item["sub_type"] == SWITCH_VALVE:
                entities.append(WiLightValveSwitch(api_device, index, item_name))
            elif item["sub_type"] == SWITCH_PAUSE_VALVE:
                entities.append(WiLightValvePauseSwitch(api_device, index, item_name))

    return entities


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up WiLight switches from a config entry."""
    parent = hass.data[DOMAIN][entry.entry_id]

    # Handle a discovered WiLight device.
    entities = entities_from_discovered_wilight(parent.api)
    async_add_entities(entities)

    # Handle services for a discovered WiLight device.
    async def set_watering_time(service: Any) -> None:
        entity_id = service.data[ATTR_ENTITY_ID]

        for entity in entities:
            if (entity.entity_id == entity_id) & isinstance(entity, WiLightValveSwitch):
                watering_time = service.data[ATTR_WATERING_TIME]
                await entity.async_set_switch_time(watering_time=watering_time)

    async def set_trigger(service: Any) -> None:
        entity_id = service.data[ATTR_ENTITY_ID]

        for entity in entities:
            if (entity.entity_id == entity_id) & isinstance(entity, WiLightValveSwitch):
                trigger_index = service.data[ATTR_TRIGGER_INDEX]
                trigger = service.data[ATTR_TRIGGER]
                await entity.async_set_trigger(
                    trigger_index=trigger_index, trigger=trigger
                )

    async def set_pause_time(service: Any) -> None:
        entity_id = service.data[ATTR_ENTITY_ID]

        for entity in entities:
            if (entity.entity_id == entity_id) & isinstance(
                entity, WiLightValvePauseSwitch
            ):
                pause_time = service.data[ATTR_PAUSE_TIME]
                await entity.async_set_switch_time(pause_time=pause_time)

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_WATERING_TIME,
        set_watering_time,
        schema=SERVICE_SCHEMA_WATERING_TIME,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_TRIGGER,
        set_trigger,
        schema=SERVICE_SCHEMA_TRIGGER,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_PAUSE_TIME,
        set_pause_time,
        schema=SERVICE_SCHEMA_PAUSE_TIME,
    )


def wilight_to_hass_pause_time(value: int) -> int:
    """Convert wilight pause_time seconds to hass hour."""
    return round(value / 3600)


def hass_to_wilight_pause_time(value: int) -> int:
    """Convert hass pause_time hours to wilight seconds."""
    return int(value * 3600)


class WiLightValveSwitch(WiLightDevice, SwitchEntity):
    """Representation of a WiLights Valve switch."""

    @property
    def name(self) -> str:
        """Return the name of the switch."""
        return f"{self._name} {DESC_WATERING}"

    @property
    def is_on(self) -> bool:
        """Return true if device is on."""
        return self._status.get("on", False)

    @property
    def watering_time(self) -> int | None:
        """Return watering time of valve switch.

        None is unknown, 1 is minimum, 1800 is maximum.
        """
        return self._status.get("timer_target")

    @property
    def trigger_1(self) -> str | None:
        """Return trigger_1 of valve switch."""
        return self._status.get("trigger_1")

    @property
    def trigger_2(self) -> str | None:
        """Return trigger_2 of valve switch."""
        return self._status.get("trigger_2")

    @property
    def trigger_3(self) -> str | None:
        """Return trigger_3 of valve switch."""
        return self._status.get("trigger_3")

    @property
    def trigger_4(self) -> str | None:
        """Return trigger_4 of valve switch."""
        return self._status.get("trigger_4")

    @property
    def trigger_1_description(self) -> str | None:
        """Return trigger_1_description of valve switch."""
        return wilight_to_hass_trigger(self._status.get("trigger_1"))

    @property
    def trigger_2_description(self) -> str | None:
        """Return trigger_2_description of valve switch."""
        return wilight_to_hass_trigger(self._status.get("trigger_2"))

    @property
    def trigger_3_description(self) -> str | None:
        """Return trigger_3_description of valve switch."""
        return wilight_to_hass_trigger(self._status.get("trigger_3"))

    @property
    def trigger_4_description(self) -> str | None:
        """Return trigger_4_description of valve switch."""
        return wilight_to_hass_trigger(self._status.get("trigger_4"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        attr: dict[str, Any] = {}

        if self.watering_time is not None:
            attr[ATTR_WATERING_TIME] = self.watering_time

        if self.trigger_1 is not None:
            attr[ATTR_TRIGGER_1] = self.trigger_1

        if self.trigger_2 is not None:
            attr[ATTR_TRIGGER_2] = self.trigger_2

        if self.trigger_3 is not None:
            attr[ATTR_TRIGGER_3] = self.trigger_3

        if self.trigger_4 is not None:
            attr[ATTR_TRIGGER_4] = self.trigger_4

        if self.trigger_1_description is not None:
            attr[ATTR_TRIGGER_1_DESC] = self.trigger_1_description

        if self.trigger_2_description is not None:
            attr[ATTR_TRIGGER_2_DESC] = self.trigger_2_description

        if self.trigger_3_description is not None:
            attr[ATTR_TRIGGER_3_DESC] = self.trigger_3_description

        if self.trigger_4_description is not None:
            attr[ATTR_TRIGGER_4_DESC] = self.trigger_4_description

        return attr

    @property
    def icon(self) -> str:
        """Return the icon to use in the frontend."""
        return ICON_WATERING

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the device on."""
        await self._client.turn_on(self._index)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the device off."""
        await self._client.turn_off(self._index)

    async def async_set_switch_time(self, **kwargs: Any) -> None:
        """Set the watering time."""
        if ATTR_WATERING_TIME in kwargs:
            target_time = kwargs[ATTR_WATERING_TIME]
            await self._client.set_switch_time(self._index, target_time)

    async def async_set_trigger(self, **kwargs: Any) -> None:
        """Set the trigger according to index."""
        if (ATTR_TRIGGER_INDEX in kwargs) & (ATTR_TRIGGER in kwargs):
            trigger_index = kwargs[ATTR_TRIGGER_INDEX]
            trigger = kwargs[ATTR_TRIGGER]
            if trigger_index == 1:
                await self._client.set_switch_trigger_1(self._index, trigger)
            if trigger_index == 2:
                await self._client.set_switch_trigger_2(self._index, trigger)
            if trigger_index == 3:
                await self._client.set_switch_trigger_3(self._index, trigger)
            if trigger_index == 4:
                await self._client.set_switch_trigger_4(self._index, trigger)


class WiLightValvePauseSwitch(WiLightDevice, ToggleEntity):
    """Representation of a WiLights Valve Pause switch."""

    @property
    def name(self) -> str:
        """Return the name of the switch."""
        return f"{self._name} {DESC_PAUSE}"

    @property
    def is_on(self) -> bool:
        """Return true if device is on."""
        return self._status.get("on", False)

    @property
    def pause_time(self) -> int | None:
        """Return pause time of valve switch.

        None is unknown, 1 is minimum, 24 is maximum.
        """
        pause_time = self._status.get("timer_target")
        if pause_time is not None:
            return wilight_to_hass_pause_time(pause_time)
        return pause_time

    @property
    def state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        attr: dict[str, Any] = {}

        if self.pause_time is not None:
            attr[ATTR_PAUSE_TIME] = self.pause_time

        return attr

    @property
    def icon(self) -> str:
        """Return the icon to use in the frontend."""
        return ICON_PAUSE

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the device on."""
        await self._client.turn_on(self._index)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the device off."""
        await self._client.turn_off(self._index)

    async def async_set_switch_time(self, **kwargs: Any) -> None:
        """Set the pause time."""
        if ATTR_PAUSE_TIME in kwargs:
            target_time = hass_to_wilight_pause_time(kwargs[ATTR_PAUSE_TIME])
            await self._client.set_switch_time(self._index, target_time)
