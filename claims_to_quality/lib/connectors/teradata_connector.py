""""Functions to connect to Teradata databases."""
import select
import sys

from claims_to_quality.config import config, settings
from claims_to_quality.lib.qpp_logging import logging_config
from claims_to_quality.lib.teradata_methods import teradata_errors
from claims_to_quality.lib.teradata_methods import type_conversion

import newrelic.agent

import requests

from retrying import retry

import teradata

logger = logging_config.get_logger(__name__)


@retry(wait_exponential_multiplier=settings.WAIT_EXPONENTIAL_START_MILLISECONDS,
       stop_max_delay=settings.STOP_MAX_DELAY_MILLISECONDS)
def teradata_connection(connection_parameters=config.get('teradata.connection.parameters')):
    """Return a connection to the IDR in the given environment, with retry."""
    return _teradata_connection(connection_parameters)


@newrelic.agent.function_trace(name='teradata-connection', group='Task')
def _teradata_connection(connection_parameters=config.get('teradata.connection.parameters')):
    """Return a connection to the IDR in the given environment."""
    teradata_config = config.get('teradata.config')
    uda_exec = _get_uda_exec(teradata_config)

    session = None

    # Create a Teradata session.
    try:
        session = uda_exec.connect(**connection_parameters)
        logger.debug('Session created successfully.')
    except teradata_errors.TeradataError:
        raise teradata_errors.TeradataError(
            'Could not create a new session. You may have a Teradata Driver issue.')
    except (teradata.DatabaseError, teradata.InterfaceError):
        raise teradata_errors.TeradataError(
            'Could not create a new session. You may need to check your credentials.')
    return session


def _test_access_to_idr_instance(
        connection_parameters=config.get('teradata.connection.parameters')):
    idr_endpoint = 'http://' + connection_parameters['system'] + ':1025'
    try:
        requests.get(idr_endpoint)
    except requests.ConnectionError as e:
        # If the system is able to connect to the IDR instance, the message will be:
        # "414K(The LAN message Format field is invalid."
        if 'LAN message Format field is invalid.' in str(e):
            logger.debug("You can ping the IDR instance! Let's check access to the database.")
            return True
        else:
            error_message = 'Unable to ping the IDR instance.'
            if config.get('teradata.connection.method').upper() == 'JUMP':
                error_message += ' An error likely occured during SSH tunneling.'
            else:
                error_message += ' Likely a network or network-access issue.'
            raise teradata_errors.TeradataError(error_message)


def test_teradata_connection(
        connection_parameters=config.get('teradata.connection.parameters'),
        continue_prompt=True):
    """Test Teradata connection and ask user for input if fails."""
    try:
        # Test access to the IDR instance.
        _test_access_to_idr_instance(connection_parameters)
        # Test access to the Teradata database and session creation.
        _teradata_connection(connection_parameters)
        logger.info('Teradata connection confirmed.')
        return True
    # TODO: avoid catch all.
    except Exception as error:
        error_message = error.message if hasattr(error, 'message') else repr(error)
        if continue_prompt:
            print('Would you like to continue without connection to IDR? (y/n) ',
                  'You have 10 seconds to reply.')
            # select takes no keyword args. Args are rlist, wlist, xlist, timeout.
            read, write, exception = select.select([sys.stdin], [], [], 10)
            if read and sys.stdin.readline().strip() in ['y', 'yes']:
                logger.warn(
                    'Continuing without Teradata connection. '
                    'Error - {}'.format(error_message))
                return False

        raise teradata_errors.TeradataError(error_message)


@retry(wait_exponential_multiplier=settings.WAIT_EXPONENTIAL_START_MILLISECONDS,
       stop_max_delay=settings.STOP_MAX_DELAY_MILLISECONDS)
def _get_uda_exec(params=None, dataTypeConverter=type_conversion.DataTypeConverter()):
    uda_exec = None
    try:
        uda_exec = teradata.UdaExec(
            dataTypeConverter=dataTypeConverter,
            **params
        )
    except OSError:
        raise teradata_errors.TeradataError(
            'Impossible to connect to Teradata. Could not initialize UdaExec. Driver issue.')
    except (teradata.DatabaseError, teradata.InterfaceError):
        raise teradata_errors.TeradataError(
            'Impossible to connect to Teradata. Could not initialize UdaExec.')
    return uda_exec
