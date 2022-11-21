"""Component to allow setting text as platforms."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging
import re
from typing import Any, final

import voluptuous as vol

from homeassistant.backports.enum import StrEnum
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import MAX_LENGTH_STATE_STATE
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.config_validation import (  # noqa: F401
    PLATFORM_SCHEMA,
    PLATFORM_SCHEMA_BASE,
)
from homeassistant.helpers.entity import Entity, EntityDescription
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.typing import ConfigType

from .const import (
    ATTR_MAX,
    ATTR_MIN,
    ATTR_MODE,
    ATTR_PATTERN,
    ATTR_VALUE,
    DOMAIN,
    SERVICE_SET_VALUE,
)

SCAN_INTERVAL = timedelta(seconds=30)

ENTITY_ID_FORMAT = DOMAIN + ".{}"

MIN_TIME_BETWEEN_SCANS = timedelta(seconds=10)

_LOGGER = logging.getLogger(__name__)

__all__ = ["DOMAIN", "TextEntity", "TextEntityDescription", "TextMode"]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up Text entities."""
    component = hass.data[DOMAIN] = EntityComponent[TextEntity](
        _LOGGER, DOMAIN, hass, SCAN_INTERVAL
    )
    await component.async_setup(config)

    component.async_register_entity_service(
        SERVICE_SET_VALUE,
        {vol.Required(ATTR_VALUE): cv.string},
        _async_set_value,
    )

    return True


async def _async_set_value(entity: TextEntity, service_call: ServiceCall) -> None:
    """Service call wrapper to set a new value."""
    value = service_call.data[ATTR_VALUE]
    if len(value) < entity.min:
        raise HomeAssistantError(
            f"Value {value} for {entity.name} is too short (minimum length {entity.min})"
        )
    if len(value) > entity.max:
        raise HomeAssistantError(
            f"Value {value} for {entity.name} is too long (maximum length {entity.max})"
        )
    if entity.pattern is not None and re.compile(entity.pattern).match(value) is None:
        raise HomeAssistantError(
            f"Value {value} for {entity.name} doesn't match pattern {entity.pattern}"
        )
    await entity.async_set_value(value)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a config entry."""
    component: EntityComponent[TextEntity] = hass.data[DOMAIN]
    return await component.async_setup_entry(entry)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    component: EntityComponent[TextEntity] = hass.data[DOMAIN]
    return await component.async_unload_entry(entry)


class TextMode(StrEnum):
    """Modes for text entities."""

    PASSWORD = "password"
    TEXT = "text"


@dataclass
class TextEntityDescription(EntityDescription):
    """A class that describes text entities."""

    native_min: int | None = None
    native_max: int | None = None
    mode: TextMode | None = None
    pattern: str | None = None


class TextEntity(Entity):
    """Representation of a Text entity."""

    entity_description: TextEntityDescription
    _attr_mode: TextMode = TextMode.TEXT
    _attr_native_value: str | None
    _attr_native_min: int = 0
    _attr_native_max: int = MAX_LENGTH_STATE_STATE
    _attr_pattern: str | None = None
    _attr_state: None = None

    @property
    def capability_attributes(self) -> dict[str, Any]:
        """Return capability attributes."""
        return {
            ATTR_MODE: self.mode,
            ATTR_MIN: self.min,
            ATTR_MAX: self.max,
            ATTR_PATTERN: self.pattern,
        }

    @property
    @final
    def state(self) -> str | None:
        """Return the entity state."""
        if self.native_value is None:
            return None
        if len(self.native_value) < self.min:
            raise ValueError(
                f"Value {self.native_value} is too short (minimum length {self.min})"
            )
        if len(self.native_value) > self.max:
            raise ValueError(
                f"Value {self.native_value} is too long (maximum length {self.max})"
            )
        if (
            self.pattern is not None
            and re.compile(self.pattern).match(self.native_value) is None
        ):
            raise ValueError(f"Value does not match expected pattern {self.pattern}")
        return self.native_value

    @property
    def mode(self) -> TextMode:
        """Return the mode of the entity."""
        if (
            hasattr(self, "entity_description")
            and self.entity_description.mode is not None
        ):
            return self.entity_description.mode
        return self._attr_mode

    @property
    def native_min(self) -> int:
        """Return the minimum length of the value."""
        if (
            hasattr(self, "entity_description")
            and self.entity_description.native_min is not None
        ):
            return self.entity_description.native_min
        return self._attr_native_min

    @property
    @final
    def min(self) -> int:
        """Return the minimum length of the value."""
        return max(self.native_min, 0)

    @property
    def native_max(self) -> int:
        """Return the maximum length of the value."""
        if (
            hasattr(self, "entity_description")
            and self.entity_description.native_max is not None
        ):
            return self.entity_description.native_max
        return self._attr_native_max

    @property
    @final
    def max(self) -> int:
        """Return the maximum length of the value."""
        return min(self.native_max, MAX_LENGTH_STATE_STATE)

    @property
    def pattern(self) -> str | None:
        """Return the regex pattern that the value must match."""
        if (
            hasattr(self, "entity_description")
            and self.entity_description.pattern is not None
        ):
            return self.entity_description.pattern
        return self._attr_pattern

    @property
    def native_value(self) -> str | None:
        """Return the value reported by the text."""
        return self._attr_native_value

    def set_value(self, value: str) -> None:
        """Change the value."""
        raise NotImplementedError()

    async def async_set_value(self, value: str) -> None:
        """Change the value."""
        await self.hass.async_add_executor_job(self.set_value, value)
