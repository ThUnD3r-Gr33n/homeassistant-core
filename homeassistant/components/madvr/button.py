"""Binary sensor entities for the madVR integration."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import MadVRConfigEntry
from .const import ButtonCommands
from .coordinator import MadVRCoordinator
from .entity import MadVREntity


@dataclass(frozen=True, kw_only=True)
class MadvrButtonEntityDescription(ButtonEntityDescription):
    """Describe madVR button entity."""

    command: Iterable[str]


COMMANDS: tuple[MadvrButtonEntityDescription, ...] = (
    MadvrButtonEntityDescription(
        key=ButtonCommands.openmenu_info.name,
        translation_key=ButtonCommands.openmenu_info.name,
        command=ButtonCommands.openmenu_info.value,
    ),
    MadvrButtonEntityDescription(
        key=ButtonCommands.openmenu_settings.name,
        translation_key=ButtonCommands.openmenu_settings.name,
        command=ButtonCommands.openmenu_settings.value,
    ),
    MadvrButtonEntityDescription(
        key=ButtonCommands.openmenu_configuration.name,
        translation_key=ButtonCommands.openmenu_configuration.name,
        command=ButtonCommands.openmenu_configuration.value,
    ),
    MadvrButtonEntityDescription(
        key=ButtonCommands.openmenu_profiles.name,
        translation_key=ButtonCommands.openmenu_profiles.name,
        command=ButtonCommands.openmenu_profiles.value,
    ),
    MadvrButtonEntityDescription(
        key=ButtonCommands.openmenu_testpatterns.name,
        translation_key=ButtonCommands.openmenu_testpatterns.name,
        command=ButtonCommands.openmenu_testpatterns.value,
    ),
    MadvrButtonEntityDescription(
        key=ButtonCommands.toggle_debugosd.name,
        translation_key=ButtonCommands.toggle_debugosd.name,
        command=ButtonCommands.toggle_debugosd.value,
    ),
    MadvrButtonEntityDescription(
        key=ButtonCommands.force1080p60output.name,
        translation_key=ButtonCommands.force1080p60output.name,
        command=ButtonCommands.force1080p60output.value,
    ),
    MadvrButtonEntityDescription(
        key=ButtonCommands.restart.name,
        translation_key=ButtonCommands.restart.name,
        command=ButtonCommands.restart.value,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MadVRConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensor entities."""
    coordinator = entry.runtime_data
    async_add_entities(
        MadvrButtonEntity(coordinator, description) for description in COMMANDS
    )


class MadvrButtonEntity(MadVREntity, ButtonEntity):
    """Base class for madVR binary sensors."""

    def __init__(
        self,
        coordinator: MadVRCoordinator,
        description: MadvrButtonEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.entity_description: MadvrButtonEntityDescription = description
        self._attr_unique_id = f"{coordinator.mac}_{description.key}"

    async def async_press(self) -> None:
        """Press the button."""
        await self.coordinator.client.add_command_to_queue(
            self.entity_description.command
        )
