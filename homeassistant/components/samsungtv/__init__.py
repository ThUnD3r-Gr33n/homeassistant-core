"""The Samsung TV integration."""
import socket

import voluptuous as vol

from homeassistant.components.media_player.const import DOMAIN as MP_DOMAIN
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
import homeassistant.helpers.config_validation as cv

from .const import CONF_ON_ACTION, DEFAULT_NAME, DOMAIN

UNDO_UPDATE_LISTENER = "update_update_listener"


def ensure_unique_hosts(value):
    """Validate that all configs have a unique host."""
    vol.Schema(vol.Unique("duplicate host entries found"))(
        [socket.gethostbyname(entry[CONF_HOST]) for entry in value]
    )
    return value


CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.All(
            cv.ensure_list,
            [
                cv.deprecated(CONF_PORT),
                vol.Schema(
                    {
                        vol.Required(CONF_HOST): cv.string,
                        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
                        vol.Optional(CONF_PORT): cv.port,
                        vol.Optional(CONF_ON_ACTION): cv.SCRIPT_SCHEMA,
                    }
                ),
            ],
            ensure_unique_hosts,
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass, config):
    """Set up the Samsung TV integration."""
    if DOMAIN in config:
        hass.data[DOMAIN] = {}
        for entry_config in config[DOMAIN]:
            ip_address = await hass.async_add_executor_job(
                socket.gethostbyname, entry_config[CONF_HOST]
            )
            hass.data[DOMAIN][ip_address] = {
                CONF_ON_ACTION: entry_config.get(CONF_ON_ACTION)
            }
            hass.async_create_task(
                hass.config_entries.flow.async_init(
                    DOMAIN, context={"source": "import"}, data=entry_config
                )
            )

    return True


async def async_setup_entry(hass, entry):
    """Set up the Samsung TV platform."""
    undo_listener = entry.add_update_listener(_update_listener)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        UNDO_UPDATE_LISTENER: undo_listener,
    }

    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, MP_DOMAIN)
    )

    return True


async def async_unload_entry(hass, entry):
    """Unload a config entry."""
    unload_ok = await hass.async_create_task(
        hass.config_entries.async_forward_entry_unload(entry, MP_DOMAIN)
    )

    if unload_ok:
        hass.data[DOMAIN][entry.entry_id][UNDO_UPDATE_LISTENER]()
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def _update_listener(hass, entry):
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)
