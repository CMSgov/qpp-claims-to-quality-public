"""Tests methods for Measure 155, which has multiple procedure codes in an eligibility option."""
from datetime import date

from claims_to_quality.analyzer import measure_mapping
from claims_to_quality.analyzer.models import claim
from claims_to_quality.analyzer.models import claim_line


class TestMeasure155():
    """Test Measure155."""

    def setup(self):
        """Initialization of measure 155."""
        self.measure = measure_mapping.get_measure_calculator('155')
        self.claim_meets_prefilter_and_filter = claim.Claim({
            'bene_sk': 'elderly_patient_id',
            'clm_ptnt_birth_dt': date(1920, 1, 1),
            'clm_from_dt': date(2017, 1, 1),
            'claim_lines': [
                claim_line.ClaimLine(
                    {'clm_line_hcpcs_cd': '1100F'},
                    {'mdfr_cds': []}
                ),
                claim_line.ClaimLine(
                    {'clm_line_hcpcs_cd': '92541'},
                )
            ]
        })
        self.claim_meets_prefilter_but_not_filter = claim.Claim({
            'bene_sk': 'elderly_patient_id',
            'clm_ptnt_birth_dt': date(1920, 1, 1),
            'clm_from_dt': date(2017, 1, 1),
            'claim_lines': [
                claim_line.ClaimLine(
                    {'clm_line_hcpcs_cd': '1100F'},
                    {'mdfr_cds': []}
                )
            ]
        })
        self.claim_does_not_meet_prefilter_1 = claim.Claim({
            'bene_sk': 'elderly_patient_id',
            'clm_ptnt_birth_dt': date(1920, 1, 1),
            'clm_from_dt': date(2017, 1, 1),
            'claim_lines': [
                claim_line.ClaimLine(
                    {'clm_line_hcpcs_cd': '1100F'},
                    {'mdfr_cds': ['1P']},
                ),
                claim_line.ClaimLine(
                    {'clm_line_hcpcs_cd': '92541'},
                )
            ]
        })
        self.claim_does_not_meet_prefilter_2 = claim.Claim({
            'bene_sk': 'elderly_patient_id',
            'clm_ptnt_birth_dt': date(1920, 1, 1),
            'clm_from_dt': date(2017, 1, 1),
            'claim_lines': [
                claim_line.ClaimLine(
                    {'clm_line_hcpcs_cd': '92541'},
                )
            ]
        })

        self.claims = [
            self.claim_meets_prefilter_and_filter,
            self.claim_meets_prefilter_but_not_filter,
            self.claim_does_not_meet_prefilter_1,
            self.claim_does_not_meet_prefilter_2,
        ]

    def test_filter_by_eligibility_criteria(self):
        """Test claims are correctly filtered according to all eligibility options."""
        output = self.measure.filter_by_eligibility_criteria(claims=self.claims)
        assert output == [
            self.claim_meets_prefilter_and_filter
        ]
