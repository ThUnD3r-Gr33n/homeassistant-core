"""Test the Lovelace initialization."""
from homeassistant.setup import async_setup_component
from homeassistant.components import lovelace


async def test_lovelace_from_storage(hass, hass_ws_client, hass_storage):
    """Test we load lovelace config from storage."""
    assert await async_setup_component(hass, 'lovelace', {})

    client = await hass_ws_client(hass)

    # Fetch data
    await client.send_json({
        'id': 5,
        'type': 'lovelace/config'
    })
    response = await client.receive_json()
    assert response['success']

    assert response['result'] is None

    # Store new config
    await client.send_json({
        'id': 6,
        'type': 'lovelace/config/save',
        'config': {
            'yo': 'hello'
        }
    })
    response = await client.receive_json()
    assert response['success']
    assert hass_storage[lovelace.STORAGE_KEY]['data'] == {
        'yo': 'hello'
    }

    # Load new config
    await client.send_json({
        'id': 7,
        'type': 'lovelace/config'
    })
    response = await client.receive_json()
    assert response['success']

    assert response['result'] == {
        'yo': 'hello'
    }


async def test_lovelace_from_yaml(hass, hass_ws_client):
    """Test we load lovelace config from yaml."""
    assert await async_setup_component(hass, 'lovelace', {
        'lovelace': {
            'legacy': True
        }
    })

    client = await hass_ws_client(hass)

    # Fetch data
    await client.send_json({
        'id': 5,
        'type': 'lovelace/config'
    })
    response = await client.receive_json()
    assert not response['success']

    assert response['error']['code'] == 'file_not_found'

    # Store new config not allowed
    await client.send_json({
        'id': 6,
        'type': 'lovelace/config/save',
        'config': {
            'yo': 'hello'
        }
    })
    response = await client.receive_json()
    assert not response['success']
