"""The tests for the humidifier component."""
from unittest.mock import MagicMock
from typing import List

import pytest
import voluptuous as vol

from homeassistant.helpers.config_validation import ENTITY_SERVICE_SCHEMA

from homeassistant.components.humidifier import (
    HumidifierDevice,
    OPERATION_MODE_HUMIDIFY,
    OPERATION_MODE_OFF,
    ATTR_HUMIDITY,
    SUPPORT_TARGET_HUMIDITY,
)
from tests.common import async_mock_service

SET_HUMIDITY_SCHEMA = ENTITY_SERVICE_SCHEMA.extend(
    {vol.Required(ATTR_HUMIDITY): vol.Coerce(float)}
)


async def test_set_hum_schema_no_req(hass, caplog):
    """Test the set humidity schema with missing required data."""
    domain = "humidifier"
    service = "test_set_humidity"
    schema = SET_HUMIDITY_SCHEMA
    calls = async_mock_service(hass, domain, service, schema)

    data = {"entity_id": ["humidifier.test_id"]}
    with pytest.raises(vol.Invalid):
        await hass.services.async_call(domain, service, data)
    await hass.async_block_till_done()

    assert len(calls) == 0


async def test_set_hum_schema(hass, caplog):
    """Test the set humidity schema with ok required data."""
    domain = "humidifier"
    service = "test_set_humidity"
    schema = SET_HUMIDITY_SCHEMA
    calls = async_mock_service(hass, domain, service, schema)

    data = {"humidity": 50.0, "entity_id": ["humidifier.test_id"]}
    await hass.services.async_call(domain, service, data)
    await hass.async_block_till_done()

    assert len(calls) == 1
    assert calls[-1].data == data


class MockHumidifierDevice(HumidifierDevice):
    """Mock Humidifier device to use in tests."""

    @property
    def operation_mode(self) -> str:
        """Return humidifier operation ie. humidify, dry mode."""
        return OPERATION_MODE_HUMIDIFY

    @property
    def operation_modes(self) -> List[str]:
        """Return the list of available humidifier operation modes."""
        return [OPERATION_MODE_OFF, OPERATION_MODE_HUMIDIFY]

    @property
    def supported_features(self) -> int:
        """Return the list of supported features."""
        return SUPPORT_TARGET_HUMIDITY


async def test_sync_turn_on(hass):
    """Test if async turn_on calls sync turn_on."""
    humidifier = MockHumidifierDevice()
    humidifier.hass = hass

    humidifier.turn_on = MagicMock()
    await humidifier.async_turn_on()

    assert humidifier.turn_on.called


async def test_sync_turn_off(hass):
    """Test if async turn_off calls sync turn_off."""
    humidifier = MockHumidifierDevice()
    humidifier.hass = hass

    humidifier.turn_off = MagicMock()
    await humidifier.async_turn_off()

    assert humidifier.turn_off.called
