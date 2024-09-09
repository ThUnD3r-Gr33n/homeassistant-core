"""ViCare helpers functions."""

import logging

from PyViCare.PyViCareDevice import Device as PyViCareDevice
from PyViCare.PyViCareDeviceConfig import PyViCareDeviceConfig
from PyViCare.PyViCareHeatingDevice import (
    HeatingDeviceWithComponent as PyViCareHeatingDeviceComponent,
)
from PyViCare.PyViCareUtils import PyViCareNotSupportedFeatureError

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import STORAGE_DIR

from .const import (
    CONF_HEATING_TYPE,
    DOMAIN,
    HEATING_TYPE_TO_CREATOR_METHOD,
    HeatingType,
)
from .types import ViCareRequiredKeysMixin

_LOGGER = logging.getLogger(__name__)


def get_device(
    entry: ConfigEntry, device_config: PyViCareDeviceConfig
) -> PyViCareDevice:
    """Get device for device config."""
    return getattr(
        device_config,
        HEATING_TYPE_TO_CREATOR_METHOD[HeatingType(entry.data[CONF_HEATING_TYPE])],
    )()


def is_supported(
    name: str,
    entity_description: ViCareRequiredKeysMixin,
    vicare_device,
) -> bool:
    """Check if the PyViCare device supports the requested sensor."""
    try:
        entity_description.value_getter(vicare_device)
    except PyViCareNotSupportedFeatureError:
        _LOGGER.debug("Feature not supported %s", name)
        return False
    except AttributeError as error:
        _LOGGER.debug("Feature not supported %s: %s", name, error)
        return False
    _LOGGER.debug("Found entity %s", name)
    return True


def get_burners(device: PyViCareDevice) -> list[PyViCareHeatingDeviceComponent]:
    """Return the list of burners."""
    try:
        return device.burners
    except PyViCareNotSupportedFeatureError:
        _LOGGER.debug("No burners found")
    except AttributeError as error:
        _LOGGER.debug("No burners found: %s", error)
    return []


def get_circuits(device: PyViCareDevice) -> list[PyViCareHeatingDeviceComponent]:
    """Return the list of circuits."""
    try:
        return device.circuits
    except PyViCareNotSupportedFeatureError:
        _LOGGER.debug("No circuits found")
    except AttributeError as error:
        _LOGGER.debug("No circuits found: %s", error)
    return []


def get_compressors(device: PyViCareDevice) -> list[PyViCareHeatingDeviceComponent]:
    """Return the list of compressors."""
    try:
        return device.compressors
    except PyViCareNotSupportedFeatureError:
        _LOGGER.debug("No compressors found")
    except AttributeError as error:
        _LOGGER.debug("No compressors found: %s", error)
    return []


def get_token_path(hass: HomeAssistant, entry: ConfigEntry | None) -> str:
    """Return the path to the token storage file for the given ConfigEntry."""
    return hass.config.path(
        STORAGE_DIR, f"{DOMAIN}.{entry.entry_id if entry else 'tmp'}"
    )
