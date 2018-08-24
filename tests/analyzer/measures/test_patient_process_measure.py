"""Tests for methods of PatientProcessMeasure class."""
from claims_to_quality.analyzer.calculation.patient_process_measure import PatientProcessMeasure
from claims_to_quality.analyzer.models import claim, claim_line
from claims_to_quality.analyzer.models.measures.eligibility_option import EligibilityOption
from claims_to_quality.analyzer.models.measures.measure_code import MeasureCode
from claims_to_quality.analyzer.models.measures.measure_definition import MeasureDefinition
from claims_to_quality.analyzer.models.measures.performance_option import PerformanceOption


def test_execute():
    """
    Test for execute method.

    Note that some patient process measures have multiple eligibility options.
    """
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
        }),
        EligibilityOption({
            'procedureCodes': [MeasureCode({'code': 'other_enc_code'})]
        })
    ]

    measure = PatientProcessMeasure(
        measure_definition=MeasureDefinition({
            'eligibility_options': eligibility_options,
            'performance_options': performance_options
        })
    )

    best_line = claim_line.ClaimLine({'clm_line_hcpcs_cd': 'pn_code'})
    second_best_line = claim_line.ClaimLine({'clm_line_hcpcs_cd': 'pd_exl_code'})
    worst_claim_line = claim_line.ClaimLine({'clm_line_hcpcs_cd': 'pn_x_code'})
    enc_line = claim_line.ClaimLine({'clm_line_hcpcs_cd': 'enc_code'})
    exception_line = claim_line.ClaimLine({'clm_line_hcpcs_cd': 'pd_exe_code'})
    other_enc_line = claim_line.ClaimLine({'clm_line_hcpcs_cd': 'other_enc_code'})

    claim_best_a = claim.Claim({'bene_sk': 'a', 'claim_lines': [second_best_line, enc_line]})
    claim_worst_a = claim.Claim({'bene_sk': 'a', 'claim_lines': [worst_claim_line, enc_line]})
    claim_best_b = claim.Claim({'bene_sk': 'b', 'claim_lines': [worst_claim_line, enc_line]})
    claim_best_c = claim.Claim({'bene_sk': 'c', 'claim_lines': [best_line, enc_line]})
    claim_worst_c = claim.Claim({'bene_sk': 'c', 'claim_lines': [second_best_line, enc_line]})
    claim_best_d = claim.Claim({'bene_sk': 'd', 'claim_lines': [exception_line, enc_line]})
    claim_irrelevant_e = claim.Claim({'bene_sk': 'e', 'claim_lines': [best_line]})
    claim_best_f = claim.Claim({'bene_sk': 'f', 'claim_lines': [best_line, other_enc_line]})

    claims = [
        claim_best_a, claim_worst_a, claim_best_b, claim_best_c, claim_worst_c, claim_best_d,
        claim_irrelevant_e, claim_best_f
    ]

    output = measure.execute(claims)

    expected = {
        'eligible_population_exclusion': 1,
        'eligible_population_exception': 1,
        'performance_met': 2,
        'performance_not_met': 1,
        'eligible_population': 5
    }

    assert output == expected
