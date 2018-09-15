"""Huawei LTE component tests."""
import pytest

from homeassistant.components import huawei_lte


@pytest.fixture(autouse=True)
def routerdata():
    """Set up a router data for testing."""
    rd = huawei_lte.RouterData(None)
    rd.device_information = dict(
        SoftwareVersion="1.0",
        nested=dict(foo="bar"),
    )
    return rd


async def test_routerdata_get_nonexistent_leaf(routerdata):
    """Test that accessing a nonexistent leaf element raises KeyError."""
    with pytest.raises(KeyError):
        routerdata["device_information.foo"]


async def test_routerdata_get_nonexistent_leaf_path(routerdata):
    """Test that accessing a nonexistent long path raises KeyError."""
    with pytest.raises(KeyError):
        routerdata["device_information.long.path.foo"]


async def test_routerdata_get_simple(routerdata):
    """Test that accessing a short, simple path works."""
    assert routerdata["device_information.SoftwareVersion"] == "1.0"


async def test_routerdata_get_longer(routerdata):
    """Test that accessing a longer path works."""
    assert routerdata["device_information.nested.foo"] == "bar"


async def test_routerdata_get_dict(routerdata):
    """Test that returning an intermediate dict works."""
    assert routerdata["device_information.nested"] == dict(foo="bar")
