"""Support for Z-Wave controls using the number platform."""
from __future__ import annotations

from typing import cast

from zwave_js_server.client import Client as ZwaveClient
from zwave_js_server.const import TARGET_VALUE_PROPERTY, CommandClass
from zwave_js_server.model.driver import Driver
from zwave_js_server.model.value import Value

from homeassistant.components.number import DOMAIN as NUMBER_DOMAIN, NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_CLIENT, DOMAIN
from .discovery import ZwaveDiscoveryInfo
from .entity import ZWaveBaseEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Z-Wave Number entity from Config Entry."""
    client: ZwaveClient = hass.data[DOMAIN][config_entry.entry_id][DATA_CLIENT]

    @callback
    def async_add_number(info: ZwaveDiscoveryInfo) -> None:
        """Add Z-Wave number entity."""
        driver = client.driver
        assert driver is not None  # Driver is ready before platforms are loaded.
        entities: list[ZWaveBaseEntity] = []
        if info.platform_hint == "volume":
            entities.append(ZwaveVolumeNumberEntity(config_entry, driver, info))
        else:
            entities.append(ZwaveNumberEntity(config_entry, driver, info))
        async_add_entities(entities)

    config_entry.async_on_unload(
        async_dispatcher_connect(
            hass,
            f"{DOMAIN}_{config_entry.entry_id}_add_{NUMBER_DOMAIN}",
            async_add_number,
        )
    )


class ZwaveNumberEntity(ZWaveBaseEntity, NumberEntity):
    """Representation of a Z-Wave number entity."""

    def __init__(
        self, config_entry: ConfigEntry, driver: Driver, info: ZwaveDiscoveryInfo
    ) -> None:
        """Initialize a ZwaveNumberEntity entity."""
        super().__init__(config_entry, driver, info)
        self._target_value: Value | None
        if self.info.primary_value.metadata.writeable:
            self._target_value = self.info.primary_value
        else:
            self._target_value = self.get_zwave_value(TARGET_VALUE_PROPERTY)

        # Entity class attributes
        self._attr_name = self.generate_name(alternate_value_name=info.platform_hint)

        self._set_attr_native_value()

    def _set_attr_native_value(self) -> None:
        """Set _attr_native_value."""
        value = self.info.primary_value.value
        self._attr_native_value = None if value is None else float(value)

    def on_value_update(self) -> None:
        """Call when one of the watched values change."""
        self._set_attr_native_value()

    @property
    def native_min_value(self) -> float:
        """Return the minimum value."""
        min_ = self.info.primary_value.metadata.min
        return float(0 if min_ is None else min_)

    @property
    def native_max_value(self) -> float:
        """Return the maximum value."""
        max_ = self.info.primary_value.metadata.max
        return float(255 if max_ is None else max_)

    @property
    def native_value(self) -> float | None:
        """Return the entity value."""
        if self.info.primary_value.command_class == CommandClass.SWITCH_MULTILEVEL:
            return self._attr_native_value
        value = self.info.primary_value.value
        return None if value is None else float(value)

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit of measurement of this entity, if any."""
        unit = self.info.primary_value.metadata.unit
        return None if unit is None else str(unit)

    async def async_set_native_value(self, value: float) -> None:
        """Set new value."""
        if (target_value := self._target_value) is None:
            raise HomeAssistantError("Missing target value on device.")
        await self.info.node.async_set_value(target_value, value)
        self._attr_native_value = value
        self.async_write_ha_state()


class ZwaveVolumeNumberEntity(ZWaveBaseEntity, NumberEntity):
    """Representation of a volume number entity."""

    def __init__(
        self, config_entry: ConfigEntry, driver: Driver, info: ZwaveDiscoveryInfo
    ) -> None:
        """Initialize a ZwaveVolumeNumberEntity entity."""
        super().__init__(config_entry, driver, info)
        max_value = cast(int, self.info.primary_value.metadata.max)
        min_value = cast(int, self.info.primary_value.metadata.min)
        self.correction_factor = (max_value - min_value) or 1

        # Entity class attributes
        self._attr_native_min_value = 0
        self._attr_native_max_value = 1
        self._attr_native_step = 0.01
        self._attr_name = self.generate_name(include_value_name=True)

    @property
    def native_value(self) -> float | None:
        """Return the entity value."""
        if self.info.primary_value.value is None:
            return None
        return float(self.info.primary_value.value) / self.correction_factor

    async def async_set_native_value(self, value: float) -> None:
        """Set new value."""
        await self.info.node.async_set_value(
            self.info.primary_value, round(value * self.correction_factor)
        )
