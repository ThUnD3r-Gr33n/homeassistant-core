"""Support for Homekit fans."""
from aiohomekit.model.characteristics import CharacteristicsTypes
from aiohomekit.model.services import ServicesTypes

from homeassistant.components.fan import (
    DIRECTION_FORWARD,
    DIRECTION_REVERSE,
    SUPPORT_DIRECTION,
    SUPPORT_OSCILLATE,
    SUPPORT_SET_SPEED,
    SUPPORT_SET_SPEED_PERCENTAGE,
    FanEntity,
)
from homeassistant.core import callback

from . import KNOWN_DEVICES, HomeKitEntity

# 0 is clockwise, 1 is counter-clockwise. The match to forward and reverse is so that
# its consistent with homeassistant.components.homekit.
DIRECTION_TO_HK = {
    DIRECTION_REVERSE: 1,
    DIRECTION_FORWARD: 0,
}
HK_DIRECTION_TO_HA = {v: k for (k, v) in DIRECTION_TO_HK.items()}


class BaseHomeKitFan(HomeKitEntity, FanEntity):
    """Representation of a Homekit fan."""

    # This must be set in subclasses to the name of a boolean characteristic
    # that controls whether the fan is on or off.
    on_characteristic = None

    def get_characteristic_types(self):
        """Define the homekit characteristics the entity cares about."""
        return [
            CharacteristicsTypes.SWING_MODE,
            CharacteristicsTypes.ROTATION_DIRECTION,
            CharacteristicsTypes.ROTATION_SPEED,
            self.on_characteristic,
        ]

    @property
    def is_on(self):
        """Return true if device is on."""
        return self.service.value(self.on_characteristic) == 1

    @property
    def percentage_speed(self):
        """Return the current speed."""
        if not self.is_on:
            return 0

        return self.service.value(CharacteristicsTypes.ROTATION_SPEED)

    @property
    def current_direction(self):
        """Return the current direction of the fan."""
        direction = self.service.value(CharacteristicsTypes.ROTATION_DIRECTION)
        return HK_DIRECTION_TO_HA[direction]

    @property
    def oscillating(self):
        """Return whether or not the fan is currently oscillating."""
        oscillating = self.service.value(CharacteristicsTypes.SWING_MODE)
        return oscillating == 1

    @property
    def supported_features(self):
        """Flag supported features."""
        features = 0

        if self.service.has(CharacteristicsTypes.ROTATION_DIRECTION):
            features |= SUPPORT_DIRECTION

        if self.service.has(CharacteristicsTypes.ROTATION_SPEED):
            features |= SUPPORT_SET_SPEED | SUPPORT_SET_SPEED_PERCENTAGE

        if self.service.has(CharacteristicsTypes.SWING_MODE):
            features |= SUPPORT_OSCILLATE

        return features

    async def async_set_direction(self, direction):
        """Set the direction of the fan."""
        await self.async_put_characteristics(
            {CharacteristicsTypes.ROTATION_DIRECTION: DIRECTION_TO_HK[direction]}
        )

    async def async_set_speed_percentage(self, speed):
        """Set the speed of the fan."""
        if speed == 0:
            return await self.async_turn_off()

        await self.async_put_characteristics(
            {CharacteristicsTypes.ROTATION_SPEED: speed}
        )

    async def async_oscillate(self, oscillating: bool):
        """Oscillate the fan."""
        await self.async_put_characteristics(
            {CharacteristicsTypes.SWING_MODE: 1 if oscillating else 0}
        )

    #
    # The fan entity model has changed to use percentages and preset_modes
    # instead of speeds.
    #
    # Please review
    # https://developers.home-assistant.io/docs/core/entity/fan/
    #
    async def async_turn_on(
        self, speed=None, percentage=None, preset_mode=None, **kwargs
    ):
        """Turn the specified fan on."""
        characteristics = {}

        if not self.is_on:
            characteristics[self.on_characteristic] = True

        if self.supported_features & SUPPORT_SET_SPEED_PERCENTAGE and speed:
            characteristics[
                CharacteristicsTypes.ROTATION_SPEED
            ] = self.speed_to_percentage(speed)

        if characteristics:
            await self.async_put_characteristics(characteristics)

    async def async_turn_off(self, **kwargs):
        """Turn the specified fan off."""
        await self.async_put_characteristics({self.on_characteristic: False})


class HomeKitFanV1(BaseHomeKitFan):
    """Implement fan support for public.hap.service.fan."""

    on_characteristic = CharacteristicsTypes.ON


class HomeKitFanV2(BaseHomeKitFan):
    """Implement fan support for public.hap.service.fanv2."""

    on_characteristic = CharacteristicsTypes.ACTIVE


ENTITY_TYPES = {
    ServicesTypes.FAN: HomeKitFanV1,
    ServicesTypes.FAN_V2: HomeKitFanV2,
}


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Homekit fans."""
    hkid = config_entry.data["AccessoryPairingID"]
    conn = hass.data[KNOWN_DEVICES][hkid]

    @callback
    def async_add_service(service):
        entity_class = ENTITY_TYPES.get(service.short_type)
        if not entity_class:
            return False
        info = {"aid": service.accessory.aid, "iid": service.iid}
        async_add_entities([entity_class(conn, info)], True)
        return True

    conn.add_listener(async_add_service)
