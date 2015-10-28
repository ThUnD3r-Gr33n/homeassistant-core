"""
homeassistant.components.sensor.zwave
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Interfaces with Z-Wave sensors.

For more details about the zwave component, please refer to the documentation
at https://home-assistant.io/components/zwave.html
"""
# pylint: disable=import-error
from homeassistant.helpers.event import track_point_in_time
from openzwave.network import ZWaveNetwork
from pydispatch import dispatcher
import datetime
import homeassistant.util.dt as dt_util
import homeassistant.components.zwave as zwave
from homeassistant.helpers.entity import Entity
from homeassistant.const import (
    ATTR_BATTERY_LEVEL, STATE_ON, STATE_OFF,
    TEMP_CELCIUS, TEMP_FAHRENHEIT, ATTR_LOCATION)

PHILIO = '013c'
PHILIO_SLIM_SENSOR = '0002'
PHILIO_SLIM_SENSOR_MOTION = (PHILIO, PHILIO_SLIM_SENSOR, 0)

WORKAROUND_NO_TRIGGER_OFF_EVENT = 'trigger_no_off_event'

SPECIFIC_DEVICE_MAPPINGS = [
    (WORKAROUND_NO_TRIGGER_OFF_EVENT, PHILIO_SLIM_SENSOR_MOTION),
]


def setup_platform(hass, config, add_devices, discovery_info=None):
    """ Sets up Z-Wave sensors. """
    node = zwave.NETWORK.nodes[discovery_info[zwave.ATTR_NODE_ID]]
    value = node.values[discovery_info[zwave.ATTR_VALUE_ID]]

    value.set_change_verified(False)

    # Check workaround mappings for specific devices
    for workaround_definition in SPECIFIC_DEVICE_MAPPINGS:
        workaround, sensor_specification = workaround_definition
        if sensor_specification == (
                value.command_class, value.node.manufacturer_id,
                value.node.manufacturer_id, value.node.manufacturer_id):
            if workaround == WORKAROUND_NO_TRIGGER_OFF_EVENT:
                add_devices([ZWaveTriggerSensor(value, hass)])
                return

    # generic Device mappings
    if value.command_class == zwave.COMMAND_CLASS_SENSOR_BINARY:
        add_devices([ZWaveBinarySensor(value)])

    elif value.command_class == zwave.COMMAND_CLASS_SENSOR_MULTILEVEL:
        add_devices([ZWaveMultilevelSensor(value)])


class ZWaveSensor(Entity):
    """ Represents a Z-Wave sensor. """

    def __init__(self, sensor_value):
        self._value = sensor_value
        self._node = sensor_value.node

        dispatcher.connect(
            self.value_changed, ZWaveNetwork.SIGNAL_VALUE_CHANGED)

    @property
    def should_poll(self):
        """ False because we will push our own state to HA when changed. """
        return False

    @property
    def unique_id(self):
        """ Returns a unique id. """
        return "ZWAVE-{}-{}".format(self._node.node_id, self._value.object_id)

    @property
    def name(self):
        """ Returns the name of the device. """
        name = self._node.name or "{} {}".format(
            self._node.manufacturer_name, self._node.product_name)

        return "{} {}".format(name, self._value.label)

    @property
    def state(self):
        """ Returns the state of the sensor. """
        return self._value.data

    @property
    def state_attributes(self):
        """ Returns the state attributes. """
        attrs = {
            zwave.ATTR_NODE_ID: self._node.node_id,
        }

        battery_level = self._node.get_battery_level()

        if battery_level is not None:
            attrs[ATTR_BATTERY_LEVEL] = battery_level

        location = self._node.location

        if location:
            attrs[ATTR_LOCATION] = location

        return attrs

    @property
    def unit_of_measurement(self):
        return self._value.units

    def value_changed(self, value):
        """ Called when a value has changed on the network. """
        if self._value.value_id == value.value_id:
            self.update_ha_state()


# pylint: disable=too-few-public-methods
class ZWaveBinarySensor(ZWaveSensor):
    """ Represents a binary sensor within Z-Wave. """

    @property
    def state(self):
        """ Returns the state of the sensor. """
        return STATE_ON if self._value.data else STATE_OFF


# pylint: disable=too-few-public-methods
class ZWaveTriggerSensor(ZWaveSensor):
    """ Represents a stateless sensor which triggers events within Z-Wave. """

    def __init__(self, sensor_value, hass):
        super(ZWaveTriggerSensor, self).__init__(sensor_value)
        self._hass = hass
        self.invalidate_after = None

    def value_changed(self, value):
        """ Called when a value has changed on the network. """
        if self._value.value_id == value.value_id:
            self.update_ha_state()
            if value.data:
                # only allow this value to be true for 60 secs
                self.invalidate_after = dt_util.utcnow() + datetime.timedelta(
                    seconds=60)
                track_point_in_time(
                    self._hass, self.update_ha_state,
                    self.invalidate_after)

    @property
    def state(self):
        """ Returns the state of the sensor. """
        if not self._value.data or \
                (self.invalidate_after is not None and
                 self.invalidate_after <= dt_util.utcnow()):
            return STATE_OFF

        return STATE_ON


class ZWaveMultilevelSensor(ZWaveSensor):
    """ Represents a multi level sensor Z-Wave sensor. """

    @property
    def state(self):
        """ Returns the state of the sensor. """
        value = self._value.data

        if self._value.units in ('C', 'F'):
            return round(value, 1)
        elif isinstance(value, float):
            return round(value, 2)

        return value

    @property
    def unit_of_measurement(self):
        unit = self._value.units

        if unit == 'C':
            return TEMP_CELCIUS
        elif unit == 'F':
            return TEMP_FAHRENHEIT
        else:
            return unit
