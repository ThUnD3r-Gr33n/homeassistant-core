"""The Synology DSM component."""
from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
import logging

from synology_dsm import SynologyDSM
from synology_dsm.api.core.security import SynoCoreSecurity
from synology_dsm.api.core.system import SynoCoreSystem
from synology_dsm.api.core.upgrade import SynoCoreUpgrade
from synology_dsm.api.core.utilization import SynoCoreUtilization
from synology_dsm.api.dsm.information import SynoDSMInformation
from synology_dsm.api.dsm.network import SynoDSMNetwork
from synology_dsm.api.photos import SynoPhotos
from synology_dsm.api.storage.storage import SynoStorage
from synology_dsm.api.surveillance_station import SynoSurveillanceStation
from synology_dsm.exceptions import (
    SynologyDSMAPIErrorException,
    SynologyDSMException,
    SynologyDSMRequestException,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SSL,
    CONF_TIMEOUT,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_DEVICE_TOKEN, DEFAULT_TIMEOUT, SYNOLOGY_CONNECTION_EXCEPTIONS

LOGGER = logging.getLogger(__name__)


class SynoApi:
    """Class to interface with Synology DSM API."""

    information: SynoDSMInformation
    network: SynoDSMNetwork

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the API wrapper class."""
        self._hass = hass
        self._entry = entry
        if entry.data.get(CONF_SSL):
            self.config_url = f"https://{entry.data[CONF_HOST]}:{entry.data[CONF_PORT]}"
        else:
            self.config_url = f"http://{entry.data[CONF_HOST]}:{entry.data[CONF_PORT]}"

        # DSM APIs
        session = async_get_clientsession(hass, entry.data[CONF_VERIFY_SSL])
        self.dsm = SynologyDSM(
            session,
            entry.data[CONF_HOST],
            entry.data[CONF_PORT],
            entry.data[CONF_USERNAME],
            entry.data[CONF_PASSWORD],
            entry.data[CONF_SSL],
            timeout=entry.options.get(CONF_TIMEOUT, DEFAULT_TIMEOUT),
            device_token=entry.data.get(CONF_DEVICE_TOKEN),
        )
        self.security: SynoCoreSecurity | None = None
        self.storage: SynoStorage | None = None
        self.photos: SynoPhotos | None = None
        self.surveillance_station: SynoSurveillanceStation | None = None
        self.system: SynoCoreSystem | None = None
        self.upgrade: SynoCoreUpgrade | None = None
        self.utilisation: SynoCoreUtilization | None = None

        # Should we fetch them
        self._fetching_entities: dict[str, set[str]] = {}
        self._with_information = True
        self._with_security = True
        self._with_storage = True
        self._with_photos = True
        self._with_surveillance_station = True
        self._with_system = True
        self._with_upgrade = True
        self._with_utilisation = True

    async def async_setup(self) -> None:
        """Start interacting with the NAS."""
        await self.dsm.login()

        # check if surveillance station is used
        self._with_surveillance_station = bool(
            self.dsm.apis.get(SynoSurveillanceStation.CAMERA_API_KEY)
        )
        if self._with_surveillance_station:
            try:
                await self.dsm.surveillance_station.update()
            except SYNOLOGY_CONNECTION_EXCEPTIONS:
                self._with_surveillance_station = False
                self.dsm.reset(SynoSurveillanceStation.API_KEY)
                LOGGER.info(
                    "Surveillance Station found, but disabled due to missing user"
                    " permissions"
                )

        LOGGER.debug(
            "State of Surveillance_station during setup of '%s': %s",
            self._entry.unique_id,
            self._with_surveillance_station,
        )

        # check if upgrade is available
        try:
            await self.dsm.upgrade.update()
        except SYNOLOGY_CONNECTION_EXCEPTIONS as ex:
            self._with_upgrade = False
            self.dsm.reset(SynoCoreUpgrade.API_KEY)
            LOGGER.debug("Disabled fetching upgrade data during setup: %s", ex)

        await self._fetch_device_configuration()

        try:
            await self._update()
        except SYNOLOGY_CONNECTION_EXCEPTIONS as err:
            LOGGER.debug(
                "Connection error during setup of '%s' with exception: %s",
                self._entry.unique_id,
                err,
            )
            raise err

    @callback
    def subscribe(self, api_key: str, unique_id: str) -> Callable[[], None]:
        """Subscribe an entity to API fetches."""
        LOGGER.debug("Subscribe new entity: %s", unique_id)
        if api_key not in self._fetching_entities:
            self._fetching_entities[api_key] = set()
        self._fetching_entities[api_key].add(unique_id)

        @callback
        def unsubscribe() -> None:
            """Unsubscribe an entity from API fetches (when disable)."""
            LOGGER.debug("Unsubscribe entity: %s", unique_id)
            self._fetching_entities[api_key].remove(unique_id)
            if len(self._fetching_entities[api_key]) == 0:
                self._fetching_entities.pop(api_key)

        return unsubscribe

    def _setup_api_requests(self) -> None:
        """Determine if we should fetch each API, if one entity needs it."""
        # Entities not added yet, fetch all
        if not self._fetching_entities:
            LOGGER.debug(
                "Entities not added yet, fetch all for '%s'", self._entry.unique_id
            )
            return

        # surveillance_station is updated by own coordinator
        if self.surveillance_station is not None:
            self.dsm.reset(self.surveillance_station)

        # Determine if we should fetch an API
        self._with_system = bool(self.dsm.apis.get(SynoCoreSystem.API_KEY))
        self._with_security = bool(
            self._fetching_entities.get(SynoCoreSecurity.API_KEY)
        )
        self._with_storage = bool(self._fetching_entities.get(SynoStorage.API_KEY))
        self._with_photos = bool(self._fetching_entities.get(SynoStorage.API_KEY))
        self._with_upgrade = bool(self._fetching_entities.get(SynoCoreUpgrade.API_KEY))
        self._with_utilisation = bool(
            self._fetching_entities.get(SynoCoreUtilization.API_KEY)
        )
        self._with_information = bool(
            self._fetching_entities.get(SynoDSMInformation.API_KEY)
        )

        # Reset not used API, information is not reset since it's used in device_info
        if not self._with_security and self.security is not None:
            LOGGER.debug(
                "Disable security api from being updated for '%s'",
                self._entry.unique_id,
            )
            self.dsm.reset(self.security)
            self.security = None

        if not self._with_photos and self.photos is not None:
            LOGGER.debug(
                "Disable photos api from being updated or '%s'", self._entry.unique_id
            )
            self.dsm.reset(self.photos)
            self.photos = None

        if not self._with_storage and self.storage is not None:
            LOGGER.debug(
                "Disable storage api from being updatedf or '%s'", self._entry.unique_id
            )
            self.dsm.reset(self.storage)
            self.storage = None

        if not self._with_system and self.system is not None:
            LOGGER.debug(
                "Disable system api from being updated for '%s'", self._entry.unique_id
            )
            self.dsm.reset(self.system)
            self.system = None

        if not self._with_upgrade and self.upgrade is not None:
            LOGGER.debug(
                "Disable upgrade api from being updated for '%s'", self._entry.unique_id
            )
            self.dsm.reset(self.upgrade)
            self.upgrade = None

        if not self._with_utilisation and self.utilisation is not None:
            LOGGER.debug(
                "Disable utilisation api from being updated for '%s'",
                self._entry.unique_id,
            )
            self.dsm.reset(self.utilisation)
            self.utilisation = None

    async def _fetch_device_configuration(self) -> None:
        """Fetch initial device config."""
        self.information = self.dsm.information
        self.network = self.dsm.network
        await self.network.update()

        if self._with_security:
            LOGGER.debug("Enable security api updates for '%s'", self._entry.unique_id)
            self.security = self.dsm.security

        if self._with_photos:
            LOGGER.debug("Enable photos api updates for '%s'", self._entry.unique_id)
            self.photos = self.dsm.photos

        if self._with_storage:
            LOGGER.debug("Enable storage api updates for '%s'", self._entry.unique_id)
            self.storage = self.dsm.storage

        if self._with_upgrade:
            LOGGER.debug("Enable upgrade api updates for '%s'", self._entry.unique_id)
            self.upgrade = self.dsm.upgrade

        if self._with_system:
            LOGGER.debug("Enable system api updates for '%s'", self._entry.unique_id)
            self.system = self.dsm.system

        if self._with_utilisation:
            LOGGER.debug(
                "Enable utilisation api updates for '%s'", self._entry.unique_id
            )
            self.utilisation = self.dsm.utilisation

        if self._with_surveillance_station:
            LOGGER.debug(
                "Enable surveillance_station api updates for '%s'",
                self._entry.unique_id,
            )
            self.surveillance_station = self.dsm.surveillance_station

    async def _syno_api_executer(self, api_call: Callable) -> None:
        """Synology api call wrapper."""
        try:
            await api_call()
        except (SynologyDSMAPIErrorException, SynologyDSMRequestException) as err:
            LOGGER.debug(
                "Error from '%s': %s", self._entry.unique_id, err, exc_info=True
            )
            raise err

    async def async_reboot(self) -> None:
        """Reboot NAS."""
        if self.system is not None:
            await self._syno_api_executer(self.system.reboot)

    async def async_shutdown(self) -> None:
        """Shutdown NAS."""
        if self.system is not None:
            await self._syno_api_executer(self.system.shutdown)

    async def async_unload(self) -> None:
        """Stop interacting with the NAS and prepare for removal from hass."""
        # ignore API errors during logout
        with suppress(SynologyDSMException):
            await self._syno_api_executer(self.dsm.logout)

    async def async_update(self) -> None:
        """Update function for updating API information."""
        try:
            await self._update()
        except SYNOLOGY_CONNECTION_EXCEPTIONS as err:
            LOGGER.debug(
                "Connection error during update of '%s' with exception: %s",
                self._entry.unique_id,
                err,
            )
            LOGGER.warning(
                "Connection error during update, fallback by reloading the entry"
            )
            await self._hass.config_entries.async_reload(self._entry.entry_id)

    async def _update(self) -> None:
        """Update function for updating API information."""
        LOGGER.debug("Start data update for '%s'", self._entry.unique_id)
        self._setup_api_requests()

        await self.dsm.update(self._with_information)
