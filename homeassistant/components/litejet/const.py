"""LiteJet constants."""
from homeassistant.const import Platform

DOMAIN = "litejet"

CONF_EXCLUDE_NAMES = "exclude_names"
CONF_INCLUDE_SWITCHES = "include_switches"

PLATFORMS = [Platform.LIGHT, Platform.SWITCH, Platform.SCENE]

CONF_DEFAULT_TRANSITION = "default_transition"
