"""
tests.components.test_proximity
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Tests proximity component.
"""
import homeassistant.core as ha
from homeassistant.components import proximity


class TestProximity:
    """ Test the Proximity component. """

    def setup_method(self, method):
        self.hass = ha.HomeAssistant()
        self.hass.states.set(
            'zone.home', 'zoning',
            {
                'name': 'home',
                'latitude': 2.1,
                'longitude': 1.1,
                'radius': 10
            })

    def teardown_method(self, method):
        """ Stop down stuff we started. """
        self.hass.stop()

    def test_proximity(self):
        assert proximity.setup(self.hass, {
            'proximity': {
                'zone': 'home',
                'ignored_zones': {
                    'work'
                },
                'devices': {
                    'device_tracker.test1',
                    'device_tracker.test2'
                },
                'tolerance': '1'
            }
        })

        state = self.hass.states.get('proximity.home')
        assert state.state == 'not set'
        assert state.attributes.get('nearest') == 'not set'
        assert state.attributes.get('dir_of_travel') == 'not set'

        self.hass.states.set('proximity.home', '0')
        self.hass.pool.block_till_done()
        state = self.hass.states.get('proximity.home')
        assert state.state == '0'

    def test_no_devices_in_config(self):
        assert not proximity.setup(self.hass, {
            'proximity': {
                'zone': 'home',
                'ignored_zones': {
                    'work'
                },
                'tolerance': '1'
            }
        })

    def test_no_tolerance_in_config(self):
        assert proximity.setup(self.hass, {
            'proximity': {
                'zone': 'home',
                'ignored_zones': {
                    'work'
                },
                'devices': {
                    'device_tracker.test1',
                    'device_tracker.test2'
                }
            }
        })

    def test_no_ignored_zones_in_config(self):
        assert proximity.setup(self.hass, {
            'proximity': {
                'zone': 'home',
                'devices': {
                    'device_tracker.test1',
                    'device_tracker.test2'
                },
                'tolerance': '1'
            }
        })

    def test_no_zone_in_config(self):
        assert proximity.setup(self.hass, {
            'proximity': {
                'ignored_zones': {
                    'work'
                },
                'devices': {
                    'device_tracker.test1',
                    'device_tracker.test2'
                },
                'tolerance': '1'
            }
        })

    def test_device_tracker_test1_in_zone(self):
        assert proximity.setup(self.hass, {
            'proximity': {
                'zone': 'home',
                'ignored_zones': {
                    'work'
                },
                'devices': {
                    'device_tracker.test1'
                },
                'tolerance': '1'
            }
        })

        self.hass.states.set(
            'device_tracker.test1', 'home',
            {
                'friendly_name': 'test1',
                'latitude': 2.1,
                'longitude': 1.1
            })
        self.hass.pool.block_till_done()
        state = self.hass.states.get('proximity.home')
        assert state.state == '0'
        assert state.attributes.get('nearest') == 'test1'
        assert state.attributes.get('dir_of_travel') == 'arrived'

    def test_device_trackers_in_zone(self):
        assert proximity.setup(self.hass, {
            'proximity': {
                'zone': 'home',
                'ignored_zones': {
                    'work'
                },
                'devices': {
                    'device_tracker.test1',
                    'device_tracker.test2'
                },
                'tolerance': '1'
            }
        })

        self.hass.states.set(
            'device_tracker.test1', 'home',
            {
                'friendly_name': 'test1',
                'latitude': 2.1,
                'longitude': 1.1
            })
        self.hass.pool.block_till_done()
        self.hass.states.set(
            'device_tracker.test2', 'home',
            {
                'friendly_name': 'test2',
                'latitude': 2.1,
                'longitude': 1.1
            })
        self.hass.pool.block_till_done()
        state = self.hass.states.get('proximity.home')
        assert state.state == '0'
        assert ((state.attributes.get('nearest') == 'test1, test2') or
                (state.attributes.get('nearest') == 'test2, test1'))
        assert state.attributes.get('dir_of_travel') == 'arrived'

    def test_device_tracker_test1_away(self):
        assert proximity.setup(self.hass, {
            'proximity': {
                'zone': 'home',
                'ignored_zones': {
                    'work'
                },
                'devices': {
                    'device_tracker.test1'
                },
                'tolerance': '1'
            }
        })

        self.hass.states.set(
            'device_tracker.test1', 'not_home',
            {
                'friendly_name': 'test1',
                'latitude': 20.1,
                'longitude': 10.1
            })
        self.hass.pool.block_till_done()
        state = self.hass.states.get('proximity.home')
        assert state.attributes.get('nearest') == 'test1'
        assert state.attributes.get('dir_of_travel') == 'unknown'

    def test_device_tracker_test1_awayfurther(self):
        assert proximity.setup(self.hass, {
            'proximity': {
                'zone': 'home',
                'ignored_zones': {
                    'work'
                },
                'devices': {
                    'device_tracker.test1'
                }
            }
        })

        self.hass.states.set(
            'device_tracker.test1', 'not_home',
            {
                'friendly_name': 'test1',
                'latitude': 20.1,
                'longitude': 10.1
            })
        self.hass.pool.block_till_done()
        state = self.hass.states.get('proximity.home')
        assert state.attributes.get('nearest') == 'test1'
        assert state.attributes.get('dir_of_travel') == 'unknown'
        self.hass.states.set(
            'device_tracker.test1', 'not_home',
            {
                'friendly_name': 'test1',
                'latitude': 40.1,
                'longitude': 20.1
            })
        self.hass.pool.block_till_done()
        state = self.hass.states.get('proximity.home')
        assert state.attributes.get('nearest') == 'test1'
        assert state.attributes.get('dir_of_travel') == 'away_from'

    def test_device_tracker_test1_awaycloser(self):
        assert proximity.setup(self.hass, {
            'proximity': {
                'zone': 'home',
                'ignored_zones': {
                    'work'
                },
                'devices': {
                    'device_tracker.test1'
                }
            }
        })

        self.hass.states.set(
            'device_tracker.test1', 'not_home',
            {
                'friendly_name': 'test1',
                'latitude': 40.1,
                'longitude': 20.1
            })
        self.hass.pool.block_till_done()
        state = self.hass.states.get('proximity.home')
        assert state.attributes.get('nearest') == 'test1'
        assert state.attributes.get('dir_of_travel') == 'unknown'
        self.hass.states.set(
            'device_tracker.test1', 'not_home',
            {
                'friendly_name': 'test1',
                'latitude': 20.1,
                'longitude': 10.1
            })
        self.hass.pool.block_till_done()
        state = self.hass.states.get('proximity.home')
        assert state.attributes.get('nearest') == 'test1'
        assert state.attributes.get('dir_of_travel') == 'towards'

    def test_all_device_trackers_in_ignored_zone(self):
        assert proximity.setup(self.hass, {
            'proximity': {
                'zone': 'home',
                'ignored_zones': {
                    'work'
                },
                'devices': {
                    'device_tracker.test1'
                }
            }
        })

        self.hass.states.set(
            'device_tracker.test1', 'work',
            {
                'friendly_name': 'test1'
            })
        self.hass.pool.block_till_done()
        state = self.hass.states.get('proximity.home')
        assert state.state == 'not set'
        assert state.attributes.get('nearest') == 'not set'
        assert state.attributes.get('dir_of_travel') == 'not set'

    def test_device_tracker_test1_no_coordinates(self):
        assert proximity.setup(self.hass, {
            'proximity': {
                'zone': 'home',
                'ignored_zones': {
                    'work'
                },
                'devices': {
                    'device_tracker.test1'
                },
                'tolerance': '1'
            }
        })

        self.hass.states.set(
            'device_tracker.test1', 'not_home',
            {
                'friendly_name': 'test1'
            })
        self.hass.pool.block_till_done()
        state = self.hass.states.get('proximity.home')
        assert state.attributes.get('nearest') == 'not set'
        assert state.attributes.get('dir_of_travel') == 'not set'

    def test_device_tracker_test1_awayfurther_than_test2_first_test1(self):
        self.hass.states.set(
            'device_tracker.test1', 'not_home',
            {
                'friendly_name': 'test1'
            })
        self.hass.pool.block_till_done()
        self.hass.states.set(
            'device_tracker.test2', 'not_home',
            {
                'friendly_name': 'test2'
            })
        self.hass.pool.block_till_done()
        assert proximity.setup(self.hass, {
            'proximity': {
                'zone': 'home',
                'ignored_zones': {
                    'work'
                },
                'devices': {
                    'device_tracker.test1',
                    'device_tracker.test2'
                }
            }
        })

        self.hass.states.set(
            'device_tracker.test1', 'not_home',
            {
                'friendly_name': 'test1',
                'latitude': 20.1,
                'longitude': 10.1
            })
        self.hass.pool.block_till_done()
        state = self.hass.states.get('proximity.home')
        assert state.attributes.get('nearest') == 'test1'
        assert state.attributes.get('dir_of_travel') == 'unknown'
        self.hass.states.set(
            'device_tracker.test2', 'not_home',
            {
                'friendly_name': 'test2',
                'latitude': 40.1,
                'longitude': 20.1
            })
        self.hass.pool.block_till_done()
        state = self.hass.states.get('proximity.home')
        assert state.attributes.get('nearest') == 'test1'
        assert state.attributes.get('dir_of_travel') == 'unknown'

    def test_device_tracker_test1_awayfurther_than_test2_first_test2(self):
        self.hass.states.set(
            'device_tracker.test1', 'not_home',
            {
                'friendly_name': 'test1'
            })
        self.hass.pool.block_till_done()
        self.hass.states.set(
            'device_tracker.test2', 'not_home',
            {
                'friendly_name': 'test2'
            })
        self.hass.pool.block_till_done()
        assert proximity.setup(self.hass, {
            'proximity': {
                'zone': 'home',
                'ignored_zones': {
                    'work'
                },
                'devices': {
                    'device_tracker.test1',
                    'device_tracker.test2'
                }
            }
        })

        self.hass.states.set(
            'device_tracker.test2', 'not_home',
            {
                'friendly_name': 'test2',
                'latitude': 40.1,
                'longitude': 20.1
            })
        self.hass.pool.block_till_done()
        state = self.hass.states.get('proximity.home')
        assert state.attributes.get('nearest') == 'test2'
        assert state.attributes.get('dir_of_travel') == 'unknown'
        self.hass.states.set(
            'device_tracker.test1', 'not_home',
            {
                'friendly_name': 'test1',
                'latitude': 20.1,
                'longitude': 10.1
            })
        self.hass.pool.block_till_done()
        state = self.hass.states.get('proximity.home')
        assert state.attributes.get('nearest') == 'test1'
        assert state.attributes.get('dir_of_travel') == 'unknown'

    def test_device_tracker_test1_awayfurther_test2_in_ignored_zone(self):
        self.hass.states.set(
            'device_tracker.test1', 'not_home',
            {
                'friendly_name': 'test1'
            })
        self.hass.pool.block_till_done()
        self.hass.states.set(
            'device_tracker.test2', 'work',
            {
                'friendly_name': 'test2'
            })
        self.hass.pool.block_till_done()
        assert proximity.setup(self.hass, {
            'proximity': {
                'zone': 'home',
                'ignored_zones': {
                    'work'
                },
                'devices': {
                    'device_tracker.test1',
                    'device_tracker.test2'
                }
            }
        })

        self.hass.states.set(
            'device_tracker.test1', 'not_home',
            {
                'friendly_name': 'test1',
                'latitude': 20.1,
                'longitude': 10.1
            })
        self.hass.pool.block_till_done()
        state = self.hass.states.get('proximity.home')
        assert state.attributes.get('nearest') == 'test1'
        assert state.attributes.get('dir_of_travel') == 'unknown'

    def test_device_tracker_test1_awayfurther_test2_first(self):
        self.hass.states.set(
            'device_tracker.test1', 'not_home',
            {
                'friendly_name': 'test1'
            })
        self.hass.pool.block_till_done()
        self.hass.states.set(
            'device_tracker.test2', 'not_home',
            {
                'friendly_name': 'test2'
            })
        self.hass.pool.block_till_done()
        assert proximity.setup(self.hass, {
            'proximity': {
                'zone': 'home',
                'ignored_zones': {
                    'work'
                },
                'devices': {
                    'device_tracker.test1',
                    'device_tracker.test2'
                }
            }
        })

        self.hass.states.set(
            'device_tracker.test1', 'not_home',
            {
                'friendly_name': 'test1',
                'latitude': 10.1,
                'longitude': 5.1
            })
        self.hass.pool.block_till_done()

        self.hass.states.set(
            'device_tracker.test2', 'not_home',
            {
                'friendly_name': 'test2',
                'latitude': 20.1,
                'longitude': 10.1
            })
        self.hass.pool.block_till_done()
        self.hass.states.set(
            'device_tracker.test1', 'not_home',
            {
                'friendly_name': 'test1',
                'latitude': 40.1,
                'longitude': 20.1
            })
        self.hass.pool.block_till_done()
        self.hass.states.set(
            'device_tracker.test1', 'not_home',
            {
                'friendly_name': 'test1',
                'latitude': 35.1,
                'longitude': 15.1
            })
        self.hass.pool.block_till_done()
        self.hass.states.set(
            'device_tracker.test1', 'work',
            {
                'friendly_name': 'test1'
            })
        self.hass.pool.block_till_done()
        state = self.hass.states.get('proximity.home')
        assert state.attributes.get('nearest') == 'test2'
        assert state.attributes.get('dir_of_travel') == 'unknown'

    def test_device_tracker_test1_awayfurther_a_bit(self):
        assert proximity.setup(self.hass, {
            'proximity': {
                'zone': 'home',
                'ignored_zones': {
                    'work'
                },
                'devices': {
                    'device_tracker.test1'
                },
                'tolerance': 1000
            }
        })

        self.hass.states.set(
            'device_tracker.test1', 'not_home',
            {
                'friendly_name': 'test1',
                'latitude': 20.1000001,
                'longitude': 10.1000001
            })
        self.hass.pool.block_till_done()
        state = self.hass.states.get('proximity.home')
        assert state.attributes.get('nearest') == 'test1'
        assert state.attributes.get('dir_of_travel') == 'unknown'
        self.hass.states.set(
            'device_tracker.test1', 'not_home',
            {
                'friendly_name': 'test1',
                'latitude': 20.1000002,
                'longitude': 10.1000002
            })
        self.hass.pool.block_till_done()
        state = self.hass.states.get('proximity.home')
        assert state.attributes.get('nearest') == 'test1'
        assert state.attributes.get('dir_of_travel') == 'stationary'

    def test_device_tracker_test1_nearest_after_test2_in_ignored_zone(self):
        self.hass.states.set(
            'device_tracker.test1', 'not_home',
            {
                'friendly_name': 'test1'
            })
        self.hass.pool.block_till_done()
        self.hass.states.set(
            'device_tracker.test2', 'not_home',
            {
                'friendly_name': 'test2'
            })
        self.hass.pool.block_till_done()
        assert proximity.setup(self.hass, {
            'proximity': {
                'zone': 'home',
                'ignored_zones': {
                    'work'
                },
                'devices': {
                    'device_tracker.test1',
                    'device_tracker.test2'
                }
            }
        })

        self.hass.states.set(
            'device_tracker.test1', 'not_home',
            {
                'friendly_name': 'test1',
                'latitude': 20.1,
                'longitude': 10.1
            })
        self.hass.pool.block_till_done()
        state = self.hass.states.get('proximity.home')
        assert state.attributes.get('nearest') == 'test1'
        assert state.attributes.get('dir_of_travel') == 'unknown'

        self.hass.states.set(
            'device_tracker.test2', 'not_home',
            {
                'friendly_name': 'test2',
                'latitude': 10.1,
                'longitude': 5.1
            })
        self.hass.pool.block_till_done()
        state = self.hass.states.get('proximity.home')
        assert state.attributes.get('nearest') == 'test2'
        assert state.attributes.get('dir_of_travel') == 'unknown'

        self.hass.states.set(
            'device_tracker.test2', 'work',
            {
                'friendly_name': 'test2',
                'latitude': 12.6,
                'longitude': 7.6
            })
        self.hass.pool.block_till_done()
        state = self.hass.states.get('proximity.home')
        assert state.attributes.get('nearest') == 'test1'
        assert state.attributes.get('dir_of_travel') == 'unknown'
