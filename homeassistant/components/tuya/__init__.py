"""Support for Tuya Smart devices."""

from __future__ import annotations

import logging
from typing import Any, NamedTuple

from tuya_sharing import (
    CustomerDevice,
    Manager,
    SharingDeviceListener,
    SharingTokenListener,
    logger as tuya_logger,
    strategy as tuya_strategy,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import dispatcher_send

from .const import (
    CONF_APP_TYPE,
    CONF_ENDPOINT,
    CONF_TERMINAL_ID,
    CONF_TOKEN_INFO,
    CONF_USER_CODE,
    DOMAIN,
    LOGGER,
    PLATFORMS,
    TUYA_CLIENT_ID,
    TUYA_DISCOVERY_NEW,
    TUYA_HA_SIGNAL_UPDATE_ENTITY,
)

# Suppress logs from the library, it logs unneeded on error
logging.getLogger("tuya_sharing").setLevel(logging.CRITICAL)

type TuyaConfigEntry = ConfigEntry[HomeAssistantTuyaData]


class HomeAssistantTuyaData(NamedTuple):
    """Tuya data stored in the Home Assistant data object."""

    manager: Manager
    listener: SharingDeviceListener


async def async_setup_entry(hass: HomeAssistant, entry: TuyaConfigEntry) -> bool:
    """Async setup hass config entry."""
    if CONF_APP_TYPE in entry.data:
        raise ConfigEntryAuthFailed("Authentication failed. Please re-authenticate.")

    token_listener = TokenListener(hass, entry)
    manager = TuyaManager(
        TUYA_CLIENT_ID,
        entry.data[CONF_USER_CODE],
        entry.data[CONF_TERMINAL_ID],
        entry.data[CONF_ENDPOINT],
        entry.data[CONF_TOKEN_INFO],
        token_listener,
    )

    listener = DeviceListener(hass, manager)
    manager.add_device_listener(listener)

    # Get all devices from Tuya
    try:
        await hass.async_add_executor_job(manager.update_device_cache)
    except Exception as exc:
        # While in general, we should avoid catching broad exceptions,
        # we have no other way of detecting this case.
        if "sign invalid" in str(exc):
            msg = "Authentication failed. Please re-authenticate"
            raise ConfigEntryAuthFailed(msg) from exc
        raise

    # Connection is successful, store the manager & listener
    entry.runtime_data = HomeAssistantTuyaData(manager=manager, listener=listener)

    # Cleanup device registry
    await cleanup_device_registry(hass, manager)

    # Register known device IDs
    device_registry = dr.async_get(hass)
    for device in manager.device_map.values():
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, device.id)},
            manufacturer="Tuya",
            name=device.name,
            model=f"{device.product_name} (unsupported)",
            model_id=device.product_id,
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # If the device does not register any entities, the device does not need to subscribe
    # So the subscription is here
    await hass.async_add_executor_job(manager.refresh_mq)
    return True


async def cleanup_device_registry(hass: HomeAssistant, device_manager: Manager) -> None:
    """Remove deleted device registry entry if there are no remaining entities."""
    device_registry = dr.async_get(hass)
    for dev_id, device_entry in list(device_registry.devices.items()):
        for item in device_entry.identifiers:
            if item[0] == DOMAIN and item[1] not in device_manager.device_map:
                device_registry.async_remove_device(dev_id)
                break


async def async_unload_entry(hass: HomeAssistant, entry: TuyaConfigEntry) -> bool:
    """Unloading the Tuya platforms."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        tuya = entry.runtime_data
        if tuya.manager.mq is not None:
            tuya.manager.mq.stop()
        tuya.manager.remove_device_listener(tuya.listener)
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: TuyaConfigEntry) -> None:
    """Remove a config entry.

    This will revoke the credentials from Tuya.
    """
    manager = Manager(
        TUYA_CLIENT_ID,
        entry.data[CONF_USER_CODE],
        entry.data[CONF_TERMINAL_ID],
        entry.data[CONF_ENDPOINT],
        entry.data[CONF_TOKEN_INFO],
    )
    await hass.async_add_executor_job(manager.unload)


class TuyaManager(Manager):
    """Patched tuya_sharing Manager.

    This can be removed once change has been merged upstream in tuya-device-sharing-sdk. Please
    check the status of https://github.com/tuya/tuya-device-sharing-sdk/pull/17
    """

    def __update_device(
        self, device: CustomerDevice, updated_status_properties: list[str] | None = None
    ):
        for listener in self.device_listeners:
            listener.update_device(device, updated_status_properties)

    def _on_device_report(self, device_id: str, status: list):
        device = self.device_map.get(device_id, None)
        if not device:
            return
        tuya_logger.debug(f"mq _on_device_report-> {status}")
        updated_status_properties = []
        value = None
        if device.support_local:
            for item in status:
                if "dpId" in item and "value" in item:
                    dp_id_item = device.local_strategy[item["dpId"]]
                    strategy_name = dp_id_item["value_convert"]
                    config_item = dp_id_item["config_item"]
                    dp_item = (dp_id_item["status_code"], item["value"])
                    tuya_logger.debug(
                        f"mq _on_device_report before strategy convert strategy_name={strategy_name},dp_item={dp_item},config_item={config_item}"
                    )
                    code, value = tuya_strategy.convert(
                        strategy_name, dp_item, config_item
                    )
                    tuya_logger.debug(
                        f"mq _on_device_report after strategy convert code={code},value={value}"
                    )
                    device.status[code] = value
                    updated_status_properties.append(code)
        else:
            for item in status:
                if "code" in item and "value" in item:
                    code = item["code"]
                    value = item["value"]
                    device.status[code] = value
                    updated_status_properties.append(code)

        self.__update_device(device, updated_status_properties)


class DeviceListener(SharingDeviceListener):
    """Device Update Listener."""

    def __init__(
        self,
        hass: HomeAssistant,
        manager: Manager,
    ) -> None:
        """Init DeviceListener."""
        self.hass = hass
        self.manager = manager

    def update_device(
        self, device: CustomerDevice, updated_status_properties: list[str] | None
    ) -> None:
        """Update device status."""
        LOGGER.debug(
            "Received update for device %s: %s (updated properties: %s)",
            device.id,
            self.manager.device_map[device.id].status,
            updated_status_properties,
        )
        dispatcher_send(
            self.hass,
            f"{TUYA_HA_SIGNAL_UPDATE_ENTITY}_{device.id}",
            updated_status_properties,
        )

    def add_device(self, device: CustomerDevice) -> None:
        """Add device added listener."""
        # Ensure the device isn't present stale
        self.hass.add_job(self.async_remove_device, device.id)

        dispatcher_send(self.hass, TUYA_DISCOVERY_NEW, [device.id])

    def remove_device(self, device_id: str) -> None:
        """Add device removed listener."""
        self.hass.add_job(self.async_remove_device, device_id)

    @callback
    def async_remove_device(self, device_id: str) -> None:
        """Remove device from Home Assistant."""
        LOGGER.debug("Remove device: %s", device_id)
        device_registry = dr.async_get(self.hass)
        device_entry = device_registry.async_get_device(
            identifiers={(DOMAIN, device_id)}
        )
        if device_entry is not None:
            device_registry.async_remove_device(device_entry.id)


class TokenListener(SharingTokenListener):
    """Token listener for upstream token updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: TuyaConfigEntry,
    ) -> None:
        """Init TokenListener."""
        self.hass = hass
        self.entry = entry

    def update_token(self, token_info: dict[str, Any]) -> None:
        """Update token info in config entry."""
        data = {
            **self.entry.data,
            CONF_TOKEN_INFO: {
                "t": token_info["t"],
                "uid": token_info["uid"],
                "expire_time": token_info["expire_time"],
                "access_token": token_info["access_token"],
                "refresh_token": token_info["refresh_token"],
            },
        }

        @callback
        def async_update_entry() -> None:
            """Update config entry."""
            self.hass.config_entries.async_update_entry(self.entry, data=data)

        self.hass.add_job(async_update_entry)
