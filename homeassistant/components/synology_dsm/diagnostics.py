"""Diagnostics support for Synology DSM."""
from __future__ import annotations

from synology_dsm.api.surveillance_station.camera import SynoCamera

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from . import SynoApi
from .const import DOMAIN, SYNO_API, SYSTEM_LOADED


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> dict:
    """Return diagnostics for a config entry."""
    data: dict = hass.data[DOMAIN][config_entry.unique_id]
    syno_api: SynoApi = data[SYNO_API]
    dsm_info = syno_api.dsm.information

    diag_data = {
        "device_info": {
            "model": dsm_info.model,
            "version": dsm_info.version_string,
            "ram": dsm_info.ram,
            "uptime": dsm_info.uptime,
            "temperature": dsm_info.temperature,
        },
        "network": {"interfaces": {}},
        "storage": {"disks": {}, "volumes": {}},
        "surveillance_station": {"cameras": {}},
        "upgrade": {},
        "utilisation": {},
        "is_system_loaded": data[SYSTEM_LOADED],
        "api_details": {
            "fetching_entities": syno_api._fetching_entities,
        },
    }

    if syno_api.network is not None:
        intf: dict
        for intf in syno_api.network.interfaces:
            diag_data["network"]["interfaces"][intf["id"]] = {
                "type": intf["type"],
                "ip": intf["ip"],
            }

    if syno_api.storage is not None:
        disk: dict
        for disk in syno_api.storage.disks:
            diag_data["storage"]["disks"][disk["id"]] = {
                "name": disk["name"],
                "vendor": disk["vendor"],
                "model": disk["model"],
                "device": disk["device"],
                "temp": disk["temp"],
                "size_total": disk["size_total"],
            }

        volume: dict
        for volume in syno_api.storage.volumes:
            diag_data["storage"]["volumes"][volume["id"]] = {
                "name": volume["fs_type"],
                "size": volume["size"],
            }

    if syno_api.surveillance_station is not None:
        camera: SynoCamera
        for cam_id, camera in syno_api.surveillance_station._cameras_by_id.items():
            diag_data["surveillance_station"]["cameras"][cam_id] = {
                "name": camera.name,
                "is_enabled": camera.is_enabled,
                "is_motion_detection_enabled": camera.is_motion_detection_enabled,
                "model": camera.model,
                "resolution": camera.resolution,
            }

    if syno_api.upgrade is not None:
        diag_data["upgrade"] = {
            "update_available": syno_api.upgrade.update_available,
            "available_version": syno_api.upgrade.available_version,
            "reboot_needed": syno_api.upgrade.reboot_needed,
            "service_restarts": syno_api.upgrade.service_restarts,
        }

    if syno_api.utilisation is not None:
        diag_data["utilisation"] = {
            "cpu": syno_api.utilisation.cpu,
            "memory": syno_api.utilisation.memory,
            "network": syno_api.utilisation.network,
        }

    return diag_data
