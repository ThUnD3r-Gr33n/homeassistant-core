"""
homeassistant.components.camera
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Component to interface with various cameras that can be monitored.
"""
import urllib3
import mimetypes
import requests
import logging
import time
from homeassistant import bootstrap
from homeassistant.helpers.entity import Entity
# from homeassistant.components.switch.generic_switch import GenericSwitch

import time
import math
import datetime
from datetime import timedelta
import re
import os
from homeassistant.loader import get_component
from homeassistant.const import (
    ATTR_ENTITY_PICTURE,
    HTTP_NOT_FOUND,
    ATTR_ENTITY_ID,
    SERVICE_TURN_ON,
    SERVICE_TURN_OFF,
    EVENT_FTP_FILE_RECEIVED,
    EVENT_COMPONENT_LOADED,
    STATE_MOTION_DETECTED,
    STATE_STREAMING,
    STATE_ARMED,
    STATE_ON,
    STATE_OFF,
    STATE_IDLE,
    EVENT_PLATFORM_DISCOVERED,
    ATTR_SERVICE,
    ATTR_DISCOVERED,
    EVENT_STATE_CHANGED,
    ATTR_DOMAIN,
    EVENT_SERVICE_EXECUTED
    )


from homeassistant.helpers.entity_component import EntityComponent


DOMAIN = 'camera'
DEPENDENCIES = ['http', 'switch']
GROUP_NAME_ALL_CAMERAS = 'all_cameras'
SCAN_INTERVAL = 30
ENTITY_ID_FORMAT = DOMAIN + '.{}'
EVENT_CAMERA_MOTION_DETECTED = 'camera_motion_detected'

SWITCH_ACTION_RECORD = 'record'
SWITCH_ACTION_MOTION = 'motion_detection'

# The number of seconds between images before being
# considerd a new event
EVENT_GAP_THRESHOLD = 15

# Maps discovered services to their platforms
DISCOVERY_PLATFORMS = {}
DISCOVER_SWITCHES = "camera.switches"
ATTR_FRIENDLY_LOG_MESSAGE = "friendly_log_message"


def setup(hass, config):
    """ Track states and offer events for sensors. """

    component = EntityComponent(
        logging.getLogger(__name__), DOMAIN, hass, SCAN_INTERVAL,
        DISCOVERY_PLATFORMS)

    component.setup(config)

    for entity_id in component.entities.keys():
        entity = component.entities[entity_id]
        entity.refesh_all_settings_from_device()

        data = {}
        data['entity_id'] = entity_id
        data[ATTR_DOMAIN] = DOMAIN
        data['name'] = entity.name + ' Record'
        data['parent_action'] = SWITCH_ACTION_RECORD
        data['watched_attribute'] = 'is_recording'
        hass.bus.fire(EVENT_PLATFORM_DISCOVERED,
                      {ATTR_SERVICE: DISCOVER_SWITCHES,
                       ATTR_DISCOVERED: data})

        data = {}
        data['entity_id'] = entity_id
        data[ATTR_DOMAIN] = DOMAIN
        data['name'] = entity.name + ' Motion Detection'
        data['parent_action'] = SWITCH_ACTION_MOTION
        data['watched_attribute'] = 'is_motion_detection_enabled'
        hass.bus.fire(EVENT_PLATFORM_DISCOVERED,
                      {ATTR_SERVICE: DISCOVER_SWITCHES,
                       ATTR_DISCOVERED: data})


    def _proxy_camera_image(handler, path_match, data):
        """ Proxies the camera image via the HA server. """
        entity_id = path_match.group('entity_id')

        camera = None
        if entity_id in component.entities.keys():
            camera = component.entities[entity_id]

        if camera:
            response = camera.get_camera_image()
            handler.wfile.write(response.content)
        else:
            handler.send_response(HTTP_NOT_FOUND)

    hass.http.register_path('GET', re.compile(r'/api/camera_proxy/(?P<entity_id>[a-zA-Z\._0-9]+)'), _proxy_camera_image, require_auth=True)


    def _proxy_camera_mjpeg_stream(handler, path_match, data):
        """ Proxies the camera image via the HA server. """
        entity_id = path_match.group('entity_id')

        camera = None
        if entity_id in component.entities.keys():
            camera = component.entities[entity_id]

        if camera:
            camera._last_connected_address = handler.address_string()
            message = "{0} started streaming to {1}".format(camera.name, handler.address_string())
            hass.bus.fire(
                "camera_stream_started", {"component": DOMAIN,
                ATTR_ENTITY_ID: entity_id,
                ATTR_FRIENDLY_LOG_MESSAGE: message})

            try:
                camera.is_streaming = True
                camera.update_ha_state()


                http = urllib3.PoolManager()
                handler.request.sendall(bytes('HTTP/1.1 200 OK\r\n', 'utf-8'))
                handler.request.sendall(bytes('Content-type: multipart/x-mixed-replace; boundary=--jpgboundary\r\n\r\n', 'utf-8'))
                handler.request.sendall(bytes('--jpgboundary\r\n', 'utf-8'))
                count = 0
                while True:

                    headers = urllib3.util.make_headers(basic_auth=camera.username + ':' + camera.password)
                    req = http.request('GET', camera.still_image_url, headers = headers)

                    headersStr = ''
                    headersStr = headersStr + 'Content-length: ' + str(len(req.data)) + '\r\n'
                    headersStr = headersStr + 'Content-type: image/jpeg\r\n'
                    headersStr = headersStr + '\r\n'

                    handler.request.sendall(bytes(headersStr, 'utf-8') + req.data + bytes('\r\n', 'utf-8'))
                    handler.request.sendall(bytes('--jpgboundary\r\n', 'utf-8'))
            except Exception:
                camera.is_streaming = False
                camera.update_ha_state()

            message = "{0} stopped streaming to {1}".format(camera.name, handler.address_string())
            hass.bus.fire(
                "camera_stream_stopped", {"component": DOMAIN,
                ATTR_ENTITY_ID: entity_id,
                ATTR_FRIENDLY_LOG_MESSAGE: message})

        else:
            handler.send_response(HTTP_NOT_FOUND)

        camera.is_streaming = False

    hass.http.register_path('GET', re.compile(r'/api/camera_proxy_stream/(?P<entity_id>[a-zA-Z\._0-9]+)'), _proxy_camera_mjpeg_stream, require_auth=True)


    def _get_camera_events(handler, path_match, data):
        """ Proxies the camera image via the HA server. """
        entity_id = path_match.group('entity_id')

        camera = None
        if entity_id in component.entities.keys():
            camera = component.entities[entity_id]

        if camera:
            offset = int(data.get('offset', 0))
            length = int(data.get('length', 10))
            handler.write_json(camera.get_all_events(offset, length))
        else:
            handler.send_response(HTTP_NOT_FOUND)

    hass.http.register_path('GET', re.compile(r'/api/camera_events/(?P<entity_id>[a-zA-Z\._0-9]+)'), _get_camera_events, require_auth=True)


    def _saved_camera_image(handler, path_match, data):
        """ Get a saved camera image via the HA server. """
        entity_id = path_match.group('entity_id')

        camera = None
        if entity_id in component.entities.keys():
            camera = component.entities[entity_id]

        if camera:
            image_path = os.path.normpath(os.path.join(camera.event_images_path, data['image_path']))
            # check to see that someone is not trying to do something dodgey with relative paths
            if not image_path.startswith(camera.event_images_path) :
                handler.send_response(HTTP_NOT_FOUND)

            handler.write_file(image_path)

        else:
            handler.send_response(HTTP_NOT_FOUND)

    hass.http.register_path('GET', re.compile(r'/api/saved_camera_image/(?P<entity_id>[a-zA-Z\._0-9]+)'), _saved_camera_image, require_auth=True)


    def handle_motion_detection_service(service):
        """ Handles calls to the camera services. """
        target_cameras = component.extract_from_service(service)
        feature_name = service.data.get('feature', 'motion_detection')
        for camera in target_cameras:
            if feature_name == 'configure_ftp':
                if service.service == SERVICE_TURN_ON:
                    camera.set_ftp_details()
            else:
                if service.service == SERVICE_TURN_ON:
                    camera.enable_motion_detection()
                else:
                    camera.disable_motion_detection()

            camera.update_ha_state(True)

    hass.services.register(DOMAIN, SERVICE_TURN_ON, handle_motion_detection_service)
    hass.services.register(DOMAIN, SERVICE_TURN_OFF, handle_motion_detection_service)

    return True

class Camera(Entity):
    """ Base class for cameras. """

    def __init__(self, hass, device_info):
        #super().__init__(hass, device_info)
        self.hass = hass
        self.device_info = device_info
        self.BASE_URL = device_info.get('base_url')
        if not self.BASE_URL.endswith('/'):
            self.BASE_URL = self.BASE_URL + '/'
        self.username = device_info.get('username')
        self.password = device_info.get('password')
        self.is_streaming = False
        self._is_detecting_motion = False
        self._last_motion_detected = datetime.datetime.now()
        self._last_connected_address = None
        # these are the camera functions and capabilities initialised
        # to defaults, these should be overridden in derived classes
        self._is_motion_detection_supported = False
        self._is_motion_detection_enabled = False

        self._is_recording = False

        self._is_ftp_upload_supported = False
        self._is_ftp_upload_enabled = False

        self._is_ftp_configured = False
        self._ftp_host = ''
        self._ftp_port = 21
        self._ftp_username = ''
        self._ftp_password = ''

        self._logger = logging.getLogger(__name__)

        self._images_path = device_info.get('images_path', None)

        if self._images_path != None and not os.path.isdir(self._images_path):
            os.makedirs(self._images_path)

        self._event_images_path = None
        self._ftp_path = None

        self._child_entities = {}

        self.hass.bus.listen(
            EVENT_FTP_FILE_RECEIVED,
            self.process_file_event)

        self.hass.bus.listen(
            EVENT_STATE_CHANGED,
            self.process_child_entity_change)



    def process_child_entity_change(self, event):

        if not event or not event.data:
            return
        new_state = event.data['new_state']
        if new_state is None:
            return

        parent_entity_id = new_state.attributes.get('parent_entity_id', None)

        if parent_entity_id == self.entity_id:
            entity_action = new_state.attributes.get('parent_action', None)
            if not entity_action:
                return

            # this is the first callback we get when the entity is registered
            old_state_val = None
            if not entity_action in self._child_entities.keys():
                self._child_entities[entity_action] = new_state
                old_state_val = self._child_entities[entity_action].state
                self._logger.info('Registered {0} as a child of {1}'.format(
                    new_state.entity_id, self.entity_id))
                self.refesh_all_settings_from_device()
            else:
                old_state_val = self._child_entities[entity_action].state
                self._child_entities[entity_action] = new_state
                # new_state_val = new_state.state
                #return


            if self._child_entities[entity_action].state != old_state_val:
                if entity_action == SWITCH_ACTION_MOTION:
                    if new_state.state == STATE_ON and not self.is_motion_detection_enabled:
                        self.enable_motion_detection()
                        self._logger.info('Enabling motion detection on {0}'.format(self.entity_id))
                    elif new_state.state == STATE_OFF and self.is_motion_detection_enabled:
                        self.disable_motion_detection()
                        self._logger.info('Disabling motion detection on {0}'.format(self.entity_id))
                    else:
                        self._logger.info('Ignoring state change {0} is {1} is already {2}'
                            .format(self.entity_id, entity_action, self.is_motion_detection_enabled))




        # print(event_data)
    def update_switch_states(self):

        pass

    def refesh_all_settings_from_device(self):
        pass

    def get_camera_image(self, stream=False):
        response = requests.get(self.still_image_url, auth=(self.username, self.password), stream=stream)
        return response

    @property
    def name(self):
        if self.device_info.get('name'):
            return self.device_info.get('name')
        else:
            return super().name

    @property
    def state(self):
        """ Returns the state of the entity. """
        seconds_since_last_motion = (datetime.datetime.now() - self._last_motion_detected).total_seconds()
        if self._is_detecting_motion and seconds_since_last_motion > EVENT_GAP_THRESHOLD:
            self._is_detecting_motion = False

        if self._is_detecting_motion:
            return STATE_MOTION_DETECTED
        elif self.is_streaming:
            return STATE_STREAMING
        elif self._is_motion_detection_enabled:
            return STATE_ARMED
        else:
            return STATE_IDLE


    @property
    def state_attributes(self):
        """ Returns optional state attributes. """
        attr = super().state_attributes
        attr['model_name'] = self.device_info.get('model', 'generic')
        attr['brand'] = self.device_info.get('brand', 'generic')
        attr['still_image_url'] = '/api/camera_proxy/' + self.entity_id
        # attr[ATTR_ENTITY_PICTURE] = '/api/camera_proxy/' + self.entity_id + '?api_password=' + self.hass.http.api_password + '&time=' + str(time.time())
        attr[ATTR_ENTITY_PICTURE] = '/api/camera_proxy/' + self.entity_id + '?time=' + str(time.time())
        attr['stream_url'] = '/api/camera_proxy_stream/' + self.entity_id
        attr['last_motion_time'] = self._last_motion_detected.strftime('%Y-%m-%d %H-%M-%S')
        attr['last_connected_address'] = self._last_connected_address

        attr.update(self.function_attributes)

        return attr

    @property
    def still_image_url(self):
        """ This should be implemented by different camera models. """
        if self.device_info.get('still_image_url'):
            return self.BASE_URL + self.device_info.get('still_image_url')
        return self.BASE_URL + 'image.jpg'

    def enable_motion_detection(self):
        if not self.is_motion_detection_supported:
            return False
        if self.is_motion_detection_enabled:
            return True

    def disable_motion_detection(self):
        if not self.is_motion_detection_supported:
            return False
        if self.is_motion_detection_enabled:
            return True

    def set_ftp_details(self):
        if not self.is_motion_detection_supported:
            return False

    def process_file_event(self, event):
        if self.ftp_path != None:
            if event.data.get('file_name').startswith(self.ftp_path):
                self._is_detecting_motion = True
                self._last_motion_detected = datetime.datetime.now()
                self.process_new_file(event.data.get('file_name'))

    def process_new_file(self, path):
        if not os.path.isfile(path):
            return False

        if self.event_images_path == None:
            return False

        if not os.path.isdir(self.event_images_path):
            os.makedirs(self.event_images_path)

        all_subdirs = [d for d in os.listdir(self.event_images_path)
            if os.path.isdir(os.path.join(self.event_images_path, d)) and d.startswith('event-')]

        event_dir = None
        if len(all_subdirs) > 0:
            event_dir = sorted(all_subdirs, key=lambda x: os.path.getctime(os.path.join(self.event_images_path, x)), reverse=True)[:1][0]
            event_dir = os.path.join(self.event_images_path, event_dir)
            file_dt = datetime.datetime.fromtimestamp(os.path.getctime(path))

            # Get the newest file in the dir
            all_subfiles = [f for f in os.listdir(event_dir)
                if os.path.isfile(os.path.join(event_dir, f)) and f.startswith('event_image-')]

            if len(all_subfiles) > 0:
                newest_image = sorted(all_subfiles, key=lambda x: os.path.getctime(os.path.join(event_dir, x)), reverse=True)[:1][0]
                newest_image_path = os.path.join(event_dir, newest_image)
                newest_file_dt = datetime.datetime.fromtimestamp(os.path.getctime(newest_image_path))
                if (file_dt - newest_file_dt).total_seconds() > EVENT_GAP_THRESHOLD:
                    event_dir = None
            else:
                event_dir_dt = datetime.datetime.fromtimestamp(os.path.getctime(event_dir))
                if (file_dt - event_dir_dt).total_seconds() > EVENT_GAP_THRESHOLD:
                    event_dir = None


        if event_dir == None:
            new_event_dir_name = 'event-' + datetime.datetime.fromtimestamp(os.path.getctime(path)).strftime('%Y-%m-%d_%H-%M-%S')
            event_dir = os.path.join(self.event_images_path, new_event_dir_name)
            if not os.path.isdir(event_dir):
                os.makedirs(event_dir)

            self.hass.bus.fire(
                EVENT_CAMERA_MOTION_DETECTED, {"component": DOMAIN,
                ATTR_ENTITY_ID: self.entity_id,
                'event_images_path': event_dir,
                'event_images_dir': new_event_dir_name})

        new_file_name = 'event_image-' + datetime.datetime.fromtimestamp(os.path.getctime(path)).strftime('%Y-%m-%d_%H-%M-%S-%f') + '.jpg'
        new_file_path = os.path.join(event_dir, new_file_name)

        if not os.path.isfile(path):
            return False

        os.rename(path, new_file_path)

        return True

    def get_all_events(self, start=0, length=10):

        events_data = []
        all_subdirs = [d for d in os.listdir(self.event_images_path)
            if os.path.isdir(os.path.join(self.event_images_path, d)) and d.startswith('event-')]
        event_dirs = sorted(all_subdirs, key=lambda x: os.path.getctime(os.path.join(self.event_images_path, x)), reverse=True)

        count = 0
        for event_dir in event_dirs:
            if count < start:
                continue
            if count >= start + length:
                break
            event_data = {}
            event_data['directory'] = event_dir
            event_data['name'] = event_dir
            event_data['fullPath'] = os.path.join(self.event_images_path, event_dir)
            event_data['thumbUrl'] = ''
            event_data['images'] = []
            event_data['time'] = datetime.datetime.fromtimestamp(os.path.getctime(event_data['fullPath'])).strftime('%Y-%m-%d %H:%M:%S')

            all_subfiles = [f for f in os.listdir(event_data['fullPath'])
                if os.path.isfile(os.path.join(event_data['fullPath'], f)) and f.startswith('event_image-')]

            for image_file in all_subfiles:
                full_image_path = os.path.join(event_data['fullPath'], image_file)
                image_data = {}
                image_data['fileName'] = image_file
                image_data['path'] = event_dir + os.path.sep + image_file
                image_data['url'] = 'api/saved_camera_image/' + self.entity_id + '?image_path=' + image_data['path']
                image_data['time'] = datetime.datetime.fromtimestamp(os.path.getctime(full_image_path)).strftime('%Y-%m-%d %H:%M:%S')
                event_data['images'].append(image_data)

            if len(event_data['images']) > 0:
                thumb_index = math.floor(len(event_data['images'])/2)
                event_data['thumbUrl'] = event_data['images'][thumb_index]['url']

            events_data.append(event_data)
            count += 1

        return events_data


    @property
    def images_path(self):
        if self._images_path == None:
            default_images_path = os.path.join(self.hass.config.config_dir, 'camera_data')
            default_images_path = os.path.join(default_images_path, self.entity_id)
            self._images_path = default_images_path

            if not os.path.isdir(self.images_path):
                os.makedirs(self.images_path)

        return self._images_path

    @property
    def event_images_path(self):
        if self.images_path == None:
            return None

        if self._event_images_path == None:
           self._event_images_path = os.path.join(self.images_path, 'events')

        return self._event_images_path

    @property
    def ftp_path(self):
        if self._ftp_path == None:
            ftp_comp = get_component('ftp')
            if ftp_comp != None and ftp_comp.ftp_server != None:
                self._ftp_path = os.path.join(ftp_comp.ftp_server.ftp_root_path, self.entity_id)
        return self._ftp_path

    @property
    def is_motion_detection_supported(self):
        return self._is_motion_detection_supported

    @property
    def is_motion_detection_enabled(self):
        return self._is_motion_detection_enabled

    @property
    def is_recording(self):
        return self._is_recording

    @property
    def is_ftp_upload_supported(self):
        return self._is_ftp_upload_supported

    @property
    def is_ftp_upload_enabled(self):
        return self._is_ftp_upload_enabled

    @property
    def is_ftp_configured(self):
        return self._is_ftp_configured

    @property
    def function_attributes(self):
        attr = {}
        attr['is_motion_detection_supported'] = self.is_motion_detection_supported
        attr['is_motion_detection_enabled'] = self.is_motion_detection_enabled
        attr['is_ftp_upload_supported'] = self.is_ftp_upload_supported
        attr['is_ftp_upload_enabled'] = self.is_ftp_upload_enabled
        attr['is_ftp_configured'] = self.is_ftp_configured
        return attr

    # def get_switches(self):
    #     switches = []
    #     motion_btn_state = STATE_ON if self.is_motion_detection_enabled else STATE_OFF
    #     if self.is_motion_detection_supported:
    #         switches.append(GenericSwitch(self.name + ' Motion Detection', motion_btn_state))

    #     switches.append(GenericSwitch(self.name + ' Record'))

    #     return switches
