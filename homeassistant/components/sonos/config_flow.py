"""Config flow for SONOS."""
import logging

import pysonos

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.config_entry_flow import DiscoveryFlowHandler
from homeassistant.helpers.typing import DiscoveryInfoType

from .const import DATA_SONOS_DISCOVERY_MANAGER, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def _async_has_devices(hass: HomeAssistant) -> bool:
    """Return if there are devices that can be discovered."""
    result = await hass.async_add_executor_job(pysonos.discover)
    return bool(result)


class SonosDiscoveryFlowHandler(DiscoveryFlowHandler):
    """Sonos discovery flow that callsback zeroconf updates."""

    def __init__(self) -> None:
        """Init discovery flow."""
        super().__init__(DOMAIN, "Sonos", _async_has_devices)

    async def async_step_zeroconf(
        self, discovery_info: DiscoveryInfoType
    ) -> FlowResult:
        """Handle a flow initialized by zeroconf."""
        hostname = discovery_info["hostname"]
        if hostname is None or not hostname.startswith("Sonos-"):
            return self.async_abort(reason="not_sonos_device")
        await self.async_set_unique_id(self._domain, raise_on_progress=False)
        host = discovery_info[CONF_HOST]
        boot_seqnum = discovery_info["properties"].get("bootseq")
        # TODO: make a utility to convert hostnames to uids
        baseuid = hostname.split("-")[1].replace(".local.", "")
        uid = f"RINCON_{baseuid}01400"
        _LOGGER.debug(
            "Calling async_discovered_player for %s with uid=%s and boot_seqnum=%s",
            host,
            uid,
            boot_seqnum,
        )
        self.hass.data[DATA_SONOS_DISCOVERY_MANAGER].async_discovered_player(
            discovery_info["properties"], host, uid, boot_seqnum
        )
        return await self.async_step_discovery(discovery_info)


config_entries.HANDLERS.register(DOMAIN)(SonosDiscoveryFlowHandler)
