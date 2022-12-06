"""The TED component."""
from homeassistant.const import Platform

DOMAIN = "ted"
PLATFORMS = [Platform.SENSOR]

COORDINATOR = "coordinator"
NAME = "name"

OPTION_DEFAULTS = {
    "show_spyder_energy_now": False,
    "show_spyder_energy_daily": False,
    "show_spyder_energy_mtd": True,
    "show_mtu_power_voltage": True,
    "show_mtu_energy_now": False,
    "show_mtu_energy_daily": False,
    "show_mtu_energy_mtd": True,
}
