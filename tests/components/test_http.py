"""The tests for the Home Assistant HTTP component."""
# pylint: disable=protected-access
import logging
from ipaddress import ip_network
from unittest.mock import patch, mock_open

import requests

from homeassistant import bootstrap, const
import homeassistant.components.http as http

from tests.common import get_test_instance_port, get_test_home_assistant

API_PASSWORD = 'test1234'
SERVER_PORT = get_test_instance_port()
HTTP_BASE = '127.0.0.1:{}'.format(SERVER_PORT)
HTTP_BASE_URL = 'http://{}'.format(HTTP_BASE)
HA_HEADERS = {
    const.HTTP_HEADER_HA_AUTH: API_PASSWORD,
    const.HTTP_HEADER_CONTENT_TYPE: const.CONTENT_TYPE_JSON,
}
# Don't add 127.0.0.1/::1 as trusted, as it may interfere with other test cases
TRUSTED_NETWORKS = ['192.0.2.0/24', '2001:DB8:ABCD::/48', '100.64.0.1',
                    'FD01:DB8::1']
TRUSTED_ADDRESSES = ['100.64.0.1', '192.0.2.100', 'FD01:DB8::1',
                     '2001:DB8:ABCD::1']
UNTRUSTED_ADDRESSES = ['198.51.100.1', '2001:DB8:FA1::1', '127.0.0.1', '::1']
BANNED_IPS = ['200.201.202.203', '100.64.0.1']

CORS_ORIGINS = [HTTP_BASE_URL, HTTP_BASE]

hass = None


def _url(path=''):
    """Helper method to generate URLs."""
    return HTTP_BASE_URL + path


# pylint: disable=invalid-name
def setUpModule():
    """Initialize a Home Assistant server."""
    global hass

    hass = get_test_home_assistant()

    hass.bus.listen('test_event', lambda _: _)
    hass.states.set('test.test', 'a_state')

    bootstrap.setup_component(
        hass, http.DOMAIN, {
            http.DOMAIN: {
                http.CONF_API_PASSWORD: API_PASSWORD,
                http.CONF_SERVER_PORT: SERVER_PORT,
                http.CONF_CORS_ORIGINS: CORS_ORIGINS,
            }
        }
    )

    bootstrap.setup_component(hass, 'api')

    hass.http.trusted_networks = [
        ip_network(trusted_network)
        for trusted_network in TRUSTED_NETWORKS]

    hass.http.ip_bans = [http.IpBan(banned_ip)
                         for banned_ip in BANNED_IPS]

    hass.start()


# pylint: disable=invalid-name
def tearDownModule():
    """Stop the Home Assistant server."""
    hass.stop()


class TestHttp:
    """Test HTTP component."""

    def test_access_denied_without_password(self):
        """Test access without password."""
        req = requests.get(_url(const.URL_API))

        assert req.status_code == 401

    def test_access_denied_with_wrong_password_in_header(self):
        """Test access with wrong password."""
        req = requests.get(
            _url(const.URL_API),
            headers={const.HTTP_HEADER_HA_AUTH: 'wrongpassword'})

        assert req.status_code == 401

    def test_access_denied_with_x_forwarded_for(self, caplog):
        """Test access denied through the X-Forwarded-For http header."""
        hass.http.use_x_forwarded_for = True
        for remote_addr in UNTRUSTED_ADDRESSES:
            req = requests.get(_url(const.URL_API), headers={
                const.HTTP_HEADER_X_FORWARDED_FOR: remote_addr})

            assert req.status_code == 401, \
                "{} shouldn't be trusted".format(remote_addr)

    def test_access_denied_with_untrusted_ip(self, caplog):
        """Test access with an untrusted ip address."""
        for remote_addr in UNTRUSTED_ADDRESSES:
            with patch('homeassistant.components.http.'
                       'HomeAssistantWSGI.get_real_ip',
                       return_value=remote_addr):
                req = requests.get(
                    _url(const.URL_API), params={'api_password': ''})

                assert req.status_code == 401, \
                    "{} shouldn't be trusted".format(remote_addr)

    def test_access_with_password_in_header(self, caplog):
        """Test access with password in URL."""
        # Hide logging from requests package that we use to test logging
        caplog.set_level(
            logging.WARNING, logger='requests.packages.urllib3.connectionpool')

        req = requests.get(
            _url(const.URL_API),
            headers={const.HTTP_HEADER_HA_AUTH: API_PASSWORD})

        assert req.status_code == 200

        logs = caplog.text

        # assert const.URL_API in logs
        assert API_PASSWORD not in logs

    def test_access_denied_with_wrong_password_in_url(self):
        """Test access with wrong password."""
        req = requests.get(
            _url(const.URL_API), params={'api_password': 'wrongpassword'})

        assert req.status_code == 401

    def test_access_with_password_in_url(self, caplog):
        """Test access with password in URL."""
        # Hide logging from requests package that we use to test logging
        caplog.set_level(
            logging.WARNING, logger='requests.packages.urllib3.connectionpool')

        req = requests.get(
            _url(const.URL_API), params={'api_password': API_PASSWORD})

        assert req.status_code == 200

        logs = caplog.text

        # assert const.URL_API in logs
        assert API_PASSWORD not in logs

    def test_access_granted_with_x_forwarded_for(self, caplog):
        """Test access denied through the X-Forwarded-For http header."""
        hass.http.use_x_forwarded_for = True
        for remote_addr in TRUSTED_ADDRESSES:
            req = requests.get(_url(const.URL_API), headers={
                const.HTTP_HEADER_X_FORWARDED_FOR: remote_addr})

            assert req.status_code == 200, \
                "{} should be trusted".format(remote_addr)

    def test_access_granted_with_trusted_ip(self, caplog):
        """Test access with trusted addresses."""
        for remote_addr in TRUSTED_ADDRESSES:
            with patch('homeassistant.components.http.'
                       'HomeAssistantWSGI.get_real_ip',
                       return_value=remote_addr):
                req = requests.get(
                    _url(const.URL_API), params={'api_password': ''})

                assert req.status_code == 200, \
                    '{} should be trusted'.format(remote_addr)

    def test_cors_allowed_with_password_in_url(self):
        """Test cross origin resource sharing with password in url."""
        req = requests.get(_url(const.URL_API),
                           params={'api_password': API_PASSWORD},
                           headers={const.HTTP_HEADER_ORIGIN: HTTP_BASE_URL})

        allow_origin = const.HTTP_HEADER_ACCESS_CONTROL_ALLOW_ORIGIN

        assert req.status_code == 200
        assert req.headers.get(allow_origin) == HTTP_BASE_URL

    def test_cors_allowed_with_password_in_header(self):
        """Test cross origin resource sharing with password in header."""
        headers = {
            const.HTTP_HEADER_HA_AUTH: API_PASSWORD,
            const.HTTP_HEADER_ORIGIN: HTTP_BASE_URL
        }
        req = requests.get(_url(const.URL_API), headers=headers)

        allow_origin = const.HTTP_HEADER_ACCESS_CONTROL_ALLOW_ORIGIN

        assert req.status_code == 200
        assert req.headers.get(allow_origin) == HTTP_BASE_URL

    def test_cors_denied_without_origin_header(self):
        """Test cross origin resource sharing with password in header."""
        headers = {
            const.HTTP_HEADER_HA_AUTH: API_PASSWORD
        }
        req = requests.get(_url(const.URL_API), headers=headers)

        allow_origin = const.HTTP_HEADER_ACCESS_CONTROL_ALLOW_ORIGIN
        allow_headers = const.HTTP_HEADER_ACCESS_CONTROL_ALLOW_HEADERS

        assert req.status_code == 200
        assert allow_origin not in req.headers
        assert allow_headers not in req.headers

    def test_cors_preflight_allowed(self):
        """Test cross origin resource sharing preflight (OPTIONS) request."""
        headers = {
            const.HTTP_HEADER_ORIGIN: HTTP_BASE_URL,
            'Access-Control-Request-Method': 'GET',
            'Access-Control-Request-Headers': 'x-ha-access'
        }
        req = requests.options(_url(const.URL_API), headers=headers)

        allow_origin = const.HTTP_HEADER_ACCESS_CONTROL_ALLOW_ORIGIN
        allow_headers = const.HTTP_HEADER_ACCESS_CONTROL_ALLOW_HEADERS

        assert req.status_code == 200
        assert req.headers.get(allow_origin) == HTTP_BASE_URL
        assert req.headers.get(allow_headers) == \
            const.HTTP_HEADER_HA_AUTH.upper()

    def test_access_from_banned_ip(self):
        """Test accessing to server from banned IP. Both trusted and not."""
        hass.http.is_ban_enabled = True
        for remote_addr in BANNED_IPS:
            with patch('homeassistant.components.http.'
                       'HomeAssistantWSGI.get_real_ip',
                       return_value=remote_addr):
                req = requests.get(
                    _url(const.URL_API))
                assert req.status_code == 403

    def test_access_from_banned_ip_when_ban_is_off(self):
        """Test accessing to server from banned IP when feature is off"""
        hass.http.is_ban_enabled = False
        for remote_addr in BANNED_IPS:
            with patch('homeassistant.components.http.'
                       'HomeAssistantWSGI.get_real_ip',
                       return_value=remote_addr):
                req = requests.get(
                    _url(const.URL_API),
                    headers={const.HTTP_HEADER_HA_AUTH: API_PASSWORD})
                assert req.status_code == 200

    def test_ip_bans_file_creation(self):
        """Testing if banned IP file created"""
        hass.http.is_ban_enabled = True
        hass.http.login_threshold = 1

        m = mock_open()

        def call_server():
            with patch('homeassistant.components.http.'
                       'HomeAssistantWSGI.get_real_ip',
                       return_value="200.201.202.204"):
                return requests.get(
                    _url(const.URL_API),
                    headers={const.HTTP_HEADER_HA_AUTH: 'Wrong password'})

        with patch('homeassistant.components.http.open', m, create=True):
            req = call_server()
            assert req.status_code == 401
            assert len(hass.http.ip_bans) == len(BANNED_IPS)
            assert m.call_count == 0

            req = call_server()
            assert req.status_code == 401
            assert len(hass.http.ip_bans) == len(BANNED_IPS) + 1
            m.assert_called_once_with(hass.config.path(http.IP_BANS), 'a')

            req = call_server()
            assert req.status_code == 403
            assert m.call_count == 1
