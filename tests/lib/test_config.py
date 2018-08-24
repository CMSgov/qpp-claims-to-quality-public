"""Tests for methods of the Config class."""
import json

from claims_to_quality.config import config
from claims_to_quality.config.config import InvalidConfigurationException
from claims_to_quality.lib.helpers import dict_utils

import mock

import pytest


class TestConfig():
    """Tests for the Config class methods."""

    def test_load_config_from_path(self):
        """Verify that a Config object can be properly instantiated from a filepath."""
        test_config_dict = {'test': 'test'}

        with mock.patch('builtins.open', mock.mock_open(read_data=json.dumps(test_config_dict))):
            test_config = config.Config.from_path('test_path')

        assert test_config._config == test_config_dict

    def test_check_submission_endpoint(self):
        """Verify that the ket test for  submission endpoint works as expected."""
        with pytest.raises(InvalidConfigurationException):
            config.Config.check_submission_endpoint('test_endpoint', 'missing_key')

        config.Config.check_submission_endpoint('test_endpoint.key', 'key')

    def test_get(self):
        """Verify that get returns value if present in config."""
        test_config_dict = {'key': 'value'}
        test_config = config.Config(test_config_dict)
        assert test_config.get('key') == 'value'

    def test_get_missing_key(self):
        """Verify that a KeyError is raised if the key is not present in the config."""
        test_config_dict = {}
        test_config = config.Config(test_config_dict)
        with pytest.raises(KeyError):
            test_config.get('key')

    def test_getitem(self):
        """Test the get item private method."""
        test_config_dict = {
            'layer1': {
                'layer2': {
                    'layer3': 'value'
                }
            }
        }

        test_config = config.Config(test_config_dict)
        output = test_config.__getitem__('layer1.layer2.layer3')

        assert output == 'value'

    # TODO: Test reloading configuration from file.

    @mock.patch('claims_to_quality.config.config._load_config')
    def test_get_value_not_set(self, _load_config):
        """Test that global get function calls reload if config isn't set."""
        config._CONFIG = None
        config.get('key')
        _load_config.assert_called_once_with()

    @mock.patch('claims_to_quality.config.config._load_config')
    def test_get_value_set(self, _load_config):
        """Test that if the config_ is set, _load_config is not called."""
        config._CONFIG = config.Config({'key': 'value'})
        config.get('key')
        assert not _load_config.called

    @mock.patch('claims_to_quality.config.config._load_config')
    def test_get_sets_value(self, _load_config):
        """Test that if global config value is not set initially, it's set after get is called."""
        test_config = {'key': 'value'}
        config._CONFIG = None
        _load_config.return_value = test_config
        config.get('key')
        assert config._CONFIG == test_config

    def test_loading_config_with_valid_measure_year(self):
        """Test that configuration correctly initialises when a valid measure year is set."""
        base_params = TestConfig.get_config_params_with_necessary_attributes_for_reloading()
        test_params = {
            'calculation': {
                'measures_year': '1234'
            },
            'assets': {
                'qpp_single_source_json': {
                    '1234': 'test'
                }
            }
        }
        params = dict_utils.nested_update(base_params, test_params)

        with mock.patch('builtins.open', mock.mock_open(read_data=json.dumps(params))):
            config.reload_config('test_path')

    def test_loading_config_with_invalid_measure_year(self):
        """
        Test that configuration throws an exception when the measure year is invalid due to a
        path to the measure definitions for that year not being defined.
        """
        base_params = TestConfig.get_config_params_with_necessary_attributes_for_reloading()
        test_params = {
            'calculation': {
                'measures_year': '1234'
            },
            'assets': {
                'qpp_single_source_json': {
                    'abcd': 'test'
                }
            }
        }
        params = dict_utils.nested_update(base_params, test_params)

        with pytest.raises(InvalidConfigurationException):
            with mock.patch('builtins.open', mock.mock_open(read_data=json.dumps(params))):
                config.reload_config('test_path')

    @classmethod
    def teardown_class(cls):
        # Reload default config for the other tests.
        config.reload_config()

    @staticmethod
    def get_config_params_with_necessary_attributes_for_reloading():
        """
        Get base parameters for config to avoid unwanted exceptions from reload_config().

        TODO: Come up with better means of testing behaviour relating to reload_config so as to
        minimise needing to specify non-test-relevant config attributes.
        """
        return {
            'environment': 'PRD',  # Needed attribute for reload_config().
            'submission': {
                'write_submissions_to_file': False  # Needed attribute for reload_config().
            }
        }
