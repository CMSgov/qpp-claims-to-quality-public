"""Tests for datasource.measures."""
import collections

from claims_to_quality.analyzer.datasource import measure_reader

import pytest


def test_load_measure_definition():
    """Test that load_measure_definition loads the correct measure."""
    assert measure_reader.load_measure_definition('047') is not None


def test_load_single_source_missing_file():
    """Test that load_measure_definition throws the expected error if file is missing."""
    with pytest.raises(IOError):
        measure_reader.load_single_source('missing_path')


def test_load_measure_definition_missing_measure():
    """Test that load_measure_definition throws error if measure number doesn't exist."""
    with pytest.raises(KeyError):
        measure_reader.load_measure_definition(0)


def test_get_all_procedure_codes_in_eligibility_options():
    """The method should return all procedure codes mentioned in the measure definition."""
    measure_numbers = ['052']
    output = measure_reader._get_all_procedure_codes_in_eligibility_options(
        measure_numbers)

    expected = ['99201', '99202', '99203', '99204', '99205', '99212', '99213', '99214', '99215']

    assert collections.Counter(output) == collections.Counter(expected)
