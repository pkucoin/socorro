import unittest

import mock
from nose.tools import eq_, ok_

from crashstats.api.cleaner import Cleaner, SmartWhitelistMatcher
from crashstats import scrubber


class TestCleaner(unittest.TestCase):

    def test_simplest_case(self):
        whitelist = {'hits': ('foo', 'bar')}
        data = {
            'hits': [
                {'foo': 1,
                 'bar': 2,
                 'baz': 3},
                {'foo': 4,
                 'bar': 5,
                 'baz': 6},
            ]
        }
        cleaner = Cleaner(whitelist)
        cleaner.start(data)
        expect = {
            'hits': [
                {'foo': 1,
                 'bar': 2},
                {'foo': 4,
                 'bar': 5},
            ]
        }
        eq_(data, expect)

    @mock.patch('warnings.warn')
    def test_simplest_case_with_warning(self, p_warn):
        whitelist = {'hits': ('foo', 'bar')}
        data = {
            'hits': [
                {'foo': 1,
                 'bar': 2,
                 'baz': 3},
                {'foo': 4,
                 'bar': 5,
                 'baz': 6},
            ]
        }
        cleaner = Cleaner(whitelist, debug=True)
        cleaner.start(data)
        p_warn.assert_called_with("Skipping 'baz'")

    def test_all_dict_data(self):
        whitelist = {Cleaner.ANY: ('foo', 'bar')}
        data = {
            'WaterWolf': {
                'foo': 1,
                'bar': 2,
                'baz': 3,
            },
            'NightTrain': {
                'foo': 7,
                'bar': 8,
                'baz': 9,
            },
        }
        cleaner = Cleaner(whitelist)
        cleaner.start(data)
        expect = {
            'WaterWolf': {
                'foo': 1,
                'bar': 2,
            },
            'NightTrain': {
                'foo': 7,
                'bar': 8,
            },
        }
        eq_(data, expect)

    def test_simple_list(self):
        whitelist = ('foo', 'bar')
        data = [
            {
                'foo': 1,
                'bar': 2,
                'baz': 3,
            },
            {
                'foo': 7,
                'bar': 8,
                'baz': 9,
            },
        ]
        cleaner = Cleaner(whitelist)
        cleaner.start(data)
        expect = [
            {
                'foo': 1,
                'bar': 2,
            },
            {
                'foo': 7,
                'bar': 8,
            },
        ]
        eq_(data, expect)

    def test_plain_dict(self):
        whitelist = ('foo', 'bar')
        data = {
            'foo': 1,
            'bar': 2,
            'baz': 3,
        }
        cleaner = Cleaner(whitelist)
        cleaner.start(data)
        expect = {
            'foo': 1,
            'bar': 2,
        }
        eq_(data, expect)

    def test_dict_data_with_lists(self):
        whitelist = {
            'hits': {
                Cleaner.ANY: ('foo', 'bar')
            }
        }
        data = {
            'hits': {
                'WaterWolf': [
                    {'foo': 1, 'bar': 2, 'baz': 3},
                    {'foo': 4, 'bar': 5, 'baz': 6}
                ],
                'NightTrain': [
                    {'foo': 7, 'bar': 8, 'baz': 9},
                    {'foo': 10, 'bar': 11, 'baz': 12}
                ]
            }
        }
        cleaner = Cleaner(whitelist)
        cleaner.start(data)
        expect = {
            'hits': {
                'WaterWolf': [
                    {'foo': 1, 'bar': 2},
                    {'foo': 4, 'bar': 5}
                ],
                'NightTrain': [
                    {'foo': 7, 'bar': 8},
                    {'foo': 10, 'bar': 11}
                ]
            }
        }
        eq_(data, expect)

    def test_all_dict_data_deeper(self):
        whitelist = {Cleaner.ANY: {Cleaner.ANY: ('foo', 'bar')}}
        data = {
            'WaterWolf': {
                '2012': {
                    'foo': 1,
                    'bar': 2,
                    'baz': 3,
                },
                '2013': {
                    'foo': 4,
                    'bar': 5,
                    'baz': 6,
                }
            },
            'NightTrain': {
                '2012': {
                    'foo': 7,
                    'bar': 8,
                    'baz': 9,
                },
                '2013': {
                    'foo': 10,
                    'bar': 11,
                    'baz': 12,
                }
            },
        }
        cleaner = Cleaner(whitelist)
        cleaner.start(data)
        expect = {
            'WaterWolf': {
                '2012': {
                    'foo': 1,
                    'bar': 2,
                },
                '2013': {
                    'foo': 4,
                    'bar': 5,
                }
            },
            'NightTrain': {
                '2012': {
                    'foo': 7,
                    'bar': 8,
                },
                '2013': {
                    'foo': 10,
                    'bar': 11,
                }
            },
        }
        eq_(data, expect)

    def test_with_scrubber_cleaning(self):
        whitelist = {'hits': ('foo', 'bar', 'baz')}
        data = {
            'hits': [
                {'foo': "Bla bla",
                 'bar': "contact me on big@penis.com",
                 'baz': "when I visited http://www.p0rn.com"},
                {'foo': "Ble ble unconfiged@email.com",
                 'bar': "other things on https://google.com here",
                 'baz': "talk to bill@gates.com"},
            ]
        }
        cleaner = Cleaner(
            whitelist,
            clean_scrub=(
                ('bar', scrubber.EMAIL),
                ('bar', scrubber.URL),
                ('baz', scrubber.URL),
            )
        )
        cleaner.start(data)
        expect = {
            'hits': [
                {'foo': "Bla bla",
                 'bar': "contact me on ",
                 'baz': "when I visited "},
                {'foo': "Ble ble unconfiged@email.com",
                 'bar': "other things on  here",
                 # because 'baz' doesn't have an EMAIL scrubber
                 'baz': "talk to bill@gates.com"},
            ]
        }
        eq_(data, expect)


class TestSmartWhitelistMatcher(unittest.TestCase):

    def test_basic_in(self):
        whitelist = ['some', 'thing*']
        matcher = SmartWhitelistMatcher(whitelist)
        ok_('some' in matcher)
        ok_('something' not in matcher)
        ok_('awesome' not in matcher)
        ok_('thing' in matcher)
        ok_('things' in matcher)
        ok_('nothing' not in matcher)
