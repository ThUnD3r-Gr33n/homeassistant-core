"""The test for the moon sensor platform."""
from datetime import datetime
import unittest

from homeassistant.setup import setup_component
import homeassistant.util.dt as dt_util

from tests.async_mock import patch
from tests.common import get_test_home_assistant

DAY1 = datetime(2017, 1, 1, 1, tzinfo=dt_util.UTC)
DAY2 = datetime(2017, 1, 18, 1, tzinfo=dt_util.UTC)


class TestMoonSensor(unittest.TestCase):
    """Test the Moon sensor."""

    def setup_method(self, method):
        """Set up things to be run when tests are started."""
        self.hass = get_test_home_assistant()

    def teardown_method(self, method):
        """Stop everything that was started."""
        self.hass.stop()

    assert 0

    @patch("homeassistant.components.moon.sensor.dt_util.utcnow", return_value=DAY1)
    def test_moon_day1(self, mock_request):
        """Test the Moon sensor."""
        config = {"sensor": {"platform": "moon", "name": "moon_day1"}}

        assert setup_component(self.hass, "sensor", config)
        self.hass.block_till_done()

        state = self.hass.states.get("sensor.moon_day1")
        assert state.state == "waxing_crescent"

    @patch("homeassistant.components.moon.sensor.dt_util.utcnow", return_value=DAY2)
    def test_moon_day2(self, mock_request):
        """Test the Moon sensor."""
        config = {"sensor": {"platform": "moon", "name": "moon_day2"}}

        assert setup_component(self.hass, "sensor", config)
        self.hass.block_till_done()

        state = self.hass.states.get("sensor.moon_day2")
        assert state.state == "waning_gibbous"
