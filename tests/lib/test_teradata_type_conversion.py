"""Tests for datatype conversion from Teradata SQL to Python."""
from claims_to_quality.lib.teradata_methods import type_conversion

import pytest

import teradata


@pytest.fixture(params=[
    # Parameters are dataType, value pairs.
    ('DATE', '2018-01-01'),
    ('DATE', 10**6),
    ('INTEGER', '999'),
    ('INTEGER', 999),
    ('TIME', '20:20:20.123456+20:20'),
    ('TIME', 10**8),
    ('TIMESTAMP', '2018-01-01 20:20:20.123456+20:20'),
    ('TIMESTAMP', 10**8),
    ('BYTE', '356a192b7913b04c54574d18c28d46e6395428ab'),
    ('VARCHAR', 'test_input_string'),
])
def test_parameters(request):
    """Return sample inputs for the convertValue function."""
    teradata_converter = teradata.datatypes.DefaultDataTypeConverter()
    dbtype = ''
    datatype, value = request.param
    return {
        'dbType': dbtype,
        'dataType': datatype,
        'typeCode': teradata_converter.convertType(dbtype, datatype),
        'value': value,
    }


def test_convert_value(test_parameters):
    """Test that all values are converted identically to the Teradata default."""
    qpp_converter = type_conversion.DataTypeConverter()
    teradata_converter = teradata.datatypes.DefaultDataTypeConverter()

    qpp_output = qpp_converter.convertValue(**test_parameters)
    teradata_output = teradata_converter.convertValue(**test_parameters)

    assert qpp_output == teradata_output
