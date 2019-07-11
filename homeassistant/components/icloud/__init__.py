"""The iCloud component."""
import logging
import operator
import os
from datetime import timedelta

import voluptuous as vol
from pyicloud import PyiCloudService
from pyicloud.exceptions import (PyiCloudException,
                                 PyiCloudFailedLoginException,
                                 PyiCloudNoDevicesException)
from pyicloud.services.findmyiphone import AppleDevice

import homeassistant.helpers.config_validation as cv
from homeassistant.components.zone import async_active_zone
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ATTRIBUTION, CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.discovery import load_platform
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.typing import ConfigType, HomeAssistantType
from homeassistant.util import slugify
from homeassistant.util.async_ import run_callback_threadsafe
from homeassistant.util.dt import utcnow
from homeassistant.util.location import distance

from .config_flow import IcloudFlowHandler  # noqa
from .const import (CONF_ACCOUNTNAME, CONF_GPS_ACCURACY_THRESHOLD,
                    CONF_MAX_INTERVAL, DATA_ICLOUD, DOMAIN, ICLOUD_COMPONENTS,
                    SIGNAL_UPDATE_ICLOUD)

ATTRIBUTION = "Data provided by Apple iCloud"

# entity attributes
ATTR_BATTERY = 'battery'
ATTR_BATTERYSTATUS = 'battery_status'
ATTR_DEVICENAME = 'device_name'
ATTR_DEVICESTATUS = 'device_status'
ATTR_LOWPOWERMODE = 'low_power_mode'
ATTR_OWNERNAME = 'owner_fullname'

DEVICE_STATUS_SET = ['features', 'maxMsgChar', 'darkWake', 'fmlyShare',
                     'deviceStatus', 'remoteLock', 'activationLocked',
                     'deviceClass', 'id', 'deviceModel', 'rawDeviceModel',
                     'passcodeLength', 'canWipeAfterLock', 'trackingInfo',
                     'location', 'msg', 'batteryLevel', 'remoteWipe',
                     'thisDevice', 'snd', 'prsId', 'wipeInProgress',
                     'lowPowerMode', 'lostModeEnabled', 'isLocating',
                     'lostModeCapable', 'mesg', 'name', 'batteryStatus',
                     'lockedTimestamp', 'lostTimestamp', 'locationCapable',
                     'deviceDisplayName', 'lostDevice', 'deviceColor',
                     'wipedTimestamp', 'modelDisplayName', 'locationEnabled',
                     'isMac', 'locFoundEnabled']

DEVICE_STATUS_CODES = {
    '200': 'online',
    '201': 'offline',
    '203': 'pending',
    '204': 'unregistered',
}

_CONFIGURING = {}

_LOGGER = logging.getLogger(__name__)

SERVICE_ICLOUD_PLAY_SOUND = 'play_sound'
SERVICE_ICLOUD_DISPLAY_MESSAGE = 'display_message'
SERVICE_ICLOUD_LOST_DEVICE = 'lost_device'
SERVICE_ICLOUD_UPDATE = 'update'
SERVICE_ICLOUD_RESET = 'reset'
SERVICE_ATTR_LOST_DEVICE_MESSAGE = 'message'
SERVICE_ATTR_LOST_DEVICE_NUMBER = 'number'
SERVICE_ATTR_LOST_DEVICE_SOUND = 'sound'

SERVICE_SCHEMA = vol.Schema({
    vol.Optional(CONF_ACCOUNTNAME): cv.string,
})

SERVICE_SCHEMA_PLAY_SOUND = vol.Schema({
    vol.Required(CONF_ACCOUNTNAME): cv.string,
    vol.Required(ATTR_DEVICENAME): cv.string,
})

SERVICE_SCHEMA_DISPLAY_MESSAGE = vol.Schema({
    vol.Required(CONF_ACCOUNTNAME): cv.string,
    vol.Required(ATTR_DEVICENAME): cv.string,
    vol.Required(SERVICE_ATTR_LOST_DEVICE_MESSAGE): cv.string,
    vol.Optional(SERVICE_ATTR_LOST_DEVICE_SOUND): cv.boolean,
})

SERVICE_SCHEMA_LOST_DEVICE = vol.Schema({
    vol.Required(CONF_ACCOUNTNAME): cv.string,
    vol.Required(ATTR_DEVICENAME): cv.string,
    vol.Required(SERVICE_ATTR_LOST_DEVICE_NUMBER): cv.string,
    vol.Required(SERVICE_ATTR_LOST_DEVICE_MESSAGE): cv.string,
})

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.All(cv.ensure_list, [vol.Schema({
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_ACCOUNTNAME): cv.slugify,
        vol.Optional(CONF_MAX_INTERVAL, default=30): cv.positive_int,
        vol.Optional(CONF_GPS_ACCURACY_THRESHOLD, default=500): cv.positive_int
    })])
}, extra=vol.ALLOW_EXTRA)

_LOGGER.error('ICLOUD_INIT_:')

async def async_setup(hass: HomeAssistantType, config: ConfigType) -> bool:
    """Set up the iCloud components."""
    _LOGGER.error('ICLOUD_INIT_:setup')
    return True

async def async_setup_entry(
        hass: HomeAssistantType, entry: ConfigEntry
) -> bool:
    """Set up an iCloud account from a config entry."""

    _LOGGER.error('ICLOUD_INIT_:entry')

    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    account_name = entry.data.get(
        CONF_ACCOUNTNAME,
        slugify(username.partition('@')[0])
    )
    max_interval = entry.data[CONF_MAX_INTERVAL]
    gps_accuracy_threshold = entry.data[CONF_GPS_ACCURACY_THRESHOLD]

    account = IcloudAccount(
        hass,
        username,
        password,
        account_name,
        max_interval,
        gps_accuracy_threshold
    )
    account.reset_account()

    if account.api is None:
        _LOGGER.error("No iCloud data added for account=%s", account_name)
        return False

    hass.data[DATA_ICLOUD][account.name] = account

    for component in ICLOUD_COMPONENTS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    def play_sound(service):
        """Play sound on the device."""
        accountname = service.data.get(CONF_ACCOUNTNAME)
        accountname = slugify(accountname.partition('@')[0])
        devicename = service.data.get(ATTR_DEVICENAME)
        devicename = slugify(devicename.replace(' ', '', 99))

        hass.data[DATA_ICLOUD][accountname].devices[devicename].play_sound()

    def display_message(service):
        """Display a message on the device."""
        accountname = service.data.get(CONF_ACCOUNTNAME)
        accountname = slugify(accountname.partition('@')[0])
        devicename = service.data.get(ATTR_DEVICENAME)
        devicename = slugify(devicename.replace(' ', '', 99))
        message = service.data.get(SERVICE_ATTR_LOST_DEVICE_MESSAGE)
        sound = service.data.get(SERVICE_ATTR_LOST_DEVICE_SOUND, False)

        hass.data[DATA_ICLOUD][accountname].devices[
            devicename].display_message(
                message,
                sound)

    def lost_device(service):
        """Make the device in lost state."""
        accountname = service.data.get(CONF_ACCOUNTNAME)
        accountname = slugify(accountname.partition('@')[0])
        devicename = service.data.get(ATTR_DEVICENAME)
        devicename = slugify(devicename.replace(' ', '', 99))
        number = service.data.get(SERVICE_ATTR_LOST_DEVICE_NUMBER)
        message = service.data.get(SERVICE_ATTR_LOST_DEVICE_MESSAGE)

        hass.data[DATA_ICLOUD][accountname].devices[devicename].lost_device(
            number,
            message)

    def update(service):
        """Call the update function of an iCloud account."""
        accountname = service.data.get(CONF_ACCOUNTNAME)

        if accountname is None:
            for accountname, account in hass.data[DATA_ICLOUD].items():
                account.keep_alive(utcnow())
        else:
            accountname = slugify(accountname.partition('@')[0])
            hass.data[DATA_ICLOUD][accountname].keep_alive(utcnow())
    
    def reset_account(service):
        """Reset an iCloud account."""
        accountname = service.data.get(CONF_ACCOUNTNAME)

        if accountname is None:
            for accountname, account in hass.data[DATA_ICLOUD].items():
                account.reset_account()
        else:
            accountname = slugify(accountname.partition('@')[0])
            hass.data[DATA_ICLOUD][accountname].reset_account()

    hass.services.register(
        DOMAIN, SERVICE_ICLOUD_PLAY_SOUND, play_sound,
        schema=SERVICE_SCHEMA_PLAY_SOUND
    )

    hass.services.register(
        DOMAIN, SERVICE_ICLOUD_DISPLAY_MESSAGE, display_message,
        schema=SERVICE_SCHEMA_DISPLAY_MESSAGE
    )
    
    hass.services.register(
        DOMAIN, SERVICE_ICLOUD_LOST_DEVICE, lost_device,
        schema=SERVICE_SCHEMA_LOST_DEVICE
    )

    hass.services.register(
        DOMAIN, SERVICE_ICLOUD_UPDATE, update,
        schema=SERVICE_SCHEMA
    )

    hass.services.register(
        DOMAIN, SERVICE_ICLOUD_RESET, reset_account,
        schema=SERVICE_SCHEMA
    )

    return True

async def async_unload_entry(
        hass: HomeAssistantType, entry: ConfigType
) -> bool:
    """Unload iCloud config entry."""
    # for component in 'sensor', 'switch':
    #     await hass.config_entries.async_forward_entry_unload(entry, component)

    hass.data[DOMAIN].pop(entry.data[CONF_ACCOUNTNAME])
    return True

class IcloudAccount():
    """Representation of an iCloud account."""

    def __init__(self, hass, username, password, accountname, max_interval,
                 gps_accuracy_threshold):
        """Initialize an iCloud account."""
        self._hass = hass
        self.username = username
        self.__password = password
        self._accountname = accountname
        self._max_interval = max_interval
        self._gps_accuracy_threshold = gps_accuracy_threshold

        self.api = None
        self.account_owner_fullname = None
        self.family_members_fullname = {}
        self.devices = {}

        self.__trusted_device = None
        self.__verification_code = None

    def reset_account(self):
        """Reset an iCloud account."""
        icloud_dir = self._hass.config.path('icloud')
        if not os.path.exists(icloud_dir):
            os.makedirs(icloud_dir)

        try:
            self.api = PyiCloudService(
                self.username, self.__password,
                cookie_directory=icloud_dir,
                verify=True)
        except PyiCloudFailedLoginException as error:
            self.api = None
            _LOGGER.error("Error logging into iCloud Service: %s", error)
            return

        try:
            # Gets device owners infos
            user_info = self.api.devices.response['userInfo']
            self.account_owner_fullname = user_info[
                'firstName'] + ' ' + user_info['lastName']

            self.family_members_fullname = {}
            for prs_id, member in user_info['membersInfo'].items():
                self.family_members_fullname[prs_id] = member[
                    'firstName'] + ' ' + member['lastName']

            self.devices = {}
            self.update_devices()

        except PyiCloudNoDevicesException:
            _LOGGER.error('No iCloud Devices found')

    def update_devices(self):
        """Update iCloud devices."""
        if self.api is None:
            return

        try:
            # Gets devices infos
            for device in self.api.devices:
                status = device.status(DEVICE_STATUS_SET)
                devicename = slugify(status['name'].replace(' ', '', 99))

                if self.devices.get(devicename, None) is not None:
                    # Seen device -> updating
                    _LOGGER.info('Updating iCloud device: %s', devicename)
                    self.devices[devicename].update(status)
                else:
                    # New device, should be unique
                    if devicename in self.devices:
                        _LOGGER.error('Multiple devices with name: %s',
                                      devicename)
                        continue

                    _LOGGER.debug('Adding iCloud device: %s', devicename)
                    self.devices[devicename] = IcloudDevice(self, device)

        except PyiCloudNoDevicesException:
            _LOGGER.error("No iCloud Devices found")

        async_dispatcher_send(self._hass, SIGNAL_UPDATE_ICLOUD)
        interval = self.determine_interval()
        _LOGGER.error('determine_interval : %s', interval)
        async_track_point_in_utc_time(
            self._hass,
            self.keep_alive, utcnow() + timedelta(minutes=interval))

    def determine_interval(self) -> int:
        """Calculate new interval between to API fetch (in minutes)."""
        intervals = {}
        for device in self.devices:
            if device.location is None:
                continue

            currentzone = run_callback_threadsafe(
                self._hass.loop,
                async_active_zone,
                self._hass,
                device.location['latitude'],
                device.location['longitude']
            ).result()

            if currentzone is not None:
                intervals[device.name] = self._max_interval
                continue

            zones = (self._hass.states.get(entity_id) for entity_id
                     in sorted(self._hass.states.entity_ids('zone')))

            distances = []
            for zone_state in zones:
                zone_state_lat = zone_state.attributes['latitude']
                zone_state_long = zone_state.attributes['longitude']
                zone_distance = distance(
                    device.location['latitude'],
                    device.location['longitude'],
                    zone_state_lat,
                    zone_state_long)
                distances.append(round(zone_distance / 1000, 1))

            if distances:
                mindistance = min(distances)
            else:
                continue

            # Calculate out how long it would take for the device to drive
            # to the nearest zone at 120 km/h:
            interval = round(mindistance / 2, 0)

            # Never poll more than once per minute
            interval = max(interval, 1)

            if interval > 180:
                # Three hour drive?
                # This is far enough that they might be flying
                interval = 30

            if (device.battery_level is not None and
                    device.battery_level <= 33 and
                    mindistance > 3):
                # Low battery - let's check half as often
                interval = interval * 2

            intervals[device.name] = interval

        return max(
            int(min(
                intervals.items(),
                key=operator.itemgetter(1))[1]),
            self._max_interval)

    def keep_alive(self, now):
        """Keep the API alive."""
        if self.api is None:
            self.reset_account()

        if self.api is None:
            return

        self.api.authenticate()
        self.update_devices()


    @property
    def name(self):
        """Return the account name."""
        return self._accountname


class IcloudDevice():
    """Representation of a iCloud device."""

    def __init__(self, account: IcloudAccount, device: AppleDevice):
        """Initialize the iCloud device."""
        self.__account = account
        self._accountname = account.name

        self._device = device
        self.__status = device.status(DEVICE_STATUS_SET)
        _LOGGER.debug('Device Status is %s', self.__status)

        self._name = self.__status['name']
        self._dev_id = slugify(self._name.replace(' ', '', 99))  # devicename
        self._device_class = self.__status['deviceClass']
        self._device_name = self.__status['deviceDisplayName']
        if self.__status['prsId']:
            self._owner_fullname = account.family_members_fullname[
                self.__status['prsId']]
        else:
            self._owner_fullname = account.account_owner_fullname

        self._battery_level = None
        self._battery_status = None
        self._low_power_mode = None
        self._location = None

        self._seen = False

        self.update(self.__status)

    def update(self, status):
        """Update the iCloud device."""
        self.__status = status

        self._device_status = DEVICE_STATUS_CODES.get(self.__status[
            'deviceStatus'], 'error')

        self._attrs = {
            CONF_ACCOUNTNAME: self._accountname,
            ATTR_ATTRIBUTION: ATTRIBUTION,
            ATTR_DEVICENAME: self._device_name,
            ATTR_DEVICESTATUS: self._device_status,
            ATTR_OWNERNAME: self._owner_fullname
        }

        if self.__status['batteryStatus'] != 'Unknown':
            self._battery_level = round(self.__status.get('batteryLevel', 0)
                                        * 100)
            self._battery_status = self.__status['batteryStatus']
            self._low_power_mode = self.__status['lowPowerMode']

            self._attrs[ATTR_BATTERY] = self._battery_level
            self._attrs[ATTR_BATTERYSTATUS] = self._battery_status
            self._attrs[ATTR_LOWPOWERMODE] = self._low_power_mode

            if self.__status['location'] and self.__status[
                    'location']['latitude']:
                location = self.__status['location']
                self._location = location

    def play_sound(self):
        """Play sound on the device."""
        if self.__account.api is None:
            return

        self.__account.api.authenticate()
        _LOGGER.info("Playing Lost iPhone sound for %s", self.name)
        self.device.play_sound()

    def display_message(self, message: str, sound: bool = False):
        """Display a message on the device."""
        if self.__account.api is None:
            return

        self.__account.api.authenticate()
        _LOGGER.info("Displaying message for %s", self.name)
        self.device.display_message('Subject not working', message, sound)

    def lost_device(self, number: str, message: str):
        """Make the device in lost state."""
        if self.__account.api is None:
            return

        self.__account.api.authenticate()
        if self.__status['lostModeCapable']:
            _LOGGER.info("Make device lost for %s", self.name)
            self.device.lost_device(number, message, None)
        else:
            _LOGGER.error("Cannot make device lost for %s", self.name)

    @property
    def device(self) -> AppleDevice:
        """Return the Apple device."""
        return self._device

    @property
    def dev_id(self):
        """Return the device ID."""
        return self._dev_id

    @property
    def device_class(self):
        """Return the Apple device class."""
        return self._device_class

    @property
    def name(self):
        """Return the Apple device name."""
        return self._name

    @property
    def battery_level(self):
        """Return the Apple device battery level."""
        return self._battery_level

    @property
    def battery_status(self):
        """Return the Apple device battery status."""
        return self._battery_status

    @property
    def location(self):
        """Return the Apple device location."""
        return self._location

    @property
    def attributes(self):
        """Return the attributes."""
        return self._attrs

    @property
    def seen(self):
        """Return the seen value."""
        return self._seen

    def set_seen(self, seen):
        """Set the seen value."""
        self._seen = seen
