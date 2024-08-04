"""Constants for the evohome tests."""

from __future__ import annotations

from typing import Final

ACCESS_TOKEN: Final = "at_1dc7z657UKzbhKA..."
REFRESH_TOKEN: Final = "rf_jg68ZCKYdxEI3fF..."
SESSION_ID: Final = "F7181186..."
USERNAME: Final = "test_user@gmail.com"

TEST_INSTALLS: Final = {
    "minimal": {},  # evohome (single zone, no DHW)
    "default": {},  # evohome
    "h032585": {},  # VisionProWifi
    "h099625": {},  # RoundThermostat
    "system_004": {},  # Multiple
}
