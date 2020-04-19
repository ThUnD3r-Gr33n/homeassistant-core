"""The Panasonic Viera integration."""
import asyncio
from functools import partial
import logging
from urllib.request import URLError

from panasonic_viera import EncryptionRequired, Keys, RemoteControl, SOAPError
import voluptuous as vol

from homeassistant.components.media_player.const import (
    DOMAIN as MEDIA_PLAYER_DOMAIN,
    MEDIA_TYPE_URL,
)
from homeassistant.components.remote import DOMAIN as REMOTE_DOMAIN
from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, STATE_OFF, STATE_ON
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.script import Script

from .const import (
    ATTR_REMOTE,
    CONF_APP_ID,
    CONF_ENCRYPTION_KEY,
    CONF_ON_ACTION,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.All(
            cv.ensure_list,
            [
                vol.Schema(
                    {
                        vol.Required(CONF_HOST): cv.string,
                        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
                        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
                        vol.Optional(CONF_ON_ACTION): cv.SCRIPT_SCHEMA,
                    }
                )
            ],
        )
    },
    extra=vol.ALLOW_EXTRA,
)

PLATFORMS = [MEDIA_PLAYER_DOMAIN, REMOTE_DOMAIN]


async def async_setup(hass, config):
    """Set up Panasonic Viera from configuration.yaml."""
    if DOMAIN not in config:
        return True

    for conf in config[DOMAIN]:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, context={"source": SOURCE_IMPORT}, data=conf
            )
        )

    return True


async def async_setup_entry(hass, config_entry):
    """Set up Panasonic Viera from a config entry."""

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    config = config_entry.data

    host = config[CONF_HOST]
    port = config[CONF_PORT]

    on_action = config[CONF_ON_ACTION]
    if on_action is not None:
        on_action = Script(hass, on_action)

    params = {}
    if CONF_APP_ID in config and CONF_ENCRYPTION_KEY in config:
        params["app_id"] = config[CONF_APP_ID]
        params["encryption_key"] = config[CONF_ENCRYPTION_KEY]

    remote = Remote(hass, host, port, on_action, **params)
    await remote.async_create_remote_control(during_setup=True)

    hass.data[DOMAIN][host] = {ATTR_REMOTE: remote}

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(config_entry, component)
        )

    return True


async def async_unload_entry(hass, config_entry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(config_entry, component)
                for component in PLATFORMS
            ]
        )
    )

    if unload_ok:
        hass.data[DOMAIN].pop(config_entry.data[CONF_HOST])

    return unload_ok


class Remote:
    """The Remote class. It stores the TV properties and the remote control connection itself."""

    def __init__(
        self, hass, host, port, on_action=None, app_id=None, encryption_key=None,
    ):
        """Initialize the Remote class."""
        self._hass = hass

        self._host = host
        self._port = port

        self._on_action = on_action

        self._app_id = app_id
        self._encryption_key = encryption_key

        self.state = None
        self.available = False
        self.volume = 0
        self.muted = False
        self.playing = True

        self._control = None

    async def async_create_remote_control(self, during_setup=False):
        """Create remote control."""
        control_existed = self._control is not None
        try:
            params = {}
            if self._app_id and self._encryption_key:
                params["app_id"] = self._app_id
                params["encryption_key"] = self._encryption_key

            self._control = await self._hass.async_add_executor_job(
                partial(RemoteControl, self._host, self._port, **params)
            )

            self.state = STATE_ON
            self.available = True
        except (TimeoutError, URLError, SOAPError, OSError) as err:
            if control_existed or during_setup:
                _LOGGER.error("Could not establish remote connection: %s", err)

            self._control = None
            self.state = STATE_OFF
            self.available = self._on_action is not None
        except Exception as err:  # pylint: disable=broad-except
            if control_existed or during_setup:
                _LOGGER.exception("An unknown error occurred: %s", err)
                self._control = None
                self.state = STATE_OFF
                self.available = self._on_action is not None

    async def async_update(self):
        """Update device data."""
        if self._control is None:
            await self.async_create_remote_control()
            return

        await self._handle_errors(self._update)

    async def _update(self):
        """Retrieve the latest data."""
        self.muted = self._control.get_mute()
        self.volume = self._control.get_volume() / 100

        self.state = STATE_ON
        self.available = True

    async def async_send_key(self, key):
        """Send a key to the TV and handle exceptions."""
        if key in Keys._member_names_:  # pylint: disable=no-member, protected-access
            await self._handle_errors(self._control.send_key, Keys[key])
        elif (
            key
            in Keys._value2member_map_  # pylint: disable=no-member, protected-access
        ):
            await self._handle_errors(self._control.send_key, key)
        else:
            _LOGGER.error("Key command not supported")

    async def async_turn_on(self):
        """Turn on the TV."""
        if self._on_action is not None:
            await self._on_action.async_run()
            self.state = STATE_ON
        elif self.state != STATE_ON:
            await self.async_send_key(Keys.power)
            self.state = STATE_ON

    async def async_turn_off(self):
        """Turn off the TV."""
        if self.state != STATE_OFF:
            await self.async_send_key(Keys.power)
            self.state = STATE_OFF
            await self.async_update()

    async def async_set_mute(self, enable):
        """Set mute based on 'enable'."""
        await self._handle_errors(self._control.set_mute, enable)

    async def async_set_volume(self, volume):
        """Set volume level, range 0..1."""
        volume = int(volume * 100)
        await self._handle_errors(self._control.set_volume, volume)

    async def async_play_media(self, media_type, media_id):
        """Play media."""
        _LOGGER.debug("Play media: %s (%s)", media_id, media_type)

        if media_type != MEDIA_TYPE_URL:
            _LOGGER.warning("Unsupported media_type: %s", media_type)
            return

        await self._handle_errors(self._control.open_webpage, media_id)

    async def _handle_errors(self, func, *args):
        """Handle errors from func, set available and reconnect if needed."""
        try:
            await self._hass.async_add_executor_job(func, *args)
        except EncryptionRequired:
            _LOGGER.error("The connection couldn't be encrypted")
        except (TimeoutError, URLError, SOAPError, OSError):
            self.state = STATE_OFF
            self.available = self._on_action is not None
            await self.async_create_remote_control()
