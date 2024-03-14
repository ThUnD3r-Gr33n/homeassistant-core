"""Test Roborock Image platform."""

import copy
from datetime import timedelta
from http import HTTPStatus
import io
from unittest.mock import patch

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from tests.common import MockConfigEntry, async_fire_time_changed
from tests.components.roborock.mock_data import MAP_DATA, PROP
from tests.typing import ClientSessionGenerator


async def test_floorplan_image(
    hass: HomeAssistant,
    setup_entry: MockConfigEntry,
    hass_client: ClientSessionGenerator,
) -> None:
    """Test floor plan map image is correctly set up."""
    # Setup calls the image parsing the first time and caches it.
    assert len(hass.states.async_all("image")) == 4

    assert hass.states.get("image.roborock_s7_maxv_upstairs") is not None
    # call a second time -should return cached data
    client = await hass_client()
    resp = await client.get("/api/image_proxy/image.roborock_s7_maxv_upstairs")
    assert resp.status == HTTPStatus.OK
    body = await resp.read()
    assert body is not None
    # Call a third time - this time forcing it to update
    now = dt_util.utcnow() + timedelta(seconds=91)

    # Copy the device prop so we don't override it
    prop = copy.deepcopy(PROP)
    prop.status.in_cleaning = 1
    with patch(
        "homeassistant.components.roborock.coordinator.RoborockLocalClient.get_prop",
        return_value=prop,
    ), patch(
        "homeassistant.components.roborock.image.dt_util.utcnow", return_value=now
    ):
        async_fire_time_changed(hass, now)
        await hass.async_block_till_done()
        resp = await client.get("/api/image_proxy/image.roborock_s7_maxv_upstairs")
    assert resp.status == HTTPStatus.OK
    body = await resp.read()
    assert body is not None


async def test_floorplan_image_failed_parse(
    hass: HomeAssistant,
    setup_entry: MockConfigEntry,
    hass_client: ClientSessionGenerator,
) -> None:
    """Test that we correctly handle getting None from the image parser."""
    client = await hass_client()
    map_data = copy.deepcopy(MAP_DATA)
    map_data.image = None
    now = dt_util.utcnow() + timedelta(seconds=91)
    # Copy the device prop so we don't override it
    prop = copy.deepcopy(PROP)
    prop.status.in_cleaning = 1
    # Update image, but get none for parse image.
    with patch(
        "homeassistant.components.roborock.image.RoborockMapDataParser.parse",
        return_value=map_data,
    ), patch(
        "homeassistant.components.roborock.coordinator.RoborockLocalClient.get_prop",
        return_value=prop,
    ), patch(
        "homeassistant.components.roborock.image.dt_util.utcnow", return_value=now
    ):
        async_fire_time_changed(hass, now)
        resp = await client.get("/api/image_proxy/image.roborock_s7_maxv_upstairs")
    assert not resp.ok


async def test_restore_image(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    setup_entry: MockConfigEntry,
):
    """Test that we correctly restore an image when it already exists."""
    img_byte_arr = io.BytesIO()
    MAP_DATA.image.data.save(img_byte_arr, format="PNG")
    img_bytes = img_byte_arr.getvalue()

    with patch(
        "homeassistant.components.roborock.image.RoborockMapDataParser.parse",
    ) as parse_map:
        # Reload the config entry so that restore data is saved and entities exist.
        await hass.config_entries.async_reload(setup_entry.entry_id)
        await hass.async_block_till_done()
        # Ensure that we never tried to update the map, and only used the cached image.
        assert parse_map.call_count == 0
        assert hass.states.get("image.roborock_s7_maxv_upstairs") is not None
        client = await hass_client()
        resp = await client.get("/api/image_proxy/image.roborock_s7_maxv_upstairs")
        # Test that we can get the image and it correctly serialized and unserialized.
        assert resp.status == HTTPStatus.OK
        body = await resp.read()
        assert body == img_bytes
