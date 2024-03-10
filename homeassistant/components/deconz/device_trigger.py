"""Provides device automations for deconz events."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
from homeassistant.components.device_automation.exceptions import (
    InvalidDeviceAutomationConfig,
)
from homeassistant.components.homeassistant.triggers import event as event_trigger
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_DOMAIN,
    CONF_EVENT,
    CONF_PLATFORM,
    CONF_TYPE,
    CONF_UNIQUE_ID,
)
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.trigger import TriggerActionType, TriggerInfo
from homeassistant.helpers.typing import ConfigType

from . import DOMAIN
from .deconz_event import (
    CONF_DECONZ_EVENT,
    CONF_GESTURE,
    DeconzAlarmEvent,
    DeconzEvent,
    DeconzPresenceEvent,
    DeconzRelativeRotaryEvent,
)
from .hub import DeconzHub

CONF_SUBTYPE = "subtype"

CONF_SHORT_PRESS = "remote_button_short_press"
CONF_SHORT_RELEASE = "remote_button_short_release"
CONF_LONG_PRESS = "remote_button_long_press"
CONF_LONG_RELEASE = "remote_button_long_release"
CONF_DOUBLE_PRESS = "remote_button_double_press"
CONF_TRIPLE_PRESS = "remote_button_triple_press"
CONF_QUADRUPLE_PRESS = "remote_button_quadruple_press"
CONF_QUINTUPLE_PRESS = "remote_button_quintuple_press"
CONF_ROTATED = "remote_button_rotated"
CONF_ROTATED_FAST = "remote_button_rotated_fast"
CONF_ROTATION_STOPPED = "remote_button_rotation_stopped"
CONF_AWAKE = "remote_awakened"
CONF_MOVE = "remote_moved"
CONF_DOUBLE_TAP = "remote_double_tap"
CONF_SHAKE = "remote_gyro_activated"
CONF_FREE_FALL = "remote_falling"
CONF_FLIP_90 = "remote_flip_90_degrees"
CONF_FLIP_180 = "remote_flip_180_degrees"
CONF_MOVE_ANY = "remote_moved_any_side"
CONF_DOUBLE_TAP_ANY = "remote_double_tap_any_side"
CONF_TURN_CW = "remote_turned_clockwise"
CONF_TURN_CCW = "remote_turned_counter_clockwise"
CONF_ROTATE_FROM_SIDE_1 = "remote_rotate_from_side_1"
CONF_ROTATE_FROM_SIDE_2 = "remote_rotate_from_side_2"
CONF_ROTATE_FROM_SIDE_3 = "remote_rotate_from_side_3"
CONF_ROTATE_FROM_SIDE_4 = "remote_rotate_from_side_4"
CONF_ROTATE_FROM_SIDE_5 = "remote_rotate_from_side_5"
CONF_ROTATE_FROM_SIDE_6 = "remote_rotate_from_side_6"

CONF_TURN_ON = "turn_on"
CONF_TURN_OFF = "turn_off"
CONF_DIM_UP = "dim_up"
CONF_DIM_DOWN = "dim_down"
CONF_LEFT = "left"
CONF_RIGHT = "right"
CONF_OPEN = "open"
CONF_CLOSE = "close"
CONF_BOTH_BUTTONS = "both_buttons"
CONF_TOP_BUTTONS = "top_buttons"
CONF_BOTTOM_BUTTONS = "bottom_buttons"
CONF_BUTTON_1 = "button_1"
CONF_BUTTON_2 = "button_2"
CONF_BUTTON_3 = "button_3"
CONF_BUTTON_4 = "button_4"
CONF_BUTTON_5 = "button_5"
CONF_BUTTON_6 = "button_6"
CONF_BUTTON_7 = "button_7"
CONF_BUTTON_8 = "button_8"
CONF_SIDE_1 = "side_1"
CONF_SIDE_2 = "side_2"
CONF_SIDE_3 = "side_3"
CONF_SIDE_4 = "side_4"
CONF_SIDE_5 = "side_5"
CONF_SIDE_6 = "side_6"


HUE_DIMMER_REMOTE_MODEL_GEN1 = "RWL020"
HUE_DIMMER_REMOTE_MODEL_GEN2 = "RWL021"
HUE_DIMMER_REMOTE_MODEL_GEN3 = "RWL022"
HUE_DIMMER_REMOTE = {
    (CONF_SHORT_PRESS, CONF_TURN_ON): {CONF_EVENT: 1000},
    (CONF_SHORT_RELEASE, CONF_TURN_ON): {CONF_EVENT: 1002},
    (CONF_LONG_PRESS, CONF_TURN_ON): {CONF_EVENT: 1001},
    (CONF_LONG_RELEASE, CONF_TURN_ON): {CONF_EVENT: 1003},
    (CONF_SHORT_PRESS, CONF_DIM_UP): {CONF_EVENT: 2000},
    (CONF_SHORT_RELEASE, CONF_DIM_UP): {CONF_EVENT: 2002},
    (CONF_LONG_PRESS, CONF_DIM_UP): {CONF_EVENT: 2001},
    (CONF_LONG_RELEASE, CONF_DIM_UP): {CONF_EVENT: 2003},
    (CONF_SHORT_PRESS, CONF_DIM_DOWN): {CONF_EVENT: 3000},
    (CONF_SHORT_RELEASE, CONF_DIM_DOWN): {CONF_EVENT: 3002},
    (CONF_LONG_PRESS, CONF_DIM_DOWN): {CONF_EVENT: 3001},
    (CONF_LONG_RELEASE, CONF_DIM_DOWN): {CONF_EVENT: 3003},
    (CONF_SHORT_PRESS, CONF_TURN_OFF): {CONF_EVENT: 4000},
    (CONF_SHORT_RELEASE, CONF_TURN_OFF): {CONF_EVENT: 4002},
    (CONF_LONG_PRESS, CONF_TURN_OFF): {CONF_EVENT: 4001},
    (CONF_LONG_RELEASE, CONF_TURN_OFF): {CONF_EVENT: 4003},
}

HUE_BUTTON_REMOTE_MODEL = "ROM001"  # Hue smart button
HUE_BUTTON_REMOTE = {
    (CONF_SHORT_PRESS, CONF_TURN_ON): {CONF_EVENT: 1000},
    (CONF_SHORT_RELEASE, CONF_TURN_ON): {CONF_EVENT: 1002},
    (CONF_LONG_PRESS, CONF_TURN_ON): {CONF_EVENT: 1001},
    (CONF_LONG_RELEASE, CONF_TURN_ON): {CONF_EVENT: 1003},
}

HUE_TAP_REMOTE_MODEL = "ZGPSWITCH"
HUE_TAP_REMOTE = {
    (CONF_SHORT_PRESS, CONF_BUTTON_1): {CONF_EVENT: 34},
    (CONF_SHORT_PRESS, CONF_BUTTON_2): {CONF_EVENT: 16},
    (CONF_SHORT_PRESS, CONF_BUTTON_3): {CONF_EVENT: 17},
    (CONF_SHORT_PRESS, CONF_BUTTON_4): {CONF_EVENT: 18},
}

HUE_WALL_REMOTE_MODEL = "RDM001"  # Hue wall switch
HUE_WALL_REMOTE = {
    (CONF_SHORT_PRESS, CONF_BUTTON_1): {CONF_EVENT: 1000},
    (CONF_SHORT_RELEASE, CONF_BUTTON_1): {CONF_EVENT: 1002},
    (CONF_LONG_PRESS, CONF_BUTTON_1): {CONF_EVENT: 1001},
    (CONF_LONG_RELEASE, CONF_BUTTON_1): {CONF_EVENT: 1003},
    (CONF_SHORT_PRESS, CONF_BUTTON_2): {CONF_EVENT: 2000},
    (CONF_SHORT_RELEASE, CONF_BUTTON_2): {CONF_EVENT: 2002},
    (CONF_LONG_PRESS, CONF_BUTTON_2): {CONF_EVENT: 2001},
    (CONF_LONG_RELEASE, CONF_BUTTON_2): {CONF_EVENT: 2003},
}

FRIENDS_OF_HUE_SWITCH_MODEL = "FOHSWITCH"
FRIENDS_OF_HUE_SWITCH = {
    (CONF_SHORT_PRESS, CONF_BUTTON_1): {CONF_EVENT: 1000},
    (CONF_SHORT_RELEASE, CONF_BUTTON_1): {CONF_EVENT: 1002},
    (CONF_LONG_PRESS, CONF_BUTTON_1): {CONF_EVENT: 1001},
    (CONF_LONG_RELEASE, CONF_BUTTON_1): {CONF_EVENT: 1003},
    (CONF_SHORT_PRESS, CONF_BUTTON_2): {CONF_EVENT: 2000},
    (CONF_SHORT_RELEASE, CONF_BUTTON_2): {CONF_EVENT: 2002},
    (CONF_LONG_PRESS, CONF_BUTTON_2): {CONF_EVENT: 2001},
    (CONF_LONG_RELEASE, CONF_BUTTON_2): {CONF_EVENT: 2003},
    (CONF_SHORT_PRESS, CONF_BUTTON_3): {CONF_EVENT: 3000},
    (CONF_SHORT_RELEASE, CONF_BUTTON_3): {CONF_EVENT: 3002},
    (CONF_LONG_PRESS, CONF_BUTTON_3): {CONF_EVENT: 3001},
    (CONF_LONG_RELEASE, CONF_BUTTON_3): {CONF_EVENT: 3003},
    (CONF_SHORT_PRESS, CONF_BUTTON_4): {CONF_EVENT: 4000},
    (CONF_SHORT_RELEASE, CONF_BUTTON_4): {CONF_EVENT: 4002},
    (CONF_LONG_PRESS, CONF_BUTTON_4): {CONF_EVENT: 4001},
    (CONF_LONG_RELEASE, CONF_BUTTON_4): {CONF_EVENT: 4003},
    (CONF_SHORT_PRESS, CONF_TOP_BUTTONS): {CONF_EVENT: 5000},
    (CONF_SHORT_RELEASE, CONF_TOP_BUTTONS): {CONF_EVENT: 5002},
    (CONF_LONG_PRESS, CONF_TOP_BUTTONS): {CONF_EVENT: 5001},
    (CONF_LONG_RELEASE, CONF_TOP_BUTTONS): {CONF_EVENT: 5003},
    (CONF_SHORT_PRESS, CONF_BOTTOM_BUTTONS): {CONF_EVENT: 6000},
    (CONF_SHORT_RELEASE, CONF_BOTTOM_BUTTONS): {CONF_EVENT: 6002},
    (CONF_LONG_PRESS, CONF_BOTTOM_BUTTONS): {CONF_EVENT: 6001},
    (CONF_LONG_RELEASE, CONF_BOTTOM_BUTTONS): {CONF_EVENT: 6003},
}

STYRBAR_REMOTE_MODEL = "Remote Control N2"
STYRBAR_REMOTE = {
    (CONF_SHORT_RELEASE, CONF_DIM_UP): {CONF_EVENT: 1002},
    (CONF_LONG_PRESS, CONF_DIM_UP): {CONF_EVENT: 1001},
    (CONF_LONG_RELEASE, CONF_DIM_UP): {CONF_EVENT: 1003},
    (CONF_SHORT_RELEASE, CONF_DIM_DOWN): {CONF_EVENT: 2002},
    (CONF_LONG_PRESS, CONF_DIM_DOWN): {CONF_EVENT: 2001},
    (CONF_LONG_RELEASE, CONF_DIM_DOWN): {CONF_EVENT: 2003},
    (CONF_SHORT_RELEASE, CONF_LEFT): {CONF_EVENT: 3002},
    (CONF_LONG_PRESS, CONF_LEFT): {CONF_EVENT: 3001},
    (CONF_LONG_RELEASE, CONF_LEFT): {CONF_EVENT: 3003},
    (CONF_SHORT_RELEASE, CONF_RIGHT): {CONF_EVENT: 4002},
    (CONF_LONG_PRESS, CONF_RIGHT): {CONF_EVENT: 4001},
    (CONF_LONG_RELEASE, CONF_RIGHT): {CONF_EVENT: 4003},
}

SYMFONISK_SOUND_CONTROLLER_MODEL = "SYMFONISK Sound Controller"
SYMFONISK_SOUND_CONTROLLER = {
    (CONF_SHORT_PRESS, CONF_TURN_ON): {CONF_EVENT: 1002},
    (CONF_DOUBLE_PRESS, CONF_TURN_ON): {CONF_EVENT: 1004},
    (CONF_TRIPLE_PRESS, CONF_TURN_ON): {CONF_EVENT: 1005},
    (CONF_ROTATED, CONF_LEFT): {CONF_EVENT: 2001},
    (CONF_ROTATION_STOPPED, CONF_LEFT): {CONF_EVENT: 2003},
    (CONF_ROTATED, CONF_RIGHT): {CONF_EVENT: 3001},
    (CONF_ROTATION_STOPPED, CONF_RIGHT): {CONF_EVENT: 3003},
}

TRADFRI_ON_OFF_SWITCH_MODEL = "TRADFRI on/off switch"
TRADFRI_ON_OFF_SWITCH = {
    (CONF_SHORT_PRESS, CONF_TURN_ON): {CONF_EVENT: 1002},
    (CONF_LONG_PRESS, CONF_TURN_ON): {CONF_EVENT: 1001},
    (CONF_LONG_RELEASE, CONF_TURN_ON): {CONF_EVENT: 1003},
    (CONF_SHORT_PRESS, CONF_TURN_OFF): {CONF_EVENT: 2002},
    (CONF_LONG_PRESS, CONF_TURN_OFF): {CONF_EVENT: 2001},
    (CONF_LONG_RELEASE, CONF_TURN_OFF): {CONF_EVENT: 2003},
}

TRADFRI_OPEN_CLOSE_REMOTE_MODEL = "TRADFRI open/close remote"
TRADFRI_OPEN_CLOSE_REMOTE = {
    (CONF_SHORT_PRESS, CONF_OPEN): {CONF_EVENT: 1002},
    (CONF_LONG_PRESS, CONF_OPEN): {CONF_EVENT: 1003},
    (CONF_SHORT_PRESS, CONF_CLOSE): {CONF_EVENT: 2002},
    (CONF_LONG_PRESS, CONF_CLOSE): {CONF_EVENT: 2003},
}

TRADFRI_REMOTE_MODEL = "TRADFRI remote control"
TRADFRI_REMOTE = {
    (CONF_SHORT_PRESS, CONF_TURN_ON): {CONF_EVENT: 1002},
    (CONF_LONG_PRESS, CONF_TURN_ON): {CONF_EVENT: 1001},
    (CONF_SHORT_PRESS, CONF_DIM_UP): {CONF_EVENT: 2002},
    (CONF_LONG_PRESS, CONF_DIM_UP): {CONF_EVENT: 2001},
    (CONF_LONG_RELEASE, CONF_DIM_UP): {CONF_EVENT: 2003},
    (CONF_SHORT_PRESS, CONF_DIM_DOWN): {CONF_EVENT: 3002},
    (CONF_LONG_PRESS, CONF_DIM_DOWN): {CONF_EVENT: 3001},
    (CONF_LONG_RELEASE, CONF_DIM_DOWN): {CONF_EVENT: 3003},
    (CONF_SHORT_PRESS, CONF_LEFT): {CONF_EVENT: 4002},
    (CONF_LONG_PRESS, CONF_LEFT): {CONF_EVENT: 4001},
    (CONF_LONG_RELEASE, CONF_LEFT): {CONF_EVENT: 4003},
    (CONF_SHORT_PRESS, CONF_RIGHT): {CONF_EVENT: 5002},
    (CONF_LONG_PRESS, CONF_RIGHT): {CONF_EVENT: 5001},
    (CONF_LONG_RELEASE, CONF_RIGHT): {CONF_EVENT: 5003},
}

TRADFRI_SHORTCUT_REMOTE_MODEL = "TRADFRI SHORTCUT Button"
TRADFRI_SHORTCUT_REMOTE = {
    (CONF_SHORT_PRESS, ""): {CONF_EVENT: 1002},
    (CONF_LONG_PRESS, ""): {CONF_EVENT: 1001},
    (CONF_LONG_RELEASE, ""): {CONF_EVENT: 1003},
}

TRADFRI_WIRELESS_DIMMER_MODEL = "TRADFRI wireless dimmer"
TRADFRI_WIRELESS_DIMMER = {
    (CONF_ROTATED_FAST, CONF_LEFT): {CONF_EVENT: 4002},
    (CONF_ROTATED, CONF_LEFT): {CONF_EVENT: 3002},
    (CONF_ROTATED, CONF_RIGHT): {CONF_EVENT: 2002},
    (CONF_ROTATED_FAST, CONF_RIGHT): {CONF_EVENT: 1002},
}

AQARA_CUBE_MODEL = "lumi.sensor_cube"
AQARA_CUBE_MODEL_ALT1 = "lumi.sensor_cube.aqgl01"
AQARA_CUBE = {
    (CONF_ROTATE_FROM_SIDE_1, CONF_SIDE_2): {CONF_EVENT: 2001},
    (CONF_ROTATE_FROM_SIDE_1, CONF_SIDE_3): {CONF_EVENT: 3001},
    (CONF_ROTATE_FROM_SIDE_1, CONF_SIDE_4): {CONF_EVENT: 4001},
    (CONF_ROTATE_FROM_SIDE_1, CONF_SIDE_5): {CONF_EVENT: 5001},
    (CONF_ROTATE_FROM_SIDE_1, CONF_SIDE_6): {CONF_EVENT: 6001},
    (CONF_ROTATE_FROM_SIDE_2, CONF_SIDE_1): {CONF_EVENT: 1002},
    (CONF_ROTATE_FROM_SIDE_2, CONF_SIDE_3): {CONF_EVENT: 3002},
    (CONF_ROTATE_FROM_SIDE_2, CONF_SIDE_4): {CONF_EVENT: 4002},
    (CONF_ROTATE_FROM_SIDE_2, CONF_SIDE_5): {CONF_EVENT: 5002},
    (CONF_ROTATE_FROM_SIDE_2, CONF_SIDE_6): {CONF_EVENT: 6002},
    (CONF_ROTATE_FROM_SIDE_3, CONF_SIDE_1): {CONF_EVENT: 1003},
    (CONF_ROTATE_FROM_SIDE_3, CONF_SIDE_2): {CONF_EVENT: 2003},
    (CONF_ROTATE_FROM_SIDE_3, CONF_SIDE_4): {CONF_EVENT: 4003},
    (CONF_ROTATE_FROM_SIDE_3, CONF_SIDE_5): {CONF_EVENT: 5003},
    (CONF_ROTATE_FROM_SIDE_3, CONF_SIDE_6): {CONF_EVENT: 6003},
    (CONF_ROTATE_FROM_SIDE_4, CONF_SIDE_1): {CONF_EVENT: 1004},
    (CONF_ROTATE_FROM_SIDE_4, CONF_SIDE_2): {CONF_EVENT: 2004},
    (CONF_ROTATE_FROM_SIDE_4, CONF_SIDE_3): {CONF_EVENT: 3004},
    (CONF_ROTATE_FROM_SIDE_4, CONF_SIDE_5): {CONF_EVENT: 5004},
    (CONF_ROTATE_FROM_SIDE_4, CONF_SIDE_6): {CONF_EVENT: 6004},
    (CONF_ROTATE_FROM_SIDE_5, CONF_SIDE_1): {CONF_EVENT: 1005},
    (CONF_ROTATE_FROM_SIDE_5, CONF_SIDE_2): {CONF_EVENT: 2005},
    (CONF_ROTATE_FROM_SIDE_5, CONF_SIDE_3): {CONF_EVENT: 3005},
    (CONF_ROTATE_FROM_SIDE_5, CONF_SIDE_4): {CONF_EVENT: 4005},
    (CONF_ROTATE_FROM_SIDE_5, CONF_SIDE_6): {CONF_EVENT: 6005},
    (CONF_ROTATE_FROM_SIDE_6, CONF_SIDE_1): {CONF_EVENT: 1006},
    (CONF_ROTATE_FROM_SIDE_6, CONF_SIDE_2): {CONF_EVENT: 2006},
    (CONF_ROTATE_FROM_SIDE_6, CONF_SIDE_3): {CONF_EVENT: 3006},
    (CONF_ROTATE_FROM_SIDE_6, CONF_SIDE_4): {CONF_EVENT: 4006},
    (CONF_ROTATE_FROM_SIDE_6, CONF_SIDE_5): {CONF_EVENT: 5006},
    (CONF_MOVE, CONF_SIDE_1): {CONF_EVENT: 1000},
    (CONF_MOVE, CONF_SIDE_2): {CONF_EVENT: 2000},
    (CONF_MOVE, CONF_SIDE_3): {CONF_EVENT: 3000},
    (CONF_MOVE, CONF_SIDE_4): {CONF_EVENT: 4000},
    (CONF_MOVE, CONF_SIDE_5): {CONF_EVENT: 5000},
    (CONF_MOVE, CONF_SIDE_6): {CONF_EVENT: 6000},
    (CONF_DOUBLE_TAP, CONF_SIDE_1): {CONF_EVENT: 1001},
    (CONF_DOUBLE_TAP, CONF_SIDE_2): {CONF_EVENT: 2002},
    (CONF_DOUBLE_TAP, CONF_SIDE_3): {CONF_EVENT: 3003},
    (CONF_DOUBLE_TAP, CONF_SIDE_4): {CONF_EVENT: 4004},
    (CONF_DOUBLE_TAP, CONF_SIDE_5): {CONF_EVENT: 5005},
    (CONF_DOUBLE_TAP, CONF_SIDE_6): {CONF_EVENT: 6006},
    (CONF_AWAKE, ""): {CONF_GESTURE: 0},
    (CONF_SHAKE, ""): {CONF_GESTURE: 1},
    (CONF_FREE_FALL, ""): {CONF_GESTURE: 2},
    (CONF_FLIP_90, ""): {CONF_GESTURE: 3},
    (CONF_FLIP_180, ""): {CONF_GESTURE: 4},
    (CONF_MOVE_ANY, ""): {CONF_GESTURE: 5},
    (CONF_DOUBLE_TAP_ANY, ""): {CONF_GESTURE: 6},
    (CONF_TURN_CW, ""): {CONF_GESTURE: 7},
    (CONF_TURN_CCW, ""): {CONF_GESTURE: 8},
}

AQARA_DOUBLE_WALL_SWITCH_MODEL = "lumi.remote.b286acn01"
AQARA_DOUBLE_WALL_SWITCH_MODEL_2020 = "lumi.remote.b286acn02"
AQARA_DOUBLE_WALL_SWITCH = {
    (CONF_SHORT_PRESS, CONF_LEFT): {CONF_EVENT: 1002},
    (CONF_LONG_PRESS, CONF_LEFT): {CONF_EVENT: 1001},
    (CONF_DOUBLE_PRESS, CONF_LEFT): {CONF_EVENT: 1004},
    (CONF_SHORT_PRESS, CONF_RIGHT): {CONF_EVENT: 2002},
    (CONF_LONG_PRESS, CONF_RIGHT): {CONF_EVENT: 2001},
    (CONF_DOUBLE_PRESS, CONF_RIGHT): {CONF_EVENT: 2004},
    (CONF_SHORT_PRESS, CONF_BOTH_BUTTONS): {CONF_EVENT: 3002},
    (CONF_LONG_PRESS, CONF_BOTH_BUTTONS): {CONF_EVENT: 3001},
    (CONF_DOUBLE_PRESS, CONF_BOTH_BUTTONS): {CONF_EVENT: 3004},
}

AQARA_DOUBLE_WALL_SWITCH_WXKG02LM_MODEL = "lumi.sensor_86sw2"
AQARA_DOUBLE_WALL_SWITCH_WXKG02LM = {
    (CONF_SHORT_PRESS, CONF_LEFT): {CONF_EVENT: 1002},
    (CONF_SHORT_PRESS, CONF_RIGHT): {CONF_EVENT: 2002},
    (CONF_SHORT_PRESS, CONF_BOTH_BUTTONS): {CONF_EVENT: 3002},
}

AQARA_DOUBLE_WALL_SWITCH_QBKG12LM_MODEL = "lumi.ctrl_ln2.aq1"
AQARA_DOUBLE_WALL_SWITCH_QBKG12LM = {
    (CONF_SHORT_PRESS, CONF_LEFT): {CONF_EVENT: 1002},
    (CONF_DOUBLE_PRESS, CONF_LEFT): {CONF_EVENT: 1004},
    (CONF_SHORT_PRESS, CONF_RIGHT): {CONF_EVENT: 2002},
    (CONF_DOUBLE_PRESS, CONF_RIGHT): {CONF_EVENT: 2004},
    (CONF_SHORT_PRESS, CONF_BOTH_BUTTONS): {CONF_EVENT: 3002},
}

AQARA_SINGLE_WALL_SWITCH_QBKG11LM_MODEL = "lumi.ctrl_ln1.aq1"
AQARA_SINGLE_WALL_SWITCH_QBKG11LM = {
    (CONF_SHORT_PRESS, CONF_TURN_ON): {CONF_EVENT: 1002},
    (CONF_DOUBLE_PRESS, CONF_TURN_ON): {CONF_EVENT: 1004},
}

AQARA_SINGLE_WALL_SWITCH_WXKG03LM_MODEL = "lumi.remote.b186acn01"
AQARA_SINGLE_WALL_SWITCH_WXKG06LM_MODEL = "lumi.remote.b186acn02"
AQARA_SINGLE_WALL_SWITCH = {
    (CONF_SHORT_PRESS, CONF_TURN_ON): {CONF_EVENT: 1002},
    (CONF_LONG_PRESS, CONF_TURN_ON): {CONF_EVENT: 1001},
    (CONF_DOUBLE_PRESS, CONF_TURN_ON): {CONF_EVENT: 1004},
}

AQARA_MINI_SWITCH_MODEL = "lumi.remote.b1acn01"
AQARA_MINI_SWITCH = {
    (CONF_SHORT_PRESS, CONF_TURN_ON): {CONF_EVENT: 1002},
    (CONF_DOUBLE_PRESS, CONF_TURN_ON): {CONF_EVENT: 1004},
    (CONF_LONG_PRESS, CONF_TURN_ON): {CONF_EVENT: 1001},
    (CONF_LONG_RELEASE, CONF_TURN_ON): {CONF_EVENT: 1003},
}


AQARA_ROUND_SWITCH_MODEL = "lumi.sensor_switch"
AQARA_ROUND_SWITCH = {
    (CONF_SHORT_PRESS, CONF_TURN_ON): {CONF_EVENT: 1000},
    (CONF_SHORT_RELEASE, CONF_TURN_ON): {CONF_EVENT: 1002},
    (CONF_DOUBLE_PRESS, CONF_TURN_ON): {CONF_EVENT: 1004},
    (CONF_TRIPLE_PRESS, CONF_TURN_ON): {CONF_EVENT: 1005},
    (CONF_QUADRUPLE_PRESS, CONF_TURN_ON): {CONF_EVENT: 1006},
    (CONF_QUINTUPLE_PRESS, CONF_TURN_ON): {CONF_EVENT: 1010},
    (CONF_LONG_PRESS, CONF_TURN_ON): {CONF_EVENT: 1001},
    (CONF_LONG_RELEASE, CONF_TURN_ON): {CONF_EVENT: 1003},
}

AQARA_SQUARE_SWITCH_MODEL = "lumi.sensor_switch.aq3"
AQARA_SQUARE_SWITCH = {
    (CONF_SHORT_PRESS, CONF_TURN_ON): {CONF_EVENT: 1002},
    (CONF_DOUBLE_PRESS, CONF_TURN_ON): {CONF_EVENT: 1004},
    (CONF_LONG_PRESS, CONF_TURN_ON): {CONF_EVENT: 1001},
    (CONF_LONG_RELEASE, CONF_TURN_ON): {CONF_EVENT: 1003},
    (CONF_SHAKE, ""): {CONF_EVENT: 1007},
}

AQARA_SQUARE_SWITCH_WXKG11LM_2016_MODEL = "lumi.sensor_switch.aq2"
AQARA_SQUARE_SWITCH_WXKG11LM_2016 = {
    (CONF_SHORT_PRESS, CONF_TURN_ON): {CONF_EVENT: 1002},
    (CONF_DOUBLE_PRESS, CONF_TURN_ON): {CONF_EVENT: 1004},
    (CONF_TRIPLE_PRESS, CONF_TURN_ON): {CONF_EVENT: 1005},
    (CONF_QUADRUPLE_PRESS, CONF_TURN_ON): {CONF_EVENT: 1006},
}

AQARA_OPPLE_2_BUTTONS_MODEL = "lumi.remote.b286opcn01"
AQARA_OPPLE_2_BUTTONS = {
    (CONF_LONG_PRESS, CONF_TURN_OFF): {CONF_EVENT: 1001},
    (CONF_SHORT_RELEASE, CONF_TURN_OFF): {CONF_EVENT: 1002},
    (CONF_LONG_RELEASE, CONF_TURN_OFF): {CONF_EVENT: 1003},
    (CONF_DOUBLE_PRESS, CONF_TURN_OFF): {CONF_EVENT: 1004},
    (CONF_TRIPLE_PRESS, CONF_TURN_OFF): {CONF_EVENT: 1005},
    (CONF_LONG_PRESS, CONF_TURN_ON): {CONF_EVENT: 2001},
    (CONF_SHORT_RELEASE, CONF_TURN_ON): {CONF_EVENT: 2002},
    (CONF_LONG_RELEASE, CONF_TURN_ON): {CONF_EVENT: 2003},
    (CONF_DOUBLE_PRESS, CONF_TURN_ON): {CONF_EVENT: 2004},
    (CONF_TRIPLE_PRESS, CONF_TURN_ON): {CONF_EVENT: 2005},
}

AQARA_OPPLE_4_BUTTONS_MODEL = "lumi.remote.b486opcn01"
AQARA_OPPLE_4_BUTTONS = {
    **AQARA_OPPLE_2_BUTTONS,
    (CONF_LONG_PRESS, CONF_DIM_DOWN): {CONF_EVENT: 3001},
    (CONF_SHORT_RELEASE, CONF_DIM_DOWN): {CONF_EVENT: 3002},
    (CONF_LONG_RELEASE, CONF_DIM_DOWN): {CONF_EVENT: 3003},
    (CONF_DOUBLE_PRESS, CONF_DIM_DOWN): {CONF_EVENT: 3004},
    (CONF_TRIPLE_PRESS, CONF_DIM_DOWN): {CONF_EVENT: 3005},
    (CONF_LONG_PRESS, CONF_DIM_UP): {CONF_EVENT: 4001},
    (CONF_SHORT_RELEASE, CONF_DIM_UP): {CONF_EVENT: 4002},
    (CONF_LONG_RELEASE, CONF_DIM_UP): {CONF_EVENT: 4003},
    (CONF_DOUBLE_PRESS, CONF_DIM_UP): {CONF_EVENT: 4004},
    (CONF_TRIPLE_PRESS, CONF_DIM_UP): {CONF_EVENT: 4005},
}

AQARA_OPPLE_6_BUTTONS_MODEL = "lumi.remote.b686opcn01"
AQARA_OPPLE_6_BUTTONS = {
    **AQARA_OPPLE_4_BUTTONS,
    (CONF_LONG_PRESS, CONF_LEFT): {CONF_EVENT: 5001},
    (CONF_SHORT_RELEASE, CONF_LEFT): {CONF_EVENT: 5002},
    (CONF_LONG_RELEASE, CONF_LEFT): {CONF_EVENT: 5003},
    (CONF_DOUBLE_PRESS, CONF_LEFT): {CONF_EVENT: 5004},
    (CONF_TRIPLE_PRESS, CONF_LEFT): {CONF_EVENT: 5005},
    (CONF_LONG_PRESS, CONF_RIGHT): {CONF_EVENT: 6001},
    (CONF_SHORT_RELEASE, CONF_RIGHT): {CONF_EVENT: 6002},
    (CONF_LONG_RELEASE, CONF_RIGHT): {CONF_EVENT: 6003},
    (CONF_DOUBLE_PRESS, CONF_RIGHT): {CONF_EVENT: 6004},
    (CONF_TRIPLE_PRESS, CONF_RIGHT): {CONF_EVENT: 6005},
}

DRESDEN_ELEKTRONIK_LIGHTING_SWITCH_MODEL = "Lighting Switch"
DRESDEN_ELEKTRONIK_LIGHTING_SWITCH = {
    (CONF_SHORT_RELEASE, CONF_TURN_ON): {CONF_EVENT: 1002},
    (CONF_LONG_PRESS, CONF_TURN_ON): {CONF_EVENT: 1001},
    (CONF_LONG_RELEASE, CONF_TURN_ON): {CONF_EVENT: 1003},
    (CONF_SHORT_RELEASE, CONF_DIM_UP): {CONF_EVENT: 2002},
    (CONF_LONG_PRESS, CONF_DIM_UP): {CONF_EVENT: 2001},
    (CONF_LONG_RELEASE, CONF_DIM_UP): {CONF_EVENT: 2003},
    (CONF_SHORT_RELEASE, CONF_DIM_DOWN): {CONF_EVENT: 3002},
    (CONF_LONG_PRESS, CONF_DIM_DOWN): {CONF_EVENT: 3001},
    (CONF_LONG_RELEASE, CONF_DIM_DOWN): {CONF_EVENT: 3003},
    (CONF_SHORT_RELEASE, CONF_TURN_OFF): {CONF_EVENT: 4002},
    (CONF_LONG_PRESS, CONF_TURN_OFF): {CONF_EVENT: 4001},
    (CONF_LONG_RELEASE, CONF_TURN_OFF): {CONF_EVENT: 4003},
}

DRESDEN_ELEKTRONIK_SCENE_SWITCH_MODEL = "Scene Switch"
DRESDEN_ELEKTRONIK_SCENE_SWITCH = {
    (CONF_SHORT_RELEASE, CONF_TURN_ON): {CONF_EVENT: 1002},
    (CONF_LONG_PRESS, CONF_TURN_ON): {CONF_EVENT: 1001},
    (CONF_LONG_RELEASE, CONF_TURN_ON): {CONF_EVENT: 1003},
    (CONF_SHORT_RELEASE, CONF_DIM_UP): {CONF_EVENT: 2002},
    (CONF_LONG_PRESS, CONF_DIM_UP): {CONF_EVENT: 2001},
    (CONF_LONG_RELEASE, CONF_DIM_UP): {CONF_EVENT: 2003},
    (CONF_SHORT_RELEASE, CONF_BUTTON_1): {CONF_EVENT: 3002},
    (CONF_SHORT_RELEASE, CONF_BUTTON_2): {CONF_EVENT: 4002},
    (CONF_SHORT_RELEASE, CONF_BUTTON_3): {CONF_EVENT: 5002},
    (CONF_SHORT_RELEASE, CONF_BUTTON_4): {CONF_EVENT: 6002},
}

GIRA_JUNG_SWITCH_MODEL = "HS_4f_GJ_1"
GIRA_SWITCH_MODEL = "WS_4f_J_1"
JUNG_SWITCH_MODEL = "WS_3f_G_1"
GIRA_JUNG_SWITCH = {
    (CONF_SHORT_RELEASE, CONF_TURN_ON): {CONF_EVENT: 1002},
    (CONF_LONG_PRESS, CONF_TURN_ON): {CONF_EVENT: 1001},
    (CONF_LONG_RELEASE, CONF_TURN_ON): {CONF_EVENT: 1003},
    (CONF_SHORT_RELEASE, CONF_DIM_UP): {CONF_EVENT: 2002},
    (CONF_LONG_PRESS, CONF_DIM_UP): {CONF_EVENT: 2001},
    (CONF_LONG_RELEASE, CONF_DIM_UP): {CONF_EVENT: 2003},
    (CONF_SHORT_RELEASE, CONF_BUTTON_3): {CONF_EVENT: 3002},
    (CONF_SHORT_RELEASE, CONF_BUTTON_4): {CONF_EVENT: 4002},
    (CONF_SHORT_RELEASE, CONF_BUTTON_5): {CONF_EVENT: 5002},
    (CONF_SHORT_RELEASE, CONF_BUTTON_6): {CONF_EVENT: 6002},
    (CONF_SHORT_RELEASE, CONF_BUTTON_7): {CONF_EVENT: 7002},
    (CONF_SHORT_RELEASE, CONF_BUTTON_8): {CONF_EVENT: 8002},
}

LEGRAND_ZGP_TOGGLE_SWITCH_MODEL = "LEGRANDZGPTOGGLESWITCH"
LEGRAND_ZGP_TOGGLE_SWITCH = {
    (CONF_SHORT_PRESS, CONF_TURN_ON): {CONF_EVENT: 1002},
    (CONF_DOUBLE_PRESS, CONF_TURN_ON): {CONF_EVENT: 1004},
}

LEGRAND_ZGP_SCENE_SWITCH_MODEL = "LEGRANDZGPSCENESWITCH"
LEGRAND_ZGP_SCENE_SWITCH = {
    (CONF_SHORT_PRESS, CONF_BUTTON_1): {CONF_EVENT: 1002},
    (CONF_SHORT_PRESS, CONF_BUTTON_2): {CONF_EVENT: 2002},
    (CONF_SHORT_PRESS, CONF_BUTTON_3): {CONF_EVENT: 3002},
    (CONF_SHORT_PRESS, CONF_BUTTON_4): {CONF_EVENT: 4002},
}

LIDL_SILVERCREST_DOORBELL_MODEL = "HG06668"
LIDL_SILVERCREST_DOORBELL_MODEL_2 = "TS0211"
LIDL_SILVERCREST_DOORBELL = {
    (CONF_SHORT_PRESS, ""): {CONF_EVENT: 1002},
}

LIDL_SILVERCREST_BUTTON_REMOTE_MODEL = "TS004F"
LIDL_SILVERCREST_BUTTON_REMOTE = {
    (CONF_SHORT_PRESS, ""): {CONF_EVENT: 1002},
    (CONF_DOUBLE_PRESS, ""): {CONF_EVENT: 1004},
}

LIGHTIFIY_FOUR_BUTTON_REMOTE_MODEL = "Switch-LIGHTIFY"
LIGHTIFIY_FOUR_BUTTON_REMOTE_4X_MODEL = "Switch 4x-LIGHTIFY"
LIGHTIFIY_FOUR_BUTTON_REMOTE_4X_EU_MODEL = "Switch 4x EU-LIGHTIFY"
LIGHTIFIY_FOUR_BUTTON_REMOTE = {
    (CONF_SHORT_RELEASE, CONF_TURN_ON): {CONF_EVENT: 1002},
    (CONF_LONG_PRESS, CONF_TURN_ON): {CONF_EVENT: 1001},
    (CONF_LONG_RELEASE, CONF_TURN_ON): {CONF_EVENT: 1003},
    (CONF_SHORT_RELEASE, CONF_DIM_UP): {CONF_EVENT: 2002},
    (CONF_LONG_PRESS, CONF_DIM_UP): {CONF_EVENT: 2001},
    (CONF_LONG_RELEASE, CONF_DIM_UP): {CONF_EVENT: 2003},
    (CONF_SHORT_RELEASE, CONF_DIM_DOWN): {CONF_EVENT: 3002},
    (CONF_LONG_PRESS, CONF_DIM_DOWN): {CONF_EVENT: 3001},
    (CONF_LONG_RELEASE, CONF_DIM_DOWN): {CONF_EVENT: 3003},
    (CONF_SHORT_RELEASE, CONF_TURN_OFF): {CONF_EVENT: 4002},
    (CONF_LONG_PRESS, CONF_TURN_OFF): {CONF_EVENT: 4001},
    (CONF_LONG_RELEASE, CONF_TURN_OFF): {CONF_EVENT: 4003},
}

BUSCH_JAEGER_REMOTE_1_MODEL = "RB01"
BUSCH_JAEGER_REMOTE_2_MODEL = "RM01"
BUSCH_JAEGER_REMOTE = {
    (CONF_SHORT_RELEASE, CONF_BUTTON_1): {CONF_EVENT: 1002},
    (CONF_LONG_PRESS, CONF_BUTTON_1): {CONF_EVENT: 1001},
    (CONF_LONG_RELEASE, CONF_BUTTON_1): {CONF_EVENT: 1003},
    (CONF_SHORT_RELEASE, CONF_BUTTON_2): {CONF_EVENT: 2002},
    (CONF_LONG_PRESS, CONF_BUTTON_2): {CONF_EVENT: 2001},
    (CONF_LONG_RELEASE, CONF_BUTTON_2): {CONF_EVENT: 2003},
    (CONF_SHORT_RELEASE, CONF_BUTTON_3): {CONF_EVENT: 3002},
    (CONF_LONG_PRESS, CONF_BUTTON_3): {CONF_EVENT: 3001},
    (CONF_LONG_RELEASE, CONF_BUTTON_3): {CONF_EVENT: 3003},
    (CONF_SHORT_RELEASE, CONF_BUTTON_4): {CONF_EVENT: 4002},
    (CONF_LONG_PRESS, CONF_BUTTON_4): {CONF_EVENT: 4001},
    (CONF_LONG_RELEASE, CONF_BUTTON_4): {CONF_EVENT: 4003},
    (CONF_SHORT_RELEASE, CONF_BUTTON_5): {CONF_EVENT: 5002},
    (CONF_LONG_PRESS, CONF_BUTTON_5): {CONF_EVENT: 5001},
    (CONF_LONG_RELEASE, CONF_BUTTON_5): {CONF_EVENT: 5003},
    (CONF_SHORT_RELEASE, CONF_BUTTON_6): {CONF_EVENT: 6002},
    (CONF_LONG_PRESS, CONF_BUTTON_6): {CONF_EVENT: 6001},
    (CONF_LONG_RELEASE, CONF_BUTTON_6): {CONF_EVENT: 6003},
    (CONF_SHORT_RELEASE, CONF_BUTTON_7): {CONF_EVENT: 7002},
    (CONF_LONG_PRESS, CONF_BUTTON_7): {CONF_EVENT: 7001},
    (CONF_LONG_RELEASE, CONF_BUTTON_7): {CONF_EVENT: 7003},
    (CONF_SHORT_RELEASE, CONF_BUTTON_8): {CONF_EVENT: 8002},
    (CONF_LONG_PRESS, CONF_BUTTON_8): {CONF_EVENT: 8001},
    (CONF_LONG_RELEASE, CONF_BUTTON_8): {CONF_EVENT: 8003},
}

SONOFF_SNZB_01_1_MODEL = "WB01"
SONOFF_SNZB_01_2_MODEL = "WB-01"
SONOFF_SNZB_01P_MODEL = "SNZB-01P"
SONOFF_SNZB_01_SWITCH = {
    (CONF_SHORT_RELEASE, CONF_BUTTON_1): {CONF_EVENT: 1002},
    (CONF_LONG_RELEASE, CONF_BUTTON_1): {CONF_EVENT: 1003},
    (CONF_DOUBLE_PRESS, CONF_BUTTON_1): {CONF_EVENT: 1004},
}

TRUST_ZYCT_202_MODEL = "ZYCT-202"
TRUST_ZYCT_202_ZLL_MODEL = "ZLL-NonColorController"
TRUST_ZYCT_202 = {
    (CONF_SHORT_RELEASE, CONF_BUTTON_1): {CONF_EVENT: 1002},
    (CONF_LONG_PRESS, CONF_BUTTON_2): {CONF_EVENT: 2001},
    (CONF_LONG_RELEASE, CONF_BUTTON_2): {CONF_EVENT: 2003},
    (CONF_LONG_PRESS, CONF_BUTTON_3): {CONF_EVENT: 3001},
    (CONF_LONG_RELEASE, CONF_BUTTON_3): {CONF_EVENT: 3003},
    (CONF_SHORT_RELEASE, CONF_BUTTON_4): {CONF_EVENT: 4002},
}

UBISYS_POWER_SWITCH_S2_MODEL = "S2"
UBISYS_POWER_SWITCH_S2 = {
    (CONF_SHORT_RELEASE, CONF_BUTTON_1): {CONF_EVENT: 1002},
    (CONF_LONG_PRESS, CONF_BUTTON_1): {CONF_EVENT: 1001},
    (CONF_LONG_RELEASE, CONF_BUTTON_1): {CONF_EVENT: 1003},
    (CONF_SHORT_RELEASE, CONF_BUTTON_2): {CONF_EVENT: 2002},
    (CONF_LONG_PRESS, CONF_BUTTON_2): {CONF_EVENT: 2001},
    (CONF_LONG_RELEASE, CONF_BUTTON_2): {CONF_EVENT: 2003},
}

UBISYS_CONTROL_UNIT_C4_MODEL = "C4"
UBISYS_CONTROL_UNIT_C4 = {
    **UBISYS_POWER_SWITCH_S2,
    (CONF_SHORT_RELEASE, CONF_BUTTON_3): {CONF_EVENT: 3002},
    (CONF_LONG_PRESS, CONF_BUTTON_3): {CONF_EVENT: 3001},
    (CONF_LONG_RELEASE, CONF_BUTTON_3): {CONF_EVENT: 3003},
    (CONF_SHORT_RELEASE, CONF_BUTTON_4): {CONF_EVENT: 4002},
    (CONF_LONG_PRESS, CONF_BUTTON_4): {CONF_EVENT: 4001},
    (CONF_LONG_RELEASE, CONF_BUTTON_4): {CONF_EVENT: 4003},
}

REMOTES = {
    HUE_DIMMER_REMOTE_MODEL_GEN1: HUE_DIMMER_REMOTE,
    HUE_DIMMER_REMOTE_MODEL_GEN2: HUE_DIMMER_REMOTE,
    HUE_DIMMER_REMOTE_MODEL_GEN3: HUE_DIMMER_REMOTE,
    HUE_BUTTON_REMOTE_MODEL: HUE_BUTTON_REMOTE,
    HUE_TAP_REMOTE_MODEL: HUE_TAP_REMOTE,
    HUE_WALL_REMOTE_MODEL: HUE_WALL_REMOTE,
    FRIENDS_OF_HUE_SWITCH_MODEL: FRIENDS_OF_HUE_SWITCH,
    STYRBAR_REMOTE_MODEL: STYRBAR_REMOTE,
    SYMFONISK_SOUND_CONTROLLER_MODEL: SYMFONISK_SOUND_CONTROLLER,
    TRADFRI_ON_OFF_SWITCH_MODEL: TRADFRI_ON_OFF_SWITCH,
    TRADFRI_OPEN_CLOSE_REMOTE_MODEL: TRADFRI_OPEN_CLOSE_REMOTE,
    TRADFRI_REMOTE_MODEL: TRADFRI_REMOTE,
    TRADFRI_SHORTCUT_REMOTE_MODEL: TRADFRI_SHORTCUT_REMOTE,
    TRADFRI_WIRELESS_DIMMER_MODEL: TRADFRI_WIRELESS_DIMMER,
    AQARA_CUBE_MODEL: AQARA_CUBE,
    AQARA_CUBE_MODEL_ALT1: AQARA_CUBE,
    AQARA_DOUBLE_WALL_SWITCH_MODEL: AQARA_DOUBLE_WALL_SWITCH,
    AQARA_DOUBLE_WALL_SWITCH_MODEL_2020: AQARA_DOUBLE_WALL_SWITCH,
    AQARA_DOUBLE_WALL_SWITCH_WXKG02LM_MODEL: AQARA_DOUBLE_WALL_SWITCH_WXKG02LM,
    AQARA_DOUBLE_WALL_SWITCH_QBKG12LM_MODEL: AQARA_DOUBLE_WALL_SWITCH_QBKG12LM,
    AQARA_SINGLE_WALL_SWITCH_QBKG11LM_MODEL: AQARA_SINGLE_WALL_SWITCH_QBKG11LM,
    AQARA_SINGLE_WALL_SWITCH_WXKG03LM_MODEL: AQARA_SINGLE_WALL_SWITCH,
    AQARA_SINGLE_WALL_SWITCH_WXKG06LM_MODEL: AQARA_SINGLE_WALL_SWITCH,
    AQARA_MINI_SWITCH_MODEL: AQARA_MINI_SWITCH,
    AQARA_ROUND_SWITCH_MODEL: AQARA_ROUND_SWITCH,
    AQARA_SQUARE_SWITCH_MODEL: AQARA_SQUARE_SWITCH,
    AQARA_SQUARE_SWITCH_WXKG11LM_2016_MODEL: AQARA_SQUARE_SWITCH_WXKG11LM_2016,
    AQARA_OPPLE_2_BUTTONS_MODEL: AQARA_OPPLE_2_BUTTONS,
    AQARA_OPPLE_4_BUTTONS_MODEL: AQARA_OPPLE_4_BUTTONS,
    AQARA_OPPLE_6_BUTTONS_MODEL: AQARA_OPPLE_6_BUTTONS,
    DRESDEN_ELEKTRONIK_LIGHTING_SWITCH_MODEL: DRESDEN_ELEKTRONIK_LIGHTING_SWITCH,
    DRESDEN_ELEKTRONIK_SCENE_SWITCH_MODEL: DRESDEN_ELEKTRONIK_SCENE_SWITCH,
    GIRA_JUNG_SWITCH_MODEL: GIRA_JUNG_SWITCH,
    GIRA_SWITCH_MODEL: GIRA_JUNG_SWITCH,
    JUNG_SWITCH_MODEL: GIRA_JUNG_SWITCH,
    LEGRAND_ZGP_TOGGLE_SWITCH_MODEL: LEGRAND_ZGP_TOGGLE_SWITCH,
    LEGRAND_ZGP_SCENE_SWITCH_MODEL: LEGRAND_ZGP_SCENE_SWITCH,
    LIDL_SILVERCREST_DOORBELL_MODEL: LIDL_SILVERCREST_DOORBELL,
    LIDL_SILVERCREST_DOORBELL_MODEL_2: LIDL_SILVERCREST_DOORBELL,
    LIDL_SILVERCREST_BUTTON_REMOTE_MODEL: LIDL_SILVERCREST_BUTTON_REMOTE,
    LIGHTIFIY_FOUR_BUTTON_REMOTE_MODEL: LIGHTIFIY_FOUR_BUTTON_REMOTE,
    LIGHTIFIY_FOUR_BUTTON_REMOTE_4X_MODEL: LIGHTIFIY_FOUR_BUTTON_REMOTE,
    LIGHTIFIY_FOUR_BUTTON_REMOTE_4X_EU_MODEL: LIGHTIFIY_FOUR_BUTTON_REMOTE,
    BUSCH_JAEGER_REMOTE_1_MODEL: BUSCH_JAEGER_REMOTE,
    BUSCH_JAEGER_REMOTE_2_MODEL: BUSCH_JAEGER_REMOTE,
    TRUST_ZYCT_202_MODEL: TRUST_ZYCT_202,
    TRUST_ZYCT_202_ZLL_MODEL: TRUST_ZYCT_202,
    UBISYS_POWER_SWITCH_S2_MODEL: UBISYS_POWER_SWITCH_S2,
    UBISYS_CONTROL_UNIT_C4_MODEL: UBISYS_CONTROL_UNIT_C4,
    SONOFF_SNZB_01_1_MODEL: SONOFF_SNZB_01_SWITCH,
    SONOFF_SNZB_01_2_MODEL: SONOFF_SNZB_01_SWITCH,
    SONOFF_SNZB_01P_MODEL: SONOFF_SNZB_01_SWITCH,
}

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {vol.Required(CONF_TYPE): str, vol.Required(CONF_SUBTYPE): str}
)


def _get_deconz_event_from_device(
    hass: HomeAssistant,
    device: dr.DeviceEntry,
) -> DeconzAlarmEvent | DeconzEvent | DeconzPresenceEvent | DeconzRelativeRotaryEvent:
    """Resolve deconz event from device."""
    gateways: dict[str, DeconzHub] = hass.data.get(DOMAIN, {})
    for gateway in gateways.values():
        for deconz_event in gateway.events:
            if device.id == deconz_event.device_id:
                return deconz_event

    raise InvalidDeviceAutomationConfig(
        f'No deconz_event tied to device "{device.name}" found'
    )


async def async_validate_trigger_config(
    hass: HomeAssistant,
    config: ConfigType,
) -> ConfigType:
    """Validate config."""
    config = TRIGGER_SCHEMA(config)

    device_registry = dr.async_get(hass)
    device = device_registry.async_get(config[CONF_DEVICE_ID])

    trigger = (config[CONF_TYPE], config[CONF_SUBTYPE])

    if not device:
        raise InvalidDeviceAutomationConfig(
            f"deCONZ trigger {trigger} device with ID "
            f"{config[CONF_DEVICE_ID]} not found"
        )

    if device.model not in REMOTES or trigger not in REMOTES[device.model]:
        raise InvalidDeviceAutomationConfig(
            f"deCONZ trigger {trigger} is not valid for device "
            f"{device} ({config[CONF_DEVICE_ID]})"
        )

    return config


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: TriggerActionType,
    trigger_info: TriggerInfo,
) -> CALLBACK_TYPE:
    """Listen for state changes based on configuration."""
    event_data: dict[str, int | str] = {}

    device_registry = dr.async_get(hass)
    device = device_registry.devices[config[CONF_DEVICE_ID]]

    deconz_event = _get_deconz_event_from_device(hass, device)
    if event_id := deconz_event.serial:
        event_data[CONF_UNIQUE_ID] = event_id

    if device_model := device.model:
        config_trigger = (config[CONF_TYPE], config[CONF_SUBTYPE])
        event_data |= REMOTES[device_model][config_trigger]

    raw_event_config = {
        event_trigger.CONF_PLATFORM: "event",
        event_trigger.CONF_EVENT_TYPE: CONF_DECONZ_EVENT,
        event_trigger.CONF_EVENT_DATA: event_data,
    }

    event_config = event_trigger.TRIGGER_SCHEMA(raw_event_config)
    return await event_trigger.async_attach_trigger(
        hass, event_config, action, trigger_info, platform_type="device"
    )


async def async_get_triggers(
    hass: HomeAssistant,
    device_id: str,
) -> list[dict[str, str]]:
    """List device triggers.

    Make sure device is a supported remote model.
    Retrieve the deconz event object matching device entry.
    Generate device trigger list.
    """
    device_registry = dr.async_get(hass)
    device = device_registry.devices[device_id]

    if device.model not in REMOTES:
        return []

    triggers = []
    for trigger, subtype in REMOTES[device.model]:
        triggers.append(
            {
                CONF_DEVICE_ID: device_id,
                CONF_DOMAIN: DOMAIN,
                CONF_PLATFORM: "device",
                CONF_TYPE: trigger,
                CONF_SUBTYPE: subtype,
            }
        )

    return triggers
