"""Support for Freebox alarms."""
from typing import Any

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    STATE_ALARM_ARMED_AWAY,
    STATE_ALARM_ARMED_HOME,
    STATE_ALARM_ARMING,
    STATE_ALARM_DISARMED,
    STATE_ALARM_TRIGGERED,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, FreeboxHomeCategory
from .home_base import FreeboxHomeEntity
from .router import FreeboxRouter

FREEBOX_TO_STATUS = {
    "alarm1_arming": STATE_ALARM_ARMING,
    "alarm2_arming": STATE_ALARM_ARMING,
    "alarm1_armed": STATE_ALARM_ARMED_AWAY,
    "alarm2_armed": STATE_ALARM_ARMED_HOME,
    "alarm1_alert_timer": STATE_ALARM_TRIGGERED,
    "alarm2_alert_timer": STATE_ALARM_TRIGGERED,
    "alert": STATE_ALARM_TRIGGERED,
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up alarm panel."""
    router: FreeboxRouter = hass.data[DOMAIN][entry.unique_id]

    alarm_entities: list[AlarmControlPanelEntity] = []

    for node in router.home_devices.values():
        if node["category"] == FreeboxHomeCategory.ALARM:
            alarm_entities.append(FreeboxAlarm(hass, router, node))

    if alarm_entities:
        async_add_entities(alarm_entities, True)


class FreeboxAlarm(FreeboxHomeEntity, AlarmControlPanelEntity):
    """Representation of a Freebox alarm."""

    def __init__(
        self, hass: HomeAssistant, router: FreeboxRouter, node: dict[str, Any]
    ) -> None:
        """Initialize an alarm."""
        super().__init__(hass, router, node)

        # Commands
        self._command_trigger = self.get_command_id(
            node["type"]["endpoints"], "slot", "trigger"
        )
        self._command_arm_away = self.get_command_id(
            node["type"]["endpoints"], "slot", "alarm1"
        )
        self._command_arm_home = self.get_command_id(
            node["type"]["endpoints"], "slot", "alarm2"
        )
        self._command_disarm = self.get_command_id(
            node["type"]["endpoints"], "slot", "off"
        )
        self._command_state = self.get_command_id(
            node["type"]["endpoints"], "signal", "state"
        )
        self._set_features()

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        """Send disarm command."""
        await self.set_home_endpoint_value(self._command_disarm)

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        """Send arm away command."""
        await self.set_home_endpoint_value(self._command_arm_away)

    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        """Send arm home command."""
        await self.set_home_endpoint_value(self._command_arm_home)

    async def async_alarm_trigger(self, code: str | None = None) -> None:
        """Send alarm trigger command."""
        await self.set_home_endpoint_value(self._command_trigger)

    async def async_update(self) -> None:
        """Update state."""
        state: str | None = await self.get_home_endpoint_value(self._command_state)
        if state:
            self._attr_state = FREEBOX_TO_STATUS.get(state)
        else:
            self._attr_state = STATE_ALARM_DISARMED

    def _set_features(self) -> None:
        """Set alarm features."""
        # Search if the arm home feature is present => has an "alarm2" endpoint
        can_arm_home = next(
            (
                endpoint
                for endpoint in self._node["type"]["endpoints"]
                if endpoint["name"] == "alarm2" and endpoint["ep_type"] == "signal"
            ),
            None,
        )

        if (
            self._command_arm_home and can_arm_home
        ):  # or check self.get_value("slot", "alarm2") ???
            self._attr_supported_features = (
                AlarmControlPanelEntityFeature.ARM_AWAY
                | AlarmControlPanelEntityFeature.ARM_HOME
                | AlarmControlPanelEntityFeature.TRIGGER
            )

        else:
            self._attr_supported_features = (
                AlarmControlPanelEntityFeature.ARM_AWAY
                | AlarmControlPanelEntityFeature.TRIGGER
            )
