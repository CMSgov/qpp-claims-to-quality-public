"""Config file for the analyzer and storage modules."""
# TODO: Add call protection. Who uses config?
import datetime
import os

from claims_to_quality.lib.helpers import dict_utils

import ujson as json

_CONFIG = None


class InvalidConfigurationException(Exception):
    """Indicates configuration is invalid."""


class Config(object):
    """
    An internal representation of a configuration file.

    Handles multiple possible config sources (path or env var) and nested-key lookups.
    """

    def __init__(self, config):
        """Instantiate a Config object with config file contents."""
        self._config = config

    @classmethod
    def from_path(cls, path):
        """Load configuration from a given path."""
        with open(path) as file:
            return cls(json.loads(file.read()))

    @staticmethod
    def check_submission_endpoint(endpoint, key):
        """Check that the submission endpoint is correct."""
        if endpoint and key not in endpoint:
            raise InvalidConfigurationException(
                '{key} does not appear in endpoint {endpoint}'.format(
                    key=key, endpoint=endpoint)
            )

    @classmethod
    def default_config(cls):
        """Load configuration based on information provided in this file and ENV."""
        connection_method = _get_env_variable('CONNECTION_METHOD', default='JUMP')

        env_config = CONFIG
        environment = env_config['environment']

        if environment == 'DEV':
            env_config = dict_utils.nested_update(env_config, CONFIG_DEV)
            cls.check_submission_endpoint(env_config['submission']['endpoint'], 'dev')
        elif environment == 'PRD':
            env_config = dict_utils.nested_update(env_config, CONFIG_PRD)
        elif environment == 'IMPL':
            env_config = dict_utils.nested_update(env_config, CONFIG_IMPL)
            cls.check_submission_endpoint(env_config['submission']['endpoint'], 'imp')

        # Update connection method if needed.
        if connection_method == 'VPN':
            env_config = dict_utils.nested_update(env_config, CONFIG_VPN)

        # Update to use EUA credentials if needed.
        if 'IDR_QPPC2Q' not in _get_env_variable('IDR_USERNAME', default=''):
            env_config = dict_utils.nested_update(env_config, CONFIG_EUA_CREDENTIALS)

        return cls(env_config)

    def get(self, key, default=None):
        """
        Fetch a configuration variable, returning `default` if the key does not exist.

        :param key: Variable key.
        :param default: Default value to return if `key` is not found.
        :returns: The value, or `default` if the key does not exist.
        """
        try:
            value = self[key]
        except KeyError as e:
            if default is None:
                raise e
            value = default
        return value

    def __getitem__(self, key):
        """
        Fetch a configuration variable, returning `default` if the key does not exist.

        :param key: Variable key.
        :returns: The value.
        :raises: TypeError if key is not found.
        """
        # Handle nested parameters
        return_object = self._config
        for key in key.split('.'):
            return_object = return_object[key]

        return return_object


def get(key, default=None):
    """
    Fetch a configuration variable, returning `default` if the key does not exist.

    :param key: Variable key, possibly nested via `.`s.
    :param default: Default value to return.
    :returns: The value, or `default` if the key does not exist.
    """
    global _CONFIG
    if _CONFIG is None:
        _CONFIG = _load_config()
    return _CONFIG.get(key, default)


def reload_config(path=None):
    """
    Public function to reload configuration variable.

    This method looks in two places, in order, to find the config file:
        1. an explicit path, if one is passed as an argument
        2. this file, for CONFIG and CONFIG_ENV dictionaries.
    """
    global _CONFIG
    _CONFIG = _load_config(path)


def _load_config(path=None):
    """
    Reload configuration.

    This method looks in two places, in order, to find the config file:
        1. an explicit path, if one is passed as an argument
        2. this file, for CONFIG and CONFIG_ENV dictionaries.
    """
    if path is not None:
        config = Config.from_path(path)
    else:
        config = Config.default_config()

    # Provide fail-safe that hide_sensitive_info is not turned off by mistake.
    if (config.get('environment') not in ['IMPL', 'PRD'] and
            not config.get('hide_sensitive_information')):
        raise InvalidConfigurationException(
            'hide_sensitive_information must be True when not on IMPL or PRD.')

    # Provide fail-safe that submissions logging is not enabled by mistake.
    if (config.get('environment') in ['DEV', 'IMPL', 'PRD'] and
            config.get('submission.write_submissions_to_file')):
        raise InvalidConfigurationException(
            'write_submissions_to_file must be disabled for remote environments.'
        )

    # Check that there exists a measure definition for the desired measure year.
    if config.get('calculation.measures_year') not in config.get('assets.qpp_single_source_json'):
        raise InvalidConfigurationException(
            'There is no measure definition for the measure year specified ({})'.format(
                config.get('calculation.measures_year')
            )
        )

    return config


def _get_env_variable(env_variable, resource=None, default=None):
    """
    Wrapper around os.environ.

    This way, Python will only complain if someone actively tries to load
    the desired environment variable.
    """
    if env_variable in os.environ:
        return os.environ[env_variable]
    if default is not None:
        return default
    if resource is not None:
        print('If you wish to access {}, please set the environment variable {}'.format(
            resource, env_variable))


MEASURES_YEAR = 2018


CONFIG = {
    'hide_sensitive_information': True,
    'environment': _get_env_variable('ENV', default='TEST').upper(),
    'providers_batch_size': 50,
    'logging': {
        'log_level': _get_env_variable('LOGLEVEL', default='CRITICAL'),
        'team': 'Bayes',
        'contact': 'c2q@tistatech.com',
        'results_logger': {
            'loglevel': 'INFO',
            'max_bytes': 10**7,
            'backup_count': 3,
            'filename': '/var/log/supervisord/analyzer-results.log'
        }
    },
    'calculation': {
        'measures_year': MEASURES_YEAR,
        'start_date': datetime.date(year=MEASURES_YEAR, month=1, day=1),
        'end_date': datetime.date(year=MEASURES_YEAR, month=12, day=31),
        'as_was_date': datetime.date.today(),
        'measures': ['all'],
        'excluded_measures': [],
        'infer_performance_period': False
    },
    'submission': {
        'endpoint': 'https://qpp-submissions-sandbox.navapbc.com/submissions/',
        'obscure_providers': True,
        'filter_out_zero_reporting': False,
        'send_submissions': False,
        'patch_update': False,
        'write_submissions_to_file': False,
        'api_token': _get_env_variable('SUBMISSION_API_TOKEN', default='access_token'),
        'cookie': _get_env_variable('SUBMISSION_COOKIE', default=None)
    },
    'assets': {
        'qpp_single_source_json': {
            2017: '/home/tduser/analyzer/claims_to_quality/'
                  'lib/assets/qpp_single_source_2017.json',
            2018: '/home/tduser/analyzer/claims_to_quality/'
                  'lib/assets/qpp-measures-data-2018.json'
        }
    },
    'aws': {
        'profile_name': None,
        'sqs': {
            'queue_name': 'bayes-c2q-test',
            'num_threads': 255,
            'access_key_id': _get_env_variable(
                'SQS_ACCESS_KEY_ID', 'sqs_access_key'),
            'secret_access_key': _get_env_variable(
                'SQS_SECRET_ACCESS_KEY', 'sqs_secret_access_key')
        }
    },
    'teradata': {
        'access_layer_name': 'PRIVATE',
        'medicare_vdm_name': 'PRIVATE',
        'adm_name': 'PRIVATE',
        'config': {
            'appName': 'qpp-claims-to-quality-test',
            'version': '0',
            'configureLogging': False,
        },
        'connection': {
            'method': 'JUMP',
            'jump_ip': _get_env_variable('JUMP_IP', default='0.0.0.0'),
            'idr_ip': _get_env_variable('IDR_IP', default='0.0.0.0'),
            'parameters': {
                'tunnel_user': _get_env_variable('TUNNEL_USERNAME', 'Username for tunneling.'),
                'username': _get_env_variable('IDR_USERNAME', 'IDR username.'),
                'password': _get_env_variable('IDR_PWD', 'IDR pwd.'),
                'method': 'odbc',
                'charset': 'UTF8',
                'system': 'localhost',
                'MechanismName': 'TD2',
                'OutputAsResultSet': 'YES',
                'UseDataEncryption': 'YES'
            }
        }
    },
    'new_relic_insights': {
        'url': 'https://insights-collector.newrelic.com/v1/accounts/PLACEHOLDER_ACCOUNT_ID/events',
        'event_key': 'PLACEHOLDER_KEY'
    },
    'slack': {
        'url': _get_env_variable('SLACK_URL', default='')
    }
}


CONFIG_DEV = {
    'logging': {
        'log_level': _get_env_variable('LOGLEVEL', default='INFO')
    },
    'providers_batch_size': 10,
    'submission': {
        'endpoint': _get_env_variable('SUBMISSION_ENDPOINT'),
        'send_submissions': False,
        'write_submissions_to_file': False,
    },
    'aws': {
        'sqs': {
            'queue_name': 'claims-to-quality-dev'
        }
    },
    'teradata': {
        'access_layer_name': 'PRIVATE',
        'medicare_vdm_name': 'PRIVATE',
        'adm_name': 'PRIVATE',
        'config': {
            'appName': 'qpp-claims-to-quality-dev'
        }
    }
}

CONFIG_IMPL = {
    'hide_sensitive_information': False,
    'logging': {
        'log_level': _get_env_variable('LOGLEVEL', default='INFO')
    },
    'providers_batch_size': 10,
    'submission': {
        'endpoint': _get_env_variable('SUBMISSION_ENDPOINT'),
        'send_submissions': True,
        'write_submissions_to_file': False,
    },
    'aws': {
        'sqs': {
            'queue_name': 'claims-to-quality-impl'
        }
    },
    'teradata': {
        'access_layer_name': 'PRIVATE',
        'medicare_vdm_name': 'PRIVATE',
        'medicare_vdm_name': 'PRIVATE',
        'config': {
            'appName': 'qpp-claims-to-quality-impl'
        }
    }
}

CONFIG_PRD = {
    'hide_sensitive_information': False,
    'logging': {
        'log_level': _get_env_variable('LOGLEVEL', default='INFO')
    },
    'submission': {
        'endpoint': 'https://qpp.cms.gov/api/submissions/',
        'obscure_providers': False,
        'send_submissions': True,
        'write_submissions_to_file': False,
    },
    'aws': {
        'sqs': {
            'queue_name': 'claims-to-quality-prod'
        }
    },
    'teradata': {
        'access_layer_name': 'PRIVATE',
        'medicare_vdm_name': 'PRIVATE',
        'adm_name': 'PRIVATE',
        'config': {
            'appName': 'qpp-claims-to-quality-prd'
        }
    }
}

CONFIG_VPN = {
    'teradata': {
        'connection': {
            'method': 'VPN',
            'parameters': {
                'system': 'cmsprodtcop1-bit.cmssvc.local',
                'MechanismName': 'LDAP'
            }
        }
    }
}

CONFIG_EUA_CREDENTIALS = {
    'teradata': {
        'connection': {
            'parameters': {
                'MechanismName': 'LDAP'
            }
        }
    }
}
