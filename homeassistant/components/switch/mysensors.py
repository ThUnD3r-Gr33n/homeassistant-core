"""
Support for MySensors switches.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/switch.mysensors/
"""
import os

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components import mysensors
from homeassistant.components.switch import DOMAIN, SwitchDevice
from homeassistant.config import load_yaml_config_file
from homeassistant.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON

ATTR_IR_CODE = 'V_IR_SEND'
SERVICE_SEND_IR_CODE = 'mysensors_send_ir_code'

SEND_IR_CODE_SERVICE_SCHEMA = vol.Schema({
    vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
    vol.Required(ATTR_IR_CODE): cv.string,
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the mysensors platform for switches."""
    device_class_map = {
        'S_DOOR': MySensorsSwitch,
        'S_MOTION': MySensorsSwitch,
        'S_SMOKE': MySensorsSwitch,
        'S_LIGHT': MySensorsSwitch,
        'S_LOCK': MySensorsSwitch,
        'S_IR': MySensorsIRSwitch,
        'S_BINARY': MySensorsSwitch,
        'S_SPRINKLER': MySensorsSwitch,
        'S_WATER_LEAK': MySensorsSwitch,
        'S_SOUND': MySensorsSwitch,
        'S_VIBRATION': MySensorsSwitch,
        'S_MOISTURE': MySensorsSwitch,
        'S_WATER_QUALITY': MySensorsSwitch,
    }
    new_devices = mysensors.setup_mysensors_platform(
        hass, DOMAIN, discovery_info, device_class_map)
    if not new_devices:
        return
    add_devices(new_devices.values(), True)

    def send_ir_code_service(service):
        """Set IR code as device state attribute."""
        entity_ids = service.data.get(ATTR_ENTITY_ID)
        ir_code = service.data.get(ATTR_IR_CODE)
        devices = mysensors.get_mysensors_devices(hass, DOMAIN)

        if entity_ids:
            _devices = [device for device in devices.values()
                        if isinstance(device, MySensorsIRSwitch) and
                        device.entity_id in entity_ids]
        else:
            _devices = [device for device in devices.values()
                        if isinstance(device, MySensorsIRSwitch)]

        kwargs = {ATTR_IR_CODE: ir_code}
        for device in _devices:
            device.turn_on(**kwargs)

    descriptions = load_yaml_config_file(
        os.path.join(os.path.dirname(__file__), 'services.yaml'))

    hass.services.register(DOMAIN, SERVICE_SEND_IR_CODE,
                           send_ir_code_service,
                           descriptions.get(SERVICE_SEND_IR_CODE),
                           schema=SEND_IR_CODE_SERVICE_SCHEMA)


class MySensorsSwitch(mysensors.MySensorsEntity, SwitchDevice):
    """Representation of the value of a MySensors Switch child node."""

    @property
    def assumed_state(self):
        """Return True if unable to access real state of entity."""
        return self.gateway.optimistic

    @property
    def is_on(self):
        """Return True if switch is on."""
        return self._values.get(self.value_type) == STATE_ON

    def turn_on(self, **kwargs):
        """Turn the switch on."""
        self.gateway.set_child_value(
            self.node_id, self.child_id, self.value_type, 1)
        if self.gateway.optimistic:
            # optimistically assume that switch has changed state
            self._values[self.value_type] = STATE_ON
            self.schedule_update_ha_state()

    def turn_off(self, **kwargs):
        """Turn the switch off."""
        self.gateway.set_child_value(
            self.node_id, self.child_id, self.value_type, 0)
        if self.gateway.optimistic:
            # optimistically assume that switch has changed state
            self._values[self.value_type] = STATE_OFF
            self.schedule_update_ha_state()


class MySensorsIRSwitch(MySensorsSwitch):
    """IR switch child class to MySensorsSwitch."""

    def __init__(self, *args):
        """Set up instance attributes."""
        super().__init__(*args)
        self._ir_code = None

    @property
    def is_on(self):
        """Return True if switch is on."""
        set_req = self.gateway.const.SetReq
        return self._values.get(set_req.V_LIGHT) == STATE_ON

    def turn_on(self, **kwargs):
        """Turn the IR switch on."""
        set_req = self.gateway.const.SetReq
        if ATTR_IR_CODE in kwargs:
            self._ir_code = kwargs[ATTR_IR_CODE]
        self.gateway.set_child_value(
            self.node_id, self.child_id, self.value_type, self._ir_code)
        self.gateway.set_child_value(
            self.node_id, self.child_id, set_req.V_LIGHT, 1)
        if self.gateway.optimistic:
            # optimistically assume that switch has changed state
            self._values[self.value_type] = self._ir_code
            self._values[set_req.V_LIGHT] = STATE_ON
            self.schedule_update_ha_state()
            # turn off switch after switch was turned on
            self.turn_off()

    def turn_off(self, **kwargs):
        """Turn the IR switch off."""
        set_req = self.gateway.const.SetReq
        self.gateway.set_child_value(
            self.node_id, self.child_id, set_req.V_LIGHT, 0)
        if self.gateway.optimistic:
            # optimistically assume that switch has changed state
            self._values[set_req.V_LIGHT] = STATE_OFF
            self.schedule_update_ha_state()

    def update(self):
        """Update the controller with the latest value from a sensor."""
        super().update()
        self._ir_code = self._values.get(self.value_type)
