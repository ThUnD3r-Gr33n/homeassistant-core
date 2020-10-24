"""Config flow for Tuya."""
import logging

from tuyaha import TuyaApi
from tuyaha.tuyaapi import TuyaAPIException, TuyaNetException, TuyaServerException
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_PLATFORM,
    CONF_UNIT_OF_MEASUREMENT,
    CONF_USERNAME,
    ENTITY_MATCH_NONE,
    TEMP_CELSIUS,
    TEMP_FAHRENHEIT,
)
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

# pylint:disable=unused-import
from .const import (
    CONF_BRIGHTNESS_RANGE_MODE,
    CONF_COUNTRYCODE,
    CONF_CURR_TEMP_DIVIDER,
    CONF_DISCOVERY_INTERVAL,
    CONF_EXT_TEMP_SENSOR,
    CONF_MAX_KELVIN,
    CONF_MAX_TEMP,
    CONF_MIN_KELVIN,
    CONF_MIN_TEMP,
    CONF_QUERY_INTERVAL,
    CONF_SUPPORT_COLOR,
    CONF_TEMP_DIVIDER,
    CONF_TUYA_MAX_COLTEMP,
    DEFAULT_DISCOVERY_INTERVAL,
    DEFAULT_QUERY_INTERVAL,
    DEFAULT_TUYA_MAX_COLTEMP,
    DOMAIN,
    TUYA_DATA,
    TUYA_PLATFORMS,
)

_LOGGER = logging.getLogger(__name__)

CONF_LIST_DEVICES = "list_devices"

DATA_SCHEMA_USER = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_COUNTRYCODE): vol.Coerce(int),
        vol.Required(CONF_PLATFORM): vol.In(TUYA_PLATFORMS),
    }
)

ERROR_DEV_MULTI_TYPE = "dev_multi_type"
ERROR_DEV_NOT_CONFIG = "dev_not_config"
ERROR_DEV_NOT_FOUND = "dev_not_found"

RESULT_AUTH_FAILED = "invalid_auth"
RESULT_CONN_ERROR = "cannot_connect"
RESULT_SUCCESS = "success"

RESULT_LOG_MESSAGE = {
    RESULT_AUTH_FAILED: "Invalid credential",
    RESULT_CONN_ERROR: "Connection error",
}

TUYA_TYPE_CONFIG = ["climate", "light"]


class TuyaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a tuya config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        """Initialize flow."""
        self._country_code = None
        self._password = None
        self._platform = None
        self._username = None
        self._is_import = False

    def _save_entry(self):
        return self.async_create_entry(
            title=self._username,
            data={
                CONF_COUNTRYCODE: self._country_code,
                CONF_PASSWORD: self._password,
                CONF_PLATFORM: self._platform,
                CONF_USERNAME: self._username,
            },
        )

    def _try_connect(self):
        """Try to connect and check auth."""
        tuya = TuyaApi()
        try:
            tuya.init(
                self._username, self._password, self._country_code, self._platform
            )
        except (TuyaNetException, TuyaServerException):
            return RESULT_CONN_ERROR
        except TuyaAPIException:
            return RESULT_AUTH_FAILED

        return RESULT_SUCCESS

    async def async_step_import(self, user_input=None):
        """Handle configuration by yaml file."""
        self._is_import = True
        return await self.async_step_user(user_input)

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        errors = {}

        if user_input is not None:

            self._country_code = str(user_input[CONF_COUNTRYCODE])
            self._password = user_input[CONF_PASSWORD]
            self._platform = user_input[CONF_PLATFORM]
            self._username = user_input[CONF_USERNAME]

            result = await self.hass.async_add_executor_job(self._try_connect)

            if result == RESULT_SUCCESS:
                return self._save_entry()
            if result != RESULT_AUTH_FAILED or self._is_import:
                if self._is_import:
                    _LOGGER.error(
                        "Error importing from configuration.yaml: %s",
                        RESULT_LOG_MESSAGE.get(result, "Generic Error"),
                    )
                return self.async_abort(reason=result)
            errors["base"] = result

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA_USER, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle a option flow for Tuya."""

    def __init__(self, config_entry: config_entries.ConfigEntry):
        """Initialize options flow."""
        self.config_entry = config_entry
        self._conf_devs_id = None
        self._conf_devs_option = {}
        self._form_error = None

    def _get_form_error(self):
        """Set the error to be shown in the options form."""
        errors = {}
        if self._form_error:
            errors["base"] = self._form_error
            self._form_error = None
        return errors

    def _get_config_devices(self):
        """Get the list of Tuya device to configure."""
        config_list = {}
        tuya = self.hass.data[DOMAIN][TUYA_DATA]
        devices_list = tuya.get_all_devices()
        for device in devices_list:
            dev_type = device.device_type()
            if dev_type in TUYA_TYPE_CONFIG:
                dev_id = f"{dev_type}-{device.object_id()}"
                config_list[dev_id] = f"{device.name()} ({dev_type})"

        return config_list

    def _get_device(self, dev_id):
        """Get specific device from tuya library."""
        tuya = self.hass.data[DOMAIN][TUYA_DATA]
        return tuya.get_device_by_id(dev_id)

    def _save_config(self, data):
        """Save the updated options."""
        curr_conf = self.config_entry.options.copy()
        curr_conf.update(data)
        curr_conf.update(self._conf_devs_option)

        return self.async_create_entry(title="", data=curr_conf)

    async def _async_device_form(self, devs_id):
        """Return configuration form for devices."""
        conf_devs_id = []
        for count, dev_id in enumerate(devs_id):
            device_info = dev_id.split("-")
            if count == 0:
                device_type = device_info[0]
                device_id = device_info[1]
            elif device_type != device_info[0]:
                self._form_error = ERROR_DEV_MULTI_TYPE
                return await self.async_step_init()
            conf_devs_id.append(device_info[1])

        device = self._get_device(device_id)
        if not device:
            self._form_error = ERROR_DEV_NOT_FOUND
            return await self.async_step_init()

        curr_conf = self._conf_devs_option.get(
            device_id, self.config_entry.options.get(device_id, {})
        )

        config_schema = await self._get_device_schema(device_type, curr_conf, device)
        if not config_schema:
            self._form_error = ERROR_DEV_NOT_CONFIG
            return await self.async_step_init()

        self._conf_devs_id = conf_devs_id
        device_name = (
            "(multiple devices selected)" if len(conf_devs_id) > 1 else device.name()
        )

        return self.async_show_form(
            step_id="device",
            data_schema=config_schema,
            description_placeholders={
                "device_type": device_type,
                "device_name": device_name,
            },
        )

    async def async_step_init(self, user_input=None):
        """Handle options flow."""
        if user_input is not None:
            dev_ids = user_input.get(CONF_LIST_DEVICES)
            if dev_ids:
                return await self._async_device_form(dev_ids)

            user_input.pop(CONF_LIST_DEVICES, [])
            return self._save_config(data=user_input)

        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_DISCOVERY_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_DISCOVERY_INTERVAL, DEFAULT_DISCOVERY_INTERVAL
                    ),
                ): vol.All(vol.Coerce(int), vol.Clamp(min=30, max=900)),
                vol.Optional(
                    CONF_QUERY_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_QUERY_INTERVAL, DEFAULT_QUERY_INTERVAL
                    ),
                ): vol.All(vol.Coerce(int), vol.Clamp(min=30, max=240)),
            }
        )

        devices_list = self._get_config_devices()
        if devices_list:
            data_schema = data_schema.extend(
                {vol.Optional(CONF_LIST_DEVICES): cv.multi_select(devices_list)}
            )

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
            errors=self._get_form_error(),
        )

    async def async_step_device(self, user_input=None):
        """Handle options flow for device."""
        if user_input is not None:
            for device_id in self._conf_devs_id:
                self._conf_devs_option[device_id] = user_input

        return await self.async_step_init()

    async def _get_device_schema(self, device_type, curr_conf, device):
        """Return option schema for device."""
        if device_type == "light":
            return self._get_light_schema(curr_conf, device)
        if device_type == "climate":
            entities_list = await _get_entities_matching_domains(self.hass, ["sensor"])
            return self._get_climate_schema(curr_conf, device, entities_list)
        return None

    @staticmethod
    def _get_light_schema(curr_conf, device):
        """Create option schema for light device."""
        min_kelvin = device.max_color_temp()
        max_kelvin = device.min_color_temp()

        config_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SUPPORT_COLOR,
                    default=curr_conf.get(CONF_SUPPORT_COLOR, False),
                ): bool,
                vol.Optional(
                    CONF_BRIGHTNESS_RANGE_MODE,
                    default=curr_conf.get(CONF_BRIGHTNESS_RANGE_MODE, 0),
                ): vol.In({0: "Range 1-255", 1: "Range 10-1000"}),
                vol.Optional(
                    CONF_MIN_KELVIN,
                    default=curr_conf.get(CONF_MIN_KELVIN, min_kelvin),
                ): vol.All(vol.Coerce(int), vol.Clamp(min=min_kelvin, max=max_kelvin)),
                vol.Optional(
                    CONF_MAX_KELVIN,
                    default=curr_conf.get(CONF_MAX_KELVIN, max_kelvin),
                ): vol.All(vol.Coerce(int), vol.Clamp(min=min_kelvin, max=max_kelvin)),
                vol.Optional(
                    CONF_TUYA_MAX_COLTEMP,
                    default=curr_conf.get(
                        CONF_TUYA_MAX_COLTEMP, DEFAULT_TUYA_MAX_COLTEMP
                    ),
                ): vol.All(
                    vol.Coerce(int),
                    vol.Clamp(
                        min=DEFAULT_TUYA_MAX_COLTEMP, max=DEFAULT_TUYA_MAX_COLTEMP * 10
                    ),
                ),
            }
        )

        return config_schema

    @staticmethod
    def _get_climate_schema(curr_conf, device, entities_list):
        """Create option schema for climate device."""
        unit = device.temperature_unit()
        def_unit = TEMP_FAHRENHEIT if unit == "FAHRENHEIT" else TEMP_CELSIUS
        entities_list.insert(0, ENTITY_MATCH_NONE)

        config_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_UNIT_OF_MEASUREMENT,
                    default=curr_conf.get(CONF_UNIT_OF_MEASUREMENT, def_unit),
                ): vol.In({TEMP_CELSIUS: "Celsius", TEMP_FAHRENHEIT: "Fahrenheit"}),
                vol.Optional(
                    CONF_TEMP_DIVIDER,
                    default=curr_conf.get(CONF_TEMP_DIVIDER, 0),
                ): vol.All(vol.Coerce(int), vol.Clamp(min=0)),
                vol.Optional(
                    CONF_CURR_TEMP_DIVIDER,
                    default=curr_conf.get(CONF_CURR_TEMP_DIVIDER, 0),
                ): vol.All(vol.Coerce(int), vol.Clamp(min=0)),
                vol.Optional(
                    CONF_MIN_TEMP,
                    default=curr_conf.get(CONF_MIN_TEMP, 0),
                ): int,
                vol.Optional(
                    CONF_MAX_TEMP,
                    default=curr_conf.get(CONF_MAX_TEMP, 0),
                ): int,
                vol.Optional(
                    CONF_EXT_TEMP_SENSOR,
                    default=curr_conf.get(CONF_EXT_TEMP_SENSOR, ENTITY_MATCH_NONE),
                ): vol.In(entities_list),
            }
        )

        return config_schema


async def _get_entities_matching_domains(hass, domains):
    """List entities in the given domains."""
    included_domains = set(domains)
    entity_ids = hass.states.async_entity_ids(included_domains)
    entity_ids.sort()
    return entity_ids
