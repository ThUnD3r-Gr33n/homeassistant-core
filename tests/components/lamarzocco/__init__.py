"""Mock inputs for tests."""

from lmcloud.const import LaMarzoccoModel

from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.service_info.bluetooth import BluetoothServiceInfo

from tests.common import MockConfigEntry

USER_INPUT = {
    CONF_USERNAME: "username",
    CONF_PASSWORD: "password",
}

HOST_SELECTION = {
    CONF_HOST: "192.168.1.1",
}

PASSWORD_SELECTION = {
    CONF_PASSWORD: "password",
}


async def async_init_integration(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Set up the La Marzocco integration for testing."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()


def get_bluetooth_service_info(
    model: LaMarzoccoModel, serial: str
) -> BluetoothServiceInfo:
    """Return a mocked BluetoothServiceInfo."""
    if model in (LaMarzoccoModel.GS3_AV, LaMarzoccoModel.GS3_MP):
        name = f"GS3_{serial}"
    elif model == LaMarzoccoModel.LINEA_MINI:
        name = f"MINI_{serial}"
    elif model == LaMarzoccoModel.LINEA_MICRA:
        name = f"MICRA_{serial}"
    return BluetoothServiceInfo(
        name=name,
        address="aa:bb:cc:dd:ee:ff",
        rssi=-63,
        manufacturer_data={},
        service_data={},
        service_uuids=[],
        source="local",
    )
