"""Test Teradata connectors."""
from claims_to_quality.config import config
from claims_to_quality.lib.connectors import teradata_connector
from claims_to_quality.lib.teradata_methods import teradata_errors

import mock

import pytest

import requests

import teradata


def test_get_uda_exec():
    """
    Test _get_uda_exec.
    Note: This test only works on an instance or a container
    with properly installed Teradata uda_exec drivers.
    """
    uda_exec = teradata_connector._get_uda_exec(params=config.get('teradata.config'))
    assert isinstance(uda_exec, teradata.udaexec.UdaExec)


@mock.patch('teradata.UdaExec')
def test_get_uda_exec_universal(UdaExec):
    """
    Note: This will work across all devices but simply tests
    that provided Teradata can create a uda_exec, it is forwarded
    properly by _get_uda_exec.
    """
    UdaExec.return_value = 'uda_exec'
    uda_exec = teradata_connector._get_uda_exec(params=config.get('teradata.config'))
    assert uda_exec == 'uda_exec'


@mock.patch('teradata.UdaExec.connect')
def test_teradata_connection(connect):
    connect.return_value = 'session'
    session = teradata_connector._teradata_connection()
    assert session == 'session'


@mock.patch('requests.get')
def tets_test_access_to_idr_instance_valid(get):
    valid_message = 'LAN message Format field is invalid.'
    get.side_effect = requests.ConnectionError(valid_message)
    has_access = teradata_connector._test_access_to_idr_instance()
    assert has_access


@mock.patch('requests.get')
def tets_test_access_to_idr_instance_invalid(get):
    invalid_message = 'Invalid Error Message.'
    get.side_effect = requests.ConnectionError(invalid_message)
    with pytest.raises(teradata_errors.TeradataError):
        teradata_connector._test_access_to_idr_instance()


@mock.patch('teradata.UdaExec.connect')
@mock.patch('requests.get')
def test_test_teradata_connection(get, connect):
    valid_message = 'LAN message Format field is invalid.'
    get.side_effect = requests.ConnectionError(valid_message)
    connect.return_value = 'session'
    connection_success = teradata_connector.test_teradata_connection(continue_prompt=False)
    assert connection_success
