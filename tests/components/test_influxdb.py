"""The tests for the InfluxDB component."""
import unittest
import datetime
from unittest import mock

from datetime import timedelta
from unittest.mock import MagicMock

import influxdb as influx_client

from homeassistant.util import dt as dt_util
from homeassistant import core as ha
from homeassistant.setup import setup_component
import homeassistant.components.influxdb as influxdb
from homeassistant.const import EVENT_STATE_CHANGED, STATE_OFF, STATE_ON, \
                                STATE_STANDBY

from tests.common import get_test_home_assistant


@mock.patch('influxdb.InfluxDBClient')
class TestInfluxDB(unittest.TestCase):
    """Test the InfluxDB component."""

    def setUp(self):
        """Setup things to be run when tests are started."""
        self.hass = get_test_home_assistant()
        self.handler_method = None
        self.hass.bus.listen = mock.Mock()

    def tearDown(self):
        """Clear data."""
        self.hass.stop()

    def test_setup_config_full(self, mock_client):
        """Test the setup with full configuration."""
        config = {
            'influxdb': {
                'host': 'host',
                'port': 123,
                'database': 'db',
                'username': 'user',
                'password': 'password',
                'max_retries': 4,
                'ssl': 'False',
                'verify_ssl': 'False',
            }
        }
        assert setup_component(self.hass, influxdb.DOMAIN, config)
        self.assertTrue(self.hass.bus.listen.called)
        self.assertEqual(
            EVENT_STATE_CHANGED, self.hass.bus.listen.call_args_list[0][0][0])
        self.assertTrue(mock_client.return_value.query.called)

    def test_setup_config_defaults(self, mock_client):
        """Test the setup with default configuration."""
        config = {
            'influxdb': {
                'host': 'host',
                'username': 'user',
                'password': 'pass',
            }
        }
        assert setup_component(self.hass, influxdb.DOMAIN, config)
        self.assertTrue(self.hass.bus.listen.called)
        self.assertEqual(
            EVENT_STATE_CHANGED, self.hass.bus.listen.call_args_list[0][0][0])

    def test_setup_minimal_config(self, mock_client):
        """Test the setup with minimal configuration."""
        config = {
            'influxdb': {}
        }

        assert setup_component(self.hass, influxdb.DOMAIN, config)

    def test_setup_missing_password(self, mock_client):
        """Test the setup with existing username and missing password."""
        config = {
            'influxdb': {
                'username': 'user'
            }
        }

        assert not setup_component(self.hass, influxdb.DOMAIN, config)

    def test_setup_query_fail(self, mock_client):
        """Test the setup for query failures."""
        config = {
            'influxdb': {
                'host': 'host',
                'username': 'user',
                'password': 'pass',
            }
        }
        mock_client.return_value.query.side_effect = \
            influx_client.exceptions.InfluxDBClientError('fake')
        assert not setup_component(self.hass, influxdb.DOMAIN, config)

    def _setup(self, **kwargs):
        """Setup the client."""
        config = {
            'influxdb': {
                'host': 'host',
                'username': 'user',
                'password': 'pass',
                'exclude': {
                    'entities': ['fake.blacklisted'],
                    'domains': ['another_fake']
                }
            }
        }
        config['influxdb'].update(kwargs)
        assert setup_component(self.hass, influxdb.DOMAIN, config)
        self.handler_method = self.hass.bus.listen.call_args_list[0][0][1]

    def test_event_listener(self, mock_client):
        """Test the event listener."""
        self._setup()

        # map of HA State to valid influxdb [state, value] fields
        valid = {
            '1': [None, 1],
            '1.0': [None, 1.0],
            STATE_ON: [STATE_ON, 1],
            STATE_OFF: [STATE_OFF, 0],
            STATE_STANDBY: [STATE_STANDBY, None],
            'foo': ['foo', None]
        }
        for in_, out in valid.items():
            attrs = {
                'unit_of_measurement': 'foobars',
                'longitude': '1.1',
                'latitude': '2.2',
                'battery_level': '99%',
                'temperature': '20c',
                'last_seen': 'Last seen 23 minutes ago',
                'updated_at': datetime.datetime(2017, 1, 1, 0, 0),
                'multi_periods': '0.120.240.2023873'
            }
            state = mock.MagicMock(
                state=in_, domain='fake', entity_id='fake.entity-id',
                object_id='entity', attributes=attrs)
            event = mock.MagicMock(data={'new_state': state}, time_fired=12345)
            body = [{
                'measurement': 'foobars',
                'tags': {
                    'domain': 'fake',
                    'entity_id': 'entity',
                },
                'time': 12345,
                'fields': {
                    'longitude': 1.1,
                    'latitude': 2.2,
                    'battery_level_str': '99%',
                    'battery_level': 99.0,
                    'temperature_str': '20c',
                    'temperature': 20.0,
                    'last_seen_str': 'Last seen 23 minutes ago',
                    'last_seen': 23.0,
                    'updated_at_str': '2017-01-01 00:00:00',
                    'updated_at': 20170101000000,
                    'multi_periods_str': '0.120.240.2023873'
                },
            }]
            if out[0] is not None:
                body[0]['fields']['state'] = out[0]
            if out[1] is not None:
                body[0]['fields']['value'] = out[1]

            self.handler_method(event)
            self.assertEqual(
                mock_client.return_value.write_points.call_count, 1
            )
            self.assertEqual(
                mock_client.return_value.write_points.call_args,
                mock.call(body)
            )
            mock_client.return_value.write_points.reset_mock()

    def test_event_listener_no_units(self, mock_client):
        """Test the event listener for missing units."""
        self._setup()

        for unit in (None, ''):
            if unit:
                attrs = {'unit_of_measurement': unit}
            else:
                attrs = {}
            state = mock.MagicMock(
                state=1, domain='fake', entity_id='fake.entity-id',
                object_id='entity', attributes=attrs)
            event = mock.MagicMock(data={'new_state': state}, time_fired=12345)
            body = [{
                'measurement': 'fake.entity-id',
                'tags': {
                    'domain': 'fake',
                    'entity_id': 'entity',
                },
                'time': 12345,
                'fields': {
                    'value': 1,
                },
            }]
            self.handler_method(event)
            self.assertEqual(
                mock_client.return_value.write_points.call_count, 1
            )
            self.assertEqual(
                mock_client.return_value.write_points.call_args,
                mock.call(body)
            )
            mock_client.return_value.write_points.reset_mock()

    def test_event_listener_fail_write(self, mock_client):
        """Test the event listener for write failures."""
        self._setup()

        state = mock.MagicMock(
            state=1, domain='fake', entity_id='fake.entity-id',
            object_id='entity', attributes={})
        event = mock.MagicMock(data={'new_state': state}, time_fired=12345)
        mock_client.return_value.write_points.side_effect = \
            influx_client.exceptions.InfluxDBClientError('foo')
        self.handler_method(event)

    def test_event_listener_states(self, mock_client):
        """Test the event listener against ignored states."""
        self._setup()

        for state_state in (1, 'unknown', '', 'unavailable'):
            state = mock.MagicMock(
                state=state_state, domain='fake', entity_id='fake.entity-id',
                object_id='entity', attributes={})
            event = mock.MagicMock(data={'new_state': state}, time_fired=12345)
            body = [{
                'measurement': 'fake.entity-id',
                'tags': {
                    'domain': 'fake',
                    'entity_id': 'entity',
                },
                'time': 12345,
                'fields': {
                    'value': 1,
                },
            }]
            self.handler_method(event)
            if state_state == 1:
                self.assertEqual(
                    mock_client.return_value.write_points.call_count, 1
                )
                self.assertEqual(
                    mock_client.return_value.write_points.call_args,
                    mock.call(body)
                )
            else:
                self.assertFalse(mock_client.return_value.write_points.called)
            mock_client.return_value.write_points.reset_mock()

    def test_event_listener_blacklist(self, mock_client):
        """Test the event listener against a blacklist."""
        self._setup()

        for entity_id in ('ok', 'blacklisted'):
            state = mock.MagicMock(
                state=1, domain='fake', entity_id='fake.{}'.format(entity_id),
                object_id=entity_id, attributes={})
            event = mock.MagicMock(data={'new_state': state}, time_fired=12345)
            body = [{
                'measurement': 'fake.{}'.format(entity_id),
                'tags': {
                    'domain': 'fake',
                    'entity_id': entity_id,
                },
                'time': 12345,
                'fields': {
                    'value': 1,
                },
            }]
            self.handler_method(event)
            if entity_id == 'ok':
                self.assertEqual(
                    mock_client.return_value.write_points.call_count, 1
                )
                self.assertEqual(
                    mock_client.return_value.write_points.call_args,
                    mock.call(body)
                )
            else:
                self.assertFalse(mock_client.return_value.write_points.called)
            mock_client.return_value.write_points.reset_mock()

    def test_event_listener_blacklist_domain(self, mock_client):
        """Test the event listener against a blacklist."""
        self._setup()

        for domain in ('ok', 'another_fake'):
            state = mock.MagicMock(
                state=1, domain=domain,
                entity_id='{}.something'.format(domain),
                object_id='something', attributes={})
            event = mock.MagicMock(data={'new_state': state}, time_fired=12345)
            body = [{
                'measurement': '{}.something'.format(domain),
                'tags': {
                    'domain': domain,
                    'entity_id': 'something',
                },
                'time': 12345,
                'fields': {
                    'value': 1,
                },
            }]
            self.handler_method(event)
            if domain == 'ok':
                self.assertEqual(
                    mock_client.return_value.write_points.call_count, 1
                )
                self.assertEqual(
                    mock_client.return_value.write_points.call_args,
                    mock.call(body)
                )
            else:
                self.assertFalse(mock_client.return_value.write_points.called)
            mock_client.return_value.write_points.reset_mock()

    def test_event_listener_whitelist(self, mock_client):
        """Test the event listener against a whitelist."""
        config = {
            'influxdb': {
                'host': 'host',
                'username': 'user',
                'password': 'pass',
                'include': {
                    'entities': ['fake.included'],
                }
            }
        }
        assert setup_component(self.hass, influxdb.DOMAIN, config)
        self.handler_method = self.hass.bus.listen.call_args_list[0][0][1]

        for entity_id in ('included', 'default'):
            state = mock.MagicMock(
                state=1, domain='fake', entity_id='fake.{}'.format(entity_id),
                object_id=entity_id, attributes={})
            event = mock.MagicMock(data={'new_state': state}, time_fired=12345)
            body = [{
                'measurement': 'fake.{}'.format(entity_id),
                'tags': {
                    'domain': 'fake',
                    'entity_id': entity_id,
                },
                'time': 12345,
                'fields': {
                    'value': 1,
                },
            }]
            self.handler_method(event)
            if entity_id == 'included':
                self.assertEqual(
                    mock_client.return_value.write_points.call_count, 1
                )
                self.assertEqual(
                    mock_client.return_value.write_points.call_args,
                    mock.call(body)
                )
            else:
                self.assertFalse(mock_client.return_value.write_points.called)
            mock_client.return_value.write_points.reset_mock()

    def test_event_listener_whitelist_domain(self, mock_client):
        """Test the event listener against a whitelist."""
        config = {
            'influxdb': {
                'host': 'host',
                'username': 'user',
                'password': 'pass',
                'include': {
                    'domains': ['fake'],
                }
            }
        }
        assert setup_component(self.hass, influxdb.DOMAIN, config)
        self.handler_method = self.hass.bus.listen.call_args_list[0][0][1]

        for domain in ('fake', 'another_fake'):
            state = mock.MagicMock(
                state=1, domain=domain,
                entity_id='{}.something'.format(domain),
                object_id='something', attributes={})
            event = mock.MagicMock(data={'new_state': state}, time_fired=12345)
            body = [{
                'measurement': '{}.something'.format(domain),
                'tags': {
                    'domain': domain,
                    'entity_id': 'something',
                },
                'time': 12345,
                'fields': {
                    'value': 1,
                },
            }]
            self.handler_method(event)
            if domain == 'fake':
                self.assertEqual(
                    mock_client.return_value.write_points.call_count, 1
                )
                self.assertEqual(
                    mock_client.return_value.write_points.call_args,
                    mock.call(body)
                )
            else:
                self.assertFalse(mock_client.return_value.write_points.called)
            mock_client.return_value.write_points.reset_mock()

    def test_event_listener_invalid_type(self, mock_client):
        """Test the event listener when an attribute has an invalid type."""
        self._setup()

        # map of HA State to valid influxdb [state, value] fields
        valid = {
            '1': [None, 1],
            '1.0': [None, 1.0],
            STATE_ON: [STATE_ON, 1],
            STATE_OFF: [STATE_OFF, 0],
            STATE_STANDBY: [STATE_STANDBY, None],
            'foo': ['foo', None]
        }
        for in_, out in valid.items():
            attrs = {
                'unit_of_measurement': 'foobars',
                'longitude': '1.1',
                'latitude': '2.2',
                'invalid_attribute': ['value1', 'value2']
            }
            state = mock.MagicMock(
                state=in_, domain='fake', entity_id='fake.entity-id',
                object_id='entity', attributes=attrs)
            event = mock.MagicMock(data={'new_state': state}, time_fired=12345)
            body = [{
                'measurement': 'foobars',
                'tags': {
                    'domain': 'fake',
                    'entity_id': 'entity',
                },
                'time': 12345,
                'fields': {
                    'longitude': 1.1,
                    'latitude': 2.2,
                    'invalid_attribute_str': "['value1', 'value2']"
                },
            }]
            if out[0] is not None:
                body[0]['fields']['state'] = out[0]
            if out[1] is not None:
                body[0]['fields']['value'] = out[1]

            self.handler_method(event)
            self.assertEqual(
                mock_client.return_value.write_points.call_count, 1
            )
            self.assertEqual(
                mock_client.return_value.write_points.call_args,
                mock.call(body)
            )
            mock_client.return_value.write_points.reset_mock()

    def test_event_listener_default_measurement(self, mock_client):
        """Test the event listener with a default measurement."""
        config = {
            'influxdb': {
                'host': 'host',
                'username': 'user',
                'password': 'pass',
                'default_measurement': 'state',
                'exclude': {
                    'entities': ['fake.blacklisted']
                }
            }
        }
        assert setup_component(self.hass, influxdb.DOMAIN, config)
        self.handler_method = self.hass.bus.listen.call_args_list[0][0][1]

        for entity_id in ('ok', 'blacklisted'):
            state = mock.MagicMock(
                state=1, domain='fake', entity_id='fake.{}'.format(entity_id),
                object_id=entity_id, attributes={})
            event = mock.MagicMock(data={'new_state': state}, time_fired=12345)
            body = [{
                'measurement': 'state',
                'tags': {
                    'domain': 'fake',
                    'entity_id': entity_id,
                },
                'time': 12345,
                'fields': {
                    'value': 1,
                },
            }]
            self.handler_method(event)
            if entity_id == 'ok':
                self.assertEqual(
                    mock_client.return_value.write_points.call_count, 1
                )
                self.assertEqual(
                    mock_client.return_value.write_points.call_args,
                    mock.call(body)
                )
            else:
                self.assertFalse(mock_client.return_value.write_points.called)
            mock_client.return_value.write_points.reset_mock()

    def test_event_listener_unit_of_measurement_field(self, mock_client):
        """Test the event listener for unit of measurement field."""
        config = {
            'influxdb': {
                'host': 'host',
                'username': 'user',
                'password': 'pass',
                'override_measurement': 'state',
            }
        }
        assert setup_component(self.hass, influxdb.DOMAIN, config)
        self.handler_method = self.hass.bus.listen.call_args_list[0][0][1]

        attrs = {
            'unit_of_measurement': 'foobars',
        }
        state = mock.MagicMock(
            state='foo', domain='fake', entity_id='fake.entity-id',
            object_id='entity', attributes=attrs)
        event = mock.MagicMock(data={'new_state': state}, time_fired=12345)
        body = [{
            'measurement': 'state',
            'tags': {
                'domain': 'fake',
                'entity_id': 'entity',
            },
            'time': 12345,
            'fields': {
                'state': 'foo',
                'unit_of_measurement_str': 'foobars',
            },
        }]
        self.handler_method(event)
        self.assertEqual(
            mock_client.return_value.write_points.call_count, 1
        )
        self.assertEqual(
            mock_client.return_value.write_points.call_args,
            mock.call(body)
        )
        mock_client.return_value.write_points.reset_mock()

    def test_event_listener_tags_attributes(self, mock_client):
        """Test the event listener when some attributes should be tags."""
        config = {
            'influxdb': {
                'host': 'host',
                'username': 'user',
                'password': 'pass',
                'tags_attributes': ['friendly_fake']
            }
        }
        assert setup_component(self.hass, influxdb.DOMAIN, config)
        self.handler_method = self.hass.bus.listen.call_args_list[0][0][1]

        attrs = {
            'friendly_fake': 'tag_str',
            'field_fake': 'field_str',
        }
        state = mock.MagicMock(
            state=1, domain='fake',
            entity_id='fake.something',
            object_id='something', attributes=attrs)
        event = mock.MagicMock(data={'new_state': state}, time_fired=12345)
        body = [{
            'measurement': 'fake.something',
            'tags': {
                'domain': 'fake',
                'entity_id': 'something',
                'friendly_fake': 'tag_str'
            },
            'time': 12345,
            'fields': {
                'value': 1,
                'field_fake_str': 'field_str'
            },
        }]
        self.handler_method(event)
        self.assertEqual(
            mock_client.return_value.write_points.call_count, 1
        )
        self.assertEqual(
            mock_client.return_value.write_points.call_args,
            mock.call(body)
        )
        mock_client.return_value.write_points.reset_mock()

    def test_event_listener_component_override_measurement(self, mock_client):
        """Test the event listener with overridden measurements."""
        config = {
            'influxdb': {
                'host': 'host',
                'username': 'user',
                'password': 'pass',
                'component_config': {
                    'sensor.fake_humidity': {
                        'override_measurement': 'humidity'
                    }
                },
                'component_config_glob': {
                    'binary_sensor.*motion': {
                        'override_measurement': 'motion'
                    }
                },
                'component_config_domain': {
                    'climate': {
                        'override_measurement': 'hvac'
                    }
                }
            }
        }
        assert setup_component(self.hass, influxdb.DOMAIN, config)
        self.handler_method = self.hass.bus.listen.call_args_list[0][0][1]

        test_components = [
            {'domain': 'sensor', 'id': 'fake_humidity', 'res': 'humidity'},
            {'domain': 'binary_sensor', 'id': 'fake_motion', 'res': 'motion'},
            {'domain': 'climate', 'id': 'fake_thermostat', 'res': 'hvac'},
            {'domain': 'other', 'id': 'just_fake', 'res': 'other.just_fake'},
        ]
        for comp in test_components:
            state = mock.MagicMock(
                state=1, domain=comp['domain'],
                entity_id=comp['domain'] + '.' + comp['id'],
                object_id=comp['id'], attributes={})
            event = mock.MagicMock(data={'new_state': state}, time_fired=12345)
            body = [{
                'measurement': comp['res'],
                'tags': {
                    'domain': comp['domain'],
                    'entity_id': comp['id']
                },
                'time': 12345,
                'fields': {
                    'value': 1,
                },
            }]
            self.handler_method(event)
            self.assertEqual(
                mock_client.return_value.write_points.call_count, 1
            )
            self.assertEqual(
                mock_client.return_value.write_points.call_args,
                mock.call(body)
            )
            mock_client.return_value.write_points.reset_mock()

    def test_scheduled_write(self, mock_client):
        """Test the event listener to retry after write failures."""
        self._setup(max_retries=1)

        state = mock.MagicMock(
            state=1, domain='fake', entity_id='entity.id', object_id='entity',
            attributes={})
        event = mock.MagicMock(data={'new_state': state}, time_fired=12345)
        mock_client.return_value.write_points.side_effect = \
            IOError('foo')

        start = dt_util.utcnow()

        self.handler_method(event)
        json_data = mock_client.return_value.write_points.call_args[0][0]
        self.assertEqual(mock_client.return_value.write_points.call_count, 1)

        shifted_time = start + (timedelta(seconds=20 + 1))
        self.hass.bus.fire(ha.EVENT_TIME_CHANGED,
                           {ha.ATTR_NOW: shifted_time})
        self.hass.block_till_done()
        self.assertEqual(mock_client.return_value.write_points.call_count, 2)
        mock_client.return_value.write_points.assert_called_with(json_data)

        shifted_time = shifted_time + (timedelta(seconds=20 + 1))
        self.hass.bus.fire(ha.EVENT_TIME_CHANGED,
                           {ha.ATTR_NOW: shifted_time})
        self.hass.block_till_done()
        self.assertEqual(mock_client.return_value.write_points.call_count, 2)


class TestRetryOnErrorDecorator(unittest.TestCase):
    """Test the RetryOnError decorator."""

    def setUp(self):
        """Setup things to be run when tests are started."""
        self.hass = get_test_home_assistant()

    def tearDown(self):
        """Clear data."""
        self.hass.stop()

    def test_no_retry(self):
        """Test that it does not retry if configured."""
        mock_method = MagicMock()
        wrapped = influxdb.RetryOnError(self.hass)(mock_method)
        wrapped(1, 2, test=3)
        self.assertEqual(mock_method.call_count, 1)
        mock_method.assert_called_with(1, 2, test=3)

        mock_method.side_effect = Exception()
        self.assertRaises(Exception, wrapped, 1, 2, test=3)
        self.assertEqual(mock_method.call_count, 2)
        mock_method.assert_called_with(1, 2, test=3)

    def test_single_retry(self):
        """Test that retry stops after a single try if configured."""
        mock_method = MagicMock()
        retryer = influxdb.RetryOnError(self.hass, retry_limit=1)
        wrapped = retryer(mock_method)
        wrapped(1, 2, test=3)
        self.assertEqual(mock_method.call_count, 1)
        mock_method.assert_called_with(1, 2, test=3)

        start = dt_util.utcnow()
        shifted_time = start + (timedelta(seconds=20 + 1))
        self.hass.bus.fire(ha.EVENT_TIME_CHANGED,
                           {ha.ATTR_NOW: shifted_time})
        self.hass.block_till_done()
        self.assertEqual(mock_method.call_count, 1)

        mock_method.side_effect = Exception()
        wrapped(1, 2, test=3)
        self.assertEqual(mock_method.call_count, 2)
        mock_method.assert_called_with(1, 2, test=3)

        for cnt in range(3):
            start = dt_util.utcnow()
            shifted_time = start + (timedelta(seconds=20 + 1))
            self.hass.bus.fire(ha.EVENT_TIME_CHANGED,
                               {ha.ATTR_NOW: shifted_time})
            self.hass.block_till_done()
            self.assertEqual(mock_method.call_count, 3)
            mock_method.assert_called_with(1, 2, test=3)

    def test_multi_retry(self):
        """Test that multiple retries work."""
        mock_method = MagicMock()
        retryer = influxdb.RetryOnError(self.hass, retry_limit=4)
        wrapped = retryer(mock_method)
        mock_method.side_effect = Exception()

        wrapped(1, 2, test=3)
        self.assertEqual(mock_method.call_count, 1)
        mock_method.assert_called_with(1, 2, test=3)

        for cnt in range(3):
            start = dt_util.utcnow()
            shifted_time = start + (timedelta(seconds=20 + 1))
            self.hass.bus.fire(ha.EVENT_TIME_CHANGED,
                               {ha.ATTR_NOW: shifted_time})
            self.hass.block_till_done()
            self.assertEqual(mock_method.call_count, cnt + 2)
            mock_method.assert_called_with(1, 2, test=3)

    def test_max_queue(self):
        """Test the maximum queue length."""
        # make a wrapped method
        mock_method = MagicMock()
        retryer = influxdb.RetryOnError(
            self.hass, retry_limit=4, queue_limit=3)
        wrapped = retryer(mock_method)
        mock_method.side_effect = Exception()

        # call it once, call fails, queue fills to 1
        wrapped(1, 2, test=3)
        self.assertEqual(mock_method.call_count, 1)
        mock_method.assert_called_with(1, 2, test=3)
        self.assertEqual(len(wrapped._retry_queue), 1)

        # two more calls that failed. queue is 3
        wrapped(1, 2, test=3)
        wrapped(1, 2, test=3)
        self.assertEqual(mock_method.call_count, 3)
        self.assertEqual(len(wrapped._retry_queue), 3)

        # another call, queue gets limited to 3
        wrapped(1, 2, test=3)
        self.assertEqual(mock_method.call_count, 4)
        self.assertEqual(len(wrapped._retry_queue), 3)

        # time passes
        start = dt_util.utcnow()
        shifted_time = start + (timedelta(seconds=20 + 1))
        self.hass.bus.fire(ha.EVENT_TIME_CHANGED,
                           {ha.ATTR_NOW: shifted_time})
        self.hass.block_till_done()

        # only the three queued calls where repeated
        self.assertEqual(mock_method.call_count, 7)
        self.assertEqual(len(wrapped._retry_queue), 3)

        # another call, queue stays limited
        wrapped(1, 2, test=3)
        self.assertEqual(mock_method.call_count, 8)
        self.assertEqual(len(wrapped._retry_queue), 3)

        # disable the side effect
        mock_method.side_effect = None

        # time passes, all calls should succeed
        start = dt_util.utcnow()
        shifted_time = start + (timedelta(seconds=20 + 1))
        self.hass.bus.fire(ha.EVENT_TIME_CHANGED,
                           {ha.ATTR_NOW: shifted_time})
        self.hass.block_till_done()

        # three queued calls succeeded, queue empty.
        self.assertEqual(mock_method.call_count, 11)
        self.assertEqual(len(wrapped._retry_queue), 0)