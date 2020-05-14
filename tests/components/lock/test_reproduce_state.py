"""Test reproduce state for Lock."""
from homeassistant.core import State

from tests.common import async_mock_service


async def test_reproducing_states(hass, caplog):
    """Test reproducing Lock states."""
    hass.states.async_set("lock.entity_locked", "locked", {})
    hass.states.async_set("lock.entity_unlocked", "unlocked", {})

    lock_calls = async_mock_service(hass, "lock", "lock")
    unlock_calls = async_mock_service(hass, "lock", "unlock")

    # These calls should do nothing as entities already in desired state
    await hass.helpers.state.async_reproduce_state(
        [
            State("lock.entity_locked", "locked"),
            State("lock.entity_unlocked", "unlocked", {}),
        ],
    )

    assert len(lock_calls) == 0
    assert len(unlock_calls) == 0

    # Test invalid state is handled
    await hass.helpers.state.async_reproduce_state(
        [State("lock.entity_locked", "not_supported")]
    )

    assert "not_supported" in caplog.text
    assert len(lock_calls) == 0
    assert len(unlock_calls) == 0

    # Make sure correct services are called
    await hass.helpers.state.async_reproduce_state(
        [
            State("lock.entity_locked", "unlocked"),
            State("lock.entity_unlocked", "locked"),
            # Should not raise
            State("lock.non_existing", "on"),
        ],
    )

    assert len(lock_calls) == 1
    assert lock_calls[0].domain == "lock"
    assert lock_calls[0].data == {"entity_id": "lock.entity_unlocked"}

    assert len(unlock_calls) == 1
    assert unlock_calls[0].domain == "lock"
    assert unlock_calls[0].data == {"entity_id": "lock.entity_locked"}
