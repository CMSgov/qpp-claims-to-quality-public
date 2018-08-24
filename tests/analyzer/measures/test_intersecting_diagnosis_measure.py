"""Tests for IntersectingDiagnosisMeasure Class methods."""
from claims_to_quality.analyzer.calculation.intersecting_diagnosis_measure import (
    IntersectingDiagnosisMeasure)
from claims_to_quality.analyzer.models import claim
from claims_to_quality.analyzer.models.measures.eligibility_option import EligibilityOption
from claims_to_quality.analyzer.models.measures.measure_definition import MeasureDefinition


class TestGroupClaimsByCommonDiagnosis():
    """Test that regrouping claims by diagnosis codes works as expected."""

    def setup(self):
        """Instantiate a measure for each of the tests."""
        eligibility_options = [
            EligibilityOption({
                'diagnosisCodes': ['dx_code_a', 'dx_code_b']
            })
        ]

        self.measure = IntersectingDiagnosisMeasure(
            measure_definition=MeasureDefinition({
                'eligibility_options': eligibility_options,
                'performance_options': []
            })
        )

    def test_group_claims_groups_claims_correctly(self):
        """The _regroup method should group claims with common diagnosis codes."""
        claim_one = claim.Claim({'dx_codes': ['dx_code_a']})
        claim_two = claim.Claim({'dx_codes': ['dx_code_a', 'dx_code_b']})
        claim_three = claim.Claim({'dx_codes': ['dx_code_b']})

        claims = [claim_one, claim_two, claim_three]
        output = list(self.measure.group_claims_by_common_diagnosis(claims))
        expected = [[claim_one, claim_two, claim_three]]

        assert output == expected

    def test_group_claims_splits_claims_correctly(self):
        """The _regroup method shouldn't group claims with diagnosis codes in common."""
        claim_one = claim.Claim({'dx_codes': ['dx_code_a']})
        claim_two = claim.Claim({'dx_codes': ['dx_code_b']})

        claims = [claim_one, claim_two]

        output = list(self.measure.group_claims_by_common_diagnosis(claims))
        expected = [[claim_one], [claim_two]]
        assert output == expected


def test_get_eligible_instances():
    """Test that get_eligible_instances groups by diagnosis code and beneficiary."""
    eligibility_options = [
        EligibilityOption({
            'diagnosisCodes': ['dx_code_a', 'dx_code_b'],
        }),
        EligibilityOption({
            'diagnosisCodes': ['dx_code_c'],
        })
    ]

    measure = IntersectingDiagnosisMeasure(
        measure_definition=MeasureDefinition({
            'eligibility_options': eligibility_options,
            'performance_options': []
        })
    )

    claim_one = claim.Claim({
        'dx_codes': ['dx_code_a'],
        'bene_sk': 1001,
    })
    claim_two = claim.Claim({
        'dx_codes': ['dx_code_a', 'dx_code_b'],
        'bene_sk': 1001,
    })
    claim_three = claim.Claim({
        'dx_codes': ['dx_code_c'],
        'bene_sk': 1001,
    })
    claim_four = claim.Claim({
        'dx_codes': ['dx_code_a'],
        'bene_sk': 2001,
    })

    claims = [claim_one, claim_two, claim_three, claim_four]
    output = measure.get_eligible_instances(claims)
    expected = [[claim_one, claim_two], [claim_three], [claim_four]]

    for instance in output:
        assert instance in expected

    for instance in expected:
        assert instance in output

    assert len(output) == len(expected)
