"""Home Assistant trigger dispatcher."""
import importlib

from homeassistant.const import CONF_DOMAIN, CONF_PLATFORM
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers.trigger import (
    TriggerActionType,
    TriggerInfo,
    TriggerProtocol,
)
from homeassistant.helpers.typing import ConfigType


def _get_trigger_platform(config: ConfigType) -> TriggerProtocol:
    return importlib.import_module(f"..triggers.{config[CONF_PLATFORM]}", __name__)


def _get_platform(config: ConfigType) -> TriggerProtocol:
    return importlib.import_module(
        f"....components.{config[CONF_DOMAIN]}.device_trigger", __name__
    )


async def async_validate_trigger_config(
    hass: HomeAssistant, config: ConfigType
) -> ConfigType:
    """Validate config."""
    platform = _get_trigger_platform(config)
    if hasattr(platform, "async_validate_trigger_config"):
        return await platform.async_validate_trigger_config(hass, config)

    return platform.TRIGGER_SCHEMA(config)


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: TriggerActionType,
    trigger_info: TriggerInfo,
) -> CALLBACK_TYPE:
    """Attach trigger of specified platform."""
    platform = _get_trigger_platform(config)
    return await platform.async_attach_trigger(hass, config, action, trigger_info)


async def async_get_action_completed_state(config: ConfigType) -> str | None:
    """Return expected state when action is complete."""
    try:
        platform = _get_platform(config)
        return await platform.async_get_action_completed_state(config["action"])
    except ModuleNotFoundError:
        return None


async def async_attach_trigger_from_prev_action(
    hass: HomeAssistant,
    config: ConfigType,
    action: TriggerActionType,
    trigger_info: TriggerInfo,
) -> CALLBACK_TYPE:
    """Attach trigger of specified platform based on previous action configuration."""
    platform = _get_trigger_platform(config)
    return await platform.async_attach_trigger_from_prev_action(
        hass, config, action, trigger_info
    )
