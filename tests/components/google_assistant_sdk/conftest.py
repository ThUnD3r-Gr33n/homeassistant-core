"""PyTest fixtures and test helpers."""
from collections.abc import Awaitable, Callable, Coroutine
import json
import os
import time
from typing import Any

from google.oauth2.credentials import Credentials
import pytest

from homeassistant.components.application_credentials import (
    ClientCredential,
    async_import_client_credential,
)
from homeassistant.components.google_assistant_sdk.const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from tests.common import MockConfigEntry

ComponentSetup = Callable[[], Awaitable[None]]

CLIENT_ID = "1234"
CLIENT_SECRET = "5678"
ACCESS_TOKEN = "mock-access-token"


@pytest.fixture
async def setup_credentials(hass: HomeAssistant) -> None:
    """Fixture to setup credentials."""
    assert await async_setup_component(hass, "application_credentials", {})
    await async_import_client_credential(
        hass,
        DOMAIN,
        ClientCredential(CLIENT_ID, CLIENT_SECRET),
    )


@pytest.fixture(name="scopes")
def mock_scopes() -> list[str]:
    """Fixture to set the scopes present in the OAuth token."""
    return ["https://www.googleapis.com/auth/assistant-sdk-prototype"]


@pytest.fixture(name="expires_at")
def mock_expires_at() -> int:
    """Fixture to set the oauth token expiration time."""
    return time.time() + 3600


@pytest.fixture(name="config_entry")
def mock_config_entry(expires_at: int, scopes: list[str]) -> MockConfigEntry:
    """Fixture for MockConfigEntry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            "auth_implementation": DOMAIN,
            "token": {
                "access_token": ACCESS_TOKEN,
                "refresh_token": "mock-refresh-token",
                "expires_at": expires_at,
                "scope": " ".join(scopes),
            },
        },
    )


@pytest.fixture(name="setup_integration")
async def mock_setup_integration(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> Callable[[], Coroutine[Any, Any, None]]:
    """Fixture for setting up the component."""
    config_entry.add_to_hass(hass)

    assert await async_setup_component(hass, "application_credentials", {})
    await async_import_client_credential(
        hass,
        DOMAIN,
        ClientCredential("client-id", "client-secret"),
        DOMAIN,
    )

    async def func() -> None:
        assert await async_setup_component(hass, DOMAIN, {})
        await hass.async_block_till_done()

    return func


@pytest.fixture
def credentials_json(hass: HomeAssistant) -> dict:
    """Fixture for setting up and tearing down config/google_assistant_sdk_credentials.json."""
    credentials_json = {
        "refresh_token": "a refresh token",
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": "a client id",
        "client_secret": "a client secret",
    }
    credentials_json_filename = os.path.join(
        hass.config.config_dir, "google_assistant_sdk_credentials.json"
    )
    with open(
        credentials_json_filename, "w", encoding="utf-8"
    ) as credentials_json_file:
        json.dump(credentials_json, credentials_json_file)

    yield credentials_json

    os.remove(credentials_json_filename)


class ExpectedCredentials:
    """Assert credentials have the expected tokens."""

    def __init__(
        self,
        expected_access_token: str = ACCESS_TOKEN,
        expected_refresh_token: str = None,
    ) -> None:
        """Initialize ExpectedCredentials."""
        self.expected_access_token = expected_access_token
        self.expected_refresh_token = expected_refresh_token

    def __eq__(self, other: Credentials):
        """Return true if credentials have the expected access token."""
        return (
            other.token == self.expected_access_token
            and other.refresh_token == self.expected_refresh_token
        )
