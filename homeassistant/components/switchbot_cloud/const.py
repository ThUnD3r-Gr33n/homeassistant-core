"""Constants for the SwitchBot Cloud integration."""

from datetime import timedelta
from typing import Final

DOMAIN: Final = "switchbot_cloud"
ENTRY_TITLE = "SwitchBot Cloud"
DEFAULT_SCAN_INTERVAL = timedelta(seconds=600)

SENSOR_KIND_TEMPERATURE = "temperature"
SENSOR_KIND_HUMIDITY = "humidity"
SENSOR_KIND_BATTERY = "battery"

ATTR_UNIQUE_ID = "unique_id"
ATTR_COMMAND_TYPE = "command_type"
ATTR_COMMAND = "command"
ATTR_COMMAND_PARAMETER = "parameter"
