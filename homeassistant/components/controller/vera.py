from homeassistant.components.sensor import (
    DISCOVER_CHILD_SENSORS, DISCOVER_VERA_SENSORS)
from homeassistant.components.switch import (
    DISCOVER_CHILD_SWITCHES, DISCOVER_VERA_SWITCHES)
from homeassistant.components.light import (
    DISCOVER_CHILD_LIGHTS, ATTR_BRIGHTNESS)
from homeassistant.components.controller import (
    DOMAIN)

from homeassistant.const import (
    EVENT_PLATFORM_DISCOVERED,
    ATTR_DISCOVERED,
    ATTR_SERVICE,
    ATTR_TRIPPED,
    TEMP_CELCIUS,
    TEMP_FAHRENHEIT,
    ATTR_BATTERY_LEVEL,
    ATTR_ARMED,
    STATE_ON,
    ATTR_HIDDEN,
    STATE_NOT_TRIPPED,
    STATE_TRIPPED,
    ATTR_LAST_TRIP_TIME)

import homeassistant.util.dt as dt_util
from homeassistant.components.controller import Controller
from homeassistant.helpers.entity import Entity
# pylint: disable=no-name-in-module, import-error
import homeassistant.external.vera.vera as veraApi

SERVICE_SET_VAL = 'service_set_vera_value'

def setup_platform(hass, config, add_devices_callback, discovery_info=None):

    base_url = config.get('vera_controller_url')
    vera_api = veraApi.VeraController(base_url)
    devices = vera_api.refresh_data()

    vera_controller = VeraController(hass, config, vera_api)
    vera_devices = [vera_controller]

    # device_data = config.get('device_data', {})
    # for key, value in devices.items():
    #     child_config = device_data.get(key, {})
    #     cdev = VeraControllerDevice(hass, child_config, vera_controller, value)
    #     vera_controller.child_devices[key] = cdev
    #     vera_devices.append(cdev)

    add_devices_callback(vera_devices)

    for key, value in vera_controller.child_devices.items():
        value.create_child_devices()

    device_data = config.get('device_data', {})
    for key, value in devices.items():
        child_config = device_data.get(key, {})
        print('-------------------------------------------------------------------------')
        print(child_config)
        if child_config.get('excluded', False):
            continue

        if value.get('categoryName', 'Unkown') in ["On/Off Switch", "Switch", "Dimmable Switch"]:
            data = {}
            data['name'] = child_config.get('name', value.get('name'))
            data['parent_entity_id'] = vera_controller.entity_id
            data['parent_entity_domain'] = DOMAIN
            data['vera_id'] = value.get('id')
            data['state_variable'] = 'status'
            data['config_data'] = child_config
            data['device_data'] = value
            hass.bus.fire(
                EVENT_PLATFORM_DISCOVERED, {
                    ATTR_SERVICE: DISCOVER_VERA_SWITCHES,
                    ATTR_DISCOVERED: data})
        else:
            data = {}
            data['name'] = child_config.get('name', value.get('name'))
            data['parent_entity_id'] = vera_controller.entity_id
            data['vera_id'] = value.get('id')
            child_config['temperature_units'] = child_config.get('temperature_units', vera_controller.temperature_units)
            data['config_data'] = child_config
            data['device_data'] = value
            hass.bus.fire(
                EVENT_PLATFORM_DISCOVERED, {
                    ATTR_SERVICE: DISCOVER_VERA_SENSORS,
                    ATTR_DISCOVERED: data})

    def set_value_service(service):
        device_id = service.data.get('extra_data').get('vera_device_id')
        variable = service.data.get('extra_data').get('vera_variable')

        val = 0
        if service.data.get('action') == 'dim':
            brightness = int(service.data.get(ATTR_BRIGHTNESS))
            val = round((brightness / 255) * 100)
        else:
            state = service.data.get('state')
            if state == STATE_ON:
                val = 1

        vera_controller.vera_api.set_value(device_id, variable, val)

    hass.services.register(DOMAIN, SERVICE_SET_VAL, set_value_service)

class VeraController(Controller):

    def __init__(self, hass, config, vera_api):
        self._state = 0
        self._vera_api = vera_api
        self._name = config.get('name', vera_api.model)
        self.child_devices = {}
        self._vera_device_data = {}

    @property
    def state_attributes(self):
        attr = super().state_attributes
        attr['model'] = self._vera_api.model
        attr['version'] = self._vera_api.version
        attr['serial_number'] = self._vera_api.serial_number
        attr['vera_device_data'] = self._vera_device_data

        return attr

    def update(self):
        """ Update the state of the device """
        devices = self._vera_api.refresh_data()
        for key, value in devices.items():
            if not self.child_devices.get(key, False):
                continue
            self.child_devices.get(key).set_device_data(value)
        self._vera_device_data = devices;

    @property
    def vera_api(self):
        """ Get the Vera API instance. """
        return self._vera_api

    @property
    def name(self):
        """ Get the mame of the Controller. """
        return self._name

    @property
    def state(self):
        return self._state

    @property
    def temperature_units(self):
        """ Get the temperature units of the Controller. """
        return self._vera_api.temperature_units


class VeraControllerDevice(Entity):

    def __init__(self, hass, config, device_data):
        self._state = None
        self._vera_controller = vera_controller
        self._device_data = device_data
        self._name = config.get('name', self._device_data.get('name'))
        self._config = config
        self._hass = hass
        self._state_variable = self._config.get('state_variable', 'id')
        self._parent_entity_id = config.get('parent_entity_id', None)

    @property
    def state_attributes(self):
        attr = super().state_attributes
        attr['vera_id'] = self._device_data.get('id')

        if 'lasttrip' in self._device_data.keys():
            last_trip_dt = dt_util.utc_from_timestamp(
                int(self._device_data.get('lasttrip', 0)))
            attr[ATTR_LAST_TRIP_TIME] = dt_util.datetime_to_str(last_trip_dt)

        if self.has_temperature:
            # pylint: disable=unused-variable
            temp, units = self.get_temperature()
            attr['temperature'] = temp

        if self.is_trippable:
            attr[ATTR_TRIPPED] = 'True' if str(self._device_data.get('tripped')) == '1' else 'False'

        if self.has_battery:
            attr[ATTR_BATTERY_LEVEL] = self._device_data.get('batterylevel')

        if self.has_lightlevel:
            attr['light_level'] = self._device_data.get('light')

        if self.has_humidity:
            attr['humidity'] = self._device_data.get('humidity')

        if self.is_armable:
            attr[ATTR_ARMED] = 'True' if str(self._device_data.get('armed')) == '1' else 'False'

        if self.is_armedtripped:
            attr['armed_tripped'] = (
                'True' if str(self._device_data.get('armedtripped')) == '1'
                else 'False')

        if self.is_switchable:
            attr['status'] = 'True' if str(self._device_data.get('status')) == '1' else 'False'

        if self.is_dimmable:
            attr['status'] = 'True' if str(self._device_data.get('status')) == '1' else 'False'
            attr['level'] = self._device_data.get('level')
            attr[ATTR_BRIGHTNESS] = self.get_brightness()

        attr[ATTR_HIDDEN] = self._config.get('hidden', False)
        if self._parent_entity_id is not None:
            attr['parent_entity_id'] = self._parent_entity_id

        attr['state_variable'] = self._state_variable

        return attr

    def set_device_data(self, device_data):
        self._device_data = device_data
        self.update_ha_state()

    @property
    def name(self):
        """ Get the mame of the Controller. """
        return self._name

    def get_temperature(self):
        """ Get the temperature and units. """
        current_temp = self._device_data.get('temperature')
        vera_temp_units = self._config.get('temperature_units', TEMP_CELCIUS)

        if vera_temp_units == 'F':
            temperature_units = TEMP_FAHRENHEIT
        else:
            temperature_units = TEMP_CELCIUS

        return self._hass.config.temperature(
            current_temp,
            temperature_units)

    @property
    def state(self):
        return self._state

    @property
    def should_poll(self):
        """
        Polling is not required as state is updated from the parent
        """
        return False

    @property
    def is_trippable(self):
        """ Returns true if the device supports a trippable state """
        return True if 'tripped' in self._device_data.keys() else False

    @property
    def is_armable(self):
        """ Returns true if the device supports a armable state """
        return True if 'armed' in self._device_data.keys() else False

    @property
    def is_armedtripped(self):
        """ Returns true if the device is armed and tripped """
        return True if 'armedtripped' in self._device_data.keys() else False

    @property
    def has_battery(self):
        """ Returns true if the device supports battery level """
        return True if 'batterylevel' in self._device_data.keys() else False

    @property
    def has_temperature(self):
        """ Returns true if the device supports temperature level """
        return True if 'temperature' in self._device_data.keys() else False

    @property
    def has_lightlevel(self):
        """ Returns true if the device supports light level """
        return True if 'light' in self._device_data.keys() else False

    @property
    def has_humidity(self):
        """ Returns true if the device has a humidity reading """
        return True if 'humidity' in self._device_data.keys() else False

    @property
    def is_switchable(self):
        """ Returns true if the device supports switching """
        if self.category_name == "On/Off Switch" or self.category_name == "Switch":
            return True
        else:
            return False

    @property
    def is_dimmable(self):
        """ Returns true if the device supports dimming """
        if self.category_name == "Dimmable Switch":
            return True
        else:
            return False

    @property
    def category_name(self):
        """ Returns the vera category name """
        return self._device_data.get('categoryName', 'None')

    # pylint: disable=too-many-statements
    def create_child_devices(self):
        """ Create child devices based on available properties """

        if self.has_temperature and not self.should_exclude_child('temperature'):
            temp, units = self.get_temperature()
            data = {}
            data['name'] = self._config.get('temperature', {}).get('name', self._name)
            data['parent_entity_id'] = self.entity_id
            data['watched_variable'] = 'temperature'
            data['initial_state'] = temp
            data['unit_of_measurement'] = units
            data['state_attributes'] = self.get_common_state_attrs()
            data['state_attributes'][ATTR_HIDDEN] = self.is_child_hidden('temperature')
            self._hass.bus.fire(
                EVENT_PLATFORM_DISCOVERED, {
                    ATTR_SERVICE: DISCOVER_CHILD_SENSORS,
                    ATTR_DISCOVERED: data})

        if self.is_trippable and not self.should_exclude_child('tripped'):
            data = {}
            data['name'] = self._config.get('tripped', {}).get('name', self._name)
            data['parent_entity_id'] = self.entity_id
            data['watched_variable'] = ATTR_TRIPPED
            data['value_map'] = {
                'True': STATE_TRIPPED,
                'False': STATE_NOT_TRIPPED
            }
            data['initial_state'] = (
                'True' if str(self._device_data.get('tripped')) == '1' else 'False')
            data['state_attributes'] = self.get_common_state_attrs()
            data['state_attributes'][ATTR_HIDDEN] = self.is_child_hidden('tripped')
            self._hass.bus.fire(
                EVENT_PLATFORM_DISCOVERED, {
                    ATTR_SERVICE: DISCOVER_CHILD_SENSORS,
                    ATTR_DISCOVERED: data})

        if self.has_battery and not self.should_exclude_child('battery'):
            data = {}
            data['name'] = self._config.get('battery', {}).get('name', self._name + ' Battery')
            data['parent_entity_id'] = self.entity_id
            data['watched_variable'] = ATTR_BATTERY_LEVEL
            data['initial_state'] = self._device_data.get('batterylevel')
            data['unit_of_measurement'] = '%'
            data['state_attributes'] = self.get_common_state_attrs()
            data['state_attributes'][ATTR_HIDDEN] = self.is_child_hidden('battery')
            self._hass.bus.fire(
                EVENT_PLATFORM_DISCOVERED, {
                    ATTR_SERVICE: DISCOVER_CHILD_SENSORS,
                    ATTR_DISCOVERED: data})

        if self.has_humidity and not self.should_exclude_child('humidity'):
            data = {}
            data['name'] = self._config.get('humidity', {}).get('name', self._name)
            data['parent_entity_id'] = self.entity_id
            data['watched_variable'] = 'humidity'
            data['initial_state'] = self._device_data.get('humidity')
            data['unit_of_measurement'] = '%'
            data['state_attributes'] = self.get_common_state_attrs()
            data['state_attributes'][ATTR_HIDDEN] = self.is_child_hidden('humidity')
            self._hass.bus.fire(
                EVENT_PLATFORM_DISCOVERED, {
                    ATTR_SERVICE: DISCOVER_CHILD_SENSORS,
                    ATTR_DISCOVERED: data})

        if self.has_lightlevel and not self.should_exclude_child('lightlevel'):
            data = {}
            data['name'] = self._config.get('lightlevel', {}).get('name', self._name)
            data['parent_entity_id'] = self.entity_id
            data['watched_variable'] = 'light_level'
            data['initial_state'] = self._device_data.get('light')
            data['unit_of_measurement'] = 'lux'
            data['state_attributes'] = self.get_common_state_attrs()
            data['state_attributes'][ATTR_HIDDEN] = self.is_child_hidden('lightlevel')
            self._hass.bus.fire(EVENT_PLATFORM_DISCOVERED, {
                ATTR_SERVICE: DISCOVER_CHILD_SENSORS,
                ATTR_DISCOVERED: data})

        if self.is_armable and not self.should_exclude_child('arm_switch'):
            data = {}
            data['name'] = self._config.get('arm_switch', {}).get('name', self._name)
            data['parent_entity_id'] = self.entity_id
            data['watched_variable'] = ATTR_ARMED
            data['parent_domain'] = DOMAIN
            data['parent_service'] = SERVICE_SET_VAL
            data['parent_action'] = 'set_value'
            data['state_attributes'] = self.get_common_state_attrs()
            data['state_attributes'][ATTR_HIDDEN] = self.is_child_hidden('arm_switch')
            data['extra_data'] = {
                'vera_device_id': self._device_data.get('id'),
                'vera_variable': 'Armed'}

            data['initial_state'] = (
                'True' if str(self._device_data.get('armed')) == '1' else 'False')
            self._hass.bus.fire(
                EVENT_PLATFORM_DISCOVERED, {
                    ATTR_SERVICE: DISCOVER_CHILD_SWITCHES,
                    ATTR_DISCOVERED: data})

        if self.is_switchable and not self.should_exclude_child('switch'):
            data = {}
            data['name'] = self._config.get('switch', {}).get('name', self._name)
            data['parent_entity_id'] = self.entity_id

            data['parent_domain'] = DOMAIN
            data['parent_service'] = SERVICE_SET_VAL

            data['parent_action'] = 'switch'
            data['watched_variable'] = 'status'
            data['extra_data'] = {
                'vera_device_id': self._device_data.get('id'),
                'vera_variable': 'Target'}

            data['state_attributes'] = self.get_common_state_attrs()
            data['state_attributes'][ATTR_HIDDEN] = self.is_child_hidden('switch')
            data['initial_state'] = (
                'True' if str(self._device_data.get('status')) == '1' else 'False')

            child_type = DISCOVER_CHILD_SWITCHES
            if self._config.get('switch', {}).get('is_light', False):
                child_type = DISCOVER_CHILD_LIGHTS

            self._hass.bus.fire(
                EVENT_PLATFORM_DISCOVERED, {
                    ATTR_SERVICE: child_type,
                    ATTR_DISCOVERED: data})

        if self.is_dimmable and not self.should_exclude_child('switch'):
            data = {}
            data['name'] = self._config.get('switch', {}).get('name', self._name)
            data['parent_entity_id'] = self.entity_id

            data['parent_domain'] = DOMAIN
            data['parent_service'] = SERVICE_SET_VAL
            data['parent_action'] = 'dim'
            data['light_type'] = 'dimmer'
            data['state_attributes'] = self.get_common_state_attrs()
            data['state_attributes'][ATTR_HIDDEN] = self.is_child_hidden('switch')
            data['state_attributes']['level'] = self._device_data.get('level')

            brightness = self.get_brightness()
            data['state_attributes'][ATTR_BRIGHTNESS] = brightness
            data['watched_variable'] = ATTR_BRIGHTNESS
            data['extra_data'] = {
                'vera_device_id': self._device_data.get('id'),
                'vera_variable': 'LoadLevelTarget'}

            data['initial_state'] = (
                'True' if str(self._device_data.get('status')) == '1' else 'False')
            data['initial_brightness'] = brightness

            child_type = DISCOVER_CHILD_SWITCHES
            if self._config.get('switch', {}).get('is_light', True):
                child_type = DISCOVER_CHILD_LIGHTS

            self._hass.bus.fire(
                EVENT_PLATFORM_DISCOVERED, {
                    ATTR_SERVICE: child_type,
                    ATTR_DISCOVERED: data})


    def get_common_state_attrs(self):
        attrs = {}
        attrs['vera_id'] = self._device_data.get('id')
        return attrs

    def should_exclude_child(self, type_name):
        if type_name == self._state_variable:
            return True
        elif (type_name == 'switch' and
                self._state_variable == 'status'):
            return True

        return self._config.get(type_name, {}).get('exclude', False)

    def is_child_hidden(self, type_name):
        return self._config.get(type_name, {}).get('hidden', False)

    def get_brightness(self):
        percent = int(self._device_data.get('level', 100))
        brightness = 0
        if percent > 0:
            brightness = round(percent * 2.55)

        return int(brightness)
