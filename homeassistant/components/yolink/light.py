"""YoLink Dimmer."""
from __future__ import annotations

from typing import Any

from homeassistant.components.light import ATTR_BRIGHTNESS, ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ATTR_COORDINATORS, ATTR_DEVICE_DIMMER, DOMAIN
from .coordinator import YoLinkCoordinator
from .entity import YoLinkEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up YoLink Dimmer from a config entry."""
    device_coordinators = hass.data[DOMAIN][config_entry.entry_id][ATTR_COORDINATORS]
    entities = [
        YoLinkDimmerEntity(config_entry, device_coordinator)
        for device_coordinator in device_coordinators.values()
        if device_coordinator.device.device_type == ATTR_DEVICE_DIMMER
    ]
    async_add_entities(entities)


class YoLinkDimmerEntity(YoLinkEntity, LightEntity):
    """YoLink Dimmer Entity."""

    _attr_has_entity_name: bool = True
    _attr_color_mode: ColorMode | str | None = ColorMode.BRIGHTNESS
    _attr_supported_color_modes: set[ColorMode] | set[str] | None = {
        ColorMode.BRIGHTNESS
    }

    def __init__(
        self,
        config_entry: ConfigEntry,
        coordinator: YoLinkCoordinator,
    ) -> None:
        """Init YoLink Dimmer entity."""
        super().__init__(config_entry, coordinator)
        self._attr_unique_id = f"{coordinator.device.device_id}"
        self._attr_name = f"{coordinator.device.device_name} (State)"

    @callback
    def update_entity_state(self, state: dict[str, Any]) -> None:
        """Update HA Entity State."""
        if (dimmer_is_on := state.get("state")) is not None:
            # update _attr_is_on when device report it's state
            self._attr_is_on = dimmer_is_on
        if (brightness := state.get("brightness")) is not None:
            self._attr_brightness = round(255 * brightness / 100)
        self.async_write_ha_state()

    async def toggle_light_state(self, state: str, brightness: int | None) -> None:
        """Toggle light state."""
        params: dict[str, Any] = {"state": state}
        if brightness is not None:
            self._attr_brightness = brightness
            params["brightness"] = round(brightness / 255, 2) * 100
        await self.call_device_api("setState", params)
        self._attr_is_on = state == "open"
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on light."""
        brightness = kwargs.get(ATTR_BRIGHTNESS)
        await self.toggle_light_state("open", brightness)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off light."""
        await self.toggle_light_state("close", None)
