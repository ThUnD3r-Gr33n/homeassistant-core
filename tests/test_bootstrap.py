"""Test the bootstrapping."""
# pylint: disable=protected-access
import os
from unittest import mock
import threading
import logging

import voluptuous as vol

from homeassistant.core import callback
from homeassistant.const import EVENT_HOMEASSISTANT_START
import homeassistant.config as config_util
from homeassistant import bootstrap, loader
import homeassistant.util.dt as dt_util
from homeassistant.helpers.config_validation import PLATFORM_SCHEMA
from homeassistant.helpers import discovery

from tests.common import \
    get_test_home_assistant, MockModule, MockPlatform, \
    assert_setup_component, patch_yaml_files, get_test_config_dir

ORIG_TIMEZONE = dt_util.DEFAULT_TIME_ZONE
VERSION_PATH = os.path.join(get_test_config_dir(), config_util.VERSION_FILE)

_LOGGER = logging.getLogger(__name__)


class TestBootstrap:
    """Test the bootstrap utils."""

    hass = None
    backup_cache = None

    # pylint: disable=invalid-name, no-self-use
    def setup_method(self, method):
        """Setup the test."""
        self.backup_cache = loader._COMPONENT_CACHE

        if method == self.test_from_config_file:
            return

        self.hass = get_test_home_assistant()

    def teardown_method(self, method):
        """Clean up."""
        if method == self.test_from_config_file:
            return

        dt_util.DEFAULT_TIME_ZONE = ORIG_TIMEZONE
        self.hass.stop()
        loader._COMPONENT_CACHE = self.backup_cache
        if os.path.isfile(VERSION_PATH):
            os.remove(VERSION_PATH)

    @mock.patch(
        # prevent .HA_VERISON file from being written
        'homeassistant.bootstrap.conf_util.process_ha_config_upgrade',
        autospec=True)
    @mock.patch('homeassistant.util.location.detect_location_info',
                autospec=True, return_value=None)
    @mock.patch('homeassistant.helpers.signal.async_register_signal_handling')
    def test_from_config_file(self, mock_upgrade, mock_detect, mock_signal):
        """Test with configuration file."""
        components = ['browser', 'conversation', 'script']
        files = {
            'config.yaml': ''.join(
                '{}:\n'.format(comp)
                for comp in components
            )
        }

        with mock.patch('os.path.isfile', mock.Mock(return_value=True)), \
                mock.patch('os.access', mock.Mock(return_value=True)), \
                mock.patch('homeassistant.bootstrap.enable_logging',
                           mock.Mock(return_value=True)), \
                patch_yaml_files(files, True):
            self.hass = bootstrap.from_config_file('config.yaml')

        components.append('group')
        assert sorted(components) == sorted(self.hass.config.components)

    def test_handle_setup_circular_dependency(self):
        """Test the setup of circular dependencies."""
        loader.set_component('comp_b', MockModule('comp_b', ['comp_a']))

        def setup_a(hass, config):
            """Setup the another component."""
            bootstrap.setup_component(hass, 'comp_b')
            return True

        loader.set_component('comp_a', MockModule('comp_a', setup=setup_a))

        bootstrap.setup_component(self.hass, 'comp_a')
        assert ['comp_a'] == self.hass.config.components

    def test_validate_component_config(self):
        """Test validating component configuration."""
        config_schema = vol.Schema({
            'comp_conf': {
                'hello': str
            }
        }, required=True)
        loader.set_component(
            'comp_conf', MockModule('comp_conf', config_schema=config_schema))

        with assert_setup_component(0):
            assert not bootstrap.setup_component(self.hass, 'comp_conf', {})

        with assert_setup_component(0):
            assert not bootstrap.setup_component(self.hass, 'comp_conf', {
                'comp_conf': None
            })

        with assert_setup_component(0):
            assert not bootstrap.setup_component(self.hass, 'comp_conf', {
                'comp_conf': {}
            })

        with assert_setup_component(0):
            assert not bootstrap.setup_component(self.hass, 'comp_conf', {
                'comp_conf': {
                    'hello': 'world',
                    'invalid': 'extra',
                }
            })

        with assert_setup_component(1):
            assert bootstrap.setup_component(self.hass, 'comp_conf', {
                'comp_conf': {
                    'hello': 'world',
                }
            })

    def test_validate_platform_config(self):
        """Test validating platform configuration."""
        platform_schema = PLATFORM_SCHEMA.extend({
            'hello': str,
        })
        loader.set_component(
            'platform_conf',
            MockModule('platform_conf', platform_schema=platform_schema))

        loader.set_component(
            'platform_conf.whatever', MockPlatform('whatever'))

        with assert_setup_component(0):
            assert bootstrap.setup_component(self.hass, 'platform_conf', {
                'platform_conf': {
                    'hello': 'world',
                    'invalid': 'extra',
                }
            })

        self.hass.config.components.remove('platform_conf')

        with assert_setup_component(1):
            assert bootstrap.setup_component(self.hass, 'platform_conf', {
                'platform_conf': {
                    'platform': 'whatever',
                    'hello': 'world',
                },
                'platform_conf 2': {
                    'invalid': True
                }
            })

        self.hass.config.components.remove('platform_conf')

        with assert_setup_component(0):
            assert bootstrap.setup_component(self.hass, 'platform_conf', {
                'platform_conf': {
                    'platform': 'not_existing',
                    'hello': 'world',
                }
            })

        self.hass.config.components.remove('platform_conf')

        with assert_setup_component(1):
            assert bootstrap.setup_component(self.hass, 'platform_conf', {
                'platform_conf': {
                    'platform': 'whatever',
                    'hello': 'world',
                }
            })

        self.hass.config.components.remove('platform_conf')

        with assert_setup_component(1):
            assert bootstrap.setup_component(self.hass, 'platform_conf', {
                'platform_conf': [{
                    'platform': 'whatever',
                    'hello': 'world',
                }]
            })

        self.hass.config.components.remove('platform_conf')

        # Any falsey platform config will be ignored (None, {}, etc)
        with assert_setup_component(0) as config:
            assert bootstrap.setup_component(self.hass, 'platform_conf', {
                'platform_conf': None
            })
            assert 'platform_conf' in self.hass.config.components
            assert not config['platform_conf']  # empty

            assert bootstrap.setup_component(self.hass, 'platform_conf', {
                'platform_conf': {}
            })
            assert 'platform_conf' in self.hass.config.components
            assert not config['platform_conf']  # empty

    def test_component_not_found(self):
        """setup_component should not crash if component doesn't exist."""
        assert not bootstrap.setup_component(self.hass, 'non_existing')

    def test_component_not_double_initialized(self):
        """Test we do not setup a component twice."""
        mock_setup = mock.MagicMock(return_value=True)

        loader.set_component('comp', MockModule('comp', setup=mock_setup))

        assert bootstrap.setup_component(self.hass, 'comp')
        assert mock_setup.called

        mock_setup.reset_mock()

        assert bootstrap.setup_component(self.hass, 'comp')
        assert not mock_setup.called

    @mock.patch('homeassistant.util.package.install_package',
                return_value=False)
    def test_component_not_installed_if_requirement_fails(self, mock_install):
        """Component setup should fail if requirement can't install."""
        self.hass.config.skip_pip = False
        loader.set_component(
            'comp', MockModule('comp', requirements=['package==0.0.1']))

        assert not bootstrap.setup_component(self.hass, 'comp')
        assert 'comp' not in self.hass.config.components

    def test_component_not_setup_twice_if_loaded_during_other_setup(self):
        """Test component setup while waiting for lock is not setup twice."""
        loader.set_component('comp', MockModule('comp'))

        result = []

        def setup_component():
            """Setup the component."""
            result.append(bootstrap.setup_component(self.hass, 'comp'))

        thread = threading.Thread(target=setup_component)
        thread.start()
        self.hass.config.components.append('comp')

        thread.join()

        assert len(result) == 1
        assert result[0]

    def test_component_not_setup_missing_dependencies(self):
        """Test we do not setup a component if not all dependencies loaded."""
        deps = ['non_existing']
        loader.set_component('comp', MockModule('comp', dependencies=deps))

        assert not bootstrap.setup_component(self.hass, 'comp', {})
        assert 'comp' not in self.hass.config.components

        loader.set_component('non_existing', MockModule('non_existing'))

        assert bootstrap.setup_component(self.hass, 'comp', {})

    def test_component_failing_setup(self):
        """Test component that fails setup."""
        loader.set_component(
            'comp', MockModule('comp', setup=lambda hass, config: False))

        assert not bootstrap.setup_component(self.hass, 'comp', {})
        assert 'comp' not in self.hass.config.components

    def test_component_exception_setup(self):
        """Test component that raises exception during setup."""
        def exception_setup(hass, config):
            """Setup that raises exception."""
            raise Exception('fail!')

        loader.set_component('comp', MockModule('comp', setup=exception_setup))

        assert not bootstrap.setup_component(self.hass, 'comp', {})
        assert 'comp' not in self.hass.config.components

    @mock.patch('homeassistant.bootstrap.enable_logging')
    @mock.patch('homeassistant.helpers.signal.async_register_signal_handling')
    def test_home_assistant_core_config_validation(self, log_mock, sig_mock):
        """Test if we pass in wrong information for HA conf."""
        # Extensive HA conf validation testing is done in test_config.py
        assert None is bootstrap.from_config_dict({
            'homeassistant': {
                'latitude': 'some string'
            }
        })

    def test_component_setup_with_validation_and_dependency(self):
        """Test all config is passed to dependencies."""
        def config_check_setup(hass, config):
            """Setup method that tests config is passed in."""
            if config.get('comp_a', {}).get('valid', False):
                return True
            raise Exception('Config not passed in: {}'.format(config))

        loader.set_component('comp_a',
                             MockModule('comp_a', setup=config_check_setup))

        loader.set_component('switch.platform_a', MockPlatform('comp_b',
                                                               ['comp_a']))

        bootstrap.setup_component(self.hass, 'switch', {
            'comp_a': {
                'valid': True
            },
            'switch': {
                'platform': 'platform_a',
            }
        })
        assert 'comp_a' in self.hass.config.components

    def test_platform_specific_config_validation(self):
        """Test platform that specifies config."""
        platform_schema = PLATFORM_SCHEMA.extend({
            'valid': True,
        }, extra=vol.PREVENT_EXTRA)

        mock_setup = mock.MagicMock(spec_set=True)

        loader.set_component(
            'switch.platform_a',
            MockPlatform(platform_schema=platform_schema,
                         setup_platform=mock_setup))

        with assert_setup_component(0):
            assert bootstrap.setup_component(self.hass, 'switch', {
                'switch': {
                    'platform': 'platform_a',
                    'invalid': True
                }
            })
            assert mock_setup.call_count == 0

        self.hass.config.components.remove('switch')

        with assert_setup_component(0):
            assert bootstrap.setup_component(self.hass, 'switch', {
                'switch': {
                    'platform': 'platform_a',
                    'valid': True,
                    'invalid_extra': True,
                }
            })
            assert mock_setup.call_count == 0

        self.hass.config.components.remove('switch')

        with assert_setup_component(1):
            assert bootstrap.setup_component(self.hass, 'switch', {
                'switch': {
                    'platform': 'platform_a',
                    'valid': True
                }
            })
            assert mock_setup.call_count == 1

    def test_disable_component_if_invalid_return(self):
        """Test disabling component if invalid return."""
        loader.set_component(
            'disabled_component',
            MockModule('disabled_component', setup=lambda hass, config: None))

        assert not bootstrap.setup_component(self.hass, 'disabled_component')
        assert loader.get_component('disabled_component') is None
        assert 'disabled_component' not in self.hass.config.components

        loader.set_component(
            'disabled_component',
            MockModule('disabled_component', setup=lambda hass, config: False))

        assert not bootstrap.setup_component(self.hass, 'disabled_component')
        assert loader.get_component('disabled_component') is not None
        assert 'disabled_component' not in self.hass.config.components

        loader.set_component(
            'disabled_component',
            MockModule('disabled_component', setup=lambda hass, config: True))

        assert bootstrap.setup_component(self.hass, 'disabled_component')
        assert loader.get_component('disabled_component') is not None
        assert 'disabled_component' in self.hass.config.components

    @mock.patch('homeassistant.helpers.signal.async_register_signal_handling')
    def test_all_work_done_before_start(self, signal_mock):
        """Test all init work done till start."""
        call_order = []

        def component1_setup(hass, config):
            """Setup mock component."""
            discovery.discover(hass, 'test_component2',
                               component='test_component2')
            discovery.discover(hass, 'test_component3',
                               component='test_component3')
            return True

        def component_track_setup(hass, config):
            """Setup mock component."""
            call_order.append(1)
            return True

        loader.set_component(
            'test_component1',
            MockModule('test_component1', setup=component1_setup))

        loader.set_component(
            'test_component2',
            MockModule('test_component2', setup=component_track_setup))

        loader.set_component(
            'test_component3',
            MockModule('test_component3', setup=component_track_setup))

        @callback
        def track_start(event):
            """Track start event."""
            call_order.append(2)

        self.hass.bus.listen_once(EVENT_HOMEASSISTANT_START, track_start)

        self.hass.loop.run_until_complete = \
            lambda _: self.hass.block_till_done()

        bootstrap.from_config_dict({'test_component1': None}, self.hass)

        self.hass.start()

        assert call_order == [1, 1, 2]
