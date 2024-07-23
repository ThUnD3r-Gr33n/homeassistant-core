"""Summary data from Nextcoud."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Final

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfInformation,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.dt import utc_from_timestamp

from . import NextcloudConfigEntry
from .entity import NextcloudEntity

UNIT_OF_LOAD: Final[str] = "load"


@dataclass(frozen=True)
class NextcloudSensorEntityDescription(SensorEntityDescription):
    """Describes Nextcloud sensor entity."""

    value_fn: Callable[[str | int | float], str | int | float | datetime] = (
        lambda value: value
    )


SENSORS: Final[list[NextcloudSensorEntityDescription]] = [
    NextcloudSensorEntityDescription(
        key="activeUsers_last1hour",
        translation_key="nextcloud_activeusers_last1hour",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    NextcloudSensorEntityDescription(
        key="activeUsers_last24hours",
        translation_key="nextcloud_activeusers_last24hours",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    NextcloudSensorEntityDescription(
        key="activeUsers_last5minutes",
        translation_key="nextcloud_activeusers_last5minutes",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    NextcloudSensorEntityDescription(
        key="cache_expunges",
        translation_key="nextcloud_cache_expunges",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    NextcloudSensorEntityDescription(
        key="cache_mem_size",
        translation_key="nextcloud_cache_mem_size",
        device_class=SensorDeviceClass.DATA_SIZE,
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_display_precision=1,
        suggested_unit_of_measurement=UnitOfInformation.MEGABYTES,
    ),
    NextcloudSensorEntityDescription(
        key="cache_memory_type",
        translation_key="nextcloud_cache_memory_type",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    NextcloudSensorEntityDescription(
        key="cache_num_entries",
        translation_key="nextcloud_cache_num_entries",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    NextcloudSensorEntityDescription(
        key="cache_num_hits",
        translation_key="nextcloud_cache_num_hits",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    NextcloudSensorEntityDescription(
        key="cache_num_inserts",
        translation_key="nextcloud_cache_num_inserts",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    NextcloudSensorEntityDescription(
        key="cache_num_misses",
        translation_key="nextcloud_cache_num_misses",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    NextcloudSensorEntityDescription(
        key="cache_num_slots",
        translation_key="nextcloud_cache_num_slots",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    NextcloudSensorEntityDescription(
        key="cache_start_time",
        translation_key="nextcloud_cache_start_time",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda val: utc_from_timestamp(float(val)),
    ),
    NextcloudSensorEntityDescription(
        key="cache_ttl",
        translation_key="nextcloud_cache_ttl",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    NextcloudSensorEntityDescription(
        key="database_size",
        translation_key="nextcloud_database_size",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_display_precision=1,
        suggested_unit_of_measurement=UnitOfInformation.MEGABYTES,
    ),
    NextcloudSensorEntityDescription(
        key="database_type",
        translation_key="nextcloud_database_type",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    NextcloudSensorEntityDescription(
        key="database_version",
        translation_key="nextcloud_database_version",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    NextcloudSensorEntityDescription(
        key="interned_strings_usage_buffer_size",
        translation_key="nextcloud_interned_strings_usage_buffer_size",
        device_class=SensorDeviceClass.DATA_SIZE,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_display_precision=1,
        suggested_unit_of_measurement=UnitOfInformation.MEGABYTES,
    ),
    NextcloudSensorEntityDescription(
        key="interned_strings_usage_free_memory",
        translation_key="nextcloud_interned_strings_usage_free_memory",
        device_class=SensorDeviceClass.DATA_SIZE,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_display_precision=1,
        suggested_unit_of_measurement=UnitOfInformation.MEGABYTES,
    ),
    NextcloudSensorEntityDescription(
        key="interned_strings_usage_number_of_strings",
        translation_key="nextcloud_interned_strings_usage_number_of_strings",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    NextcloudSensorEntityDescription(
        key="interned_strings_usage_used_memory",
        translation_key="nextcloud_interned_strings_usage_used_memory",
        device_class=SensorDeviceClass.DATA_SIZE,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_display_precision=1,
        suggested_unit_of_measurement=UnitOfInformation.MEGABYTES,
    ),
    NextcloudSensorEntityDescription(
        key="jit_buffer_free",
        translation_key="nextcloud_jit_buffer_free",
        device_class=SensorDeviceClass.DATA_SIZE,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_display_precision=1,
        suggested_unit_of_measurement=UnitOfInformation.MEGABYTES,
    ),
    NextcloudSensorEntityDescription(
        key="jit_buffer_size",
        translation_key="nextcloud_jit_buffer_size",
        device_class=SensorDeviceClass.DATA_SIZE,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_display_precision=1,
        suggested_unit_of_measurement=UnitOfInformation.MEGABYTES,
    ),
    NextcloudSensorEntityDescription(
        key="jit_kind",
        translation_key="nextcloud_jit_kind",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    NextcloudSensorEntityDescription(
        key="jit_opt_flags",
        translation_key="nextcloud_jit_opt_flags",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    NextcloudSensorEntityDescription(
        key="jit_opt_level",
        translation_key="nextcloud_jit_opt_level",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    NextcloudSensorEntityDescription(
        key="opcache_statistics_blacklist_miss_ratio",
        translation_key="nextcloud_opcache_statistics_blacklist_miss_ratio",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        native_unit_of_measurement=PERCENTAGE,
    ),
    NextcloudSensorEntityDescription(
        key="opcache_statistics_blacklist_misses",
        translation_key="nextcloud_opcache_statistics_blacklist_misses",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    NextcloudSensorEntityDescription(
        key="opcache_statistics_hash_restarts",
        translation_key="nextcloud_opcache_statistics_hash_restarts",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    NextcloudSensorEntityDescription(
        key="opcache_statistics_hits",
        translation_key="nextcloud_opcache_statistics_hits",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    NextcloudSensorEntityDescription(
        key="opcache_statistics_last_restart_time",
        translation_key="nextcloud_opcache_statistics_last_restart_time",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda val: utc_from_timestamp(float(val)),
    ),
    NextcloudSensorEntityDescription(
        key="opcache_statistics_manual_restarts",
        translation_key="nextcloud_opcache_statistics_manual_restarts",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    NextcloudSensorEntityDescription(
        key="opcache_statistics_max_cached_keys",
        translation_key="nextcloud_opcache_statistics_max_cached_keys",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    NextcloudSensorEntityDescription(
        key="opcache_statistics_misses",
        translation_key="nextcloud_opcache_statistics_misses",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    NextcloudSensorEntityDescription(
        key="opcache_statistics_num_cached_keys",
        translation_key="nextcloud_opcache_statistics_num_cached_keys",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    NextcloudSensorEntityDescription(
        key="opcache_statistics_num_cached_scripts",
        translation_key="nextcloud_opcache_statistics_num_cached_scripts",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    NextcloudSensorEntityDescription(
        key="opcache_statistics_oom_restarts",
        translation_key="nextcloud_opcache_statistics_oom_restarts",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    NextcloudSensorEntityDescription(
        key="opcache_statistics_opcache_hit_rate",
        translation_key="nextcloud_opcache_statistics_opcache_hit_rate",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=1,
    ),
    NextcloudSensorEntityDescription(
        key="opcache_statistics_start_time",
        translation_key="nextcloud_opcache_statistics_start_time",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda val: utc_from_timestamp(float(val)),
    ),
    NextcloudSensorEntityDescription(
        key="server_php_opcache_memory_usage_current_wasted_percentage",
        translation_key="nextcloud_server_php_opcache_memory_usage_current_wasted_percentage",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=1,
    ),
    NextcloudSensorEntityDescription(
        key="server_php_opcache_memory_usage_free_memory",
        translation_key="nextcloud_server_php_opcache_memory_usage_free_memory",
        device_class=SensorDeviceClass.DATA_SIZE,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_display_precision=1,
        suggested_unit_of_measurement=UnitOfInformation.MEGABYTES,
    ),
    NextcloudSensorEntityDescription(
        key="server_php_opcache_memory_usage_used_memory",
        translation_key="nextcloud_server_php_opcache_memory_usage_used_memory",
        device_class=SensorDeviceClass.DATA_SIZE,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_display_precision=1,
        suggested_unit_of_measurement=UnitOfInformation.MEGABYTES,
    ),
    NextcloudSensorEntityDescription(
        key="server_php_opcache_memory_usage_wasted_memory",
        translation_key="nextcloud_server_php_opcache_memory_usage_wasted_memory",
        device_class=SensorDeviceClass.DATA_SIZE,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_display_precision=1,
        suggested_unit_of_measurement=UnitOfInformation.MEGABYTES,
    ),
    NextcloudSensorEntityDescription(
        key="server_php_max_execution_time",
        translation_key="nextcloud_server_php_max_execution_time",
        device_class=SensorDeviceClass.DURATION,
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=UnitOfTime.SECONDS,
    ),
    NextcloudSensorEntityDescription(
        key="server_php_memory_limit",
        translation_key="nextcloud_server_php_memory_limit",
        device_class=SensorDeviceClass.DATA_SIZE,
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_display_precision=1,
        suggested_unit_of_measurement=UnitOfInformation.MEGABYTES,
    ),
    NextcloudSensorEntityDescription(
        key="server_php_upload_max_filesize",
        translation_key="nextcloud_server_php_upload_max_filesize",
        device_class=SensorDeviceClass.DATA_SIZE,
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_display_precision=1,
        suggested_unit_of_measurement=UnitOfInformation.MEGABYTES,
    ),
    NextcloudSensorEntityDescription(
        key="server_php_version",
        translation_key="nextcloud_server_php_version",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    NextcloudSensorEntityDescription(
        key="server_webserver",
        translation_key="nextcloud_server_webserver",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    NextcloudSensorEntityDescription(
        key="shares_num_fed_shares_sent",
        translation_key="nextcloud_shares_num_fed_shares_sent",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    NextcloudSensorEntityDescription(
        key="shares_num_fed_shares_received",
        translation_key="nextcloud_shares_num_fed_shares_received",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    NextcloudSensorEntityDescription(
        key="shares_num_shares",
        translation_key="nextcloud_shares_num_shares",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    NextcloudSensorEntityDescription(
        key="shares_num_shares_groups",
        translation_key="nextcloud_shares_num_shares_groups",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    NextcloudSensorEntityDescription(
        key="shares_num_shares_link",
        translation_key="nextcloud_shares_num_shares_link",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    NextcloudSensorEntityDescription(
        key="shares_num_shares_link_no_password",
        translation_key="nextcloud_shares_num_shares_link_no_password",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    NextcloudSensorEntityDescription(
        key="shares_num_shares_mail",
        translation_key="nextcloud_shares_num_shares_mail",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    NextcloudSensorEntityDescription(
        key="shares_num_shares_room",
        translation_key="nextcloud_shares_num_shares_room",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    NextcloudSensorEntityDescription(
        key="shares_num_shares_user",
        translation_key="nextcloud_shares_num_shares_user",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    NextcloudSensorEntityDescription(
        key="sma_avail_mem",
        translation_key="nextcloud_sma_avail_mem",
        device_class=SensorDeviceClass.DATA_SIZE,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_display_precision=1,
        suggested_unit_of_measurement=UnitOfInformation.MEGABYTES,
    ),
    NextcloudSensorEntityDescription(
        key="sma_num_seg",
        translation_key="nextcloud_sma_num_seg",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    NextcloudSensorEntityDescription(
        key="sma_seg_size",
        translation_key="nextcloud_sma_seg_size",
        device_class=SensorDeviceClass.DATA_SIZE,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_display_precision=1,
        suggested_unit_of_measurement=UnitOfInformation.MEGABYTES,
    ),
    NextcloudSensorEntityDescription(
        key="storage_num_files",
        translation_key="nextcloud_storage_num_files",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    NextcloudSensorEntityDescription(
        key="storage_num_storages",
        translation_key="nextcloud_storage_num_storages",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    NextcloudSensorEntityDescription(
        key="storage_num_storages_home",
        translation_key="nextcloud_storage_num_storages_home",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    NextcloudSensorEntityDescription(
        key="storage_num_storages_local",
        translation_key="nextcloud_storage_num_storages_local",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    NextcloudSensorEntityDescription(
        key="storage_num_storages_other",
        translation_key="nextcloud_storage_num_storages_other",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    NextcloudSensorEntityDescription(
        key="storage_num_users",
        translation_key="nextcloud_storage_num_users",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    NextcloudSensorEntityDescription(
        key="system_apps_num_installed",
        translation_key="nextcloud_system_apps_num_installed",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    NextcloudSensorEntityDescription(
        key="system_apps_num_updates_available",
        translation_key="nextcloud_system_apps_num_updates_available",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    NextcloudSensorEntityDescription(
        key="system_cpuload_1",
        translation_key="nextcloud_system_cpuload_1",
        native_unit_of_measurement=UNIT_OF_LOAD,
        suggested_display_precision=2,
    ),
    NextcloudSensorEntityDescription(
        key="system_cpuload_5",
        translation_key="nextcloud_system_cpuload_5",
        native_unit_of_measurement=UNIT_OF_LOAD,
        suggested_display_precision=2,
    ),
    NextcloudSensorEntityDescription(
        key="system_cpuload_15",
        translation_key="nextcloud_system_cpuload_15",
        native_unit_of_measurement=UNIT_OF_LOAD,
        suggested_display_precision=2,
    ),
    NextcloudSensorEntityDescription(
        key="system_freespace",
        translation_key="nextcloud_system_freespace",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_display_precision=2,
        suggested_unit_of_measurement=UnitOfInformation.GIGABYTES,
    ),
    NextcloudSensorEntityDescription(
        key="system_mem_free",
        translation_key="nextcloud_system_mem_free",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.KILOBYTES,
        suggested_display_precision=2,
        suggested_unit_of_measurement=UnitOfInformation.GIGABYTES,
    ),
    NextcloudSensorEntityDescription(
        key="system_mem_total",
        translation_key="nextcloud_system_mem_total",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.KILOBYTES,
        suggested_display_precision=2,
        suggested_unit_of_measurement=UnitOfInformation.GIGABYTES,
    ),
    NextcloudSensorEntityDescription(
        key="system_memcache.distributed",
        translation_key="nextcloud_system_memcache_distributed",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    NextcloudSensorEntityDescription(
        key="system_memcache.local",
        translation_key="nextcloud_system_memcache_local",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    NextcloudSensorEntityDescription(
        key="system_memcache.locking",
        translation_key="nextcloud_system_memcache_locking",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    NextcloudSensorEntityDescription(
        key="system_swap_total",
        translation_key="nextcloud_system_swap_total",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.KILOBYTES,
        suggested_display_precision=2,
        suggested_unit_of_measurement=UnitOfInformation.GIGABYTES,
    ),
    NextcloudSensorEntityDescription(
        key="system_swap_free",
        translation_key="nextcloud_system_swap_free",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.KILOBYTES,
        suggested_display_precision=2,
        suggested_unit_of_measurement=UnitOfInformation.GIGABYTES,
    ),
    NextcloudSensorEntityDescription(
        key="system_theme",
        translation_key="nextcloud_system_theme",
    ),
    NextcloudSensorEntityDescription(
        key="system_version",
        translation_key="nextcloud_system_version",
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NextcloudConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Nextcloud sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        NextcloudSensor(coordinator, entry, sensor)
        for sensor in SENSORS
        if sensor.key in coordinator.data
    )


class NextcloudSensor(NextcloudEntity, SensorEntity):
    """Represents a Nextcloud sensor."""

    entity_description: NextcloudSensorEntityDescription

    @property
    def native_value(self) -> str | int | float | datetime:
        """Return the state for this sensor."""
        val = self.coordinator.data.get(self.entity_description.key)
        return self.entity_description.value_fn(val)  # type: ignore[arg-type]
