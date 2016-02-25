"""
Sensor for Steam account status.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.steam_online/
"""
from homeassistant.helpers.entity import Entity
from homeassistant.const import CONF_API_KEY

ICON = 'mdi:steam'

REQUIREMENTS = ['steamodd==4.21']


# pylint: disable=unused-argument
def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the Steam platform."""
    import steam as steamod
    steamod.api.key.set(config.get(CONF_API_KEY))
    add_devices(
        [SteamSensor(account,
                     steamod) for account in config.get('accounts', [])])


class SteamSensor(Entity):
    """A class for the Steam account."""
    # pylint: disable=abstract-method
    def __init__(self, account, steamod):
        self._steamod = steamod
        self._account = account
        self.update()

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._profile.persona

    @property
    def entity_id(self):
        """Return the entity ID."""
        return 'sensor.steam_{}'.format(self._account)

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    # pylint: disable=no-member
    def update(self):
        """Update device state."""
        self._profile = self._steamod.user.profile(self._account)
        self._state = {
            1: 'Online',
            2: 'Busy',
            3: 'Away',
            4: 'Snooze',
            5: 'Trade',
            6: 'Play',
        }.get(self._profile.status, 'Offline')

    @property
    def entity_picture(self):
        """Avatar of the account."""
        return self._profile.avatar_medium

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return ICON
