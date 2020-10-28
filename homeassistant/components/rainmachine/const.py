"""Define constants for the SimpliSafe component."""
DOMAIN = "rainmachine"

CONF_ZONE_RUN_TIME = "zone_run_time"

DATA_CLIENT = "client"
DATA_PROGRAMS = "programs"
DATA_PROVISION_SETTINGS = "provision.settings"
DATA_RESTRICTIONS_CURRENT = "restrictions.current"
DATA_RESTRICTIONS_UNIVERSAL = "restrictions.universal"
DATA_ZONES = "zones"
DATA_ZONES_DETAILS = "zones_details"

DEFAULT_PORT = 8080
DEFAULT_ZONE_RUN = 60 * 10

PROGRAM_UPDATE_TOPIC = f"{DOMAIN}_program_update"
SENSOR_UPDATE_TOPIC = f"{DOMAIN}_data_update"
ZONE_UPDATE_TOPIC = f"{DOMAIN}_zone_update"
