"""Tests for measure_mapping file."""
from claims_to_quality.analyzer import measure_mapping
from claims_to_quality.analyzer.calculation import intersecting_diagnosis_measure
from claims_to_quality.analyzer.calculation.patient_process_measure import PatientProcessMeasure
from claims_to_quality.analyzer.datasource import measure_reader
from claims_to_quality.config import config

import pytest


def test_get_measure_calculator():
    """Test the function get_measure_calculator."""
    measure = measure_mapping.get_measure_calculator(measure_number='047')
    assert isinstance(measure, PatientProcessMeasure)


def test_get_measure_calculator_not_implemented():
    """Verify get_measure_calculator raises error if the measure isn't implemented."""
    with pytest.raises(KeyError):
        measure_mapping.get_measure_calculator(measure_number='not_a_measure')


class TestReadAllMeasuresFromSingleSource2017():
    """Test suite for tests requiring reading all 2017 measures from the single source."""

    @classmethod
    def setup_class(cls):
        """Load all measures for further tests."""
        # TODO: Test these functions with their default values from config.
        year = 2017
        cls.measures = measure_mapping.get_all_measure_ids(year=year)
        cls.single_source = measure_reader.load_single_source(
            json_path=config.get('assets.qpp_single_source_json')[year]
        )
        cls.measure_calculators = measure_mapping.get_measure_calculators(
            measures=cls.measures, year=year
        ).values()
        cls.measure_definitions = [
            calculator.measure_definition for calculator in cls.measure_calculators
        ]

    def test_all_eligibility_options_include_at_least_one_procedure_code(self):
        """
        All eligibility options must require at least one procedure or encounter code.

        The logic used to filter claims returned from the IDR requires this to be the case.
        """
        for measure_definition in self.measure_definitions:
            for eligibility_option in measure_definition.eligibility_options:
                assert(len(eligibility_option.procedure_codes) > 0)

    def test_all_intersecting_diagnosis_measures_have_the_same_diagnosis_codes(self):
        """These measures should have the same diagnosis codes across eligibility options."""
        intersecting_diagnosis_measures = [
            calculator
            for calculator in self.measure_calculators
            if isinstance(calculator, intersecting_diagnosis_measure.IntersectingDiagnosisMeasure)
        ]

        for measure in intersecting_diagnosis_measures:
            for option in measure.eligibility_options:
                assert (
                    option.diagnosis_codes_set == measure.eligibility_options[0].diagnosis_codes_set
                )

    def test_all_measures_can_be_calculated(self):
        """Test that all measures have measure calculator objects."""
        # FIXME: Update this to read directly from single source instead of hard-coding.
        assert len(self.measures) == 74
        assert len(self.measure_calculators) == 74

    @classmethod
    def teardown_class(cls):
        """Reload default config for the other tests."""
        config.reload_config()


class TestReadAllMeasuresFromSingleSource2018():
    """Test suite for tests requiring reading all 2018 measures from the single source."""

    @classmethod
    def setup_class(cls):
        """Load all measures for further tests."""
        # Use 2018 as measures year in config.
        year = 2018
        cls.measures = measure_mapping.get_all_measure_ids(year=year)
        cls.single_source = measure_reader.load_single_source(
            json_path=config.get('assets.qpp_single_source_json')[year]
        )
        cls.measure_calculators = measure_mapping.get_measure_calculators(
            measures=cls.measures, year=year
        ).values()
        cls.measure_definitions = [
            calculator.measure_definition for calculator in cls.measure_calculators
        ]

    def test_all_eligibility_options_include_at_least_one_procedure_code(self):
        """
        All eligibility options must require at least one procedure or encounter code.

        The logic used to filter claims returned from the IDR requires this to be the case.
        """
        for measure_definition in self.measure_definitions:
            for eligibility_option in measure_definition.eligibility_options:
                assert(len(eligibility_option.procedure_codes) > 0)

    def test_all_intersecting_diagnosis_measures_have_the_same_diagnosis_codes(self):
        """These measures should have the same diagnosis codes across eligibility options."""
        intersecting_diagnosis_measures = [
            calculator
            for calculator in self.measure_calculators
            if isinstance(calculator, intersecting_diagnosis_measure.IntersectingDiagnosisMeasure)
        ]

        for measure in intersecting_diagnosis_measures:
            for option in measure.eligibility_options:
                assert (
                    option.diagnosis_codes_set == measure.eligibility_options[0].diagnosis_codes_set
                )

    def test_all_measures_can_be_calculated(self):
        """Test that all measures have measure calculator objects."""
        # FIXME: Update this to read directly from single source instead of hard-coding.
        assert len(self.measures) == 72
        assert len(self.measure_calculators) == 72

    @classmethod
    def teardown_class(cls):
        """Reload default config for the other tests."""
        config.reload_config()
