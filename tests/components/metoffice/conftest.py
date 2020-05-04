"""Fixtures for Met Office weather integration tests."""
from datapoint.exceptions import APIException
import pytest

from tests.async_mock import patch


@pytest.fixture()
def managerfail_mock():
    """Mock datapoint Manager with default values for testing in config_flow."""
    with patch("datapoint.Manager") as mock_manager:
        instance = mock_manager.return_value
        instance.get_nearest_forecast_site.side_effect = APIException()
        instance.get_forecast_for_site.side_effect = APIException()
        instance.latitude = None
        instance.longitude = None
        instance.mode = None
        instance.site = None
        instance.site_id = None
        instance.site_name = None
        instance.now = None
        instance.all = None

        yield mock_manager
