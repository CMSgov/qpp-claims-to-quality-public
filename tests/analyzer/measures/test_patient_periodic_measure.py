"""Tests for methods of the PatientPeriodMeasure class."""
import datetime

from claims_to_quality.analyzer.calculation.patient_periodic_measure import PatientPeriodicMeasure
from claims_to_quality.analyzer.models import claim
from claims_to_quality.analyzer.models.measures.eligibility_option import EligibilityOption
from claims_to_quality.analyzer.models.measures.measure_code import MeasureCode
from claims_to_quality.analyzer.models.measures.measure_definition import MeasureDefinition
from claims_to_quality.analyzer.models.measures.performance_option import PerformanceOption
from claims_to_quality.lib.helpers import mocking_config

import mock


def test_get_flu_season_from_start_and_end_dates_single_year_multiple_years():
    """Test that get_date_ranges works as expected with multiple years."""
    date_ranges = PatientPeriodicMeasure._get_flu_season_from_start_and_end_dates(
        start_date=datetime.date(2017, 1, 1),
        end_date=datetime.date(2019, 7, 20)
    )

    assert date_ranges == [
        (datetime.date(2017, 1, 1), datetime.date(2017, 3, 31)),
        (datetime.date(2017, 10, 1), datetime.date(2017, 12, 31)),
        (datetime.date(2018, 1, 1), datetime.date(2018, 3, 31)),
        (datetime.date(2018, 10, 1), datetime.date(2018, 12, 31)),
        (datetime.date(2019, 1, 1), datetime.date(2019, 3, 31)),
        (datetime.date(2019, 10, 1), datetime.date(2019, 12, 31)),
    ]


def test_get_flu_season_from_start_and_end_dates_single_year():
    """Test that get_date_ranges works as expected with no overlap."""
    date_ranges = PatientPeriodicMeasure._get_flu_season_from_start_and_end_dates(
        start_date=datetime.date(2017, 1, 1),
        end_date=datetime.date(2017, 12, 31)
    )

    assert date_ranges == [
        (datetime.date(2017, 1, 1), datetime.date(2017, 3, 31)),
        (datetime.date(2017, 10, 1), datetime.date(2017, 12, 31)),
    ]


def test_select_date_ranges_claim_belongs_to():
    """Test that _select_date_ranges_claim_belongs_to returns the correct indexes."""
    date_ranges = [
        (datetime.date(2017, 1, 1), datetime.date(2017, 3, 31)),
        (datetime.date(2017, 10, 1), datetime.date(2017, 12, 31))
    ]

    claim_none = claim.Claim({
        'bene_sk': '1001',
        'clm_from_dt': datetime.date(2017, 4, 1),
        'clm_thru_dt': datetime.date(2017, 4, 1),
    })
    claim_first_only = claim.Claim({
        'bene_sk': '1001',
        'clm_from_dt': datetime.date(2017, 1, 1),
        'clm_thru_dt': datetime.date(2017, 1, 1),
    })
    claim_second_only = claim.Claim({
        'bene_sk': '2001',
        'clm_from_dt': datetime.date(2017, 12, 31),
        'clm_thru_dt': datetime.date(2017, 12, 31),
    })
    claim_both = claim.Claim({
        'bene_sk': '1001',
        'clm_from_dt': datetime.date(2017, 1, 1),
        'clm_thru_dt': datetime.date(2017, 12, 31),
    })

    assert PatientPeriodicMeasure._select_date_ranges_claim_belongs_to(
        claim_none, date_ranges) == []
    assert PatientPeriodicMeasure._select_date_ranges_claim_belongs_to(
        claim_first_only, date_ranges) == [0]
    assert PatientPeriodicMeasure._select_date_ranges_claim_belongs_to(
        claim_second_only, date_ranges) == [1]
    assert PatientPeriodicMeasure._select_date_ranges_claim_belongs_to(
        claim_both, date_ranges) == [0, 1]


@mock.patch('claims_to_quality.analyzer.calculation.patient_periodic_measure.config')
def test_get_eligible_instances(mock_config):
    """
    Test that get_eligible_instances correctly groups and filters claims.

    For these measures, claims should be grouped by beneficiary ID and then grouped
    further into eligible instances according to the provided date ranges.
    """
    mock_config.get.side_effect = mocking_config.config_measures_year(2018)
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
    ]

    eligibility_options = [
        EligibilityOption({
            'procedureCodes': [MeasureCode({'code': 'enc_code'})]
        })
    ]

    measure = PatientPeriodicMeasure(
        measure_definition=MeasureDefinition({
            'measure_number': '110',
            'eligibility_options': eligibility_options,
            'performance_options': performance_options
        })
    )

    claims = [
        claim.Claim({
            'bene_sk': '1001',
            'clm_from_dt': datetime.date(2018, 1, 1),
            'clm_thru_dt': datetime.date(2018, 1, 1),
        }),
        claim.Claim({
            'bene_sk': '1001',
            'clm_from_dt': datetime.date(2018, 12, 1),
            'clm_thru_dt': datetime.date(2018, 12, 1),
        }),
        claim.Claim({
            'bene_sk': '2001',
            'clm_from_dt': datetime.date(2018, 11, 1),
            'clm_thru_dt': datetime.date(2018, 11, 1),
        }),
        claim.Claim({
            'bene_sk': '2001',
            'clm_from_dt': datetime.date(2018, 4, 1),
            'clm_thru_dt': datetime.date(2018, 4, 1),
        }),
        claim.Claim({
            'bene_sk': '2001',
            'clm_from_dt': datetime.date(2018, 12, 1),
            'clm_thru_dt': datetime.date(2018, 12, 1),
        })
    ]

    output = measure.get_eligible_instances(claims)
    expected = [
        [claims[0]],
        [claims[1]],
        [claims[2], claims[4]]
    ]

    for instance in output:
        assert instance in expected

    for instance in expected:
        assert instance in output

    assert len(output) == len(expected)
