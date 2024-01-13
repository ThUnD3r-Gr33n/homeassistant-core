"""Test ZHA firmware updates."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from zigpy.ota import CachedImage
import zigpy.ota.image as firmware
import zigpy.profiles.zha as zha
import zigpy.zcl.clusters.general as general

from homeassistant.components.update import (
    ATTR_IN_PROGRESS,
    ATTR_INSTALLED_VERSION,
    ATTR_LATEST_VERSION,
)
from homeassistant.const import STATE_OFF, STATE_ON, Platform
from homeassistant.core import HomeAssistant

from .common import async_enable_traffic, find_entity_id, update_attribute_cache
from .conftest import SIG_EP_INPUT, SIG_EP_OUTPUT, SIG_EP_TYPE


@pytest.fixture(autouse=True)
def update_platform_only():
    """Only set up the update and required base platforms to speed up tests."""
    with patch(
        "homeassistant.components.zha.PLATFORMS",
        (
            Platform.UPDATE,
            Platform.SENSOR,
            Platform.SELECT,
            Platform.SWITCH,
        ),
    ):
        yield


@pytest.fixture
def zigpy_device(zigpy_device_mock):
    """Device tracker zigpy device."""
    endpoints = {
        1: {
            SIG_EP_INPUT: [general.Basic.cluster_id, general.OnOff.cluster_id],
            SIG_EP_OUTPUT: [general.Ota.cluster_id],
            SIG_EP_TYPE: zha.DeviceType.ON_OFF_SWITCH,
        }
    }
    return zigpy_device_mock(endpoints)


async def test_firmware_updates(
    hass: HomeAssistant, zha_device_joined_restored, zigpy_device
) -> None:
    """Test ZHA update platform."""

    cluster = zigpy_device.endpoints.get(1).out_clusters[general.Ota.cluster_id]
    cluster.PLUGGED_ATTR_READS = {"current_file_version": 0x12345678 - 10}
    update_attribute_cache(cluster)

    zha_device = await zha_device_joined_restored(zigpy_device)

    entity_id = find_entity_id(Platform.UPDATE, zha_device, hass)
    assert entity_id is not None

    # allow traffic to flow through the gateway and device
    await async_enable_traffic(hass, [zha_device])

    assert hass.states.get(entity_id).state == STATE_OFF

    fw_image = firmware.OTAImage()
    fw_image.subelements = [firmware.SubElement(tag_id=0x0000, data=b"fw_image")]
    fw_header = firmware.OTAImageHeader(
        file_version=0x12345678,
        image_type=0x90,
        manufacturer_id=zha_device.manufacturer_code,
        upgrade_file_id=firmware.OTAImageHeader.MAGIC_VALUE,
        header_version=256,
        header_length=56,
        field_control=0,
        stack_version=2,
        header_string="This is a test header!",
        image_size=56 + 2 + 4 + 8,
    )
    fw_image.header = fw_header
    fw_image.should_update = MagicMock(return_value=True)
    cached_image = CachedImage(fw_image)
    zha_device.async_update_sw_build_id(fw_image.header.file_version - 10)

    cluster.endpoint.device.application.ota.get_ota_image = AsyncMock(
        return_value=cached_image
    )

    # simulate an image available notification
    await cluster._handle_query_next_image(
        fw_image.header.field_control,
        zha_device.manufacturer_code,
        fw_image.header.image_type,
        fw_image.header.file_version - 10,
        fw_image.header.header_version,
        tsn=15,
    )

    await hass.async_block_till_done()
    state = hass.states.get(entity_id)
    assert state.state == STATE_ON
    attrs = state.attributes
    assert attrs[ATTR_INSTALLED_VERSION] == f"0x{fw_image.header.file_version - 10:08x}"
    assert not attrs[ATTR_IN_PROGRESS]
    assert attrs[ATTR_LATEST_VERSION] == f"0x{fw_image.header.file_version:08x}"
