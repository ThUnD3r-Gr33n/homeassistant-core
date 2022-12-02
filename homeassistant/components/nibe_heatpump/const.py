"""Constants for the Nibe Heat Pump integration."""
import logging

DOMAIN = "nibe_heatpump"
LOGGER = logging.getLogger(__package__)

CONF_LISTENING_PORT = "listening_port"
CONF_REMOTE_READ_PORT = "remote_read_port"
CONF_REMOTE_WRITE_PORT = "remote_write_port"
CONF_WORD_SWAP = "word_swap"
CONF_CONNECTION_TYPE = "connection_type"
CONF_CONNECTION_TYPE_NIBEGW = "nibegw"
CONF_CONNECTION_TYPE_MODBUS = "modbus"
CONF_MODBUS_URL = "modbus_url"
CONF_MODBUS_UNIT = "modbus_unit"

VALUES_MIXING_VALVE_CLOSED_STATE = (30, "CLOSED", "SHUNT CLOSED")
VALUES_PRIORITY_HEATING = (30, "HEAT")
VALUES_PRIORITY_COOLING = (60, "COOLING")
