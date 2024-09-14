"""Constants for the madvr-envy integration."""

from enum import Enum

DOMAIN = "madvr"

DEFAULT_NAME = "envy"
DEFAULT_PORT = 44077

# Sensor keys
TEMP_GPU = "temp_gpu"
TEMP_HDMI = "temp_hdmi"
TEMP_CPU = "temp_cpu"
TEMP_MAINBOARD = "temp_mainboard"
INCOMING_RES = "incoming_res"
INCOMING_SIGNAL_TYPE = "incoming_signal_type"
INCOMING_FRAME_RATE = "incoming_frame_rate"
INCOMING_COLOR_SPACE = "incoming_color_space"
INCOMING_BIT_DEPTH = "incoming_bit_depth"
INCOMING_COLORIMETRY = "incoming_colorimetry"
INCOMING_BLACK_LEVELS = "incoming_black_levels"
INCOMING_ASPECT_RATIO = "incoming_aspect_ratio"
OUTGOING_RES = "outgoing_res"
OUTGOING_SIGNAL_TYPE = "outgoing_signal_type"
OUTGOING_FRAME_RATE = "outgoing_frame_rate"
OUTGOING_COLOR_SPACE = "outgoing_color_space"
OUTGOING_BIT_DEPTH = "outgoing_bit_depth"
OUTGOING_COLORIMETRY = "outgoing_colorimetry"
OUTGOING_BLACK_LEVELS = "outgoing_black_levels"
ASPECT_RES = "aspect_res"
ASPECT_DEC = "aspect_dec"
ASPECT_INT = "aspect_int"
ASPECT_NAME = "aspect_name"
MASKING_RES = "masking_res"
MASKING_DEC = "masking_dec"
MASKING_INT = "masking_int"


# Button Commands
class ButtonCommands(Enum):
    """Enum for madvr button commands and names."""

    # these use an enum to make grabbing the value and name one operation
    # internal toggles
    toggle_debugosd = ["Toggle", "DebugOSD"]
    # debug commands
    force1080p60output = ["Force1080p60Output"]
    # power commands
    restart = ["Restart"]
