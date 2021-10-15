"""Tests for the OctoPrint integration."""
from unittest.mock import patch

from pyoctoprintapi import (
    DiscoverySettings,
    OctoprintJobInfo,
    OctoprintPrinterInfo,
    TrackingSetting,
)

from homeassistant import config_entries
from homeassistant.components.octoprint import DOMAIN

from tests.common import MockConfigEntry

DEFAULT_JOB = {
    "job": {},
    "progress": {"completion": 50},
}

DEFAULT_PRINTER = {
    "state": {
        "flags": {"printing": True, "error": False},
        "text": "Operational",
    },
    "temperature": [],
}


async def init_integration(
    hass, platform, printer: dict = DEFAULT_PRINTER, job: dict = DEFAULT_JOB
):
    """Set up the octoprint integration in Home Assistant."""
    with patch("homeassistant.components.octoprint.PLATFORMS", [platform]), patch(
        "pyoctoprintapi.OctoprintClient.get_server_info", return_value={}
    ), patch(
        "pyoctoprintapi.OctoprintClient.get_printer_info",
        return_value=OctoprintPrinterInfo(printer),
    ), patch(
        "pyoctoprintapi.OctoprintClient.get_job_info",
        return_value=OctoprintJobInfo(job),
    ), patch(
        "pyoctoprintapi.OctoprintClient.get_tracking_info",
        return_value=TrackingSetting({"unique_id": "uuid"}),
    ), patch(
        "pyoctoprintapi.OctoprintClient.get_discovery_info",
        return_value=DiscoverySettings({"upnpUuid": "uuid"}),
    ):
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            entry_id="uuid",
            unique_id="uuid",
            data={
                "host": "1.1.1.1",
                "api_key": "test-key",
                "name": "Octoprint",
                "port": 81,
                "ssl": True,
                "path": "/",
            },
            title="Octoprint",
        )
        config_entry.add_to_hass(hass)

        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    assert config_entry.state == config_entries.ENTRY_STATE_LOADED
