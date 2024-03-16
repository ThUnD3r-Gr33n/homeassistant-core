"""Motionblinds BLE integration."""

from __future__ import annotations

from functools import partial
import logging

from motionblindsble.const import MotionBlindType, MotionConnectionType
from motionblindsble.crypt import MotionCrypt
from motionblindsble.device import MotionDevice

from homeassistant.components.bluetooth import (
    BluetoothCallbackMatcher,
    BluetoothChange,
    BluetoothScanningMode,
    BluetoothServiceInfoBleak,
    async_ble_device_from_address,
    async_register_callback,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_BLIND_TYPE,
    CONF_MAC_CODE,
    DOMAIN,
    OPTION_DISCONNECT_TIME,
    OPTION_PERMANENT_CONNECTION,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.COVER,
]

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up Motionblinds BLE integration."""

    _LOGGER.debug("Setting up Motionblinds BLE integration")

    # The correct time is needed for encryption
    _LOGGER.debug("Setting timezone for encryption: %s", hass.config.time_zone)
    MotionCrypt.set_timezone(hass.config.time_zone)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Motionblinds BLE device from a config entry."""

    _LOGGER.debug("(%s) Setting up device", entry.data[CONF_MAC_CODE])

    # Create MotionDevice with BLEDevice
    ble_device = async_ble_device_from_address(hass, entry.data[CONF_ADDRESS])
    device = MotionDevice(
        ble_device if ble_device is not None else entry.data[CONF_ADDRESS],
        blind_type=MotionBlindType[entry.data[CONF_BLIND_TYPE].upper()],
    )

    # Register Home Assistant functions to use in the library
    device.set_ha_create_task(
        partial(
            entry.async_create_background_task,
            hass=hass,
            name=device.ble_device.address,
        )
    )
    device.set_ha_call_later(partial(async_call_later, hass=hass))

    # Register a callback that updates the BLEDevice in the library
    @callback
    def async_update_ble_device(
        service_info: BluetoothServiceInfoBleak, change: BluetoothChange
    ) -> None:
        """Update the BLEDevice."""
        _LOGGER.debug("(%s) New BLE device found", service_info.address)
        device.set_ble_device(service_info.device, rssi=service_info.advertisement.rssi)

    async_register_callback(
        hass,
        async_update_ble_device,
        BluetoothCallbackMatcher(address=entry.data[CONF_ADDRESS]),
        BluetoothScanningMode.ACTIVE,
    )

    # Register OptionsFlow update listener and apply options
    entry.async_on_unload(entry.add_update_listener(update_listener))
    await apply_options(hass, entry)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = device

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.debug("(%s) Finished setting up device", entry.data[CONF_MAC_CODE])

    return True


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    _LOGGER.debug(
        "(%s) Updated device options: %s", entry.data[CONF_MAC_CODE], entry.options
    )
    await apply_options(hass, entry)


async def apply_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Apply the options from the OptionsFlow."""

    device: MotionDevice = hass.data[DOMAIN][entry.entry_id]
    disconnect_time: float | None = entry.options.get(OPTION_DISCONNECT_TIME, None)
    permanent_connection: bool = entry.options.get(OPTION_PERMANENT_CONNECTION, False)

    def reconnect_on_disconnect(
        connection_type: MotionConnectionType,
    ) -> None:
        """Reconnect after a disconnect."""
        if connection_type is MotionConnectionType.DISCONNECTED:
            _LOGGER.debug(
                "(%s) Device disconnected, automatically connecting again",
                entry.data[CONF_MAC_CODE],
            )
            entry.async_create_background_task(
                hass=hass, target=device.connect(), name=device.ble_device.address
            )

    device.remove_connection_callback(reconnect_on_disconnect.__name__)
    if permanent_connection:
        device.register_connection_callback(reconnect_on_disconnect)
        reconnect_on_disconnect(MotionConnectionType.DISCONNECTED)

    device.set_custom_disconnect_time(disconnect_time)
    await device.set_permanent_connection(permanent_connection)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Motionblinds BLE device from a config entry."""

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
