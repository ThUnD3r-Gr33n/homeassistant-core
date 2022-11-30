"""Tests for HomematicIP Cloud locks."""
from homematicip.base.enums import LockState

from homeassistant.components.homematicip_cloud import DOMAIN as HMIPC_DOMAIN
from homeassistant.components.lock import DOMAIN, LockEntityFeature
from homeassistant.const import ATTR_SUPPORTED_FEATURES
from homeassistant.setup import async_setup_component

from .helper import get_and_check_entity_basics


async def test_manually_configured_platform(hass):
    """Test that we do not set up an access point."""
    assert await async_setup_component(
        hass, DOMAIN, {DOMAIN: {"platform": HMIPC_DOMAIN}}
    )
    assert not hass.data.get(HMIPC_DOMAIN)


async def test_hmip_doorlockdrive(hass, default_mock_hap_factory):
    """Test HomematicipDoorLockDrive."""
    entity_id = "lock.haustuer"
    entity_name = "Haustuer"
    device_model = "HmIP-DLD"
    mock_hap = await default_mock_hap_factory.async_get_mock_hap(
        test_devices=[entity_name]
    )

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.attributes[ATTR_SUPPORTED_FEATURES] == LockEntityFeature.OPEN

    await hass.services.async_call(
        "lock",
        "open",
        {"entity_id": entity_id},
        blocking=True,
    )
    assert hmip_device.mock_calls[-1][0] == "set_lock_state"
    assert hmip_device.mock_calls[-1][1] == (LockState.OPEN,)

    await hass.services.async_call(
        "lock",
        "lock",
        {"entity_id": entity_id},
        blocking=True,
    )
    assert hmip_device.mock_calls[-1][0] == "set_lock_state"
    assert hmip_device.mock_calls[-1][1] == (LockState.LOCKED,)

    await hass.services.async_call(
        "lock",
        "unlock",
        {"entity_id": entity_id},
        blocking=True,
    )

    assert hmip_device.mock_calls[-1][0] == "set_lock_state"
    assert hmip_device.mock_calls[-1][1] == (LockState.UNLOCKED,)

    #     await async_manipulate_test_data(hass, hmip_device, "dimLevel", 1, 2)
    # await async_manipulate_test_data(
    #     hass, hmip_device, "simpleRGBColorState", RGBColorState.PURPLE, 2
    # )
    # ha_state = hass.states.get(entity_id)
    # assert ha_state.state == STATE_ON
    # # assert service_call_counter + 1 == len(hmip_device.mock_calls)
