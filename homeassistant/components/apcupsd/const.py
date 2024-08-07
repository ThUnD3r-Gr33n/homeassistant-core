"""Constants for APCUPSd component."""

from typing import Final

DOMAIN: Final = "apcupsd"
CONNECTION_TIMEOUT: int = 10

# Field name of last self test retrieved from apcupsd.
LASTSTEST: Final = "laststest"
