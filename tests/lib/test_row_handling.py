"""Tests for methods in row_handling.py."""
from claims_to_quality.lib.teradata_methods import row_handling

import mock

from tests.assets import test_helpers


def test_convert_list_of_lists_to_teradata_rows():
    """Test that lists of lists can be converted to Teradata row objects."""
    data = [('value1', 2, 3), ('value2', 5, 6)]
    columns = ['str_col', 'int_col_1', 'int_col_2']

    output = row_handling.convert_list_of_lists_to_teradata_rows(data, columns)

    assert output[1]['int_col_2'] == 6


def test_convert_dicts_to_teradata_rows():
    """Test that lists of dictionaries can be converted to Teradata row objects."""
    data = [
        {
            'str_col': 'value1',
            'int_col_1': 2,
            'int_col_2': 3
        }, {
            'str_col': 'value2',
            'int_col_1': 5,
            'int_col_2': 6
        }
    ]

    output = row_handling.convert_dicts_to_teradata_rows(data)

    assert output[1]['int_col_2'] == 6


def test_convert_dicts_to_teradata_rows_returns_empty_list():
    """Test that an empty input list of dictionaries outputs an empty list of rows."""
    data = []
    output = row_handling.convert_dicts_to_teradata_rows(data)
    assert output == []


class TestToCSV(object):
    """Test to_csv method can successfully write valid rows to file."""

    def setup(self):
        """Initialize rows and csv path."""
        self.rows = test_helpers.fetch_sample_teradata_rows()
        self.csv_path = 'not/a/real/path'

    def test_to_csv_with_no_rows_returns_none(self):
        """Test that to_csv returns None when no rows are provided."""
        output = row_handling.to_csv(rows=[], csv_path=self.csv_path)
        assert output is None

    @mock.patch('builtins.open', new_callable=mock.mock_open)
    def test_to_csv_with_valid_rows(self, mock_open):
        """Test that to_csv can write Teradata row objects to file."""
        row_handling.to_csv(rows=self.rows, csv_path=self.csv_path)
        open.assert_called_with(self.csv_path, 'w')
