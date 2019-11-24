"""Test reproduce state for Lock."""
from homeassistant.core import State

from tests.common import async_mock_service


async def test_reproducing_states(hass, caplog):
    """Test reproducing Lock states."""
    hass.states.async_set("lock.entity_locked", "locked", {})
    hass.states.async_set("lock.entity_unlocked", "unlocked", {})

    lock_calls = async_mock_service(hass, "lock", "lock")
    unlock_calls = async_mock_service(hass, "lock", "unlock")

    # Even if the target state is the same as the current we still needs
    # to do the calls, as the current state is just a cache of the real one
    # and could be out of sync.
    await hass.helpers.state.async_reproduce_state(
        [
            State("lock.entity_locked", "locked"),
            State("lock.entity_unlocked", "unlocked", {}),
        ],
        blocking=True,
    )

    assert len(lock_calls) == 1
    assert len(unlock_calls) == 1

    # Test invalid state is handled
    await hass.helpers.state.async_reproduce_state(
        [State("lock.entity_locked", "not_supported")], blocking=True
    )

    assert "not_supported" in caplog.text
    assert len(lock_calls) == 1
    assert len(unlock_calls) == 1

    # Make sure correct services are called
    await hass.helpers.state.async_reproduce_state(
        [
            State("lock.entity_locked", "unlocked"),
            State("lock.entity_unlocked", "locked"),
            # Should not raise
            State("lock.non_existing", "on"),
        ],
        blocking=True,
    )

    assert len(lock_calls) == 2
    assert lock_calls[-1].domain == "lock"
    assert lock_calls[-1].data == {"entity_id": "lock.entity_unlocked"}

    assert len(unlock_calls) == 2
    assert unlock_calls[-1].domain == "lock"
    assert unlock_calls[-1].data == {"entity_id": "lock.entity_locked"}
