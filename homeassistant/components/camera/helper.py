"""Camera helper functions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_component import EntityComponent

from .const import DOMAIN

if TYPE_CHECKING:
    from . import Camera


def get_camera_from_entity_id(hass: HomeAssistant, entity_id: str) -> Camera:
    """Get camera component from entity_id."""
    component: EntityComponent[Camera] | None = hass.data.get(DOMAIN)
    if component is None:
        raise HomeAssistantError("Camera integration not set up")

    if (camera := component.get_entity(entity_id)) is None:
        raise HomeAssistantError("Camera not found")

    if not camera.is_on:
        raise HomeAssistantError("Camera is off")

    return camera
