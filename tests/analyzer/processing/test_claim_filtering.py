"""Test date handling and filtering for claims."""
import datetime

from claims_to_quality.analyzer.models.claim import Claim
from claims_to_quality.analyzer.models.claim_line import ClaimLine
from claims_to_quality.analyzer.models.measures.eligibility_option import EligibilityOption
from claims_to_quality.analyzer.models.measures.measure_definition import MeasureDefinition
from claims_to_quality.analyzer.processing import claim_filtering


class TestClaimFiltering():
    """Tests for the claim_filtering module."""

    def setup(self):
        """Initialize useful values."""
        self.performance_year = 2017

        self.line_with_quality_code = ClaimLine({'clm_line_hcpcs_cd': 'G9607'})
        self.line_without_quality_code = ClaimLine({'clm_line_hcpcs_cd': 'not_a_real_code'})

        self.claim_with_quality_code_january = Claim({
            'clm_from_dt': datetime.date(self.performance_year, 1, 1),
            'claim_lines': [self.line_with_quality_code]
        })
        self.claim_without_quality_code_january = Claim({
            'clm_from_dt': datetime.date(self.performance_year, 1, 1),
            'claim_lines': [self.line_without_quality_code]
        })

        self.all_claims = [
            self.__getattribute__(attr) for attr in dir(self)
            if type(self.__getattribute__(attr)) == Claim
        ]

        self.all_claims_in_performance_year = [
            claim for claim in self.all_claims if claim['clm_from_dt'].year == self.performance_year
        ]

        self.claim_with_relevant_procedure_code = self.claim_with_quality_code_january
        self.measure_definition = MeasureDefinition({
            'eligibility_options': [
                EligibilityOption({
                    'procedureCodes': [{'code': 'G9607'}]
                })
            ],
            'performance_options': []
        })

    def test_does_claim_have_quality_codes(self):
        """
        Test with and without quality codes.

        Should return True iff the claim has one or more quality codes.
        """
        assert claim_filtering.does_claim_have_quality_codes(
            self.claim_with_quality_code_january, quality_codes={'G9607'})
        # Note - by default does_claim_have_quality_codes will look for ANY valid quality code.
        assert not claim_filtering.does_claim_have_quality_codes(
            self.claim_without_quality_code_january)

    def test_do_any_claims_have_quality_codes(self):
        """
        Test with and without quality codes.

        Should return True exactly when at least one claim has at least one code.
        """
        assert claim_filtering.do_any_claims_have_quality_codes(self.all_claims)
        assert not claim_filtering.do_any_claims_have_quality_codes(
            [self.claim_without_quality_code_january]
        )

    def test_filter_claims_by_date(self):
        """Only claims within the calculated reporting period should be returned."""
        filtered_claims = claim_filtering.filter_claims_by_date(
            claims_data=self.all_claims,
            from_date=datetime.date(self.performance_year, 1, 1),
            to_date=datetime.date(self.performance_year, 12, 31)
        )

        assert filtered_claims == self.all_claims_in_performance_year

    def test_filter_claims_by_measure_procedure_codes(self):
        """Only claims with matching procedure codes should be returned."""
        filtered_claims = claim_filtering.filter_claims_by_measure_procedure_codes(
            claims_data=self.all_claims,
            measure_definitions=[self.measure_definition]
        )

        assert filtered_claims == [self.claim_with_relevant_procedure_code]
