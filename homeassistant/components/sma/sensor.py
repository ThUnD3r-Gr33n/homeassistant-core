"""SMA Solar Webconnect interface."""
import logging

import pysma
import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PATH,
    CONF_SENSORS,
    CONF_SSL,
    CONF_VERIFY_SSL,
)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_CUSTOM,
    CONF_FACTOR,
    CONF_GROUP,
    CONF_KEY,
    CONF_UNIT,
    DEVICE_INFO,
    DOMAIN,
    GROUPS,
    PYSMA_COORDINATOR,
    PYSMA_SENSORS,
)

_LOGGER = logging.getLogger(__name__)


def _check_sensor_schema(conf):
    """Check sensors and attributes are valid."""
    try:
        valid = [s.name for s in pysma.Sensors()]
        valid += pysma.LEGACY_MAP.keys()
    except (ImportError, AttributeError):
        return conf

    customs = list(conf[CONF_CUSTOM])

    for sensor in conf[CONF_SENSORS]:
        if sensor in customs:
            _LOGGER.warning(
                "All custom sensors will be added automatically, no need to include them in sensors: %s",
                sensor,
            )
        elif sensor not in valid:
            raise vol.Invalid(f"{sensor} does not exist")
    return conf


CUSTOM_SCHEMA = vol.Any(
    {
        vol.Required(CONF_KEY): vol.All(cv.string, vol.Length(min=13, max=15)),
        vol.Required(CONF_UNIT): cv.string,
        vol.Optional(CONF_FACTOR, default=1): vol.Coerce(float),
        vol.Optional(CONF_PATH): vol.All(cv.ensure_list, [cv.string]),
    }
)

PLATFORM_SCHEMA = vol.All(
    PLATFORM_SCHEMA.extend(
        {
            vol.Required(CONF_HOST): cv.string,
            vol.Optional(CONF_SSL, default=False): cv.boolean,
            vol.Optional(CONF_VERIFY_SSL, default=True): cv.boolean,
            vol.Required(CONF_PASSWORD): cv.string,
            vol.Optional(CONF_GROUP, default=GROUPS[0]): vol.In(GROUPS),
            vol.Optional(CONF_SENSORS, default=[]): vol.Any(
                cv.schema_with_slug_keys(cv.ensure_list),  # will be deprecated
                vol.All(cv.ensure_list, [str]),
            ),
            vol.Optional(CONF_CUSTOM, default={}): cv.schema_with_slug_keys(
                CUSTOM_SCHEMA
            ),
        },
        extra=vol.PREVENT_EXTRA,
    ),
    _check_sensor_schema,
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Import the platform into a config entry."""
    _LOGGER.warning(
        "Loading SMA via platform setup is deprecated. "
        "Please remove it from your configuration"
    )

    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_IMPORT}, data=config
        )
    )


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up SMA sensors."""
    sma_data = hass.data[DOMAIN][config_entry.entry_id]

    coordinator = sma_data[PYSMA_COORDINATOR]
    used_sensors = sma_data[PYSMA_SENSORS]

    entities = []
    for sensor in used_sensors:
        entities.append(
            SMAsensor(
                coordinator,
                config_entry.unique_id,
                config_entry.data[DEVICE_INFO],
                sensor,
            )
        )

    async_add_entities(entities)


class SMAsensor(CoordinatorEntity, SensorEntity):
    """Representation of a SMA sensor."""

    def __init__(self, coordinator, config_entry_unique_id, device_info, pysma_sensor):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._sensor = pysma_sensor
        self._enabled_default = self._sensor.enabled
        self._config_entry_unique_id = config_entry_unique_id
        self._device_info = device_info

        # Set sensor enabled to False.
        # Will be enabled by async_added_to_hass if actually used.
        self._sensor.enabled = False

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._sensor.name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._sensor.value

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return self._sensor.unit

    @property
    def poll(self):
        """SMA sensors are updated & don't poll."""
        return False

    @property
    def unique_id(self):
        """Return a unique identifier for this sensor."""
        return (
            f"{self._config_entry_unique_id}-{self._sensor.key}_{self._sensor.key_idx}"
        )

    @property
    def device_info(self):
        """Return the device information."""
        return {
            "identifiers": {(DOMAIN, self._config_entry_unique_id)},
            "name": self._device_info["name"],
            "manufacturer": self._device_info["manufacturer"],
            "model": self._device_info["type"],
        }

    @property
    def entity_registry_enabled_default(self):
        """Return if the entity should be enabled when first added to the entity registry."""
        return self._enabled_default

    async def async_added_to_hass(self):
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        self._sensor.enabled = True

    async def async_will_remove_from_hass(self):
        """Run when entity will be removed from hass."""
        await super().async_will_remove_from_hass()
        self._sensor.enabled = False
