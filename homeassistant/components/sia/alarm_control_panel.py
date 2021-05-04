"""Module for SIA Alarm Control Panels."""
from __future__ import annotations

import logging
from typing import Any, Callable

from pysiaalarm import SIAEvent

from homeassistant.components.alarm_control_panel import (
    ENTITY_ID_FORMAT as ALARM_ENTITY_ID_FORMAT,
    AlarmControlPanelEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_PORT,
    CONF_ZONE,
    STATE_ALARM_ARMED_AWAY,
    STATE_ALARM_ARMED_CUSTOM_BYPASS,
    STATE_ALARM_ARMED_NIGHT,
    STATE_ALARM_DISARMED,
    STATE_ALARM_TRIGGERED,
    STATE_UNAVAILABLE,
)
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import StateType

from .const import (
    CONF_ACCOUNT,
    CONF_ACCOUNTS,
    CONF_PING_INTERVAL,
    CONF_ZONES,
    DOMAIN,
    SIA_ENTITY_ID_FORMAT,
    SIA_EVENT,
    SIA_NAME_FORMAT,
    SIA_UNIQUE_ID_FORMAT_ALARM,
)
from .utils import get_attr_from_sia_event, get_unavailability_interval

_LOGGER = logging.getLogger(__name__)

DEVICE_CLASS_ALARM = "alarm"
PREVIOUS_STATE = "previous_state"

CODE_CONSEQUENCES = {
    "PA": STATE_ALARM_TRIGGERED,
    "JA": STATE_ALARM_TRIGGERED,
    "TA": STATE_ALARM_TRIGGERED,
    "BA": STATE_ALARM_TRIGGERED,
    "CA": STATE_ALARM_ARMED_AWAY,
    "CG": STATE_ALARM_ARMED_AWAY,
    "CL": STATE_ALARM_ARMED_AWAY,
    "CP": STATE_ALARM_ARMED_AWAY,
    "CQ": STATE_ALARM_ARMED_AWAY,
    "CS": STATE_ALARM_ARMED_AWAY,
    "CF": STATE_ALARM_ARMED_CUSTOM_BYPASS,
    "OA": STATE_ALARM_DISARMED,
    "OG": STATE_ALARM_DISARMED,
    "OP": STATE_ALARM_DISARMED,
    "OQ": STATE_ALARM_DISARMED,
    "OR": STATE_ALARM_DISARMED,
    "OS": STATE_ALARM_DISARMED,
    "NC": STATE_ALARM_ARMED_NIGHT,
    "NL": STATE_ALARM_ARMED_NIGHT,
    "BR": PREVIOUS_STATE,
    "NP": PREVIOUS_STATE,
    "NO": PREVIOUS_STATE,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: Callable[..., None],
) -> bool:
    """Set up SIA alarm_control_panel(s) from a config entry."""
    async_add_entities(
        [
            SIAAlarmControlPanel(entry, account_data, zone)
            for account_data in entry.data[CONF_ACCOUNTS]
            for zone in range(1, account_data[CONF_ZONES] + 1)
        ]
    )
    return True


class SIAAlarmControlPanel(AlarmControlPanelEntity, RestoreEntity):
    """Class for SIA Alarm Control Panels."""

    def __init__(
        self,
        entry: ConfigEntry,
        account_data: dict[str, Any],
        zone: int,
    ):
        """Create SIAAlarmControlPanel object."""
        self._entry: ConfigEntry = entry
        self._account_data: dict[str, Any] = account_data
        self._zone: int = zone

        self._port: int = self._entry.data[CONF_PORT]
        self._account: str = self._account_data[CONF_ACCOUNT]
        self._ping_interval: int = self._account_data[CONF_PING_INTERVAL]

        self.entity_id: str = ALARM_ENTITY_ID_FORMAT.format(
            SIA_ENTITY_ID_FORMAT.format(
                self._port, self._account, self._zone, DEVICE_CLASS_ALARM
            )
        )

        self._attr: dict[str, Any] = {
            CONF_PORT: self._port,
            CONF_ACCOUNT: self._account,
            CONF_ZONE: self._zone,
            CONF_PING_INTERVAL: f"{self._ping_interval} minute(s)",
        }

        self._available: bool = True
        self._state: StateType = None
        self._old_state: StateType = None
        self._cancel_availability_tracker: CALLBACK_TYPE | None = None

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass.

        Overridden from Entity.

        1. start the event listener and add the callback to on_remove
        2. get previous state from storage
        3. if previous state: restore
        4. if previous state is unavailable: set _available to False and return
        5. if available: create availability tracker
        """
        self.async_on_remove(
            self.hass.bus.async_listen(
                event_type=SIA_EVENT.format(self._port, self._account),
                listener=self.async_handle_event,
            )
        )
        last_state = await self.async_get_last_state()
        if last_state is not None:
            self.state = last_state.state
        if self.state == STATE_UNAVAILABLE:
            self._available = False
            return
        self._cancel_availability_tracker = self.async_create_availability_tracker()

    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed from hass.

        Overridden from Entity.
        """
        if self._cancel_availability_tracker:
            self._cancel_availability_tracker()

    async def async_handle_event(self, event: Event) -> None:
        """Listen to events for this port and account and update states.

        If the port and account combo receives any message it means it is online and can therefore be set to available.
        """
        sia_event = SIAEvent.from_dict(event.data)  # pylint: disable=no-member
        _LOGGER.debug("Received event: %s", sia_event)
        if int(sia_event.ri) == self._zone:
            self.state = CODE_CONSEQUENCES.get(sia_event.code, None)
            self._attr.update(get_attr_from_sia_event(sia_event))
        self._available = True
        self.async_write_ha_state()
        self.async_reset_availability_tracker()

    @callback
    def async_reset_availability_tracker(self) -> None:
        """Reset availability tracker by cancelling the current and creating a new one."""
        if self._cancel_availability_tracker:
            self._cancel_availability_tracker()
        self._cancel_availability_tracker = self.async_create_availability_tracker()

    @callback
    def async_create_availability_tracker(self) -> CALLBACK_TYPE:
        """Create a availability tracker and return the callback."""
        return async_call_later(
            self.hass,
            get_unavailability_interval(self._ping_interval),
            self.async_set_unavailable,
        )

    @callback
    def async_set_unavailable(self, _) -> None:
        """Set unavailable."""
        self._available = False
        self.async_write_ha_state()

    @property
    def state(self) -> StateType:
        """Get state."""
        return self._state

    @state.setter
    def state(self, state: str | None) -> None:
        """Set state."""
        if state is not None:
            self._state, self._old_state = (
                self._old_state if state == PREVIOUS_STATE else state
            ), self._state

    @property
    def name(self) -> str:
        """Get Name."""
        return SIA_NAME_FORMAT.format(
            self._port, self._account, self._zone, DEVICE_CLASS_ALARM
        )

    @property
    def unique_id(self) -> str:
        """Get unique_id."""
        return SIA_UNIQUE_ID_FORMAT_ALARM.format(
            self._entry.entry_id, self._account, self._zone
        )

    @property
    def available(self) -> bool:
        """Get availability."""
        return self._available

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return device attributes."""
        return self._attr

    @property
    def should_poll(self) -> bool:
        """Return False if entity pushes its state to HA."""
        return False

    @property
    def supported_features(self) -> int:
        """Flag supported features."""
        return 0

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device_info."""
        return {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": self.name,
            "via_device": (DOMAIN, f"{self._port}_{self._account}"),
        }
