"""The bluetooth integration."""
from __future__ import annotations

from asyncio import Future
from collections.abc import Callable
import logging
import platform
import re
import time
from typing import TYPE_CHECKING, Any

import async_timeout
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from homeassistant import config_entries
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant, ServiceCall, callback as hass_callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr, discovery_flow
from homeassistant.helpers.json import json_loads
from homeassistant.loader import async_get_bluetooth

from . import models
from .const import (
    ADAPTER_ADDRESS,
    ADAPTER_HW_VERSION,
    ADAPTER_SW_VERSION,
    CONF_ADAPTER,
    CONF_DETAILS,
    DATA_MANAGER,
    DEFAULT_ADDRESS,
    DOMAIN,
    SOURCE_LOCAL,
    AdapterDetails,
)
from .manager import BluetoothManager
from .match import BluetoothCallbackMatcher, IntegrationMatcher
from .models import (
    BluetoothCallback,
    BluetoothChange,
    BluetoothScanningMode,
    BluetoothServiceInfo,
    BluetoothServiceInfoBleak,
    HaBleakScannerWrapper,
    ProcessAdvertisementCallback,
)
from .scanner import HaScanner, ScannerStartError, create_bleak_scanner
from .util import adapter_human_name, adapter_unique_name, async_default_adapter

_LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:
    from homeassistant.helpers.typing import ConfigType


__all__ = [
    "async_ble_device_from_address",
    "async_discovered_service_info",
    "async_get_scanner",
    "async_process_advertisements",
    "async_rediscover_address",
    "async_register_callback",
    "async_track_unavailable",
    "BluetoothServiceInfo",
    "BluetoothServiceInfoBleak",
    "BluetoothScanningMode",
    "BluetoothCallback",
    "SOURCE_LOCAL",
]


@hass_callback
def async_get_scanner(hass: HomeAssistant) -> HaBleakScannerWrapper:
    """Return a HaBleakScannerWrapper.

    This is a wrapper around our BleakScanner singleton that allows
    multiple integrations to share the same BleakScanner.
    """
    return HaBleakScannerWrapper()


@hass_callback
def async_discovered_service_info(
    hass: HomeAssistant,
) -> list[BluetoothServiceInfoBleak]:
    """Return the discovered devices list."""
    if DATA_MANAGER not in hass.data:
        return []
    manager: BluetoothManager = hass.data[DATA_MANAGER]
    return manager.async_discovered_service_info()


@hass_callback
def async_ble_device_from_address(
    hass: HomeAssistant,
    address: str,
) -> BLEDevice | None:
    """Return BLEDevice for an address if its present."""
    if DATA_MANAGER not in hass.data:
        return None
    manager: BluetoothManager = hass.data[DATA_MANAGER]
    return manager.async_ble_device_from_address(address)


@hass_callback
def async_address_present(
    hass: HomeAssistant,
    address: str,
) -> bool:
    """Check if an address is present in the bluetooth device list."""
    if DATA_MANAGER not in hass.data:
        return False
    manager: BluetoothManager = hass.data[DATA_MANAGER]
    return manager.async_address_present(address)


@hass_callback
def async_register_callback(
    hass: HomeAssistant,
    callback: BluetoothCallback,
    match_dict: BluetoothCallbackMatcher | None,
    mode: BluetoothScanningMode,
) -> Callable[[], None]:
    """Register to receive a callback on bluetooth change.

    mode is currently not used as we only support active scanning.
    Passive scanning will be available in the future. The flag
    is required to be present to avoid a future breaking change
    when we support passive scanning.

    Returns a callback that can be used to cancel the registration.
    """
    manager: BluetoothManager = hass.data[DATA_MANAGER]
    return manager.async_register_callback(callback, match_dict)


async def async_process_advertisements(
    hass: HomeAssistant,
    callback: ProcessAdvertisementCallback,
    match_dict: BluetoothCallbackMatcher,
    mode: BluetoothScanningMode,
    timeout: int,
) -> BluetoothServiceInfoBleak:
    """Process advertisements until callback returns true or timeout expires."""
    done: Future[BluetoothServiceInfoBleak] = Future()

    @hass_callback
    def _async_discovered_device(
        service_info: BluetoothServiceInfoBleak, change: BluetoothChange
    ) -> None:
        if not done.done() and callback(service_info):
            done.set_result(service_info)

    unload = async_register_callback(hass, _async_discovered_device, match_dict, mode)

    try:
        async with async_timeout.timeout(timeout):
            return await done
    finally:
        unload()


@hass_callback
def async_track_unavailable(
    hass: HomeAssistant,
    callback: Callable[[str], None],
    address: str,
) -> Callable[[], None]:
    """Register to receive a callback when an address is unavailable.

    Returns a callback that can be used to cancel the registration.
    """
    manager: BluetoothManager = hass.data[DATA_MANAGER]
    return manager.async_track_unavailable(callback, address)


@hass_callback
def async_rediscover_address(hass: HomeAssistant, address: str) -> None:
    """Trigger discovery of devices which have already been seen."""
    manager: BluetoothManager = hass.data[DATA_MANAGER]
    manager.async_rediscover_address(address)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the bluetooth integration."""
    integration_matcher = IntegrationMatcher(await async_get_bluetooth(hass))

    manager = BluetoothManager(hass, integration_matcher)
    manager.async_setup()
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, manager.async_stop)
    hass.data[DATA_MANAGER] = models.MANAGER = manager

    two = re.compile("..")

    @hass_callback
    def long_uuid(uuid: str) -> str:
        """Convert a UUID to a long UUID."""
        return (
            f"0000{uuid[2:].lower()}-1000-8000-00805f9b34fb" if len(uuid) < 8 else uuid
        )

    @hass_callback
    def async_advertisement(service: ServiceCall) -> None:
        data = service.data
        decoded: dict[str, Any] = json_loads(data["data"])
        _LOGGER.warning("Advertisement: %s", decoded)
        manager.scanner_adv_received(
            BLEDevice(  # type: ignore[no-untyped-call]
                address=":".join(two.findall("%012X" % data["a"])),
                name=data.get("n", ""),
                rssi=data.get("r", 0),
            ),
            AdvertisementData(  # type: ignore[no-untyped-call]
                local_name=data.get("n", ""),
                manufacturer_data={hex(k): v.encode() for k, v in decoded.get("m", {})},
                service_data={
                    long_uuid(k): v.encode() for k, v in decoded.get("s", {})
                },
                service_uuids=[long_uuid(hex) for hex in decoded.get("u", [])],
            ),
            time.monotonic(),
            data.get("s", "unknown"),
        )

    hass.services.async_register(DOMAIN, "advertisement", async_advertisement)

    adapters = await manager.async_get_bluetooth_adapters()

    async_migrate_entries(hass, adapters)
    await async_discover_adapters(hass, adapters)

    return True


@hass_callback
def async_migrate_entries(
    hass: HomeAssistant,
    adapters: dict[str, AdapterDetails],
) -> None:
    """Migrate config entries to support multiple."""
    current_entries = hass.config_entries.async_entries(DOMAIN)
    default_adapter = async_default_adapter()

    for entry in current_entries:
        if entry.unique_id:
            continue

        address = DEFAULT_ADDRESS
        adapter = entry.options.get(CONF_ADAPTER, default_adapter)
        if adapter in adapters:
            address = adapters[adapter][ADAPTER_ADDRESS]
        hass.config_entries.async_update_entry(
            entry, title=adapter_unique_name(adapter, address), unique_id=address
        )


async def async_discover_adapters(
    hass: HomeAssistant,
    adapters: dict[str, AdapterDetails],
) -> None:
    """Discover adapters and start flows."""
    if platform.system() == "Windows":
        # We currently do not have a good way to detect if a bluetooth device is
        # available on Windows. We will just assume that it is not unless they
        # actively add it.
        return

    for adapter, details in adapters.items():
        discovery_flow.async_create_flow(
            hass,
            DOMAIN,
            context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
            data={CONF_ADAPTER: adapter, CONF_DETAILS: details},
        )


async def async_update_device(
    entry: config_entries.ConfigEntry,
    manager: BluetoothManager,
    adapter: str,
    address: str,
) -> None:
    """Update device registry entry.

    The physical adapter can change from hci0/hci1 on reboot
    or if the user moves around the usb sticks so we need to
    update the device with the new location so they can
    figure out where the adapter is.
    """
    adapters = await manager.async_get_bluetooth_adapters()
    details = adapters[adapter]
    registry = dr.async_get(manager.hass)
    registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        name=adapter_human_name(adapter, details[ADAPTER_ADDRESS]),
        connections={(dr.CONNECTION_BLUETOOTH, details[ADAPTER_ADDRESS])},
        sw_version=details.get(ADAPTER_SW_VERSION),
        hw_version=details.get(ADAPTER_HW_VERSION),
    )


async def async_setup_entry(
    hass: HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
    """Set up a config entry for a bluetooth scanner."""
    manager: BluetoothManager = hass.data[DATA_MANAGER]
    address = entry.unique_id
    assert address is not None
    adapter = await manager.async_get_adapter_from_address(address)
    if adapter is None:
        raise ConfigEntryNotReady(
            f"Bluetooth adapter {adapter} with address {address} not found"
        )

    try:
        bleak_scanner = create_bleak_scanner(BluetoothScanningMode.ACTIVE, adapter)
    except RuntimeError as err:
        raise ConfigEntryNotReady(
            f"{adapter_human_name(adapter, address)}: {err}"
        ) from err
    scanner = HaScanner(hass, bleak_scanner, adapter, address)
    entry.async_on_unload(scanner.async_register_callback(manager.scanner_adv_received))
    try:
        await scanner.async_start()
    except ScannerStartError as err:
        raise ConfigEntryNotReady from err
    entry.async_on_unload(manager.async_register_scanner(scanner))
    await async_update_device(entry, manager, adapter, address)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = scanner
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
    """Unload a config entry."""
    scanner: HaScanner = hass.data[DOMAIN].pop(entry.entry_id)
    await scanner.async_stop()
    return True
