"""Tests methods within visit_measure.py."""
import collections
from datetime import date

from claims_to_quality.analyzer.calculation import visit_measure
from claims_to_quality.analyzer.models import claim
from claims_to_quality.analyzer.models.measures.eligibility_option import EligibilityOption
from claims_to_quality.analyzer.models.measures.measure_code import MeasureCode
from claims_to_quality.analyzer.models.measures.measure_definition import MeasureDefinition
from claims_to_quality.analyzer.models.measures.performance_option import PerformanceOption


class TestVisitMeasure():
    """Test VisitMeasure class."""

    def test_compute_eligible_instance_weight(self):
        """Make sure the _count_eligible_instances calculation is accurate."""
        procedure_codes = [
            MeasureCode({'code': 'code_a'}),
            MeasureCode({'code': 'code_b'}),
            MeasureCode({'code': 'code_c'})
        ]

        eligibility_options = [
            EligibilityOption({
                'procedureCodes': procedure_codes[:2]
            }),
            EligibilityOption({
                'procedureCodes': procedure_codes[2:]
            })
        ]

        measure = visit_measure.VisitMeasure(
            measure_definition=MeasureDefinition({
                'eligibility_options': eligibility_options,
                'performance_options': []
            })
        )

        claim_lines = [
            {
                'clm_line_hcpcs_cd': 'code_a',
                'mdfr_cds': [],
                'clm_pos_code': '23'
            },
            {
                'clm_line_hcpcs_cd': 'code_a',
                'mdfr_cds': ['GQ'],
                'clm_pos_code': '43'
            },
            {
                'clm_line_hcpcs_cd': 'code_c',
                'mdfr_cds': ['AX'],
                'clm_pos_code': ''
            }
        ]
        test_claims = [claim.Claim({'claim_lines': claim_lines})]

        output = measure._compute_eligible_instance_weight(test_claims)

        assert output == 3

    def test_score_eligible_instances(self):
        """Test that score_eligible_instances returns the expected values and runs without error."""
        performance_options = [
            PerformanceOption({
                'optionType': 'performanceMet',
                'qualityCodes': [
                    {'code': 'pn_code'}
                ]
            }),
            PerformanceOption({
                'optionType': 'performanceNotMet',
                'qualityCodes': [
                    {'code': 'pn_x_code'}
                ]
            }),
            PerformanceOption({
                'optionType': 'eligiblePopulationExclusion',
                'qualityCodes': [
                    {'code': 'pd_x_code'}
                ]
            })
        ]

        eligibility_options = [
            EligibilityOption({
                'procedureCodes': [MeasureCode({'code': 'enc_code'})]
            })
        ]

        measure = visit_measure.VisitMeasure(
            measure_definition=MeasureDefinition({
                'eligibility_options': eligibility_options,
                'performance_options': performance_options
            })
        )

        bene_1_claim_1 = claim.Claim({
            'bene_sk': 'bene_1',
            'clm_ptnt_birth_dt': date(1940, 1, 1),
            'clm_from_dt': date(2017, 1, 1),
            'claim_lines': [
                {'clm_line_hcpcs_cd': 'pn_code'},
                {'clm_line_hcpcs_cd': 'enc_code'}
            ]})
        bene_1_claim_2 = claim.Claim({
            'bene_sk': 'bene_1',
            'clm_ptnt_birth_dt': date(1940, 1, 1),
            'clm_from_dt': date(2017, 1, 1),
            'claim_lines': [
                {'clm_line_hcpcs_cd': 'pn_x_code'},
                {'clm_line_hcpcs_cd': 'enc_code'}
            ]})
        bene_2_claim_2 = claim.Claim({
            'bene_sk': 'bene_2',
            'clm_ptnt_birth_dt': date(1940, 1, 1),
            'clm_from_dt': date(2017, 1, 1),
            'claim_lines': [
                {'clm_line_hcpcs_cd': 'pd_x_code'},
                {'clm_line_hcpcs_cd': 'enc_code'}
            ]})

        eligible_instances = [[bene_1_claim_1, bene_1_claim_2], [bene_2_claim_2]]

        output = measure.score_eligible_instances(eligible_instances)

        expected = collections.defaultdict(int)
        expected['eligiblePopulationExclusion'] = 1
        expected['performanceMet'] = 2

        assert output == expected
