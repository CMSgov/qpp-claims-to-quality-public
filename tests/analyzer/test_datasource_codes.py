"""Tests for reading code objects from JSON."""
from claims_to_quality.analyzer.datasource import code_reader

import pytest


def test_load_quality_codes():
    """Test that load_quality_codes load the full list of quality codes."""
    assert len(code_reader.load_quality_codes()) > 0


def test_load_measure_definition_missing_file():
    """Test that load_quality_codes throws the expected error if file is missing."""
    with pytest.raises(IOError):
        code_reader.load_quality_codes(json_path='missing_path')
