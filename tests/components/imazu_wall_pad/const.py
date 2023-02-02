"""Constants for the Imazu Wall Pad tests."""

from homeassistant.const import CONF_HOST, CONF_PORT

IP = "127.0.0.1"
PORT = 8899

USER_INPUT_DATA = {CONF_HOST: IP, CONF_PORT: PORT}

UNSUPPORTED_DEVICE_PACKET = "f70b014b0440110002e1ee"

LIGHT_TEST_ENTITY_ID = "light.imazu_1_light_1_1"
LIGHT_STATE_OFF_PACKET = "f70b01190440110002b3ee"
LIGHT_STATE_ON_PACKET = "f70b01190440110001b0ee"
