"""Test Home Assistant scenes."""
from unittest.mock import patch

import pytest
import voluptuous as vol

from homeassistant.components.homeassistant import scene as ha_scene
from homeassistant.setup import async_setup_component

from tests.common import async_mock_service


async def test_reload_config_service(hass):
    """Test the reload config service."""
    assert await async_setup_component(hass, "scene", {})

    with patch(
        "homeassistant.config.load_yaml_config_file",
        autospec=True,
        return_value={"scene": {"name": "Hallo", "entities": {"light.kitchen": "on"}}},
    ):
        await hass.services.async_call("scene", "reload", blocking=True)
        await hass.async_block_till_done()

    assert hass.states.get("scene.hallo") is not None

    with patch(
        "homeassistant.config.load_yaml_config_file",
        autospec=True,
        return_value={"scene": {"name": "Bye", "entities": {"light.kitchen": "on"}}},
    ):
        await hass.services.async_call("scene", "reload", blocking=True)
        await hass.async_block_till_done()

    assert hass.states.get("scene.hallo") is None
    assert hass.states.get("scene.bye") is not None


async def test_apply_service(hass):
    """Test the apply service."""
    assert await async_setup_component(hass, "scene", {})
    assert await async_setup_component(hass, "light", {"light": {"platform": "demo"}})

    assert await hass.services.async_call(
        "scene", "apply", {"entities": {"light.bed_light": "off"}}, blocking=True
    )

    assert hass.states.get("light.bed_light").state == "off"

    assert await hass.services.async_call(
        "scene",
        "apply",
        {"entities": {"light.bed_light": {"state": "on", "brightness": 50}}},
        blocking=True,
    )

    state = hass.states.get("light.bed_light")
    assert state.state == "on"
    assert state.attributes["brightness"] == 50


async def test_create_service(hass, caplog):
    """Test the create service."""
    assert await async_setup_component(
        hass,
        "scene",
        {"scene": {"name": "hallo_2", "entities": {"light.kitchen": "on"}}},
    )
    assert hass.states.get("scene.hallo") is None
    assert hass.states.get("scene.hallo_2") is not None

    assert await hass.services.async_call(
        "scene",
        "create",
        {"scene_id": "hallo", "entities": {}, "snapshot_entities": []},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert "Empty scenes are not allowed" in caplog.text
    assert hass.states.get("scene.hallo") is None

    assert await hass.services.async_call(
        "scene",
        "create",
        {
            "scene_id": "hallo",
            "entities": {"light.bed_light": {"state": "on", "brightness": 50}},
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    scene = hass.states.get("scene.hallo")
    assert scene is not None
    assert scene.domain == "scene"
    assert scene.name == "hallo"
    assert scene.state == "scening"
    assert scene.attributes.get("entity_id") == ["light.bed_light"]

    assert await hass.services.async_call(
        "scene",
        "create",
        {
            "scene_id": "hallo",
            "entities": {"light.kitchen_light": {"state": "on", "brightness": 100}},
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    scene = hass.states.get("scene.hallo")
    assert scene is not None
    assert scene.domain == "scene"
    assert scene.name == "hallo"
    assert scene.state == "scening"
    assert scene.attributes.get("entity_id") == ["light.kitchen_light"]

    assert await hass.services.async_call(
        "scene",
        "create",
        {
            "scene_id": "hallo_2",
            "entities": {"light.bed_light": {"state": "on", "brightness": 50}},
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    assert "The scene scene.hallo_2 already exists" in caplog.text
    scene = hass.states.get("scene.hallo_2")
    assert scene is not None
    assert scene.domain == "scene"
    assert scene.name == "hallo_2"
    assert scene.state == "scening"
    assert scene.attributes.get("entity_id") == ["light.kitchen"]


async def test_snapshot_service(hass, caplog):
    """Test the snapshot option."""
    assert await async_setup_component(hass, "scene", {"scene": {}})
    hass.states.async_set("light.my_light", "on", {"hs_color": (345, 75)})
    assert hass.states.get("scene.hallo") is None

    assert await hass.services.async_call(
        "scene",
        "create",
        {"scene_id": "hallo", "snapshot_entities": ["light.my_light"]},
        blocking=True,
    )
    await hass.async_block_till_done()
    scene = hass.states.get("scene.hallo")
    assert scene is not None
    assert scene.attributes.get("entity_id") == ["light.my_light"]

    hass.states.async_set("light.my_light", "off", {"hs_color": (123, 45)})
    turn_on_calls = async_mock_service(hass, "light", "turn_on")
    assert await hass.services.async_call(
        "scene", "turn_on", {"entity_id": "scene.hallo"}, blocking=True
    )
    await hass.async_block_till_done()
    assert len(turn_on_calls) == 1
    assert turn_on_calls[0].data.get("entity_id") == "light.my_light"
    assert turn_on_calls[0].data.get("hs_color") == (345, 75)

    assert await hass.services.async_call(
        "scene",
        "create",
        {"scene_id": "hallo_2", "snapshot_entities": ["light.not_existent"]},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert hass.states.get("scene.hallo_2") is None
    assert (
        "Entity light.not_existent does not exist and therefore cannot be snapshotted"
        in caplog.text
    )

    assert await hass.services.async_call(
        "scene",
        "create",
        {
            "scene_id": "hallo_3",
            "entities": {"light.bed_light": {"state": "on", "brightness": 50}},
            "snapshot_entities": ["light.my_light"],
        },
        blocking=True,
    )
    await hass.async_block_till_done()
    scene = hass.states.get("scene.hallo_3")
    assert scene is not None
    assert "light.my_light" in scene.attributes.get("entity_id")
    assert "light.bed_light" in scene.attributes.get("entity_id")


async def test_ensure_no_intersection(hass):
    """Test that entities and snapshot_entities do not overlap."""
    assert await async_setup_component(hass, "scene", {"scene": {}})

    with pytest.raises(vol.MultipleInvalid) as ex:
        assert await hass.services.async_call(
            "scene",
            "create",
            {
                "scene_id": "hallo",
                "entities": {"light.my_light": {"state": "on", "brightness": 50}},
                "snapshot_entities": ["light.my_light"],
            },
            blocking=True,
        )
        await hass.async_block_till_done()
    assert "entities and snapshot_entities must not overlap" in str(ex.value)
    assert hass.states.get("scene.hallo") is None


async def test_scenes_with_entity(hass):
    """Test finding scenes with a specific entity."""
    assert await async_setup_component(
        hass,
        "scene",
        {
            "scene": [
                {"name": "scene_1", "entities": {"light.kitchen": "on"}},
                {"name": "scene_2", "entities": {"light.living_room": "off"}},
                {
                    "name": "scene_3",
                    "entities": {"light.kitchen": "on", "light.living_room": "off"},
                },
            ]
        },
    )

    assert sorted(ha_scene.scenes_with_entity(hass, "light.kitchen")) == [
        "scene.scene_1",
        "scene.scene_3",
    ]


async def test_entities_in_scene(hass):
    """Test finding entities in a scene."""
    assert await async_setup_component(
        hass,
        "scene",
        {
            "scene": [
                {"name": "scene_1", "entities": {"light.kitchen": "on"}},
                {"name": "scene_2", "entities": {"light.living_room": "off"}},
                {
                    "name": "scene_3",
                    "entities": {"light.kitchen": "on", "light.living_room": "off"},
                },
            ]
        },
    )

    for scene_id, entities in (
        ("scene.scene_1", ["light.kitchen"]),
        ("scene.scene_2", ["light.living_room"]),
        ("scene.scene_3", ["light.kitchen", "light.living_room"]),
    ):
        assert ha_scene.entities_in_scene(hass, scene_id) == entities


async def test_config(hass):
    """Test passing config in YAML."""
    assert await async_setup_component(
        hass,
        "scene",
        {
            "scene": [
                {
                    "id": "scene_id",
                    "name": "Scene Icon",
                    "icon": "mdi:party",
                    "entities": {"light.kitchen": "on"},
                },
                {
                    "name": "Scene No Icon",
                    "entities": {"light.kitchen": {"state": "on"}},
                },
            ]
        },
    )

    icon = hass.states.get("scene.scene_icon")
    assert icon is not None
    assert icon.attributes["icon"] == "mdi:party"

    no_icon = hass.states.get("scene.scene_no_icon")
    assert no_icon is not None
    assert "icon" not in no_icon.attributes
