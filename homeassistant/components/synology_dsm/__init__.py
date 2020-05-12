"""The Synology DSM component."""
import asyncio
from datetime import timedelta
from typing import Dict

from synology_dsm import SynologyDSM
from synology_dsm.api.core.security import SynoCoreSecurity
from synology_dsm.api.core.utilization import SynoCoreUtilization
from synology_dsm.api.dsm.information import SynoDSMInformation
from synology_dsm.api.storage.storage import SynoStorage
import voluptuous as vol

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    CONF_DISKS,
    CONF_HOST,
    CONF_MAC,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_SSL,
    CONF_USERNAME,
)
from homeassistant.helpers import entity_registry
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import HomeAssistantType

from .const import (
    BASE_NAME,
    CONF_VOLUMES,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SSL,
    DOMAIN,
    ENTITY_CLASS,
    ENTITY_ENABLE,
    ENTITY_ICON,
    ENTITY_NAME,
    ENTITY_UNIT,
    PLATFORMS,
    SYNO_API,
    TEMP_SENSORS_KEYS,
    UNDO_UPDATE_LISTENER,
)

CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_PORT): cv.port,
        vol.Optional(CONF_SSL, default=DEFAULT_SSL): cv.boolean,
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_DISKS): cv.ensure_list,
        vol.Optional(CONF_VOLUMES): cv.ensure_list,
    }
)

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.Schema(vol.All(cv.ensure_list, [CONFIG_SCHEMA]))},
    extra=vol.ALLOW_EXTRA,
)

ATTRIBUTION = "Data provided by Synology"


async def async_setup(hass, config):
    """Set up Synology DSM sensors from legacy config file."""

    conf = config.get(DOMAIN)
    if conf is None:
        return True

    for dsm_conf in conf:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, context={"source": SOURCE_IMPORT}, data=dsm_conf,
            )
        )

    return True


async def async_setup_entry(hass: HomeAssistantType, entry: ConfigEntry):
    """Set up Synology DSM sensors."""
    api = SynoApi(hass, entry)

    await api.async_setup()

    undo_listener = entry.add_update_listener(_async_update_listener)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.unique_id] = {
        SYNO_API: api,
        UNDO_UPDATE_LISTENER: undo_listener,
    }

    # For SSDP compat
    if not entry.data.get(CONF_MAC):
        network = await hass.async_add_executor_job(getattr, api.dsm, "network")
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, CONF_MAC: network.macs}
        )

    for platform in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, platform)
        )

    return True


async def async_unload_entry(hass: HomeAssistantType, entry: ConfigEntry):
    """Unload Synology DSM sensors."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, platform)
                for platform in PLATFORMS
            ]
        )
    )

    if unload_ok:
        entry_data = hass.data[DOMAIN][entry.unique_id]
        entry_data[UNDO_UPDATE_LISTENER]()
        await entry_data[SYNO_API].async_unload()
        hass.data[DOMAIN].pop(entry.unique_id)

    return unload_ok


async def _async_update_listener(hass: HomeAssistantType, entry: ConfigEntry):
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


class SynoApi:
    """Class to interface with Synology DSM API."""

    def __init__(self, hass: HomeAssistantType, entry: ConfigEntry):
        """Initialize the API wrapper class."""
        self._hass = hass
        self._entry = entry

        # DSM APIs
        self.dsm: SynologyDSM = None
        self.information: SynoDSMInformation = None
        self.security: SynoCoreSecurity = None
        self.storage: SynoStorage = None
        self.utilisation: SynoCoreUtilization = None

        # Should we fetch them
        self._with_security = False
        self._with_storage = False
        self._with_utilisation = False

        self._unsub_dispatcher = None

    @property
    def signal_sensor_update(self) -> str:
        """Event specific per Synology DSM entry to signal updates in sensors."""
        return f"{DOMAIN}-{self.information.serial}-sensor-update"

    async def async_setup(self):
        """Start interacting with the NAS."""
        self.dsm = SynologyDSM(
            self._entry.data[CONF_HOST],
            self._entry.data[CONF_PORT],
            self._entry.data[CONF_USERNAME],
            self._entry.data[CONF_PASSWORD],
            self._entry.data[CONF_SSL],
            device_token=self._entry.data.get("device_token"),
        )

        await self._should_fetch_api()

        await self._hass.async_add_executor_job(self._fetch_device_configuration)
        await self.async_update()

        self._unsub_dispatcher = async_track_time_interval(
            self._hass,
            self.async_update,
            timedelta(
                minutes=self._entry.options.get(
                    CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                )
            ),
        )

    async def _should_fetch_api(self):

        entity_reg = await self._hass.helpers.entity_registry.async_get_registry()
        entity_entries = entity_registry.async_entries_for_config_entry(
            entity_reg, self._entry.entry_id
        )
        # Entities not added yet
        if not entity_entries:
            self._with_security = True
            self._with_storage = True
            self._with_utilisation = True
            return

        # Determine which if at least one entity uses specific API
        self._with_security = False
        self._with_storage = False
        self._with_utilisation = False
        for entity_entry in entity_entries:
            # Pass disabled entries
            if entity_entry.disabled_by:
                continue

            # Check if we should fetch specific APIs
            if SynoCoreSecurity.API_KEY in entity_entry.unique_id:
                self._with_security = True
                continue

            if SynoStorage.API_KEY in entity_entry.unique_id:
                self._with_storage = True
                continue

            if SynoCoreUtilization.API_KEY in entity_entry.unique_id:
                self._with_utilisation = True
                continue

        # Reset not used API
        if not self._with_security:
            self.dsm._security = None  # pylint: disable=protected-access
            self.security = None

        if not self._with_storage:
            self.dsm._storage = None  # pylint: disable=protected-access
            self.storage = None

        if not self._with_utilisation:
            self.dsm._utilisation = None  # pylint: disable=protected-access
            self.utilisation = None

    def _fetch_device_configuration(self):
        """Fetch initial device config."""
        self.information = self.dsm.information

        if self._with_security:
            self.security = self.dsm.security

        if self._with_storage:
            self.storage = self.dsm.storage

        if self._with_utilisation:
            self.utilisation = self.dsm.utilisation

    async def async_unload(self):
        """Stop interacting with the NAS and prepare for removal from hass."""
        self._unsub_dispatcher()

    async def async_update(self, now=None):
        """Update function for updating API information."""
        await self._should_fetch_api()
        await self._hass.async_add_executor_job(self.dsm.update)
        async_dispatcher_send(self._hass, self.signal_sensor_update)


class SynologyDSMEntity(Entity):
    """Representation of a Synology NAS entry."""

    def __init__(
        self,
        api: SynoApi,
        entity_type: str,
        entity_info: Dict[str, str],
        device_id: str = None,
    ):
        """Initialize the Synology DSM entity."""
        self._api = api
        self.entity_type = entity_type.split(":")[-1]
        self._name = BASE_NAME
        self._class = entity_info[ENTITY_CLASS]
        self._enable_default = entity_info[ENTITY_ENABLE]
        self._icon = entity_info[ENTITY_ICON]
        self._unit = entity_info[ENTITY_UNIT]
        self._unique_id = f"{self._api.information.serial}_{entity_type}"
        self._device_id = device_id
        self._device_name = None
        self._device_manufacturer = None
        self._device_model = None
        self._device_firmware = None
        self._device_type = None

        if self._device_id:
            if "volume" in entity_type:
                volume = self._api.storage._get_volume(self._device_id)
                # Volume does not have a name
                self._device_name = volume["id"].replace("_", " ").capitalize()
                self._device_manufacturer = "Synology"
                self._device_model = self._api.information.model
                self._device_firmware = self._api.information.version_string
                self._device_type = (
                    volume["device_type"]
                    .replace("_", " ")
                    .replace("raid", "RAID")
                    .replace("shr", "SHR")
                )
            elif "disk" in entity_type:
                disk = self._api.storage._get_disk(self._device_id)
                self._device_name = disk["name"]
                self._device_manufacturer = disk["vendor"]
                self._device_model = disk["model"].strip()
                self._device_firmware = disk["firm"]
                self._device_type = disk["diskType"]
            self._name += f" {self._device_name}"
            self._unique_id += f"_{self._device_id}"

        self._name += f" {entity_info[ENTITY_NAME]}"

        self._unsub_dispatcher = None

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return self._unique_id

    @property
    def name(self) -> str:
        """Return the name."""
        return self._name

    @property
    def icon(self) -> str:
        """Return the icon."""
        return self._icon

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit the value is expressed in."""
        if self.entity_type in TEMP_SENSORS_KEYS:
            return self._api.temp_unit
        return self._unit

    @property
    def device_class(self) -> str:
        """Return the class of this device."""
        return self._class

    @property
    def device_state_attributes(self) -> Dict[str, any]:
        """Return the state attributes."""
        return {ATTR_ATTRIBUTION: ATTRIBUTION}

    @property
    def device_info(self) -> Dict[str, any]:
        """Return the device information."""
        return {
            "identifiers": {(DOMAIN, self._api.information.serial)},
            "name": "Synology NAS",
            "manufacturer": "Synology",
            "model": self._api.information.model,
            "sw_version": self._api.information.version_string,
        }

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return if the entity should be enabled when first added to the entity registry."""
        return self._enable_default

    @property
    def should_poll(self) -> bool:
        """No polling needed."""
        return False

    async def async_update(self):
        """Only used by the generic entity update service."""
        if not self.enabled:
            return

        await self._api.async_update()

    async def async_added_to_hass(self):
        """Register state update callback."""
        self._unsub_dispatcher = async_dispatcher_connect(
            self.hass, self._api.signal_sensor_update, self.async_write_ha_state
        )

    async def async_will_remove_from_hass(self):
        """Clean up after entity before removal."""
        self._unsub_dispatcher()
