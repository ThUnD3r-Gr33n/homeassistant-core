"""Configuration for Ring tests."""

from collections.abc import Generator
from itertools import chain
from unittest.mock import AsyncMock, Mock, create_autospec, patch

import pytest
import ring_doorbell

from homeassistant.components.ring import DOMAIN
from homeassistant.const import CONF_USERNAME
from homeassistant.core import HomeAssistant

from .device_mocks import get_active_alerts, get_devices_data, get_mock_devices

from tests.common import MockConfigEntry
from tests.components.light.conftest import mock_light_profiles  # noqa: F401


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock, None, None]:
    """Override async_setup_entry."""
    with patch(
        "homeassistant.components.ring.async_setup_entry", return_value=True
    ) as mock_setup_entry:
        yield mock_setup_entry


@pytest.fixture
def mock_ring_auth():
    """Mock ring_doorbell.Auth."""
    with patch(
        "homeassistant.components.ring.config_flow.Auth", autospec=True
    ) as mock_ring_auth:
        mock_ring_auth.return_value.fetch_token.return_value = {
            "access_token": "mock-token"
        }
        yield mock_ring_auth.return_value


@pytest.fixture
def mock_ring_devices():
    """Mock Ring devices."""

    devices = get_mock_devices()
    device_list = list(chain.from_iterable(devices.values()))

    class FakeRingDevices:
        """Class fakes the RingDevices class."""

        all_devices = device_list
        video_devices = (
            devices["stickup_cams"]
            + devices["doorbots"]
            + devices["authorized_doorbots"]
        )
        stickup_cams = devices["stickup_cams"]
        other = devices["other"]
        chimes = devices["chimes"]

        get_device = lambda _, id: [
            device for device in device_list if device.id == id
        ][0]
        get_video_device = lambda _, id: [
            device
            for device in device_list
            if (
                device.id == id
                and device.family in {"stickup_cams", "doorbots", "authorized_doorbots"}
            )
        ][0]
        get_stickup_cam = lambda _, id: [
            device
            for device in device_list
            if (device.id == id and device.family == "stickup_cams")
        ][0]
        get_other = lambda _, id: [
            device
            for device in device_list
            if (device.id == id and device.family == "others")
        ][0]

    return FakeRingDevices()


@pytest.fixture
def mock_ring_client(mock_ring_auth, mock_ring_devices):
    """Mock ring client api."""
    mock_client = create_autospec(ring_doorbell.Ring)
    mock_client.return_value.devices_data = get_devices_data()
    mock_client.return_value.devices.return_value = mock_ring_devices
    mock_client.return_value.active_alerts.side_effect = get_active_alerts

    with patch("homeassistant.components.ring.Ring", new=mock_client):
        yield mock_client.return_value


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Mock ConfigEntry."""
    return MockConfigEntry(
        title="Ring",
        domain=DOMAIN,
        data={
            CONF_USERNAME: "foo@bar.com",
            "token": {"access_token": "mock-token"},
        },
        unique_id="foo@bar.com",
    )


@pytest.fixture
async def mock_added_config_entry(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_ring_auth: Mock,
    mock_ring_client: Mock,
) -> MockConfigEntry:
    """Mock ConfigEntry that's been added to HA."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert DOMAIN in hass.config_entries.async_domains()
    return mock_config_entry
