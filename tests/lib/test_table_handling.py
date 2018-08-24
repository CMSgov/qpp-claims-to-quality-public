"""Tests for methods to create and drop Teradata tables."""
from claims_to_quality.lib.teradata_methods import table_handling

import mock

from tests.assets import test_helpers


@mock.patch('claims_to_quality.lib.teradata_methods.execute.execute')
def test_if_table_exists_method_table_does_exist(execute):
    """Test that _if_table_exists returns True when the table exists."""
    execute.return_value = test_helpers.fetch_sample_teradata_rows()
    output = table_handling._if_table_exists('fake_table', 'fake_db')
    assert output is True


@mock.patch('claims_to_quality.lib.teradata_methods.execute.execute')
def test_if_table_exists_method_table_does_not_exist(execute):
    """Test that _if_table_exists returns False when the table does not exist."""
    execute.return_value = []
    output = table_handling._if_table_exists('fake_table', 'fake_db')
    assert output is False


@mock.patch('claims_to_quality.lib.teradata_methods.execute.execute')
@mock.patch('claims_to_quality.lib.teradata_methods.table_handling._if_table_exists')
def test_drop_table_if_exists_table_does_not_exist(_if_table_exists, execute):
    """Test that no DROP TABLE statement is executed if the table does not exist."""
    _if_table_exists.return_value = False
    table_handling._drop_table_if_exists('fake_table', 'fake_db')
    execute.assert_not_called()


@mock.patch('claims_to_quality.lib.teradata_methods.execute.execute')
@mock.patch('claims_to_quality.lib.teradata_methods.table_handling._if_table_exists')
def test_drop_table_if_exists_table_exists(_if_table_exists, execute):
    """Test that the correct DROP TABLE statement is executed if the table already exists."""
    _if_table_exists.return_value = True

    expected_query_to_run = table_handling.DROP_TABLE_BASE_QUERY.format(
        database='fake_db', table='fake_table')

    table_handling._drop_table_if_exists('fake_table', 'fake_db')
    execute.assert_called_with(expected_query_to_run)
