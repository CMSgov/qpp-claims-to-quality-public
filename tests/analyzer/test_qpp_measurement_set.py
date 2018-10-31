"""Tests for MeasurementSet methods."""
import datetime
import json
import re

from claims_to_quality.analyzer.submission import qpp_measurement_set

import pytest


class TestMeasurementSet():
    """Tests for MeasurementSet class Methods."""

    def setup(self):
        """Setup base submission object for these tests."""
        self.start_date = datetime.date(2017, 1, 1)
        self.end_date = datetime.date(2017, 12, 31)
        self.measurement_set = qpp_measurement_set.MeasurementSet(
            tin='9' * 9,
            npi='8' * 10,
            performance_start=self.start_date,
            performance_end=self.end_date)

    def test_init(self):
        """Test that MeasurementSet object is initialized correctly."""
        measurement_set = self.measurement_set.data

        submission_dict = measurement_set['submission']

        assert re.match(
            qpp_measurement_set.FAKE_TIN_REGEX, submission_dict['taxpayerIdentificationNumber']
        )
        assert re.match(
            qpp_measurement_set.FAKE_NPI_REGEX, submission_dict['nationalProviderIdentifier']
        )

        assert submission_dict['performanceYear'] == 2017

        assert measurement_set['performanceStart'] == self.start_date
        assert measurement_set['performanceEnd'] == self.end_date
        assert measurement_set['measurements'] == []

    def test_init_obscure_providers(self):
        """Verify that providers are not obscured if the inputted tin and npi are fake."""
        measurement_set = qpp_measurement_set.MeasurementSet(
            tin='000' + '9' * 6,
            npi='0' + '8' * 9,
            performance_start=self.start_date,
            performance_end=self.end_date)

        submission_dict = measurement_set.data['submission']

        assert submission_dict['taxpayerIdentificationNumber'] == '000' + '9' * 6
        assert submission_dict['nationalProviderIdentifier'] == '0' + '8' * 9

    def test_validate_tin_correct(self):
        """Verify that validate_tin does not raise an error if TIN format is correct."""
        input_tin = '0' * 9
        validated_tin = self.measurement_set._validate_tin(input_tin)
        assert validated_tin == input_tin

    def test_validate_tin_with_spaces(self):
        """Test validate_tin in the case that there are extra spaces in the tin."""
        input_tin = '0' * 9 + ' '
        validated_tin = self.measurement_set._validate_tin(input_tin)
        assert validated_tin == '0' * 9

    def test_validate_tin_raises_errors(self):
        """Verify that validate_tin raises errors for malformatted tin."""
        with pytest.raises(qpp_measurement_set.TinFormatException):
            input_tin = '0' * 10
            self.measurement_set._validate_tin(input_tin)

    def test_validate_npi_correct(self):
        """Verify that validate_npi does not raise an error if npi format is correct."""
        input_npi = '0' * 10
        validated_npi = self.measurement_set._validate_npi(input_npi)
        assert validated_npi == input_npi

    def test_validate_npi_with_spaces(self):
        """Test validate_npi in the case that there are extra spaces in the npi."""
        input_npi = '0' * 10 + ' '
        validated_npi = self.measurement_set._validate_npi(input_npi)
        assert validated_npi == '0' * 10

    def test_validate_npi_raises_errors(self):
        """Verify that validate_npi raises errors for malformatted npi."""
        with pytest.raises(qpp_measurement_set.NpiFormatException):
            input_npi = '0' * 9
            self.measurement_set._validate_npi(input_npi)

    def test_add_measure(self):
        """Test add_measure method."""
        measure_results = {
            'performance_met': 0,
            'performance_not_met': 1,
            'eligible_population_exclusion': 2,
            'eligible_population_exception': 0,
            'eligible_population': 3
        }

        self.measurement_set.add_measure(
            measure_number='042',
            measure_results=measure_results,
        )
        measurement_set_dict = self.measurement_set.data

        assert len(measurement_set_dict['measurements']) == 1
        measurement = measurement_set_dict['measurements'][0]

        assert measurement['measureId'] == '042'
        assert measurement['value']['performanceMet'] == 0
        assert measurement['value']['performanceNotMet'] == 1
        assert measurement['value']['eligiblePopulationExclusion'] == 2
        assert measurement['value']['eligiblePopulationException'] == 0
        assert measurement['value']['eligiblePopulation'] == 3

    def test_add_empty_measure(self):
        """Test add_measure doesn't add measure if it's empty."""
        measure_results = {
            'performance_met': 0,
            'performance_not_met': 0,
            'eligible_population_exclusion': 0,
            'eligible_population_exception': 0,
            'eligible_population': 0
        }

        self.measurement_set.add_measure(
            measure_number='042',
            measure_results=measure_results,
        )

        assert self.measurement_set.is_empty()

    def test_add_measure_multiple(self):
        """Test adding multiple measures to the dict."""
        measure_42_results = {
            'performance_met': 0,
            'performance_not_met': 1,
            'eligible_population_exclusion': 2,
            'eligible_population_exception': 0,
            'eligible_population': 3
        }

        measure_100_results = {
            'performance_met': 0,
            'performance_not_met': 1,
            'eligible_population_exclusion': 2,
            'eligible_population_exception': 0,
            'eligible_population': 3
        }

        self.measurement_set.add_measure(
            measure_number='042',
            measure_results=measure_42_results,
        )

        self.measurement_set.add_measure(
            measure_number='100',
            measure_results=measure_100_results,
        )
        measurement_set = self.measurement_set.data

        assert len(measurement_set['measurements']) == 2
        measure_ids = [measurement['measureId'] for measurement in measurement_set['measurements']]
        assert '042' in measure_ids
        assert '100' in measure_ids

    def test_add_measure_with_multiple_strata(self):
        """Test adding measures with multiple strata."""
        measure_46_results = [
            {
                'name': 'first_stratum',
                'results': {
                    'performance_met': 2,
                    'performance_not_met': 1,
                    'eligible_population': 10,
                    'eligible_population_exclusion': 2,
                    'eligible_population_exception': 1,
                }
            },
            {
                'name': 'second_stratum',
                'results': {
                    'performance_met': 0,
                    'performance_not_met': 1,
                    'eligible_population_exclusion': 2,
                    'eligible_population_exception': 0,
                    'eligible_population': 3
                }
            },
        ]

        self.measurement_set.add_measure_with_multiple_strata(
            measure_number='046',
            measure_results=measure_46_results,
        )

        measurement_set = self.measurement_set.data

        assert len(measurement_set['measurements']) == 1

        strata = measurement_set['measurements'][0]['value']['strata']

        assert strata[0] == {
            'stratum': 'first_stratum',
            'performanceMet': 2,
            'performanceNotMet': 1,
            'eligiblePopulation': 10,
            'eligiblePopulationExclusion': 2,
            'eligiblePopulationException': 1,
        }
        assert strata[1] == {
            'stratum': 'second_stratum',
            'performanceMet': 0,
            'performanceNotMet': 1,
            'eligiblePopulationExclusion': 2,
            'eligiblePopulationException': 0,
            'eligiblePopulation': 3
        }

    def test_add_measure_with_multiple_strata_no_eligible_population(self):
        """Test add_measure_with_multiple_strata doesn't add measure if it's empty."""
        measure_46_results = [
            {
                'name': 'first_stratum',
                'results': {
                    'performance_met': 0,
                    'performance_not_met': 0,
                    'eligible_population': 0,
                    'eligible_population_exclusion': 0,
                    'eligible_population_exception': 0,
                }
            },
            {
                'name': 'second_stratum',
                'results': {
                    'performance_met': 0,
                    'performance_not_met': 0,
                    'eligible_population_exclusion': 0,
                    'eligible_population_exception': 0,
                    'eligible_population': 0
                }
            },
        ]

        self.measurement_set.add_measure_with_multiple_strata(
            measure_number='046',
            measure_results=measure_46_results,
        )

        assert self.measurement_set.is_empty()

    def test_to_json(self):
        """Test that to_json serializes the MeasurementSet object dates properly."""
        measurement_set_json = self.measurement_set.to_json()
        assert type(measurement_set_json) is str

        measurement_set_dict = json.loads(measurement_set_json)
        assert measurement_set_dict['submission']['performanceYear'] == 2017

        assert measurement_set_dict['performanceStart'] == '2017-01-01'
        assert measurement_set_dict['performanceEnd'] == '2017-12-31'

    def test_prepare_for_scoring(self):
        """Test that to_json serializes the MeasurementSet object dates properly."""
        measure_results = {
            'performance_met': 0,
            'performance_not_met': 1,
            'eligible_population_exclusion': 2,
            'eligible_population_exception': 0,
            'eligible_population': 3
        }

        self.measurement_set.add_measure(
            measure_number='042',
            measure_results=measure_results,
        )

        measurement = {
            'measureId': '042',
            'value': {
                'isEndToEndReported': False,
                'performanceMet': 0,
                'eligiblePopulationExclusion': 2,
                'eligiblePopulationException': 0,
                'performanceNotMet': 1,
                'eligiblePopulation': 3}
        }

        measurement_set_json_for_scoring = self.measurement_set.prepare_for_scoring()
        measurement_set_dict = json.loads(measurement_set_json_for_scoring)

        assert type(measurement_set_json_for_scoring) is str

        assert measurement_set_dict['performanceYear'] == 2017
        assert measurement_set_dict['programName'] == 'mips'
        assert measurement_set_dict['measurementSets'][0]['measurements'][0] == measurement

    def test_date_handler(self):
        """Test that the date handler raises an error for invalid dates."""
        with pytest.raises(TypeError):
            qpp_measurement_set.MeasurementSet.date_handler('not-a-date')
