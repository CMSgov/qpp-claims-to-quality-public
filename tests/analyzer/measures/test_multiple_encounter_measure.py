"""Tests methods within multiple_encounter_measure.py."""
import datetime

from claims_to_quality.analyzer.calculation.multiple_encounter_measure import (
    MultipleEncounterMeasure
)
from claims_to_quality.analyzer.models import claim
from claims_to_quality.analyzer.models.measures.measure_definition import MeasureDefinition


def test_filter_instances_by_multiple_encounters_one_encounter():
    """
    Test that instances with insufficiently many encounters are not returned.

    If two claims occur on the same date of service, they should count as the same encounter.
    """
    bene_1_claim_1 = claim.Claim({
        'bene_sk': 'bene_1',
        'clm_from_dt': datetime.date(2017, 1, 1),
    })
    bene_4_claim_1 = claim.Claim({
        'bene_sk': 'bene_4',
        'clm_from_dt': datetime.date(2017, 1, 1),
    })
    bene_4_claim_2 = claim.Claim({
        'bene_sk': 'bene_4',
        'clm_from_dt': datetime.date(2017, 1, 1),
    })

    instances = [
        [bene_1_claim_1],
        [bene_4_claim_1, bene_4_claim_2],
    ]

    expected = []
    output = MultipleEncounterMeasure._filter_instances_by_multiple_encounters(
        instances=instances,
        minimum_number_of_encounters=2
    )
    assert output == expected


def test_filter_instances_by_multiple_encounters():
    """Test that instances with enough encounters are returned (without the initial encounter)."""
    bene_2_claim_1 = claim.Claim({
        'bene_sk': 'bene_2',
        'clm_from_dt': datetime.date(2017, 1, 1),
    })
    bene_2_claim_2 = claim.Claim({
        'bene_sk': 'bene_2',
        'clm_from_dt': datetime.date(2017, 6, 1),
    })
    bene_3_claim_1 = claim.Claim({
        'bene_sk': 'bene_3',
        'clm_from_dt': datetime.date(2017, 1, 1),
    })
    bene_3_claim_2 = claim.Claim({
        'bene_sk': 'bene_3',
        'clm_from_dt': datetime.date(2017, 3, 1),
    })
    bene_3_claim_3 = claim.Claim({
        'bene_sk': 'bene_3',
        'clm_from_dt': datetime.date(2017, 12, 1),
    })

    instances = [
        [bene_2_claim_1] * 2 + [bene_2_claim_2],
        [bene_3_claim_1, bene_3_claim_2, bene_3_claim_3],
    ]

    expected = [[bene_2_claim_2], [bene_3_claim_2, bene_3_claim_3]]
    output = MultipleEncounterMeasure._filter_instances_by_multiple_encounters(
        instances=instances,
        minimum_number_of_encounters=2
    )
    assert output == expected


def test_get_eligible_instances():
    """Test that get eligible instances only returns instances with enough encounters."""
    bene_1_claim_1 = claim.Claim({
        'bene_sk': 'bene_1',
        'clm_from_dt': datetime.date(2017, 1, 1),
    })
    bene_2_claim_1 = claim.Claim({
        'bene_sk': 'bene_2',
        'clm_from_dt': datetime.date(2017, 1, 1),
    })
    bene_2_claim_2 = claim.Claim({
        'bene_sk': 'bene_2',
        'clm_from_dt': datetime.date(2017, 6, 1),
    })
    bene_3_claim_1 = claim.Claim({
        'bene_sk': 'bene_3',
        'clm_from_dt': datetime.date(2017, 1, 1),
    })
    bene_3_claim_2 = claim.Claim({
        'bene_sk': 'bene_3',
        'clm_from_dt': datetime.date(2017, 3, 1),
    })
    bene_3_claim_3 = claim.Claim({
        'bene_sk': 'bene_3',
        'clm_from_dt': datetime.date(2017, 12, 1),
    })
    bene_4_claim_1 = claim.Claim({
        'bene_sk': 'bene_4',
        'clm_from_dt': datetime.date(2017, 1, 1),
    })
    bene_4_claim_2 = claim.Claim({
        'bene_sk': 'bene_4',
        'clm_from_dt': datetime.date(2017, 1, 1),
    })

    claims = [
        bene_1_claim_1,
        bene_2_claim_1,
        bene_2_claim_2,
        bene_3_claim_1,
        bene_3_claim_2,
        bene_3_claim_3,
        bene_4_claim_1,
        bene_4_claim_2,
    ]

    measure = MultipleEncounterMeasure(
        measure_definition=MeasureDefinition({
            'eligibility_options': [],
            'performance_options': []
        })
    )

    output = measure.get_eligible_instances(claims)
    expected = [[bene_2_claim_2], [bene_3_claim_2, bene_3_claim_3]]
    assert output == expected
