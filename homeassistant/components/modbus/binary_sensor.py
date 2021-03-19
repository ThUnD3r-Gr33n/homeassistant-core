"""Support for Modbus Coil and Discrete Input sensors."""
from __future__ import annotations

import logging

from pymodbus.exceptions import ConnectionException, ModbusException
from pymodbus.pdu import ExceptionResponse
import voluptuous as vol

from homeassistant.components.binary_sensor import (
    DEVICE_CLASSES_SCHEMA,
    PLATFORM_SCHEMA,
    BinarySensorEntity,
)
from homeassistant.const import CONF_ADDRESS, CONF_DEVICE_CLASS, CONF_NAME, CONF_SLAVE
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import (
    ConfigType,
    DiscoveryInfoType,
    HomeAssistantType,
)

from .const import (
    CALL_TYPE_COIL,
    CALL_TYPE_DISCRETE,
    CONF_BINARY_SENSORS,
    CONF_COILS,
    CONF_HUB,
    CONF_INPUT_TYPE,
    CONF_INPUTS,
    DEFAULT_HUB,
    MODBUS_DOMAIN,
)
from .modbus import ModbusHub

_LOGGER = logging.getLogger(__name__)


PLATFORM_SCHEMA = vol.All(
    cv.deprecated(CONF_COILS, CONF_INPUTS),
    PLATFORM_SCHEMA.extend(
        {
            vol.Required(CONF_INPUTS): [
                vol.All(
                    cv.deprecated(CALL_TYPE_COIL, CONF_ADDRESS),
                    vol.Schema(
                        {
                            vol.Required(CONF_ADDRESS): cv.positive_int,
                            vol.Required(CONF_NAME): cv.string,
                            vol.Optional(CONF_DEVICE_CLASS): DEVICE_CLASSES_SCHEMA,
                            vol.Optional(CONF_HUB, default=DEFAULT_HUB): cv.string,
                            vol.Optional(CONF_SLAVE): cv.positive_int,
                            vol.Optional(
                                CONF_INPUT_TYPE, default=CALL_TYPE_COIL
                            ): vol.In([CALL_TYPE_COIL, CALL_TYPE_DISCRETE]),
                        }
                    ),
                )
            ]
        }
    ),
)


async def async_setup_platform(
    hass: HomeAssistantType,
    config: ConfigType,
    async_add_entities,
    discovery_info: DiscoveryInfoType | None = None,
):
    """Set up the Modbus binary sensors."""
    sensors = []

    #  check for old config:
    if discovery_info is None:
        _LOGGER.warning(
            "Binary_sensor configuration depreciated, will be removed in a future release"
        )
        discovery_info = {
            CONF_NAME: "noName",
            CONF_BINARY_SENSORS: config[CONF_INPUTS],
        }
        config = None

    for entry in discovery_info[CONF_BINARY_SENSORS]:
        if CONF_HUB in entry:
            # from old config!
            discovery_info[CONF_NAME] = entry[CONF_HUB]
        hub: ModbusHub = hass.data[MODBUS_DOMAIN][discovery_info[CONF_NAME]]
        sensors.append(
            ModbusBinarySensor(
                hub,
                entry[CONF_NAME],
                entry.get(CONF_SLAVE),
                entry[CONF_ADDRESS],
                entry.get(CONF_DEVICE_CLASS),
                entry[CONF_INPUT_TYPE],
            )
        )

    async_add_entities(sensors)


class ModbusBinarySensor(BinarySensorEntity):
    """Modbus binary sensor."""

    def __init__(self, hub, name, slave, address, device_class, input_type):
        """Initialize the Modbus binary sensor."""
        self._hub = hub
        self._name = name
        self._slave = int(slave) if slave else None
        self._address = int(address)
        self._device_class = device_class
        self._input_type = input_type
        self._value = None
        self._available = True

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def is_on(self):
        """Return the state of the sensor."""
        return self._value

    @property
    def device_class(self) -> str | None:
        """Return the device class of the sensor."""
        return self._device_class

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._available

    def update(self):
        """Update the state of the sensor."""
        try:
            if self._input_type == CALL_TYPE_COIL:
                result = self._hub.read_coils(self._slave, self._address, 1)
            else:
                result = self._hub.read_discrete_inputs(self._slave, self._address, 1)
        except ConnectionException:
            self._available = False
            return

        if isinstance(result, (ModbusException, ExceptionResponse)):
            self._available = False
            return

        self._value = result.bits[0] & 1
        self._available = True
