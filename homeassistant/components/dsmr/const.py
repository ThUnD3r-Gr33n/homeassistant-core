"""Constants for the NEW_NAME integration."""

DOMAIN = "dsmr"

PLATFORMS = ["sensor"]

CONF_DSMR_VERSION = "dsmr_version"
CONF_RECONNECT_INTERVAL = "reconnect_interval"
CONF_PRECISION = "precision"
CONF_POWER_WATT = "power_watt"

CONF_SERIAL_ID = "serial_id"
CONF_SERIAL_ID_GAS = "serial_id_gas"

DEFAULT_DSMR_VERSION = "2.2"
DEFAULT_PORT = "/dev/ttyUSB0"
DEFAULT_PRECISION = 3
DEFAULT_RECONNECT_INTERVAL = 30
DEFAULT_FORCE_UPDATE = False
DEFAULT_POWER_WATT = False

ICON_GAS = "mdi:fire"
ICON_POWER = "mdi:flash"
ICON_POWER_FAILURE = "mdi:flash-off"
ICON_SWELL_SAG = "mdi:pulse"
