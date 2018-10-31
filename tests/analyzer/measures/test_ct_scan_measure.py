"""Tests for the CT Scan measure class (measures 415 and 416)."""
import datetime

from claims_to_quality.analyzer.calculation.ct_scan_measure import CTScanMeasure
from claims_to_quality.analyzer.models.claim import Claim
from claims_to_quality.analyzer.models.measures.eligibility_option import EligibilityOption
from claims_to_quality.analyzer.models.measures.measure_code import MeasureCode
from claims_to_quality.analyzer.models.measures.measure_definition import MeasureDefinition
from claims_to_quality.analyzer.models.measures.performance_option import PerformanceOption

import mock


def get_test_ct_query_results():
    """Build a mock IDR response with a relevant code for these tests."""
    return [
        {
            'bene_sk': 'beneficiary_1',
            'clm_line_from_dt': datetime.date(2015, 10, 10)
        }
    ]


def get_test_claim_with_june_date():
    """Build a Claim with an invalid date for these tests."""
    return Claim({
        'dx_codes': ['dx_code_1'],
        'clm_from_dt': datetime.date(2015, 10, 10),
        'clm_thru_dt': datetime.date(2015, 10, 10),
        'bene_sk': 'beneficiary_1',
        'claim_lines': [
            {
                'clm_line_hcpcs_cd': '99281',
                'clm_line_from_dt': datetime.date(2015, 6, 6)
            },
            {
                'clm_line_hcpcs_cd': 'quality_code'
            }
        ]
    })


def get_test_claim_with_october_date():
    """Build a Claim with a valid date for these tests."""
    return Claim({
        'dx_codes': ['dx_code_1'],
        'clm_from_dt': datetime.date(2015, 10, 10),
        'clm_thru_dt': datetime.date(2015, 10, 10),
        'bene_sk': 'beneficiary_1',
        'claim_lines': [
            {
                'clm_line_hcpcs_cd': '99281',
                'clm_line_from_dt': datetime.date(2015, 10, 10)
            },
            {
                'clm_line_hcpcs_cd': 'quality_code'
            }
        ]
    })


def get_test_measure():
    """Build the Measure used in the CT Scan Measure tests."""
    eligibility_options = [
        EligibilityOption({
            'procedureCodes': [
                MeasureCode({'code': '99281'})
            ],
            'diagnosis_codes': [
                'dx_code_1'
            ]
        })
    ]
    performance_options = [
        PerformanceOption({
            'optionType': 'performanceNotMet',
            'quality_codes': [
                MeasureCode({
                    'code': 'quality_code',
                })
            ]
        })
    ]
    return CTScanMeasure(measure_definition=MeasureDefinition({
        'eligibility_options': eligibility_options,
        'performance_options': performance_options
    }))


class TestCTScanMeasure:
    """Tests for filtering of CT Scan related claims for measures 415 and 416."""

    def setup(self):
        """Build the measure and claim used in all tests."""
        self.measure = get_test_measure()
        self.claim = get_test_claim_with_october_date()

    @mock.patch(
        'claims_to_quality.analyzer.calculation.ct_scan_measure.'
        'CTScanMeasure._get_ct_scan_beneficiaries_and_dates')
    def test_filter_by_eligibility_criteria_true(self, _get_ct_scan_beneficiaries_and_dates):
        """Test that claims which do have a matching CT Scan pass through the filter."""
        _get_ct_scan_beneficiaries_and_dates.return_value = {
            (self.claim['bene_sk'], self.claim['claim_lines'][0]['clm_line_from_dt'])
        }
        assert len(self.measure.filter_by_eligibility_criteria(claims=[self.claim])) == 1

    @mock.patch(
        'claims_to_quality.analyzer.calculation.ct_scan_measure.'
        'CTScanMeasure._get_ct_scan_beneficiaries_and_dates')
    def test_filter_by_eligibility_criteria_false(self, _get_ct_scan_beneficiaries_and_dates):
        """Test that claims which do NOT have a matching CT Scan do not pass through the filter."""
        _get_ct_scan_beneficiaries_and_dates.return_value = {}
        assert len(self.measure.filter_by_eligibility_criteria(claims=[self.claim])) == 0

    @mock.patch('claims_to_quality.lib.teradata_methods.execute.execute')
    def test_ct_scan_filter_with_correct_code_and_correct_date(self, execute):
        """Test that claims with a matching CT Scan in their dates pass through the filter."""
        execute.return_value = get_test_ct_query_results()
        assert self.measure._filter_by_ct_scan([self.claim])

    @mock.patch('claims_to_quality.lib.teradata_methods.execute.execute')
    def test_ct_scan_filter_with_correct_code_and_incorrect_date(self, execute):
        """
        Test that claims without a matching CT Scan do not pass through the filter.

        This covers the case of a CT scan on the wrong date.
        """
        execute.return_value = get_test_ct_query_results()
        self.claim = get_test_claim_with_june_date()

        assert not self.measure._filter_by_ct_scan([self.claim])

    @mock.patch('claims_to_quality.lib.teradata_methods.execute.execute')
    def test_ct_scan_filter_without_ct_scans(self, execute):
        """
        Test that claims without a matching CT Scan do not pass through the filter.

        This covers the case of a matching date for a non-CT scan procedure.
        """
        execute.return_value = []
        assert not self.measure._filter_by_ct_scan([self.claim])

    def test_execute_with_no_quality_codes(self):
        """Test that execute returns 0 for all markers if no quality codes were submitted."""
        claims = []
        output = self.measure.execute(claims)
        expected = {
            'eligible_population_exclusion': 0,
            'eligible_population_exception': 0,
            'performance_met': 0,
            'performance_not_met': 0,
            'eligible_population': 0
        }

        assert output == expected
