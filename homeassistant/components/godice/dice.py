"""Contains a factory function to create a Dice and code for connection handling."""

import asyncio
import enum
import logging

from bleak import BleakClient
from bleak.backends.device import BLEDevice
from bleak_retry_connector import (
    BleakError,
    close_stale_connections,
    establish_connection,
)
import godice

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


def create_dice(hass: HomeAssistant, entry: ConfigEntry):
    """Create a Dice representative object."""
    handler = DiceConnectionHandler(hass, entry)
    return DiceProxy(handler)


class ConnectionState(enum.Enum):
    """Indicates GoDice connection state."""

    CONNECTED = 0
    DISCONNECTED = 1
    CONNECTING = 2


class DiceConnectionObserver:
    """Defines events generated by DiceConnectionHandler."""

    async def on_connected(self, _dice):
        """Event generated when device connection established."""

    async def on_reconnecting(self):
        """Event generated when device is lost and reconnection started."""

    async def on_disconnected(self):
        """Event generated when device is lost and reconnection failed."""


class DiceConnectionHandler:
    """An object responsible for connection establishment and reconnection when connection is lost."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Set default values required for connection establishment."""
        self.mac = entry.data["address"]
        self.hass: HomeAssistant = hass
        self.config_entry = entry
        self._bledev: BLEDevice | None = None
        self._client = None
        self._bledev_upd_cancel = bluetooth.async_register_callback(
            hass,
            self._upd_bledev,
            bluetooth.BluetoothCallbackMatcher({bluetooth.match.ADDRESS: self.mac}),
            bluetooth.BluetoothScanningMode.ACTIVE,
        )
        self._conn_lock = asyncio.Lock()
        self._disconnect_handler = self._on_connection_lost_while_connecting_handler
        self.observer: DiceConnectionObserver | None = None

    async def connect(self):
        """Start connection process."""
        async with self._conn_lock:
            await self._do_connect()

    async def reconnect(self, _name="reconnect"):
        """Start reconnection process."""
        try:
            async with self._conn_lock:
                await self._do_connect()
        except BleakError:
            self.hass.create_task(
                self.hass.config_entries.async_reload(self.config_entry.entry_id)
            )

    async def disconnect(self):
        """Disconnect the device."""
        async with self._conn_lock:
            await self._do_disconnect()

    async def _do_connect(self):
        _LOGGER.debug("Connecting")
        await self._notify_reconnecting()
        self._bledev = self._bledev or bluetooth.async_ble_device_from_address(
            self.hass, self.mac
        )
        try:
            self._client = await establish_connection(
                client_class=BleakClient,
                device=self._bledev,
                name=self.mac,
                disconnected_callback=self._on_disconnected_handler,
                max_attempts=3,
                use_services_cache=True,
            )
            await self._notify_connected(self._client)
            self._disconnect_handler = self._on_connection_lost_after_connected_handler
            _LOGGER.debug("Connection completed")
        except BleakError as e:
            _LOGGER.debug("Connection attempts timed out")
            await close_stale_connections(self._bledev)
            await self._notify_disconnected()
            raise e

    async def _do_disconnect(self):
        _LOGGER.debug("Disconnect called")
        if self._client:
            _LOGGER.debug("Disconnect started")
            self._disconnect_handler = self._on_disconnected_by_request_handler
            await self._client.disconnect()
            await self._notify_disconnected()
        await close_stale_connections(self._bledev)
        self._client = None

    def _on_connection_lost_while_connecting_handler(self, _data):
        _LOGGER.debug("Connection lost while connecting. Reconnection is skipped")

    def _on_connection_lost_after_connected_handler(self, _data):
        _LOGGER.debug("Connection lost. Reconnection started")
        self._disconnect_handler = self._on_connection_lost_while_connecting_handler
        self.hass.create_task(self.reconnect())

    def _on_disconnected_by_request_handler(self, _data):
        _LOGGER.debug("Disconnected by request. Reconnection is skipped")

    def _on_disconnected_handler(self, data):
        _LOGGER.debug("Disconnect event received")
        self._disconnect_handler(data)

    def _upd_bledev(
        self,
        service_info: bluetooth.BluetoothServiceInfoBleak,
        change: bluetooth.BluetoothChange,
    ):
        self._bledev = service_info.device

    def set_observer(self, observer: DiceConnectionObserver):
        """Add a connection observer."""
        self.observer = observer

    async def _notify_connected(self, client):
        await self.observer.on_connected(client)

    async def _notify_reconnecting(self):
        await self.observer.on_reconnecting()

    async def _notify_disconnected(self):
        await self.observer.on_disconnected()


class DiceProxy(DiceConnectionObserver):
    """Proxy between HA and Dice, keeps HA unaware of connection issues and reconnection to Dice."""

    def __init__(self, conn_handler) -> None:
        """Set default values and setup itself as a connection events observer."""
        self.conn_handler = conn_handler
        self.conn_handler.set_observer(self)
        self.dice = None

        self._last_color = None
        self._last_battery = None
        self._last_state = None

        async def _noop(*args, **kwargs):
            pass

        self._rolled_number_cb = _noop
        self._conn_state_cb = _noop

    async def on_connected(self, ble_client):
        """Configure proxy to respond with real device data when a device is connected."""
        dice = godice.create(ble_client, godice.Shell.D6)
        await dice.connect()
        self.dice = dice
        self._last_state = ConnectionState.CONNECTED

        await self.dice.subscribe_number_notification(self._rolled_number_cb)
        await self._conn_state_cb(self._last_state)

    async def on_reconnecting(self):
        """Configure proxy to respond with cached data while connection is in progress."""
        self.dice = None
        self._last_state = ConnectionState.CONNECTING
        await self._conn_state_cb(self._last_state)

    async def on_disconnected(self):
        """Configure proxy to keep responding with cached data when connection is lost."""
        self.dice = None
        self._last_state = ConnectionState.DISCONNECTED
        await self._conn_state_cb(self._last_state)

    async def connect(self):
        """Connect to the Dice."""
        await self.conn_handler.connect()

    async def disconnect(self):
        """Disconnect from the Dice."""
        await self.conn_handler.disconnect()

    async def get_color(self):
        """Get Dice color."""
        if not self.dice:
            return self._last_color
        self._last_color = await self.dice.get_color()
        return self._last_color

    async def get_battery_level(self):
        """Get Dice battery level."""
        if not self.dice:
            return self._last_battery
        self._last_battery = await self.dice.get_battery_level()
        return self._last_battery

    async def subscribe_number_notification(self, callback):
        """Subscribe for receiving notifications with new numbers when Dice is rolled."""
        self._rolled_number_cb = callback
        if self.dice:
            await self.dice.subscribe_number_notification(callback)

    async def subscribe_connection_notification(self, callback):
        """Subscribe for receiving notifications about connection state."""
        self._conn_state_cb = callback
        await callback(self._last_state)

    async def pulse_led(self, *args, **kwargs):
        """Pulse built-in LEDs."""
        if self.dice:
            await self.dice.pulse_led(*args, **kwargs)
