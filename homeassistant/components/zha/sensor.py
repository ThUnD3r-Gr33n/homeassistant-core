"""Sensors on Zigbee Home Automation networks."""
import logging
import numbers

from homeassistant.components.sensor import (
    DEVICE_CLASS_BATTERY,
    DEVICE_CLASS_HUMIDITY,
    DEVICE_CLASS_ILLUMINANCE,
    DEVICE_CLASS_POWER,
    DEVICE_CLASS_PRESSURE,
    DEVICE_CLASS_TEMPERATURE,
    DOMAIN,
)
from homeassistant.const import ATTR_UNIT_OF_MEASUREMENT, POWER_WATT, TEMP_CELSIUS
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .core.const import (
    CHANNEL_ELECTRICAL_MEASUREMENT,
    CHANNEL_HUMIDITY,
    CHANNEL_ILLUMINANCE,
    CHANNEL_POWER_CONFIGURATION,
    CHANNEL_PRESSURE,
    CHANNEL_SMARTENERGY_METERING,
    CHANNEL_TEMPERATURE,
    DATA_ZHA,
    DATA_ZHA_DISPATCHERS,
    SIGNAL_ATTR_UPDATED,
    SIGNAL_STATE_ATTR,
    ZHA_DISCOVERY_NEW,
)
from .core.registries import SMARTTHINGS_HUMIDITY_CLUSTER, ZHA_ENTITIES, MatchRule
from .entity import ZhaEntity

PARALLEL_UPDATES = 5
_LOGGER = logging.getLogger(__name__)

BATTERY_SIZES = {
    0: "No battery",
    1: "Built in",
    2: "Other",
    3: "AA",
    4: "AAA",
    5: "C",
    6: "D",
    7: "CR2",
    8: "CR123A",
    9: "CR2450",
    10: "CR2032",
    11: "CR1632",
    255: "Unknown",
}

CHANNEL_ST_HUMIDITY_CLUSTER = f"channel_0x{SMARTTHINGS_HUMIDITY_CLUSTER:04x}"


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Old way of setting up Zigbee Home Automation sensors."""
    pass


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Zigbee Home Automation sensor from config entry."""

    async def async_discover(discovery_info):
        await _async_setup_entities(
            hass, config_entry, async_add_entities, [discovery_info]
        )

    unsub = async_dispatcher_connect(
        hass, ZHA_DISCOVERY_NEW.format(DOMAIN), async_discover
    )
    hass.data[DATA_ZHA][DATA_ZHA_DISPATCHERS].append(unsub)

    sensors = hass.data.get(DATA_ZHA, {}).get(DOMAIN)
    if sensors is not None:
        await _async_setup_entities(
            hass, config_entry, async_add_entities, sensors.values()
        )
        del hass.data[DATA_ZHA][DOMAIN]


async def _async_setup_entities(
    hass, config_entry, async_add_entities, discovery_infos
):
    """Set up the ZHA sensors."""
    entities = []
    for discovery_info in discovery_infos:
        entities.append(await make_sensor(discovery_info))

    async_add_entities(entities, update_before_add=True)


async def make_sensor(discovery_info):
    """Create ZHA sensors factory."""

    zha_dev = discovery_info["zha_device"]
    channels = discovery_info["channels"]

    entity = ZHA_ENTITIES.get_entity(DOMAIN, zha_dev, channels, Sensor)
    return entity(**discovery_info)


class Sensor(ZhaEntity):
    """Base ZHA sensor."""

    _decimals = 1
    _device_class = None
    _divisor = 1
    _domain = DOMAIN
    _multiplier = 1
    _unit = None

    def __init__(self, unique_id, zha_device, channels, **kwargs):
        """Init this sensor."""
        super().__init__(unique_id, zha_device, channels, **kwargs)
        self._channel = channels[0]

    async def async_added_to_hass(self):
        """Run when about to be added to hass."""
        await super().async_added_to_hass()
        self._device_state_attributes = await self.async_state_attr_provider()

        await self.async_accept_signal(
            self._channel, SIGNAL_ATTR_UPDATED, self.async_set_state
        )
        await self.async_accept_signal(
            self._channel, SIGNAL_STATE_ATTR, self.async_update_state_attribute
        )

    @property
    def device_class(self) -> str:
        """Return device class from component DEVICE_CLASSES."""
        return self._device_class

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity."""
        return self._unit

    @property
    def state(self) -> str:
        """Return the state of the entity."""
        if self._state is None:
            return None
        if isinstance(self._state, float):
            return str(round(self._state, 2))
        return self._state

    def async_set_state(self, state):
        """Handle state update from channel."""
        if state is not None:
            state = self.formatter(state)
        self._state = state
        self.async_schedule_update_ha_state()

    @callback
    def async_restore_last_state(self, last_state):
        """Restore previous state."""
        self._state = last_state.state
        self._unit = last_state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)

    @callback
    async def async_state_attr_provider(self):
        """Initialize device state attributes."""
        return {}

    def formatter(self, value):
        """Numeric pass-through formatter."""
        if self._decimals > 0:
            return round(
                float(value * self._multiplier) / self._divisor, self._decimals
            )
        return round(float(value * self._multiplier) / self._divisor)


@ZHA_ENTITIES.strict_match(MatchRule(channel_names={CHANNEL_POWER_CONFIGURATION}))
class Battery(Sensor):
    """Battery sensor of power configuration cluster."""

    _device_class = DEVICE_CLASS_BATTERY
    _unit = "%"

    @staticmethod
    def formatter(value):
        """Return the state of the entity."""
        # per zcl specs battery percent is reported at 200% ¯\_(ツ)_/¯
        if not isinstance(value, numbers.Number) or value == -1:
            return value
        value = round(value / 2)
        return value

    async def async_state_attr_provider(self):
        """Return device statr attrs for battery sensors."""
        state_attrs = {}
        battery_size = await self._channel.get_attribute_value("battery_size")
        if battery_size is not None:
            state_attrs["battery_size"] = BATTERY_SIZES.get(battery_size, "Unknown")
        battery_quantity = await self._channel.get_attribute_value("battery_quantity")
        if battery_quantity is not None:
            state_attrs["battery_quantity"] = battery_quantity
        return state_attrs


@ZHA_ENTITIES.strict_match(MatchRule(channel_names={CHANNEL_ELECTRICAL_MEASUREMENT}))
class ElectricalMeasurement(Sensor):
    """Active power measurement."""

    _device_class = DEVICE_CLASS_POWER
    _divisor = 10
    _unit = POWER_WATT

    @property
    def should_poll(self) -> bool:
        """Return True if HA needs to poll for state changes."""
        return True


@ZHA_ENTITIES.strict_match(MatchRule(generic_ids={CHANNEL_ST_HUMIDITY_CLUSTER}))
@ZHA_ENTITIES.strict_match(MatchRule(channel_names={CHANNEL_HUMIDITY}))
class Humidity(Sensor):
    """Humidity sensor."""

    _device_class = DEVICE_CLASS_HUMIDITY
    _divisor = 100
    _unit = "%"


@ZHA_ENTITIES.strict_match(MatchRule(channel_names={CHANNEL_ILLUMINANCE}))
class Illuminance(Sensor):
    """Illuminance Sensor."""

    _device_class = DEVICE_CLASS_ILLUMINANCE
    _unit = "lx"

    @staticmethod
    def formatter(value):
        """Convert Illimination data."""
        return round(pow(10, ((value - 1) / 10000)), 1)


@ZHA_ENTITIES.strict_match(MatchRule(channel_names={CHANNEL_SMARTENERGY_METERING}))
class SmartEnergyMetering(Sensor):
    """Metering sensor."""

    _device_class = DEVICE_CLASS_POWER

    def formatter(self, value):
        """Pass through channel formatter."""
        return self._channel.formatter_function(value)

    @property
    def unit_of_measurement(self):
        """Return Unit of measurement."""
        return self._channel.unit_of_measurement


@ZHA_ENTITIES.strict_match(MatchRule(channel_names={CHANNEL_PRESSURE}))
class Pressure(Sensor):
    """Pressure sensor."""

    _device_class = DEVICE_CLASS_PRESSURE
    _decimals = 0
    _unit = "hPa"


@ZHA_ENTITIES.strict_match(MatchRule(channel_names={CHANNEL_TEMPERATURE}))
class Temperature(Sensor):
    """Temperature Sensor."""

    _device_class = DEVICE_CLASS_TEMPERATURE
    _divisor = 100
    _unit = TEMP_CELSIUS
