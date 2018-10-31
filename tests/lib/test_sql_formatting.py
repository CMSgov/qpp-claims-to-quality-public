"""Test Teradata methods."""
from claims_to_quality.lib.teradata_methods import measures_to_sql
from claims_to_quality.lib.teradata_methods import sql_formatting

import pytest


def test_to_sql_list_strs():
    str_list = ['a1', '2', '3']
    expected = "('a1', '2', '3')"

    assert expected == sql_formatting.to_sql_list(str_list)


def test_to_sql_list_ints():
    int_list = [1, 2, 3]
    expected = "('1', '2', '3')"

    assert expected == sql_formatting.to_sql_list(int_list)


def test_to_sql_list_empty_list():
    empty_list = []
    with pytest.raises(sql_formatting.SQLFormattingError):
        sql_formatting.to_sql_list(empty_list)


def test_convert_procedure_codes_to_sql_condition():
    procedure_codes = ['code1', 'code2', 'code3']
    output = measures_to_sql._convert_procedure_codes_to_sql_condition(procedure_codes)
    expected = "CLM_LINE_HCPCS_CD IN ('code1', 'code2', 'code3')"

    assert output == expected
