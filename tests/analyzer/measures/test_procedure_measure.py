"""Tests for ProcedureMeasure Class methods."""
from datetime import date

from claims_to_quality.analyzer.calculation import procedure_measure
from claims_to_quality.analyzer.models import claim
from claims_to_quality.analyzer.models.measures.eligibility_option import EligibilityOption
from claims_to_quality.analyzer.models.measures.measure_code import MeasureCode
from claims_to_quality.analyzer.models.measures.measure_definition import MeasureDefinition
from claims_to_quality.analyzer.models.measures.performance_option import PerformanceOption


class TestProcedureMeasure():
    """Test ProcedureMeasure class."""

    def test_execute(self):
        """Test that the execute method returns the expected values and runs without error."""
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
                    {'code': 'pd_exl_code'}
                ]
            }),
            PerformanceOption({
                'optionType': 'eligiblePopulationException',
                'qualityCodes': [
                    {'code': 'pd_exe_code'}
                ]
            })
        ]

        eligibility_options = [
            EligibilityOption({
                'procedureCodes': [MeasureCode({'code': 'enc_code'})]
            })
        ]

        measure = procedure_measure.ProcedureMeasure(
            measure_definition=MeasureDefinition({
                'eligibility_options': eligibility_options,
                'performance_options': performance_options
            })
        )

        claim_one = claim.Claim({
            'bene_sk': '1001',
            'clm_ptnt_birth_dt': date(1940, 1, 1),
            'clm_from_dt': date(2017, 1, 1),
            'claim_lines': [
                {'clm_line_hcpcs_cd': 'pn_code'},
                {'clm_line_hcpcs_cd': 'enc_code'}
            ]})
        claim_two = claim.Claim({
            'bene_sk': '1001',
            'clm_ptnt_birth_dt': date(1940, 1, 1),
            'clm_from_dt': date(2017, 1, 1),
            'claim_lines': [
                {'clm_line_hcpcs_cd': 'pn_x_code'},
                {'clm_line_hcpcs_cd': 'enc_code'}
            ]})
        claim_three = claim.Claim({
            'bene_sk': '2001',
            'clm_ptnt_birth_dt': date(1940, 1, 1),
            'clm_from_dt': date(2017, 1, 1),
            'claim_lines': [
                {'clm_line_hcpcs_cd': 'pd_exl_code'},
                {'clm_line_hcpcs_cd': 'enc_code'}
            ]})
        claim_four = claim.Claim({
            'bene_sk': '3001',
            'clm_ptnt_birth_dt': date(1940, 1, 1),
            'clm_from_dt': date(2017, 1, 1),
            'claim_lines': [
                {'clm_line_hcpcs_cd': 'irrelevant_code'},
            ]})
        claim_five = claim.Claim({
            'bene_sk': '3001',
            'clm_ptnt_birth_dt': date(1940, 1, 1),
            'clm_from_dt': date(2017, 1, 1),
            'claim_lines': [
                {'clm_line_hcpcs_cd': 'enc_code'},
            ]})
        claim_six = claim.Claim({
            'bene_sk': '4001',
            'clm_ptnt_birth_dt': date(1940, 1, 1),
            'clm_from_dt': date(2017, 1, 1),
            'claim_lines': [
                {'clm_line_hcpcs_cd': 'pd_exe_code'},
                {'clm_line_hcpcs_cd': 'enc_code'}
            ]})

        claims = [claim_one, claim_two, claim_three, claim_four, claim_five, claim_six]

        output = measure.execute(claims)

        expected = {
            'eligible_population_exclusion': 1,
            'eligible_population_exception': 1,
            'performance_met': 1,
            'performance_not_met': 0,
            'eligible_population': 4
        }

        assert output == expected
