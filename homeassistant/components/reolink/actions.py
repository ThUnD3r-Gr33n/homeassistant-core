"""Reolink integration for HomeAssistant."""

from __future__ import annotations

from reolink_aio.api import Chime
from reolink_aio.enums import ChimeToneEnum
from reolink_aio.exceptions import InvalidParameterError, ReolinkError
import voluptuous as vol

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_DEVICE_ID, ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .const import DOMAIN
from .host import ReolinkHost
from .util import get_device_uid_and_ch

ATTR_RINGTONE = "ringtone"


async def async_setup_actions(hass: HomeAssistant) -> bool:
    """Set up Reolink actions."""

    async def async_chime_play(service_call: ServiceCall) -> None:
        """Play a ringtone."""
        service_data = service_call.data
        device_registry = dr.async_get(hass)
        device_ids = []

        if ATTR_DEVICE_ID in service_data:
            device_ids.extend(service_data[ATTR_DEVICE_ID])

        if ATTR_ENTITY_ID in service_data:
            entity_reg = er.async_get(hass)
            for entity_id in service_data[ATTR_ENTITY_ID]:
                entity = entity_reg.async_get(entity_id)
                if entity is not None and entity.device_id not in device_ids:
                    device_ids.append(entity.device_id)

        for device_id in device_ids:
            config_entry = None
            device = device_registry.async_get(device_id)
            if device is not None:
                for entry_id in device.config_entries:
                    if (
                        config_entry := hass.config_entries.async_get_entry(entry_id)
                    ) is None:
                        continue
                    if config_entry.domain == DOMAIN:
                        break
            if (
                config_entry is None
                or device is None
                or config_entry.state == ConfigEntryState.NOT_LOADED
            ):
                raise ServiceValidationError(
                    "Reolink chime_play error: config entry not found or not loaded"
                )
            host: ReolinkHost = hass.data[DOMAIN][config_entry.entry_id].host
            (device_uid, chime_id, is_chime) = get_device_uid_and_ch(device, host)
            chime: Chime | None = host.api.chime(chime_id)
            if not is_chime or chime is None:
                raise ServiceValidationError(
                    f"Reolink chime_play error: {device.name} is not a chime"
                )

            ringtone = service_data[ATTR_RINGTONE]
            try:
                await chime.play(ChimeToneEnum[ringtone].value)
            except InvalidParameterError as err:
                raise ServiceValidationError(err) from err
            except ReolinkError as err:
                raise HomeAssistantError(err) from err

    hass.services.async_register(
        DOMAIN,
        "chime_play",
        async_chime_play,
        schema=vol.Schema(
            {
                vol.Optional(ATTR_DEVICE_ID): list[str],
                vol.Optional(ATTR_ENTITY_ID): list[str],
                vol.Required(ATTR_RINGTONE): vol.In(
                    [method.name for method in ChimeToneEnum][1:]
                ),
            }
        ),
    )

    return True
