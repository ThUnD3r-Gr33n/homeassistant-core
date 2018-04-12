from unittest.mock import Mock
import uuid

import pytest

from homeassistant import auth
from homeassistant.auth_providers import example


@pytest.fixture
def store():
    """Mock store."""
    return auth.AuthStore()


@pytest.fixture
def provider(store):
    """Mock provider."""
    return example.ExampleAuthProvider(store, {
        'type': 'example',
        'users': [
            {
                'username': 'user-test',
                'password': 'password-test'
            }
        ]
    })


async def test_create_new_credential(provider):
    """Test that we create a new credential."""
    credentials = await provider.async_get_or_create_credentials({
        'username': 'user-test',
        'password': 'password-test',
    })
    assert credentials.id is None


async def test_match_existing_credentials(store, provider):
    """See if we match existing users."""
    existing = auth.Credentials(
        id=uuid.uuid4(),
        auth_provider_type='example',
        auth_provider_id=None,
        data={
            'username': 'user-test'
        },
    )
    store.credentials.append(existing)
    credentials = await provider.async_get_or_create_credentials({
        'username': 'user-test',
        'password': 'password-test',
    })
    assert credentials is existing


async def test_verify_username(provider):
    """Test we raise if incorrect user specified."""
    with pytest.raises(auth.InvalidUser):
        await provider.async_get_or_create_credentials({
            'username': 'non-existing-user',
            'password': 'password-test',
        })


async def test_verify_password(provider):
    """Test we raise if incorrect user specified."""
    with pytest.raises(auth.InvalidPassword):
        await provider.async_get_or_create_credentials({
            'username': 'user-test',
            'password': 'incorrect-password',
        })
