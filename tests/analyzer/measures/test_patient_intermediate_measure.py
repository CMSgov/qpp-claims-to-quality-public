"""Tests for PatientIntermediateMeasure Class methods."""
import datetime

from claims_to_quality.analyzer.calculation.patient_intermediate_measure import (
    PatientIntermediateMeasure)
from claims_to_quality.analyzer.models import claim
from claims_to_quality.analyzer.models.measures.eligibility_option import EligibilityOption
from claims_to_quality.analyzer.models.measures.measure_code import MeasureCode
from claims_to_quality.analyzer.models.measures.measure_definition import MeasureDefinition
from claims_to_quality.analyzer.models.measures.performance_option import PerformanceOption


def test_get_claims_from_latest_date():
    """Test get_most_recent_claim method."""
    oldest_claim = claim.Claim({'clm_from_dt': datetime.date(2017, 1, 1)})
    newest_claim = claim.Claim({'clm_from_dt': datetime.date(2017, 2, 1)})
    claims = [oldest_claim, newest_claim]

    output = PatientIntermediateMeasure.get_claims_from_latest_date(claims)
    expected = [newest_claim]
    assert output == expected


def test_get_most_recent_claim_same_date():
    """Test get_most_recent_claim in the case that two claims have the same date."""
    claim_a = claim.Claim({
        'splt_clm_id': 'most_advantageous',
        'clm_from_dt': datetime.date(2017, 1, 1)
    })
    claim_b = claim.Claim({
        'splt_clm_id': 'least_advantageous',
        'clm_from_dt': datetime.date(2017, 1, 1)
    })

    output = PatientIntermediateMeasure.get_claims_from_latest_date([claim_a, claim_b])
    expected = [claim_a, claim_b]
    assert output == expected


def test_get_claims_from_latest_date_on_empty_list():
    """Test get_most_recent_claim method returns empty list when given an empty list."""
    claims = []
    output = PatientIntermediateMeasure.get_claims_from_latest_date(claims)
    expected = []
    assert output == expected


def test_get_eligible_instances():
    """
    Test that get_eligible_instances correctly groups and filters claims.

    For PatientIntermediate measures, claims should be grouped by beneficiary ID and filtered
    by most recent claims with QDCs when possible. If no claims for a beneficiary have QDCs,
    filter to the most recent claim.
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
        })
    ]

    measure = PatientIntermediateMeasure(
        measure_definition=MeasureDefinition({
            'eligibility_options': eligibility_options,
            'performance_options': performance_options
        })
    )

    claim_one = claim.Claim({
        'bene_sk': '1001',
        'clm_ptnt_birth_dt': datetime.date(1940, 1, 1),
        'clm_from_dt': datetime.date(2016, 12, 30),
        'claim_lines': [
            {'clm_line_hcpcs_cd': 'pn_code'},
            {'clm_line_hcpcs_cd': 'enc_code'}
        ]})
    claim_two = claim.Claim({
        'bene_sk': '1001',
        'clm_ptnt_birth_dt': datetime.date(1940, 1, 1),
        'clm_from_dt': datetime.date(2017, 1, 1),
        'claim_lines': [
            {'clm_line_hcpcs_cd': 'pn_x_code'},
            {'clm_line_hcpcs_cd': 'enc_code'}
        ]})
    claim_three = claim.Claim({
        'bene_sk': '2001',
        'clm_ptnt_birth_dt': datetime.date(1940, 1, 1),
        'clm_from_dt': datetime.date(2017, 1, 1),
        'claim_lines': [
            {'clm_line_hcpcs_cd': 'pd_exl_code'},
            {'clm_line_hcpcs_cd': 'enc_code'}
        ]})
    claim_four = claim.Claim({
        'bene_sk': '3001',
        'clm_ptnt_birth_dt': datetime.date(1940, 1, 1),
        'clm_from_dt': datetime.date(2017, 1, 1),
        'claim_lines': [
            {'clm_line_hcpcs_cd': 'irrelevant_code'},
        ]})
    claim_five = claim.Claim({
        'bene_sk': '4001',
        'clm_ptnt_birth_dt': datetime.date(1955, 1, 1),
        'clm_from_dt': datetime.date(2017, 1, 1),
        'claim_lines': [
            {'clm_line_hcpcs_cd': 'pd_exe_code'},
        ]})

    claims = [claim_one, claim_two, claim_three, claim_four, claim_five]

    output = measure.get_eligible_instances(claims)
    expected = [[claim_two], [claim_three], [claim_four], [claim_five]]

    for instance in output:
        assert instance in expected

    for instance in expected:
        assert instance in output

    assert len(output) == len(expected)
