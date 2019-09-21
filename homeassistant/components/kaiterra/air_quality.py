from homeassistant.components.air_quality import AirQualityEntity

from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect
)

from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_NAME,
)

from .const import (
    DOMAIN,
    ATTR_VOC,
    ATTR_AQI_LEVEL,
    ATTR_AQI_POLLUTANT,
    DISPATCHER_KAITERRA
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the air_quality kaiterra sensor."""
    if discovery_info is None:
        return

    api = hass.data.get(DOMAIN)
    name = discovery_info.get(CONF_NAME)
    device_id = discovery_info.get(CONF_DEVICE_ID)

    async_add_entities([KaiterraAirQuality(api, name, device_id)])


class KaiterraAirQuality(AirQualityEntity):
    """Implementation of a Kaittera air quality sensor."""

    def __init__(self, api, name, device_id):
        """Initialize the sensor."""
        self._api = api
        self._name = f'{name} - Air Quality'
        self._device_id = device_id

    def _data(self, key):
        prop = self._device.get(key)
        return prop.get('value') if prop else None

    @property
    def _device(self):
        return self._api.data.get(self._device_id, {})

    @property
    def should_poll(self):
        """Return that the sensor should not be polled."""
        return False

    @property
    def available(self):
        """Return the availability of the sensor."""
        return self._api.data.get(self._device_id) is not None

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def air_quality_index(self):
        """Return the Air Quality Index (AQI)."""
        return self._data('aqi')

    @property
    def air_quality_index_level(self):
        """Return the Air Quality Index level."""
        return self._data('aqi_level')

    @property
    def air_quality_index_pollutant(self):
        """Return the Air Quality Index level."""
        return self._data('aqi_pollutant')

    @property
    def particulate_matter_2_5(self):
        """Return the particulate matter 2.5 level."""
        return self._data('rpm25c')

    @property
    def particulate_matter_10(self):
        """Return the particulate matter 10 level."""
        return self._data('rpm10c')

    @property
    def volatile_organic_compounds(self):
        """Return the VOC (Volatile Organic Compounds) level."""
        return self._data('rtvoc')

    @property
    def unique_id(self):
        """Return the sensor's unique id."""
        return f'{self._device_id}_air_quality'

    @property
    def device_state_attributes(self):
        """Return the device state attributes."""
        data = {}
        attributes = [
            (ATTR_VOC, self.volatile_organic_compounds),
            (ATTR_AQI_LEVEL, self.air_quality_index_level),
            (ATTR_AQI_POLLUTANT, self.air_quality_index_pollutant)
        ]

        for attr, value in attributes:
            if value is not None:
                data[attr] = value

        return data

    async def async_added_to_hass(self):
        """Register callback."""
        async_dispatcher_connect(self.hass, DISPATCHER_KAITERRA, self.async_write_ha_state)

    async def async_update(self):
        """Force update of state."""
        await self._api.async_update()
