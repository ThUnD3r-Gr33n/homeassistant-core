"""Platform for Schlage select integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import SchlageDataUpdateCoordinator
from .entity import SchlageEntity


@dataclass(frozen=True, kw_only=True)
class SchlageSelectEntityDescription(SelectEntityDescription):
    """Entity description for a Schlage select."""


_SECONDS_TO_OPTIONS = {
    0: "disabled",
    15: "15 seconds",
    30: "30 seconds",
    60: "60 seconds",
    120: "120 seconds",
    240: "240 seconds",
    300: "300 seconds",
}
_OPTIONS_TO_SECONDS = {d: s for s, d in _SECONDS_TO_OPTIONS.items()}


_OPTIONS: tuple[SchlageSelectEntityDescription] = (
    SchlageSelectEntityDescription(
        key="auto_lock_time",
        translation_key="auto_lock_time",
        entity_category=EntityCategory.CONFIG,
        options=list(_OPTIONS_TO_SECONDS),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up selects based on a config entry."""
    coordinator: SchlageDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        SchlageSelect(
            coordinator=coordinator,
            description=description,
            device_id=device_id,
        )
        for device_id in coordinator.data.locks
        for description in _OPTIONS
    )


class SchlageSelect(SchlageEntity, SelectEntity):
    """Schlage select entity."""

    entity_description: SchlageSelectEntityDescription

    def __init__(
        self,
        coordinator: SchlageDataUpdateCoordinator,
        description: SchlageSelectEntityDescription,
        device_id: str,
    ) -> None:
        """Initialize a SchlageSelect."""
        super().__init__(coordinator, device_id)
        self.entity_description = description
        self._attr_unique_id = f"{device_id}_{self.entity_description.key}"

    @property
    def current_option(self) -> str:
        """Return the current option."""
        return _SECONDS_TO_OPTIONS[self._lock_data.lock.auto_lock_time]

    def select_option(self, option: str) -> None:
        """Set the current option."""
        self._lock.set_auto_lock_time(_OPTIONS_TO_SECONDS[option])
