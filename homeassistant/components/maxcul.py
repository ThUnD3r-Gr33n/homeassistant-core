import logging
import os

LOGGER = logging.getLogger(__name__)

import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.config import load_yaml_config_file
from homeassistant.helpers import discovery
from homeassistant.util.yaml import load_yaml, dump as dump_yaml

DOMAIN = 'maxcul'

REQUIREMENTS = [ 'pymaxcul==0.1.0' ]

CONF_DEVICE_PATH = 'device_path'
CONF_DEVICE_BAUD_RATE = 'device_baud_rate'


CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_DEVICE_PATH): cv.string,
        vol.Required(CONF_DEVICE_BAUD_RATE): cv.positive_int
    })
},extra=vol.ALLOW_EXTRA)

DATA_MAXCUL = 'maxcul'
DATA_DEVICES = 'maxcul_devices'

EVENT_THERMOSTAT_UPDATE = 'maxcul.thermostat_update'

YAML_DEVICES = 'maxcul_paired_devices.yaml'

SERIVCE_ENABLE_PAIRING = 'enable_pairing'

SCHEMA_SERVICE_ENABLE_PAIRING = vol.Schema({
    vol.Optional('duration', default=30): cv.positive_int,
})

DESCRIPTION_SERVICE_ENABLE_PAIRING = {
    'description': 'Enable pairing for a given duration',
    'fields': {
        'duration': {
            'description': 'Duration for which pairing is possible in seconds',
            'example': 30
        }
    }
}

ATTR_DEVICE_ID = 'device_id'

def read_paired_devices(path):
    if not os.path.isfile(path):
        return []
    paired_devices = load_yaml(path)
    if not isinstance(paired_devices, list):
        LOGGER.warn("Configuration file {} did not contain a list".format(path))
        return []
    return paired_devices

def write_paired_devices(path, devices):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT)
    os.write(fd, dump_yaml(devices).encode())
    os.close(fd)

def setup(hass, config):
    import maxcul
    conf = config[DOMAIN]
    path = conf[CONF_DEVICE_PATH]
    baud = conf[CONF_DEVICE_BAUD_RATE]

    paired_devices_path = hass.config.path(YAML_DEVICES)
    hass.data[DATA_DEVICES] = read_paired_devices(paired_devices_path)

    def callback(event, payload):
        if event == maxcul.EVENT_THERMOSTAT_UPDATE:
            hass.bus.fire(EVENT_THERMOSTAT_UPDATE, payload)

        elif event == maxcul.EVENT_DEVICE_PAIRED or event == maxcul.EVENT_DEVICE_REPAIRED:
            device_id = payload.get(ATTR_DEVICE_ID)
            if device_id is not None and device_id not in hass.data[DATA_DEVICES]:
                hass.data[DATA_DEVICES].append(device_id)
                discovery.load_platform(hass, 'climate', DOMAIN, payload, config)
                write_paired_devices(paired_devices_path, hass.data[DATA_DEVICES])

    maxconn = hass.data[DATA_MAXCUL] = maxcul.MaxConnection(
        device_path = path,
        baudrate = baud,
        paired_devices = list(hass.data[DATA_DEVICES]),
        callback = callback
    )
    maxconn.start()

    for device_id in hass.data[DATA_DEVICES]:
        discovery.load_platform(hass, 'climate', DOMAIN, { ATTR_DEVICE_ID: device_id }, config)

    def _service_enable_pairing(service):
        duration = service.data.get('duration')
        maxconn.enable_pairing(duration)

    hass.services.register(DOMAIN, SERIVCE_ENABLE_PAIRING, _service_enable_pairing,
                          DESCRIPTION_SERVICE_ENABLE_PAIRING, schema=SCHEMA_SERVICE_ENABLE_PAIRING)

    # Stops server when HASS is shutting down
    # TODO this leads to an exception, I don't know how to handle a separate thread :(
    #hass.bus.listen_once(
    #    EVENT_HOMEASSISTANT_STOP, hass.data[DATA_MAXCUL].stop)


    return True
