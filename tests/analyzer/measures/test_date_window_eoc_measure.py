"""Tests for DateWindowEOCMeasure Class methods."""
import datetime

from claims_to_quality.analyzer.calculation.date_window_eoc_measure import DateWindowEOCMeasure
from claims_to_quality.analyzer.models import claim
from claims_to_quality.analyzer.models.measures.eligibility_option import EligibilityOption
from claims_to_quality.analyzer.models.measures.measure_code import MeasureCode
from claims_to_quality.analyzer.models.measures.measure_definition import MeasureDefinition
from claims_to_quality.analyzer.models.measures.performance_option import PerformanceOption


def test_get_earliest_claims():
    """Test get_most_recent_claim method."""
    oldest_claim = claim.Claim({'clm_from_dt': datetime.date(2017, 1, 1)})
    newest_claim = claim.Claim({'clm_from_dt': datetime.date(2017, 2, 1)})
    claims = [oldest_claim, newest_claim]

    output = DateWindowEOCMeasure.get_claims_from_earliest_date(claims)
    expected = [oldest_claim]
    assert output == expected


def test_get_earliest_claims_same_date():
    """Test get_most_recent_claim in the case that two claims have the same date."""
    claim_a = claim.Claim({
        'splt_clm_id': 'most_advantageous',
        'clm_from_dt': datetime.date(2017, 1, 1)
    })
    claim_b = claim.Claim({
        'splt_clm_id': 'least_advantageous',
        'clm_from_dt': datetime.date(2017, 1, 1)
    })

    output = DateWindowEOCMeasure.get_claims_from_earliest_date([claim_a, claim_b])
    expected = [claim_a, claim_b]
    assert output == expected


def test_get_claims_from_earliest_date_on_empty_list():
    """Test get_most_recent_claim method returns empty list when given an empty list."""
    claims = []
    output = DateWindowEOCMeasure.get_claims_from_earliest_date(claims)
    expected = []
    assert output == expected


def test_group_claims_by_date():
    """Test that group_claims_by_date groups claims into episodes correctly."""
    measure = DateWindowEOCMeasure(
        measure_definition=MeasureDefinition({
            'eligibility_options': [],
            'performance_options': []
        })
    )

    a1 = claim.Claim({'clm_from_dt': datetime.date(2016, 1, 1)})
    a2 = claim.Claim({'clm_from_dt': datetime.date(2016, 1, 10)})
    b1 = claim.Claim({'clm_from_dt': datetime.date(2016, 6, 1)})
    b2 = claim.Claim({'clm_from_dt': datetime.date(2016, 6, 10)})
    c1 = claim.Claim({'clm_from_dt': datetime.date(2016, 12, 1)})

    claims = [a1, b1, a2, b2, c1]

    output = measure.group_claims_by_date(claims)
    expected = [[a1, a2], [b1, b2], [c1]]

    assert output == expected


def test_group_claims_by_date_returns_empty_list():
    """Test that group_claims_by_date returns an empty list of episodes when given no claims."""
    measure = DateWindowEOCMeasure(
        measure_definition=MeasureDefinition({
            'eligibility_options': [],
            'performance_options': []
        })
    )

    claims = []
    output = measure.group_claims_by_date(claims)
    expected = []

    assert output == expected


def test_get_eligible_instances():
    """
    Test that get_eligible_instances correctly groups and filters claims.

    For these measures, claims should be grouped by beneficiary ID and then grouped
    further into episodes by date range. Each episode is filtered further to the earliest
    claims with QDCs. If no claims for a beneficiary have QDCs, filter to the .
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
            'optionType': 'performanceExclusion',
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

    measure = DateWindowEOCMeasure(
        measure_definition=MeasureDefinition({
            'eligibility_options': eligibility_options,
            'performance_options': performance_options
        })
    )

    claim_one = claim.Claim({
        'bene_sk': '1001',
        'clm_from_dt': datetime.date(2016, 12, 30),
        'claim_lines': [
            {'clm_line_hcpcs_cd': 'pn_code'},
            {'clm_line_hcpcs_cd': 'enc_code'}
        ]})
    claim_two = claim.Claim({
        'bene_sk': '1001',
        'clm_from_dt': datetime.date(2017, 1, 1),
        'claim_lines': [
            {'clm_line_hcpcs_cd': 'pn_x_code'},
            {'clm_line_hcpcs_cd': 'enc_code'}
        ]})
    claim_three = claim.Claim({
        'bene_sk': '2001',
        'clm_from_dt': datetime.date(2017, 1, 1),
        'claim_lines': [
            {'clm_line_hcpcs_cd': 'pd_x_code'},
            {'clm_line_hcpcs_cd': 'enc_code'}
        ]})
    claim_four = claim.Claim({
        'bene_sk': '3001',
        'clm_from_dt': datetime.date(2017, 1, 1),
        'claim_lines': [
            {'clm_line_hcpcs_cd': 'irrelevant_code'},
        ]})

    claims = [claim_one, claim_two, claim_three, claim_four]

    output = measure.get_eligible_instances(claims)
    expected = [[claim_one], [claim_three], [claim_four]]

    for instance in output:
        assert instance in expected

    for instance in expected:
        assert instance in output

    assert len(output) == len(expected)
