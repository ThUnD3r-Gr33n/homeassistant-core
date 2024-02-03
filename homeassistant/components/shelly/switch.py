"""Switch for Shelly."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final, cast

from aioshelly.block_device import Block
from aioshelly.const import MODEL_GAS, (
    MODEL_2,
    MODEL_25,
    MODEL_GAS,
    MODEL_WALL_DISPLAY,
    MODEL_WALL_DISPLAY, RPC_GENERATIONS,
)

from homeassistant.components.automation import automations_with_entity
from homeassistant.components.script import scripts_with_entity
from homeassistant.components.switch import (
    DOMAIN as SWITCH_DOMAIN,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.components.valve import DOMAIN as VALVE_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.issue_registry import IssueSeverity, async_create_issue

from .const import DOMAIN, GAS_VALVE_OPEN_STATES
from .coordinator import ShellyBlockCoordinator, get_entry_data
from .entity import (
    BlockEntityDescription,
    RpcEntityDescription,
    ShellyBlockAttributeEntity,
    ShellyRpcAttributeEntity,
    async_setup_entry_attribute_entities,
    async_setup_entry_rpc,
)
from .utils import (
    async_remove_shelly_entity,
    get_device_entry_gen,
    is_block_exclude_from_relay,
    is_rpc_channel_type_light,
    is_rpc_thermostat_internal_actuator,
)


@dataclass(frozen=True, kw_only=True)
class BlockSwitchDescription(BlockEntityDescription, SwitchEntityDescription):
    """Class to describe a BLOCK switch."""


@dataclass(frozen=True)
class RpcSwitchDescription(RpcEntityDescription, SwitchEntityDescription):
    """Class to describe a RPC sensor."""


# This entity description is deprecated and will be removed in Home Assistant 2024.7.0.
GAS_VALVE_SWITCH: Final = {
    ("valve", "valve"): BlockSwitchDescription(
        key="valve|valve",
        name="Valve",
        available=lambda block: block.valve not in ("failure", "checking"),
        removal_condition=lambda _, block: block.valve in ("not_connected", "unknown"),
        entity_registry_enabled_default=False,
    )
}

SWITCHES: Final = {
    ("relay", "output"): BlockSwitchDescription(
        key="relay|output",
        removal_condition=is_block_exclude_from_relay,
    ),
}

RPC_SWITCHES: Final = {
    "switch": RpcSwitchDescription(
        key="switch",
        sub_key="output",
        removal_condition=is_rpc_channel_type_light,
    )
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switches for device."""
    if get_device_entry_gen(config_entry) in RPC_GENERATIONS:
        rpc_coordinator = get_entry_data(hass)[config_entry.entry_id].rpc
        if rpc_coordinator and rpc_coordinator.model == MODEL_WALL_DISPLAY:
            if not rpc_coordinator.device.shelly.get("relay_in_thermostat", False):
                # Wall Display relay is not used as the thermostat actuator,
                # we need to remove a climate entity
                unique_id = f"{rpc_coordinator.mac}-thermostat:0"
                async_remove_shelly_entity(hass, "climate", unique_id)

        return async_setup_entry_rpc(
            hass, config_entry, async_add_entities, RPC_SWITCHES, RpcRelaySwitch
        )

    block_coordinator = get_entry_data(hass)[config_entry.entry_id].block
    if block_coordinator and block_coordinator.model is MODEL_GAS:
        return async_setup_entry_attribute_entities(
            hass, config_entry, async_add_entities, GAS_VALVE_SWITCH, BlockValveSwitch
        )

    return async_setup_entry_attribute_entities(
        hass, config_entry, async_add_entities, SWITCHES, BlockRelaySwitch
    )


class BlockValveSwitch(ShellyBlockAttributeEntity, SwitchEntity):
    """Entity that controls a Gas Valve on Block based Shelly devices.

    This class is deprecated and will be removed in Home Assistant 2024.7.0.
    """

    entity_description: BlockSwitchDescription
    _attr_translation_key = "valve_switch"

    def __init__(
        self,
        coordinator: ShellyBlockCoordinator,
        block: Block,
        attribute: str,
        description: BlockSwitchDescription,
    ) -> None:
        """Initialize valve."""
        super().__init__(coordinator, block, attribute, description)
        self.control_result: dict[str, Any] | None = None

    @property
    def is_on(self) -> bool:
        """If valve is open."""
        if self.control_result:
            return self.control_result["state"] in GAS_VALVE_OPEN_STATES

        return self.attribute_value in GAS_VALVE_OPEN_STATES

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Open valve."""
        async_create_issue(
            self.hass,
            DOMAIN,
            "deprecated_valve_switch",
            breaks_in_ha_version="2024.7.0",
            is_fixable=True,
            severity=IssueSeverity.WARNING,
            translation_key="deprecated_valve_switch",
            translation_placeholders={
                "entity": f"{VALVE_DOMAIN}.{cast(str, self.name).lower().replace(' ', '_')}",
                "service": f"{VALVE_DOMAIN}.open_valve",
            },
        )
        self.control_result = await self.set_state(go="open")
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Close valve."""
        async_create_issue(
            self.hass,
            DOMAIN,
            "deprecated_valve_switch",
            breaks_in_ha_version="2024.7.0",
            is_fixable=True,
            severity=IssueSeverity.WARNING,
            translation_key="deprecated_valve_switche",
            translation_placeholders={
                "entity": f"{VALVE_DOMAIN}.{cast(str, self.name).lower().replace(' ', '_')}",
                "service": f"{VALVE_DOMAIN}.close_valve",
            },
        )
        self.control_result = await self.set_state(go="close")
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Set up a listener when this entity is added to HA."""
        await super().async_added_to_hass()

        entity_automations = automations_with_entity(self.hass, self.entity_id)
        entity_scripts = scripts_with_entity(self.hass, self.entity_id)
        for item in entity_automations + entity_scripts:
            async_create_issue(
                self.hass,
                DOMAIN,
                f"deprecated_valve_{self.entity_id}_{item}",
                breaks_in_ha_version="2024.7.0",
                is_fixable=True,
                severity=IssueSeverity.WARNING,
                translation_key="deprecated_valve_switch_entity",
                translation_placeholders={
                    "entity": f"{SWITCH_DOMAIN}.{cast(str, self.name).lower().replace(' ', '_')}",
                    "info": item,
                },
            )

    @callback
    def _update_callback(self) -> None:
        """When device updates, clear control result that overrides state."""
        self.control_result = None

        super()._update_callback()


class BlockRelaySwitch(ShellyBlockAttributeEntity, SwitchEntity):
    """Entity that controls a relay on Block based Shelly devices."""

    entity_description: BlockSwitchDescription

    def __init__(
        self,
        coordinator: ShellyBlockCoordinator,
        block: Block,
        attribute: str,
        description: BlockSwitchDescription,
    ) -> None:
        """Initialize relay switch."""
        super().__init__(coordinator, block, attribute, description)
        self.control_result: dict[str, Any] | None = None

    @property
    def is_on(self) -> bool:
        """If switch is on."""
        if self.control_result:
            return cast(bool, self.control_result["ison"])

        return bool(self.block.output)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on relay."""
        self.control_result = await self.set_state(turn="on")
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off relay."""
        self.control_result = await self.set_state(turn="off")
        self.async_write_ha_state()

    @callback
    def _update_callback(self) -> None:
        """When device updates, clear control result that overrides state."""
        self.control_result = None
        super()._update_callback()


class RpcRelaySwitch(ShellyRpcAttributeEntity, SwitchEntity):
    """Entity that controls a relay on RPC based Shelly devices."""

    entity_description: RpcSwitchDescription

    @property
    def is_on(self) -> bool:
        """If switch is on."""
        return bool(self.status["output"])

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on relay."""
        await self.call_rpc("Switch.Set", {"id": self.status["id"], "on": True})

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off relay."""
        await self.call_rpc("Switch.Set", {"id": self.status["id"], "on": False})
