"""Support for Meteo-France weather service."""
import logging
import time

from meteofrance_api.model.forecast import Forecast

from homeassistant.components.weather import (
    ATTR_FORECAST_CONDITION,
    ATTR_FORECAST_NATIVE_PRECIPITATION,
    ATTR_FORECAST_NATIVE_TEMP,
    ATTR_FORECAST_NATIVE_TEMP_LOW,
    ATTR_FORECAST_NATIVE_WIND_SPEED,
    ATTR_FORECAST_TIME,
    ATTR_FORECAST_WIND_BEARING,
    WeatherEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_MODE,
    UnitOfPrecipitationDepth,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from homeassistant.util import dt as dt_util

from .const import (
    CONDITION_CLASSES,
    COORDINATOR_FORECAST,
    DOMAIN,
    FORECAST_MODE_DAILY,
    FORECAST_MODE_HOURLY,
    MANUFACTURER,
    MODEL,
)

_LOGGER = logging.getLogger(__name__)


def format_condition(condition: str):
    """Return condition from dict CONDITION_CLASSES."""
    for key, value in CONDITION_CLASSES.items():
        if condition in value:
            return key
    return condition


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Meteo-France weather platform."""
    coordinator: DataUpdateCoordinator[Forecast] = hass.data[DOMAIN][entry.entry_id][
        COORDINATOR_FORECAST
    ]

    async_add_entities(
        [
            MeteoFranceWeather(
                coordinator,
                entry.options.get(CONF_MODE, FORECAST_MODE_DAILY),
            )
        ],
        True,
    )
    _LOGGER.debug(
        "Weather entity (%s) added for %s",
        entry.options.get(CONF_MODE, FORECAST_MODE_DAILY),
        coordinator.data.position["name"],
    )


class MeteoFranceWeather(
    CoordinatorEntity[DataUpdateCoordinator[Forecast]], WeatherEntity
):
    """Representation of a weather condition."""

    _attr_attribution = "Data provided by Météo-France"
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_native_precipitation_unit = UnitOfPrecipitationDepth.MILLIMETERS
    _attr_native_pressure_unit = UnitOfPressure.HPA
    _attr_native_wind_speed_unit = UnitOfSpeed.METERS_PER_SECOND

    def __init__(self, coordinator: DataUpdateCoordinator[Forecast], mode: str) -> None:
        """Initialise the platform with a data instance and station name."""
        super().__init__(coordinator)
        self._city_name = self.coordinator.data.position["name"]
        self._mode = mode
        self._unique_id = f"{self.coordinator.data.position['lat']},{self.coordinator.data.position['lon']}"

    @property
    def unique_id(self):
        """Return the unique id of the sensor."""
        return self._unique_id

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._city_name

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        assert (
            self.platform
            and self.platform.config_entry
            and self.platform.config_entry.unique_id
        )
        return DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, self.platform.config_entry.unique_id)},
            manufacturer=MANUFACTURER,
            model=MODEL,
            name=self.coordinator.name,
        )

    @property
    def condition(self):
        """Return the current condition."""
        return format_condition(
            self.coordinator.data.current_forecast["weather"]["desc"]
        )

    @property
    def native_temperature(self):
        """Return the temperature."""
        return self.coordinator.data.current_forecast["T"]["value"]

    @property
    def native_pressure(self):
        """Return the pressure."""
        return self.coordinator.data.current_forecast["sea_level"]

    @property
    def humidity(self):
        """Return the humidity."""
        return self.coordinator.data.current_forecast["humidity"]

    @property
    def native_wind_speed(self):
        """Return the wind speed."""
        return self.coordinator.data.current_forecast["wind"]["speed"]

    @property
    def wind_bearing(self):
        """Return the wind bearing."""
        wind_bearing = self.coordinator.data.current_forecast["wind"]["direction"]
        if wind_bearing != -1:
            return wind_bearing

    @property
    def forecast(self):
        """Return the forecast."""
        forecast_data = []

        if self._mode == FORECAST_MODE_HOURLY:
            today = time.time()
            for forecast in self.coordinator.data.forecast:
                # Can have data in the past
                if forecast["dt"] < today:
                    continue
                forecast_data.append(
                    {
                        ATTR_FORECAST_TIME: dt_util.utc_from_timestamp(
                            forecast["dt"]
                        ).isoformat(),
                        ATTR_FORECAST_CONDITION: format_condition(
                            forecast["weather"]["desc"]
                        ),
                        ATTR_FORECAST_NATIVE_TEMP: forecast["T"]["value"],
                        ATTR_FORECAST_NATIVE_PRECIPITATION: forecast["rain"].get("1h"),
                        ATTR_FORECAST_NATIVE_WIND_SPEED: forecast["wind"]["speed"],
                        ATTR_FORECAST_WIND_BEARING: forecast["wind"]["direction"]
                        if forecast["wind"]["direction"] != -1
                        else None,
                    }
                )
        else:
            for forecast in self.coordinator.data.daily_forecast:
                # stop when we don't have a weather condition (can happen around last days of forecast, max 14)
                if not forecast.get("weather12H"):
                    break
                forecast_data.append(
                    {
                        ATTR_FORECAST_TIME: self.coordinator.data.timestamp_to_locale_time(
                            forecast["dt"]
                        ),
                        ATTR_FORECAST_CONDITION: format_condition(
                            forecast["weather12H"]["desc"]
                        ),
                        ATTR_FORECAST_NATIVE_TEMP: forecast["T"]["max"],
                        ATTR_FORECAST_NATIVE_TEMP_LOW: forecast["T"]["min"],
                        ATTR_FORECAST_NATIVE_PRECIPITATION: forecast["precipitation"][
                            "24h"
                        ],
                    }
                )
        return forecast_data
