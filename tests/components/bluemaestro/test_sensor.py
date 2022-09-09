"""Test the BlueMaestro sensors."""

from unittest.mock import patch

from homeassistant.components.bluemaestro.const import DOMAIN
from homeassistant.components.bluetooth import BluetoothChange
from homeassistant.components.sensor import ATTR_STATE_CLASS
from homeassistant.const import ATTR_FRIENDLY_NAME, ATTR_UNIT_OF_MEASUREMENT

from . import BLUEMAESTRO_SERVICE_INFO

from tests.common import MockConfigEntry


async def test_sensors(hass):
    """Test setting up creates the sensors."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="aa:bb:cc:dd:ee:ff",
    )
    entry.add_to_hass(hass)

    saved_callback = None

    def _async_register_callback(_hass, _callback, _matcher, _mode):
        nonlocal saved_callback
        saved_callback = _callback
        return lambda: None

    with patch(
        "homeassistant.components.bluetooth.update_coordinator.async_register_callback",
        _async_register_callback,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert len(hass.states.async_all("sensor")) == 0
    saved_callback(BLUEMAESTRO_SERVICE_INFO, BluetoothChange.ADVERTISEMENT)
    await hass.async_block_till_done()
    assert len(hass.states.async_all("sensor")) == 4

    humid_sensor = hass.states.get("sensor.tempo_disc_thd_eeff_temperature")
    humid_sensor_attrs = humid_sensor.attributes
    assert humid_sensor.state == "24.2"
    assert humid_sensor_attrs[ATTR_FRIENDLY_NAME] == "Tempo Disc THD EEFF Temperature"
    assert humid_sensor_attrs[ATTR_UNIT_OF_MEASUREMENT] == "°C"
    assert humid_sensor_attrs[ATTR_STATE_CLASS] == "measurement"

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
