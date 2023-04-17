"""The tests for the TTS component."""
import asyncio
from collections.abc import Generator
from http import HTTPStatus
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import voluptuous as vol

from homeassistant.components import tts
from homeassistant.components.media_player import (
    ATTR_MEDIA_ANNOUNCE,
    ATTR_MEDIA_CONTENT_ID,
    ATTR_MEDIA_CONTENT_TYPE,
    DOMAIN as DOMAIN_MP,
    SERVICE_PLAY_MEDIA,
    MediaType,
)
from homeassistant.components.media_source import Unresolvable
from homeassistant.components.tts.legacy import _valid_base_url
from homeassistant.config_entries import ConfigEntry, ConfigFlow
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.setup import async_setup_component
from homeassistant.util.network import normalize_url

from .common import (
    DEFAULT_LANG,
    MockProvider,
    MockTTS,
    MockTTSEntity,
    get_media_source_url,
)

from tests.common import (
    MockConfigEntry,
    MockModule,
    MockPlatform,
    assert_setup_component,
    async_mock_service,
    mock_config_flow,
    mock_integration,
    mock_platform,
)
from tests.typing import ClientSessionGenerator, WebSocketGenerator

ORIG_WRITE_TAGS = tts.SpeechManager.write_tags
TEST_DOMAIN = "test"


@pytest.fixture
async def setup_tts(hass: HomeAssistant, mock_tts: None) -> None:
    """Mock TTS."""
    assert await async_setup_component(hass, tts.DOMAIN, {"tts": {"platform": "test"}})


class TTSFlow(ConfigFlow):
    """Test flow."""


@pytest.fixture(autouse=True)
def config_flow_fixture(hass: HomeAssistant) -> Generator[None, None, None]:
    """Mock config flow."""
    mock_platform(hass, f"{TEST_DOMAIN}.config_flow")

    with mock_config_flow(TEST_DOMAIN, TTSFlow):
        yield


@pytest.fixture(name="setup")
async def setup_fixture(
    hass: HomeAssistant,
    request: pytest.FixtureRequest,
    mock_provider: MockProvider,
    mock_tts_entity: MockTTSEntity,
) -> None:
    """Set up the test environment."""
    if request.param == "mock_setup":
        await mock_setup(hass, mock_provider)
    elif request.param == "mock_config_entry_setup":
        await mock_config_entry_setup(hass, mock_tts_entity)
    else:
        raise RuntimeError("Invalid setup fixture")


async def mock_setup(
    hass: HomeAssistant,
    mock_provider: MockProvider,
) -> None:
    """Set up a test provider."""
    mock_integration(hass, MockModule(domain=TEST_DOMAIN))
    mock_platform(hass, f"{TEST_DOMAIN}.{tts.DOMAIN}", MockTTS(mock_provider))

    await async_setup_component(
        hass, tts.DOMAIN, {tts.DOMAIN: {"platform": TEST_DOMAIN}}
    )
    await hass.async_block_till_done()


async def mock_config_entry_setup(
    hass: HomeAssistant, tts_entity: MockTTSEntity
) -> MockConfigEntry:
    """Set up a test tts platform via config entry."""

    async def async_setup_entry_init(
        hass: HomeAssistant, config_entry: ConfigEntry
    ) -> bool:
        """Set up test config entry."""
        await hass.config_entries.async_forward_entry_setup(config_entry, tts.DOMAIN)
        return True

    async def async_unload_entry_init(
        hass: HomeAssistant, config_entry: ConfigEntry
    ) -> bool:
        """Unload up test config entry."""
        await hass.config_entries.async_forward_entry_unload(config_entry, tts.DOMAIN)
        return True

    mock_integration(
        hass,
        MockModule(
            TEST_DOMAIN,
            async_setup_entry=async_setup_entry_init,
            async_unload_entry=async_unload_entry_init,
        ),
    )

    async def async_setup_entry_platform(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
    ) -> None:
        """Set up test tts platform via config entry."""
        async_add_entities([tts_entity])

    loaded_platform = MockPlatform(async_setup_entry=async_setup_entry_platform)
    mock_platform(hass, f"{TEST_DOMAIN}.{tts.DOMAIN}", loaded_platform)

    config_entry = MockConfigEntry(domain=TEST_DOMAIN)
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    return config_entry


@pytest.mark.parametrize(
    "setup", ["mock_setup", "mock_config_entry_setup"], indirect=True
)
async def test_setup_component(hass: HomeAssistant, setup: str) -> None:
    """Set up a TTS platform with defaults."""
    assert hass.services.has_service(tts.DOMAIN, "clear_cache")
    assert f"{tts.DOMAIN}.test" in hass.config.components


@pytest.mark.parametrize("init_cache_dir_side_effect", [OSError(2, "No access")])
@pytest.mark.parametrize(
    "setup", ["mock_setup", "mock_config_entry_setup"], indirect=True
)
async def test_setup_component_no_access_cache_folder(
    hass: HomeAssistant, mock_init_cache_dir: MagicMock, setup: str
) -> None:
    """Set up a TTS platform with defaults."""
    assert not hass.services.has_service(tts.DOMAIN, "test_say")
    assert not hass.services.has_service(tts.DOMAIN, "clear_cache")


@pytest.mark.parametrize(
    ("setup", "tts_service", "service_data", "expected_url_suffix"),
    [
        (
            "mock_setup",
            "test_say",
            {
                ATTR_ENTITY_ID: "media_player.something",
                tts.ATTR_MESSAGE: "There is someone at the door.",
            },
            "test",
        ),
        (
            "mock_config_entry_setup",
            "speak",
            {
                ATTR_ENTITY_ID: "tts.test",
                tts.ATTR_MEDIA_PLAYER_ENTITY_ID: "media_player.something",
                tts.ATTR_MESSAGE: "There is someone at the door.",
            },
            "tts.test",
        ),
    ],
    indirect=["setup"],
)
async def test_service(
    hass: HomeAssistant,
    empty_cache_dir,
    setup: str,
    tts_service: str,
    service_data: dict[str, Any],
    expected_url_suffix: str,
) -> None:
    """Set up a TTS platform and call service."""
    calls = async_mock_service(hass, DOMAIN_MP, SERVICE_PLAY_MEDIA)

    await hass.services.async_call(
        tts.DOMAIN,
        tts_service,
        service_data,
        blocking=True,
    )

    assert len(calls) == 1
    assert calls[0].data[ATTR_MEDIA_ANNOUNCE] is True
    assert calls[0].data[ATTR_MEDIA_CONTENT_TYPE] == MediaType.MUSIC
    assert await get_media_source_url(hass, calls[0].data[ATTR_MEDIA_CONTENT_ID]) == (
        "/api/tts_proxy/42f18378fd4393d18c8dd11d03fa9563c1e54491"
        f"_en-us_-_{expected_url_suffix}.mp3"
    )
    await hass.async_block_till_done()
    assert (
        empty_cache_dir
        / f"42f18378fd4393d18c8dd11d03fa9563c1e54491_en-us_-_{expected_url_suffix}.mp3"
    ).is_file()


# Language de is matched with de_DE
@pytest.mark.parametrize(
    ("mock_provider", "mock_tts_entity"), [(MockProvider("de"), MockTTSEntity("de"))]
)
@pytest.mark.parametrize(
    ("setup", "tts_service", "service_data", "expected_url_suffix"),
    [
        (
            "mock_setup",
            "test_say",
            {
                ATTR_ENTITY_ID: "media_player.something",
                tts.ATTR_MESSAGE: "There is someone at the door.",
            },
            "test",
        ),
        (
            "mock_config_entry_setup",
            "speak",
            {
                ATTR_ENTITY_ID: "tts.test",
                tts.ATTR_MEDIA_PLAYER_ENTITY_ID: "media_player.something",
                tts.ATTR_MESSAGE: "There is someone at the door.",
            },
            "tts.test",
        ),
    ],
    indirect=["setup"],
)
async def test_service_default_language(
    hass: HomeAssistant,
    empty_cache_dir,
    setup: str,
    tts_service: str,
    service_data: dict[str, Any],
    expected_url_suffix: str,
) -> None:
    """Set up a TTS platform with default language and call service."""
    calls = async_mock_service(hass, DOMAIN_MP, SERVICE_PLAY_MEDIA)

    await hass.services.async_call(
        tts.DOMAIN,
        tts_service,
        service_data,
        blocking=True,
    )
    assert len(calls) == 1
    assert calls[0].data[ATTR_MEDIA_CONTENT_TYPE] == MediaType.MUSIC
    assert await get_media_source_url(hass, calls[0].data[ATTR_MEDIA_CONTENT_ID]) == (
        "/api/tts_proxy/42f18378fd4393d18c8dd11d03fa9563c1e54491"
        f"_de-de_-_{expected_url_suffix}.mp3"
    )
    await hass.async_block_till_done()
    assert (
        empty_cache_dir
        / (
            f"42f18378fd4393d18c8dd11d03fa9563c1e54491_de-de_-_{expected_url_suffix}.mp3"
        )
    ).is_file()


@pytest.mark.parametrize(
    ("mock_provider", "mock_tts_entity"),
    [(MockProvider("en_US"), MockTTSEntity("en_US"))],
)
@pytest.mark.parametrize(
    ("setup", "tts_service", "service_data", "expected_url_suffix"),
    [
        (
            "mock_setup",
            "test_say",
            {
                ATTR_ENTITY_ID: "media_player.something",
                tts.ATTR_MESSAGE: "There is someone at the door.",
            },
            "test",
        ),
        (
            "mock_config_entry_setup",
            "speak",
            {
                ATTR_ENTITY_ID: "tts.test",
                tts.ATTR_MEDIA_PLAYER_ENTITY_ID: "media_player.something",
                tts.ATTR_MESSAGE: "There is someone at the door.",
            },
            "tts.test",
        ),
    ],
    indirect=["setup"],
)
async def test_service_default_special_language(
    hass: HomeAssistant,
    empty_cache_dir,
    setup: str,
    tts_service: str,
    service_data: dict[str, Any],
    expected_url_suffix: str,
) -> None:
    """Set up a TTS platform with default special language and call service."""
    calls = async_mock_service(hass, DOMAIN_MP, SERVICE_PLAY_MEDIA)

    await hass.services.async_call(
        tts.DOMAIN,
        tts_service,
        service_data,
        blocking=True,
    )
    assert len(calls) == 1
    assert calls[0].data[ATTR_MEDIA_CONTENT_TYPE] == MediaType.MUSIC
    assert await get_media_source_url(hass, calls[0].data[ATTR_MEDIA_CONTENT_ID]) == (
        "/api/tts_proxy/42f18378fd4393d18c8dd11d03fa9563c1e54491"
        f"_en-us_-_{expected_url_suffix}.mp3"
    )
    await hass.async_block_till_done()
    assert (
        empty_cache_dir
        / f"42f18378fd4393d18c8dd11d03fa9563c1e54491_en-us_-_{expected_url_suffix}.mp3"
    ).is_file()


@pytest.mark.parametrize(
    ("setup", "tts_service", "service_data", "expected_url_suffix"),
    [
        (
            "mock_setup",
            "test_say",
            {
                ATTR_ENTITY_ID: "media_player.something",
                tts.ATTR_MESSAGE: "There is someone at the door.",
                tts.ATTR_LANGUAGE: "de",
            },
            "test",
        ),
        (
            "mock_config_entry_setup",
            "speak",
            {
                ATTR_ENTITY_ID: "tts.test",
                tts.ATTR_MEDIA_PLAYER_ENTITY_ID: "media_player.something",
                tts.ATTR_MESSAGE: "There is someone at the door.",
                tts.ATTR_LANGUAGE: "de",
            },
            "tts.test",
        ),
    ],
    indirect=["setup"],
)
async def test_service_language(
    hass: HomeAssistant,
    empty_cache_dir,
    setup: str,
    tts_service: str,
    service_data: dict[str, Any],
    expected_url_suffix: str,
) -> None:
    """Set up a TTS platform and call service with language."""
    calls = async_mock_service(hass, DOMAIN_MP, SERVICE_PLAY_MEDIA)

    await hass.services.async_call(
        tts.DOMAIN,
        tts_service,
        service_data,
        blocking=True,
    )
    assert len(calls) == 1
    assert calls[0].data[ATTR_MEDIA_CONTENT_TYPE] == MediaType.MUSIC
    assert await get_media_source_url(hass, calls[0].data[ATTR_MEDIA_CONTENT_ID]) == (
        "/api/tts_proxy/42f18378fd4393d18c8dd11d03fa9563c1e54491"
        f"_de-de_-_{expected_url_suffix}.mp3"
    )
    await hass.async_block_till_done()
    assert (
        empty_cache_dir
        / f"42f18378fd4393d18c8dd11d03fa9563c1e54491_de-de_-_{expected_url_suffix}.mp3"
    ).is_file()


@pytest.mark.parametrize(
    ("setup", "tts_service", "service_data", "expected_url_suffix"),
    [
        (
            "mock_setup",
            "test_say",
            {
                ATTR_ENTITY_ID: "media_player.something",
                tts.ATTR_MESSAGE: "There is someone at the door.",
                tts.ATTR_LANGUAGE: "lang",
            },
            "test",
        ),
        (
            "mock_config_entry_setup",
            "speak",
            {
                ATTR_ENTITY_ID: "tts.test",
                tts.ATTR_MEDIA_PLAYER_ENTITY_ID: "media_player.something",
                tts.ATTR_MESSAGE: "There is someone at the door.",
                tts.ATTR_LANGUAGE: "lang",
            },
            "tts.test",
        ),
    ],
    indirect=["setup"],
)
async def test_service_wrong_language(
    hass: HomeAssistant,
    empty_cache_dir,
    setup: str,
    tts_service: str,
    service_data: dict[str, Any],
    expected_url_suffix: str,
) -> None:
    """Set up a TTS platform and call service."""
    calls = async_mock_service(hass, DOMAIN_MP, SERVICE_PLAY_MEDIA)

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            tts.DOMAIN,
            tts_service,
            service_data,
            blocking=True,
        )
    assert len(calls) == 0
    assert not (
        empty_cache_dir
        / f"42f18378fd4393d18c8dd11d03fa9563c1e54491_lang_-_{expected_url_suffix}.mp3"
    ).is_file()


@pytest.mark.parametrize(
    ("setup", "tts_service", "service_data", "expected_url_suffix"),
    [
        (
            "mock_setup",
            "test_say",
            {
                ATTR_ENTITY_ID: "media_player.something",
                tts.ATTR_MESSAGE: "There is someone at the door.",
                tts.ATTR_LANGUAGE: "de",
                tts.ATTR_OPTIONS: {"voice": "alex", "age": 5},
            },
            "test",
        ),
        (
            "mock_config_entry_setup",
            "speak",
            {
                ATTR_ENTITY_ID: "tts.test",
                tts.ATTR_MEDIA_PLAYER_ENTITY_ID: "media_player.something",
                tts.ATTR_MESSAGE: "There is someone at the door.",
                tts.ATTR_LANGUAGE: "de",
                tts.ATTR_OPTIONS: {"voice": "alex", "age": 5},
            },
            "tts.test",
        ),
    ],
    indirect=["setup"],
)
async def test_service_options(
    hass: HomeAssistant,
    empty_cache_dir,
    setup: str,
    tts_service: str,
    service_data: dict[str, Any],
    expected_url_suffix: str,
) -> None:
    """Set up a TTS platform and call service with options."""
    calls = async_mock_service(hass, DOMAIN_MP, SERVICE_PLAY_MEDIA)

    await hass.services.async_call(
        tts.DOMAIN,
        tts_service,
        service_data,
        blocking=True,
    )
    opt_hash = tts._hash_options({"voice": "alex", "age": 5})

    assert len(calls) == 1
    assert calls[0].data[ATTR_MEDIA_CONTENT_TYPE] == MediaType.MUSIC
    assert await get_media_source_url(hass, calls[0].data[ATTR_MEDIA_CONTENT_ID]) == (
        "/api/tts_proxy/42f18378fd4393d18c8dd11d03fa9563c1e54491"
        f"_de-de_{opt_hash}_{expected_url_suffix}.mp3"
    )
    await hass.async_block_till_done()
    assert (
        empty_cache_dir
        / (
            "42f18378fd4393d18c8dd11d03fa9563c1e54491"
            f"_de-de_{opt_hash}_{expected_url_suffix}.mp3"
        )
    ).is_file()


class MockProviderWithDefaults(MockProvider):
    """Mock provider with default options."""

    @property
    def default_options(self):
        """Return a mapping with the default options."""
        return {"voice": "alex"}


class MockEntityWithDefaults(MockTTSEntity):
    """Mock entity with default options."""

    @property
    def default_options(self):
        """Return a mapping with the default options."""
        return {"voice": "alex"}


@pytest.mark.parametrize(
    ("mock_provider", "mock_tts_entity"),
    [(MockProviderWithDefaults(DEFAULT_LANG), MockEntityWithDefaults(DEFAULT_LANG))],
)
@pytest.mark.parametrize(
    ("setup", "tts_service", "service_data", "expected_url_suffix"),
    [
        (
            "mock_setup",
            "test_say",
            {
                ATTR_ENTITY_ID: "media_player.something",
                tts.ATTR_MESSAGE: "There is someone at the door.",
                tts.ATTR_LANGUAGE: "de",
            },
            "test",
        ),
        (
            "mock_config_entry_setup",
            "speak",
            {
                ATTR_ENTITY_ID: "tts.test",
                tts.ATTR_MEDIA_PLAYER_ENTITY_ID: "media_player.something",
                tts.ATTR_MESSAGE: "There is someone at the door.",
                tts.ATTR_LANGUAGE: "de",
            },
            "tts.test",
        ),
    ],
    indirect=["setup"],
)
async def test_service_default_options(
    hass: HomeAssistant,
    empty_cache_dir,
    setup: str,
    tts_service: str,
    service_data: dict[str, Any],
    expected_url_suffix: str,
) -> None:
    """Set up a TTS platform and call service with default options."""
    calls = async_mock_service(hass, DOMAIN_MP, SERVICE_PLAY_MEDIA)

    await hass.services.async_call(
        tts.DOMAIN,
        tts_service,
        service_data,
        blocking=True,
    )
    opt_hash = tts._hash_options({"voice": "alex"})

    assert len(calls) == 1
    assert calls[0].data[ATTR_MEDIA_CONTENT_TYPE] == MediaType.MUSIC
    assert await get_media_source_url(hass, calls[0].data[ATTR_MEDIA_CONTENT_ID]) == (
        "/api/tts_proxy/42f18378fd4393d18c8dd11d03fa9563c1e54491"
        f"_de-de_{opt_hash}_{expected_url_suffix}.mp3"
    )
    await hass.async_block_till_done()
    assert (
        empty_cache_dir
        / (
            "42f18378fd4393d18c8dd11d03fa9563c1e54491"
            f"_de-de_{opt_hash}_{expected_url_suffix}.mp3"
        )
    ).is_file()


@pytest.mark.parametrize(
    ("mock_provider", "mock_tts_entity"),
    [(MockProviderWithDefaults(DEFAULT_LANG), MockEntityWithDefaults(DEFAULT_LANG))],
)
@pytest.mark.parametrize(
    ("setup", "tts_service", "service_data", "expected_url_suffix"),
    [
        (
            "mock_setup",
            "test_say",
            {
                ATTR_ENTITY_ID: "media_player.something",
                tts.ATTR_MESSAGE: "There is someone at the door.",
                tts.ATTR_LANGUAGE: "de",
                tts.ATTR_OPTIONS: {"age": 5},
            },
            "test",
        ),
        (
            "mock_config_entry_setup",
            "speak",
            {
                ATTR_ENTITY_ID: "tts.test",
                tts.ATTR_MEDIA_PLAYER_ENTITY_ID: "media_player.something",
                tts.ATTR_MESSAGE: "There is someone at the door.",
                tts.ATTR_LANGUAGE: "de",
                tts.ATTR_OPTIONS: {"age": 5},
            },
            "tts.test",
        ),
    ],
    indirect=["setup"],
)
async def test_merge_default_service_options(
    hass: HomeAssistant,
    empty_cache_dir,
    setup: str,
    tts_service: str,
    service_data: dict[str, Any],
    expected_url_suffix: str,
) -> None:
    """Set up a TTS platform and call service with default options.

    This tests merging default and user provided options.
    """
    calls = async_mock_service(hass, DOMAIN_MP, SERVICE_PLAY_MEDIA)

    await hass.services.async_call(
        tts.DOMAIN,
        tts_service,
        service_data,
        blocking=True,
    )
    opt_hash = tts._hash_options({"voice": "alex", "age": 5})

    assert len(calls) == 1
    assert calls[0].data[ATTR_MEDIA_CONTENT_TYPE] == MediaType.MUSIC
    assert await get_media_source_url(hass, calls[0].data[ATTR_MEDIA_CONTENT_ID]) == (
        "/api/tts_proxy/42f18378fd4393d18c8dd11d03fa9563c1e54491"
        f"_de-de_{opt_hash}_{expected_url_suffix}.mp3"
    )
    await hass.async_block_till_done()
    assert (
        empty_cache_dir
        / (
            "42f18378fd4393d18c8dd11d03fa9563c1e54491"
            f"_de-de_{opt_hash}_{expected_url_suffix}.mp3"
        )
    ).is_file()


@pytest.mark.parametrize(
    ("setup", "tts_service", "service_data", "expected_url_suffix"),
    [
        (
            "mock_setup",
            "test_say",
            {
                ATTR_ENTITY_ID: "media_player.something",
                tts.ATTR_MESSAGE: "There is someone at the door.",
                tts.ATTR_LANGUAGE: "de",
                tts.ATTR_OPTIONS: {"speed": 1},
            },
            "test",
        ),
        (
            "mock_config_entry_setup",
            "speak",
            {
                ATTR_ENTITY_ID: "tts.test",
                tts.ATTR_MEDIA_PLAYER_ENTITY_ID: "media_player.something",
                tts.ATTR_MESSAGE: "There is someone at the door.",
                tts.ATTR_LANGUAGE: "de",
                tts.ATTR_OPTIONS: {"speed": 1},
            },
            "tts.test",
        ),
    ],
    indirect=["setup"],
)
async def test_service_wrong_options(
    hass: HomeAssistant,
    empty_cache_dir,
    setup: str,
    tts_service: str,
    service_data: dict[str, Any],
    expected_url_suffix: str,
) -> None:
    """Set up a TTS platform and call service with wrong options."""
    calls = async_mock_service(hass, DOMAIN_MP, SERVICE_PLAY_MEDIA)

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            tts.DOMAIN,
            tts_service,
            service_data,
            blocking=True,
        )
    opt_hash = tts._hash_options({"speed": 1})

    assert len(calls) == 0
    await hass.async_block_till_done()
    assert not (
        empty_cache_dir
        / (
            "42f18378fd4393d18c8dd11d03fa9563c1e54491"
            f"_de-de_{opt_hash}_{expected_url_suffix}.mp3"
        )
    ).is_file()


@pytest.mark.parametrize(
    ("setup", "tts_service", "service_data", "expected_url_suffix"),
    [
        (
            "mock_setup",
            "test_say",
            {
                ATTR_ENTITY_ID: "media_player.something",
                tts.ATTR_MESSAGE: "There is someone at the door.",
            },
            "test",
        ),
        (
            "mock_config_entry_setup",
            "speak",
            {
                ATTR_ENTITY_ID: "tts.test",
                tts.ATTR_MEDIA_PLAYER_ENTITY_ID: "media_player.something",
                tts.ATTR_MESSAGE: "There is someone at the door.",
            },
            "tts.test",
        ),
    ],
    indirect=["setup"],
)
async def test_service_clear_cache(
    hass: HomeAssistant,
    empty_cache_dir,
    setup: str,
    tts_service: str,
    service_data: dict[str, Any],
    expected_url_suffix: str,
) -> None:
    """Set up a TTS platform and call service clear cache."""
    calls = async_mock_service(hass, DOMAIN_MP, SERVICE_PLAY_MEDIA)

    await hass.services.async_call(
        tts.DOMAIN,
        tts_service,
        service_data,
        blocking=True,
    )
    # To make sure the file is persisted
    assert len(calls) == 1
    await get_media_source_url(hass, calls[0].data[ATTR_MEDIA_CONTENT_ID])
    await hass.async_block_till_done()
    assert (
        empty_cache_dir
        / f"42f18378fd4393d18c8dd11d03fa9563c1e54491_en-us_-_{expected_url_suffix}.mp3"
    ).is_file()

    await hass.services.async_call(
        tts.DOMAIN, tts.SERVICE_CLEAR_CACHE, {}, blocking=True
    )

    assert not (
        empty_cache_dir
        / f"42f18378fd4393d18c8dd11d03fa9563c1e54491_en-us_-_{expected_url_suffix}.mp3"
    ).is_file()


@pytest.mark.parametrize(
    ("setup", "tts_service", "service_data", "expected_url_suffix"),
    [
        (
            "mock_setup",
            "test_say",
            {
                ATTR_ENTITY_ID: "media_player.something",
                tts.ATTR_MESSAGE: "There is someone at the door.",
            },
            "test",
        ),
        (
            "mock_config_entry_setup",
            "speak",
            {
                ATTR_ENTITY_ID: "tts.test",
                tts.ATTR_MEDIA_PLAYER_ENTITY_ID: "media_player.something",
                tts.ATTR_MESSAGE: "There is someone at the door.",
            },
            "tts.test",
        ),
    ],
    indirect=["setup"],
)
async def test_service_receive_voice(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    empty_cache_dir,
    setup: str,
    tts_service: str,
    service_data: dict[str, Any],
    expected_url_suffix: str,
) -> None:
    """Set up a TTS platform and call service and receive voice."""
    calls = async_mock_service(hass, DOMAIN_MP, SERVICE_PLAY_MEDIA)

    await hass.services.async_call(
        tts.DOMAIN,
        tts_service,
        service_data,
        blocking=True,
    )
    assert len(calls) == 1

    url = await get_media_source_url(hass, calls[0].data[ATTR_MEDIA_CONTENT_ID])
    await hass.async_block_till_done()
    client = await hass_client()
    req = await client.get(url)
    tts_data = b""
    tts_data = tts.SpeechManager.write_tags(
        f"42f18378fd4393d18c8dd11d03fa9563c1e54491_en-us_-_{expected_url_suffix}.mp3",
        tts_data,
        "Test",
        service_data[tts.ATTR_MESSAGE],
        "en",
        None,
    )
    assert req.status == HTTPStatus.OK
    assert await req.read() == tts_data

    extension, data = await tts.async_get_media_source_audio(
        hass, calls[0].data[ATTR_MEDIA_CONTENT_ID]
    )
    assert extension == "mp3"
    assert tts_data == data


async def test_service_receive_voice_german(
    hass: HomeAssistant,
    mock_provider: MockProvider,
    hass_client: ClientSessionGenerator,
    mock_tts,
) -> None:
    """Set up a TTS platform and call service and receive voice."""
    calls = async_mock_service(hass, DOMAIN_MP, SERVICE_PLAY_MEDIA)

    # Language de is matched with de_DE
    config = {tts.DOMAIN: {"platform": "test", "language": "de"}}

    with assert_setup_component(1, tts.DOMAIN):
        assert await async_setup_component(hass, tts.DOMAIN, config)

    await hass.services.async_call(
        tts.DOMAIN,
        "test_say",
        {
            ATTR_ENTITY_ID: "media_player.something",
            tts.ATTR_MESSAGE: "There is someone at the door.",
        },
        blocking=True,
    )
    assert len(calls) == 1
    url = await get_media_source_url(hass, calls[0].data[ATTR_MEDIA_CONTENT_ID])
    client = await hass_client()
    req = await client.get(url)
    _, tts_data = mock_provider.get_tts_audio("bla", "de")
    assert tts_data is not None
    tts_data = tts.SpeechManager.write_tags(
        "42f18378fd4393d18c8dd11d03fa9563c1e54491_de-de_-_test.mp3",
        tts_data,
        "Test",
        "There is someone at the door.",
        "de",
        None,
    )
    assert req.status == HTTPStatus.OK
    assert await req.read() == tts_data


async def test_web_view_wrong_file(
    hass: HomeAssistant, hass_client: ClientSessionGenerator, mock_tts
) -> None:
    """Set up a TTS platform and receive wrong file from web."""
    config = {tts.DOMAIN: {"platform": "test"}}

    with assert_setup_component(1, tts.DOMAIN):
        assert await async_setup_component(hass, tts.DOMAIN, config)

    client = await hass_client()

    url = "/api/tts_proxy/42f18378fd4393d18c8dd11d03fa9563c1e54491_en-us_-_test.mp3"

    req = await client.get(url)
    assert req.status == HTTPStatus.NOT_FOUND


async def test_web_view_wrong_filename(
    hass: HomeAssistant, hass_client: ClientSessionGenerator, mock_tts
) -> None:
    """Set up a TTS platform and receive wrong filename from web."""
    config = {tts.DOMAIN: {"platform": "test"}}

    with assert_setup_component(1, tts.DOMAIN):
        assert await async_setup_component(hass, tts.DOMAIN, config)

    client = await hass_client()

    url = "/api/tts_proxy/265944dsk32c1b2a621be5930510bb2cd_en-us_-_test.mp3"

    req = await client.get(url)
    assert req.status == HTTPStatus.NOT_FOUND


async def test_service_without_cache_config(
    hass: HomeAssistant, empty_cache_dir, mock_tts
) -> None:
    """Set up a TTS platform without cache."""
    calls = async_mock_service(hass, DOMAIN_MP, SERVICE_PLAY_MEDIA)

    config = {tts.DOMAIN: {"platform": "test", "cache": False}}

    with assert_setup_component(1, tts.DOMAIN):
        assert await async_setup_component(hass, tts.DOMAIN, config)

    await hass.services.async_call(
        tts.DOMAIN,
        "test_say",
        {
            ATTR_ENTITY_ID: "media_player.something",
            tts.ATTR_MESSAGE: "There is someone at the door.",
        },
        blocking=True,
    )
    assert len(calls) == 1
    await hass.async_block_till_done()
    assert not (
        empty_cache_dir / "42f18378fd4393d18c8dd11d03fa9563c1e54491_en-us_-_test.mp3"
    ).is_file()


async def test_service_without_cache(
    hass: HomeAssistant, empty_cache_dir, mock_tts
) -> None:
    """Set up a TTS platform with cache and call service without cache."""
    calls = async_mock_service(hass, DOMAIN_MP, SERVICE_PLAY_MEDIA)

    config = {tts.DOMAIN: {"platform": "test", "cache": True}}

    with assert_setup_component(1, tts.DOMAIN):
        assert await async_setup_component(hass, tts.DOMAIN, config)

    await hass.services.async_call(
        tts.DOMAIN,
        "test_say",
        {
            ATTR_ENTITY_ID: "media_player.something",
            tts.ATTR_MESSAGE: "There is someone at the door.",
            tts.ATTR_CACHE: False,
        },
        blocking=True,
    )
    assert len(calls) == 1
    await hass.async_block_till_done()
    assert not (
        empty_cache_dir / "42f18378fd4393d18c8dd11d03fa9563c1e54491_en-us_-_test.mp3"
    ).is_file()


async def test_setup_cache_dir(
    hass: HomeAssistant, empty_cache_dir, mock_provider: MockProvider
) -> None:
    """Set up a TTS platform with cache and call service without cache."""
    calls = async_mock_service(hass, DOMAIN_MP, SERVICE_PLAY_MEDIA)

    # Language en is matched with en_US
    _, tts_data = mock_provider.get_tts_audio("bla", "en")
    assert tts_data is not None
    cache_file = (
        empty_cache_dir / "42f18378fd4393d18c8dd11d03fa9563c1e54491_en-us_-_test.mp3"
    )

    with open(cache_file, "wb") as voice_file:
        voice_file.write(tts_data)

    config = {tts.DOMAIN: {"platform": "test", "cache": True}}

    class MockProviderBoom(MockProvider):
        """Mock provider that blows up."""

        def get_tts_audio(
            self, message: str, language: str, options: dict[str, Any] | None = None
        ) -> tts.TtsAudioType:
            """Load TTS dat."""
            # This should not be called, data should be fetched from cache
            raise Exception("Boom!")  # pylint: disable=broad-exception-raised

    mock_integration(hass, MockModule(domain="test"))
    mock_platform(hass, "test.tts", MockTTS(MockProviderBoom(DEFAULT_LANG)))

    with assert_setup_component(1, tts.DOMAIN):
        assert await async_setup_component(hass, tts.DOMAIN, config)

    await hass.services.async_call(
        tts.DOMAIN,
        "test_say",
        {
            ATTR_ENTITY_ID: "media_player.something",
            tts.ATTR_MESSAGE: "There is someone at the door.",
        },
        blocking=True,
    )
    assert len(calls) == 1
    assert (
        await get_media_source_url(hass, calls[0].data[ATTR_MEDIA_CONTENT_ID])
        == "/api/tts_proxy/42f18378fd4393d18c8dd11d03fa9563c1e54491_en-us_-_test.mp3"
    )
    await hass.async_block_till_done()


async def test_service_get_tts_error(hass: HomeAssistant) -> None:
    """Set up a TTS platform with wrong get_tts_audio."""
    calls = async_mock_service(hass, DOMAIN_MP, SERVICE_PLAY_MEDIA)

    config = {tts.DOMAIN: {"platform": "test"}}

    class MockProviderEmpty(MockProvider):
        """Mock provider with empty get_tts_audio."""

        def get_tts_audio(
            self, message: str, language: str, options: dict[str, Any] | None = None
        ) -> tts.TtsAudioType:
            """Load TTS dat."""
            return (None, None)

    mock_integration(hass, MockModule(domain="test"))
    mock_platform(hass, "test.tts", MockTTS(MockProviderEmpty(DEFAULT_LANG)))

    with assert_setup_component(1, tts.DOMAIN):
        assert await async_setup_component(hass, tts.DOMAIN, config)

    await hass.services.async_call(
        tts.DOMAIN,
        "test_say",
        {
            ATTR_ENTITY_ID: "media_player.something",
            tts.ATTR_MESSAGE: "There is someone at the door.",
        },
        blocking=True,
    )
    assert len(calls) == 1
    with pytest.raises(Unresolvable):
        await get_media_source_url(hass, calls[0].data[ATTR_MEDIA_CONTENT_ID])


async def test_load_cache_retrieve_without_mem_cache(
    hass: HomeAssistant,
    mock_provider: MockProvider,
    empty_cache_dir,
    hass_client: ClientSessionGenerator,
    mock_tts,
) -> None:
    """Set up component and load cache and get without mem cache."""
    # Language en is matched with en_US
    _, tts_data = mock_provider.get_tts_audio("bla", "en")
    assert tts_data is not None
    cache_file = (
        empty_cache_dir / "42f18378fd4393d18c8dd11d03fa9563c1e54491_en-us_-_test.mp3"
    )

    with open(cache_file, "wb") as voice_file:
        voice_file.write(tts_data)

    config = {tts.DOMAIN: {"platform": "test", "cache": True}}

    with assert_setup_component(1, tts.DOMAIN):
        assert await async_setup_component(hass, tts.DOMAIN, config)

    client = await hass_client()

    url = "/api/tts_proxy/42f18378fd4393d18c8dd11d03fa9563c1e54491_en-us_-_test.mp3"

    req = await client.get(url)
    assert req.status == HTTPStatus.OK
    assert await req.read() == tts_data


async def test_web_get_url(
    hass: HomeAssistant, hass_client: ClientSessionGenerator, mock_tts
) -> None:
    """Set up a TTS platform and receive file from web."""
    config = {tts.DOMAIN: {"platform": "test"}}

    await async_setup_component(hass, tts.DOMAIN, config)

    client = await hass_client()

    url = "/api/tts_get_url"
    data = {"platform": "test", "message": "There is someone at the door."}

    req = await client.post(url, json=data)
    assert req.status == HTTPStatus.OK
    response = await req.json()
    assert response == {
        "url": "http://example.local:8123/api/tts_proxy/42f18378fd4393d18c8dd11d03fa9563c1e54491_en-us_-_test.mp3",
        "path": "/api/tts_proxy/42f18378fd4393d18c8dd11d03fa9563c1e54491_en-us_-_test.mp3",
    }


async def test_web_get_url_missing_data(
    hass: HomeAssistant, hass_client: ClientSessionGenerator, mock_tts
) -> None:
    """Set up a TTS platform and receive wrong file from web."""
    config = {tts.DOMAIN: {"platform": "test"}}

    await async_setup_component(hass, tts.DOMAIN, config)

    client = await hass_client()

    url = "/api/tts_get_url"
    data = {"message": "There is someone at the door."}

    req = await client.post(url, json=data)
    assert req.status == HTTPStatus.BAD_REQUEST


async def test_tags_with_wave() -> None:
    """Set up a TTS platform and call service and receive voice."""

    # below data represents an empty wav file
    tts_data = bytes.fromhex(
        "52 49 46 46 24 00 00 00 57 41 56 45 66 6d 74 20 10 00 00 00 01 00 02 00"
        + "22 56 00 00 88 58 01 00 04 00 10 00 64 61 74 61 00 00 00 00"
    )

    tagged_data = ORIG_WRITE_TAGS(
        "42f18378fd4393d18c8dd11d03fa9563c1e54491_en-us_-_test.wav",
        tts_data,
        "Test",
        "AI person is in front of your door.",
        "en",
        None,
    )

    assert tagged_data != tts_data


@pytest.mark.parametrize(
    "value",
    (
        "http://example.local:8123",
        "http://example.local",
        "http://example.local:80",
        "https://example.com",
        "https://example.com:443",
        "https://example.com:8123",
    ),
)
def test_valid_base_url(value) -> None:
    """Test we validate base urls."""
    assert _valid_base_url(value) == normalize_url(value)
    # Test we strip trailing `/`
    assert _valid_base_url(value + "/") == normalize_url(value)


@pytest.mark.parametrize(
    "value",
    (
        "http://example.local:8123/sub-path",
        "http://example.local/sub-path",
        "https://example.com/sub-path",
        "https://example.com:8123/sub-path",
        "mailto:some@email",
        "http:example.com",
        "http:/example.com",
        "http//example.com",
        "example.com",
    ),
)
def test_invalid_base_url(value) -> None:
    """Test we catch bad base urls."""
    with pytest.raises(vol.Invalid):
        _valid_base_url(value)


@pytest.mark.parametrize(
    ("engine", "language", "options", "cache", "result_engine", "result_query"),
    (
        (None, None, None, None, "test", ""),
        (None, "de", None, None, "test", "language=de"),
        (None, "de", {"voice": "henk"}, None, "test", "language=de&voice=henk"),
        (None, "de", None, True, "test", "cache=true&language=de"),
    ),
)
async def test_generate_media_source_id(
    hass: HomeAssistant,
    setup_tts,
    engine,
    language,
    options,
    cache,
    result_engine,
    result_query,
) -> None:
    """Test generating a media source ID."""
    media_source_id = tts.generate_media_source_id(
        hass, "msg", engine, language, options, cache
    )

    assert media_source_id.startswith("media-source://tts/")
    _, _, engine_query = media_source_id.rpartition("/")
    engine, _, query = engine_query.partition("?")
    assert engine == result_engine
    assert query.startswith("message=msg")
    assert query[12:] == result_query


@pytest.mark.parametrize(
    ("engine", "language", "options"),
    (
        ("not-loaded-engine", None, None),
        (None, "unsupported-language", None),
        (None, None, {"option": "not-supported"}),
    ),
)
async def test_generate_media_source_id_invalid_options(
    hass: HomeAssistant, setup_tts, engine, language, options
) -> None:
    """Test generating a media source ID."""
    with pytest.raises(HomeAssistantError):
        tts.generate_media_source_id(hass, "msg", engine, language, options, None)


def test_resolve_engine(hass: HomeAssistant, setup_tts) -> None:
    """Test resolving engine."""
    assert tts.async_resolve_engine(hass, None) == "test"
    assert tts.async_resolve_engine(hass, "test") == "test"
    assert tts.async_resolve_engine(hass, "non-existing") is None

    with patch.dict(hass.data[tts.DATA_TTS_MANAGER].providers, {}, clear=True):
        assert tts.async_resolve_engine(hass, "test") is None

    with patch.dict(hass.data[tts.DATA_TTS_MANAGER].providers, {"cloud": object()}):
        assert tts.async_resolve_engine(hass, None) == "cloud"


async def test_support_options(hass: HomeAssistant, setup_tts) -> None:
    """Test supporting options."""
    # Language en is matched with en_US
    assert await tts.async_support_options(hass, "test", "en") is True
    assert await tts.async_support_options(hass, "test", "nl") is False
    assert (
        await tts.async_support_options(hass, "test", "en", {"invalid_option": "yo"})
        is False
    )


async def test_fetching_in_async(
    hass: HomeAssistant, hass_client: ClientSessionGenerator
) -> None:
    """Test async fetching of data."""
    tts_audio: asyncio.Future[bytes] = asyncio.Future()

    class ProviderWithAsyncFetching(MockProvider):
        """Provider that supports audio output option."""

        @property
        def supported_options(self) -> list[str]:
            """Return list of supported options like voice, emotions."""
            return [tts.ATTR_AUDIO_OUTPUT]

        @property
        def default_options(self) -> dict[str, str]:
            """Return a dict including the default options."""
            return {tts.ATTR_AUDIO_OUTPUT: "mp3"}

        async def async_get_tts_audio(
            self, message: str, language: str, options: dict[str, Any] | None = None
        ) -> tts.TtsAudioType:
            return ("mp3", await tts_audio)

    mock_integration(hass, MockModule(domain="test"))
    mock_platform(hass, "test.tts", MockTTS(ProviderWithAsyncFetching(DEFAULT_LANG)))
    assert await async_setup_component(hass, tts.DOMAIN, {"tts": {"platform": "test"}})

    # Test async_get_media_source_audio
    media_source_id = tts.generate_media_source_id(
        hass, "test message", "test", "en", None, None
    )

    task = hass.async_create_task(
        tts.async_get_media_source_audio(hass, media_source_id)
    )
    task2 = hass.async_create_task(
        tts.async_get_media_source_audio(hass, media_source_id)
    )

    url = await get_media_source_url(hass, media_source_id)
    client = await hass_client()
    client_get_task = hass.async_create_task(client.get(url))

    # Make sure that tasks are waiting for our future to resolve
    done, pending = await asyncio.wait((task, task2, client_get_task), timeout=0.1)
    assert len(done) == 0
    assert len(pending) == 3

    tts_audio.set_result(b"test")

    assert await task == ("mp3", b"test")
    assert await task2 == ("mp3", b"test")

    req = await client_get_task
    assert req.status == HTTPStatus.OK
    assert await req.read() == b"test"

    # Test error is not cached
    media_source_id = tts.generate_media_source_id(
        hass, "test message 2", "test", "en", None, None
    )
    tts_audio = asyncio.Future()
    tts_audio.set_exception(HomeAssistantError("test error"))
    with pytest.raises(HomeAssistantError):
        assert await tts.async_get_media_source_audio(hass, media_source_id)

    tts_audio = asyncio.Future()
    tts_audio.set_result(b"test 2")
    assert await tts.async_get_media_source_audio(hass, media_source_id) == (
        "mp3",
        b"test 2",
    )


async def test_ws_list_engines(
    hass: HomeAssistant, hass_ws_client: WebSocketGenerator, setup_tts
) -> None:
    """Test streaming audio and getting response."""
    client = await hass_ws_client()

    await client.send_json_auto_id({"type": "tts/engine/list"})

    msg = await client.receive_json()
    assert msg["success"]
    assert msg["result"] == {"providers": [{"engine_id": "test"}]}

    await client.send_json_auto_id({"type": "tts/engine/list", "language": "smurfish"})

    msg = await client.receive_json()
    assert msg["success"]
    assert msg["result"] == {
        "providers": [{"engine_id": "test", "language_supported": False}]
    }

    await client.send_json_auto_id({"type": "tts/engine/list", "language": "en"})

    msg = await client.receive_json()
    assert msg["success"]
    assert msg["result"] == {
        "providers": [{"engine_id": "test", "language_supported": True}]
    }

    await client.send_json_auto_id({"type": "tts/engine/list", "language": "en-UK"})

    msg = await client.receive_json()
    assert msg["success"]
    assert msg["result"] == {
        "providers": [{"engine_id": "test", "language_supported": True}]
    }


async def test_ws_list_voices(
    hass: HomeAssistant, hass_ws_client: WebSocketGenerator, setup_tts
) -> None:
    """Test streaming audio and getting response."""
    client = await hass_ws_client()

    await client.send_json_auto_id(
        {
            "type": "tts/engine/voices",
            "engine_id": "smurf_tts",
            "language": "smurfish",
        }
    )

    msg = await client.receive_json()
    assert not msg["success"]
    assert msg["error"] == {
        "code": "not_found",
        "message": "tts engine smurf_tts not found",
    }

    await client.send_json_auto_id(
        {
            "type": "tts/engine/voices",
            "engine_id": "test",
            "language": "smurfish",
        }
    )

    msg = await client.receive_json()
    assert msg["success"]
    assert msg["result"] == {"voices": None}

    await client.send_json_auto_id(
        {
            "type": "tts/engine/voices",
            "engine_id": "test",
            "language": "en-US",
        }
    )

    msg = await client.receive_json()
    assert msg["success"]
    assert msg["result"] == {"voices": ["James Earl Jones", "Fran Drescher"]}
