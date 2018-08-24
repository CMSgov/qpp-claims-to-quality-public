"""Test methods within qpp_measure."""
import collections
import datetime

from claims_to_quality.analyzer.calculation import qpp_measure
from claims_to_quality.analyzer.models import claim
from claims_to_quality.analyzer.models.measures.eligibility_option import EligibilityOption
from claims_to_quality.analyzer.models.measures.measure_code import MeasureCode
from claims_to_quality.analyzer.models.measures.measure_definition import MeasureDefinition
from claims_to_quality.analyzer.models.measures.performance_option import PerformanceOption

import pytest


class TestFilterByEligibilityCriteria():
    """Tests for the function filter_by_eligibility_criteria."""

    def setup(self):
        """Setup base measure object for these tests."""
        plain_measure_code = {
            'code': 'good_code',
        }

        other_measure_code = {
            'code': 'other_good_code',
        }

        self.plain_eligibility_option = EligibilityOption({
            'procedureCodes': [plain_measure_code]
        })

        self.eligibility_option_with_place_of_service = EligibilityOption({
            'procedureCodes': [MeasureCode({'code': 'good_code', 'placesOfService': [23]})]
        })

        self.eligibility_option_with_dx_codes = EligibilityOption({
            'diagnosisCodes': ['dx_code'],
            'diagnosisExclusionCodes': ['dx_code_x'],
            'procedureCodes': [plain_measure_code]
        })

        self.eligibility_option_with_additional_dx_codes = EligibilityOption({
            'diagnosisCodes': ['dx_code_1'],
            'additionalDiagnosisCodes': ['dx_code_2'],
            'procedureCodes': [plain_measure_code]
        })

        self.eligibility_option_other_code = EligibilityOption({
            'procedureCodes': [other_measure_code]
        })

    def test_procedure_code_match(self):
        """Check that only claims that have the desired encounter code are returned."""
        measure = qpp_measure.QPPMeasure(
            measure_definition=MeasureDefinition({
                'eligibility_options': [self.plain_eligibility_option],
                'performance_options': []
            })
        )
        claim_with_good_code = claim.Claim({'claim_lines': [{'clm_line_hcpcs_cd': 'good_code'}]})
        claim_with_bad_code = claim.Claim(
            {'claim_lines': [{'clm_line_hcpcs_cd': 'bad_code'}]}
        )
        other_claim_with_good_code = claim.Claim(
            {'claim_lines': [
                {'clm_line_hcpcs_cd': 'good_code'},
                {'clm_line_hcpcs_cd': 'bad_code'}
            ]}
        )

        test_claims = [claim_with_good_code, claim_with_bad_code, other_claim_with_good_code]

        output = measure.filter_by_eligibility_criteria(test_claims)
        assert output == [claim_with_good_code, other_claim_with_good_code]

    def test_procedure_code_not_match(self):
        """Check that claims that do not have the desired encounter code are not returned."""
        measure = qpp_measure.QPPMeasure(
            measure_definition=MeasureDefinition({
                'eligibility_options': [self.plain_eligibility_option],
                'performance_options': []
            })
        )

        test_claims = [claim.Claim({'claim_lines': [{'clm_line_hcpcs_cd': 'other_code'}]})]
        output = measure.filter_by_eligibility_criteria(test_claims)
        assert output == []

    def test_pos_match(self):
        """Check that only claims that have the desired encounter code and pos are returned."""
        measure = qpp_measure.QPPMeasure(
            measure_definition=MeasureDefinition({
                'eligibility_options': [self.eligibility_option_with_place_of_service],
                'performance_options': []
            })
        )

        test_claims = [claim.Claim({
            'claim_lines': [
                {
                    'clm_line_hcpcs_cd': 'good_code',
                    'clm_pos_code': 23
                }
            ]
        })]
        output = measure.filter_by_eligibility_criteria(test_claims)
        assert output == test_claims

    def test_pos_not_match(self):
        """Check that claim lines that do not have the require place of service are not returned."""
        measure = qpp_measure.QPPMeasure(
            measure_definition=MeasureDefinition({
                'eligibility_options': [self.eligibility_option_with_place_of_service],
                'performance_options': []
            })
        )

        test_claims = [claim.Claim({'claim_lines': [{'clm_line_hcpcs_cd': 'good_code'}]})]
        output = measure.filter_by_eligibility_criteria(test_claims)
        assert output == []

    def test_dx_code_match(self):
        """Check the case where the measure and claim have the same dx_code."""
        measure = qpp_measure.QPPMeasure(
            measure_definition=MeasureDefinition({
                'eligibility_options': [self.eligibility_option_with_dx_codes],
                'performance_options': []
            })
        )

        test_claim = claim.Claim({
            'dx_codes': ['dx_code'], 'claim_lines': [{'clm_line_hcpcs_cd': 'good_code'}]})

        output = measure.filter_by_eligibility_criteria([test_claim])
        assert output == [test_claim]

    def test_dx_code_not_match(self):
        """Check the case where the claim does not have the required dx_code."""
        measure = qpp_measure.QPPMeasure(
            measure_definition=MeasureDefinition({
                'eligibility_options': [self.eligibility_option_with_dx_codes],
                'performance_options': []
            })
        )

        test_claim = claim.Claim({
            'dx_codes': ['wrong_code'], 'claim_lines': [{'clm_line_hcpcs_cd': 'good_code'}]})

        output = measure.filter_by_eligibility_criteria([test_claim])
        assert output == []

    def test_dx_code_x_match(self):
        """Check the case where the measure has a dx_code_x and the claim doesn't have it."""
        measure = qpp_measure.QPPMeasure(
            measure_definition=MeasureDefinition({
                'eligibility_options': [self.eligibility_option_with_dx_codes],
                'performance_options': []
            })
        )

        test_claim = claim.Claim({
            'dx_codes': ['dx_code'], 'claim_lines': [{'clm_line_hcpcs_cd': 'good_code'}]})

        output = measure.filter_by_eligibility_criteria([test_claim])
        assert output == [test_claim]

    def test_dx_code_x_not_match_and_dx_code_match(self):
        """Check the case where the measure has a dx_code_x and the claim does have it."""
        measure = qpp_measure.QPPMeasure(
            measure_definition=MeasureDefinition({
                'eligibility_options': [self.eligibility_option_with_dx_codes],
                'performance_options': []
            })
        )

        test_claim = claim.Claim({
            'dx_codes': ['dx_code', 'dx_code_x'],
            'claim_lines': [{'clm_line_hcpcs_cd': 'good_code'}]
        })

        output = measure.filter_by_eligibility_criteria([test_claim])
        assert output == []

    def test_additional_dx_code_match(self):
        """Check the case where a measure has an additional diag code and the claim has it also."""
        measure = qpp_measure.QPPMeasure(
            measure_definition=MeasureDefinition({
                'eligibility_options': [self.eligibility_option_with_additional_dx_codes],
                'performance_options': []
            })
        )

        test_claim = claim.Claim({
            'dx_codes': ['dx_code_1', 'dx_code_2'], 'claim_lines':
                [{'clm_line_hcpcs_cd': 'good_code'}]
        })

        output = measure.filter_by_eligibility_criteria([test_claim])

        assert output == [test_claim]

    def test_additional_dx_code_no_match(self):
        """Check the case where a measure has an additional diag code and the claim lacks it."""
        measure = qpp_measure.QPPMeasure(
            measure_definition=MeasureDefinition({
                'eligibility_options': [self.eligibility_option_with_additional_dx_codes],
                'performance_options': []
            })
        )

        test_claim = claim.Claim({
            'dx_codes': ['dx_code_1'], 'claim_lines': [{'clm_line_hcpcs_cd': 'good_code'}]})

        output = measure.filter_by_eligibility_criteria([test_claim])
        assert output == []

    def test_additional_dx_code_no_prerequisites(self):
        """Check the case where a claim lacks a required dx_code, but has additional ones."""
        measure = qpp_measure.QPPMeasure(
            measure_definition=MeasureDefinition({
                'eligibility_options': [self.eligibility_option_with_additional_dx_codes],
                'performance_options': []
            })
        )

        test_claim = claim.Claim({
            'dx_codes': ['dx_code_2'], 'claim_lines': [{'clm_line_hcpcs_cd': 'good_code'}]})

        output = measure.filter_by_eligibility_criteria([test_claim])
        assert output == []


class TestGetMostAdvantageous():
    """Test the methods associated with getting the most advantageous code."""

    def setup(self):
        """Setup base measure object for these tests."""
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

        self.measure = qpp_measure.QPPMeasure(
            measure_definition=MeasureDefinition({
                'eligibility_options': [],
                'performance_options': performance_options
            })
        )

        self.inverse_measure = qpp_measure.QPPMeasure(
            measure_definition=MeasureDefinition({
                'eligibility_options': [],
                'performance_options': performance_options,
                'is_inverse': True
            })
        )

    def test_assign_performance_markers(self):
        """Test that assigning performance markers to a single claim works as intended."""
        performance_options = [
            PerformanceOption({
                'optionType': 'performanceMet',
                'qualityCodes': [
                    {
                        'code': 'code_a',
                        'placesOfService': ['AA'],
                        'placesOfServiceExclusions': ['GQ']
                    }
                ]
            }),
            PerformanceOption({
                'optionType': 'performanceNotMet',
                'qualityCodes': [
                    {'code': 'code_a'}
                ]
            })
        ]

        measure = qpp_measure.QPPMeasure(
            measure_definition=MeasureDefinition({
                'eligibility_options': [],
                'performance_options': performance_options
            })
        )

        claim_lines = [{
            'clm_line_hcpcs_cd': 'code_a',
            'mdfr_cds': [],
            'clm_pos_code': ''
        }]
        test_claim = claim.Claim({'claim_lines': claim_lines})

        output = measure._assign_performance_markers(test_claim)
        expected = set(['performanceNotMet'])

        assert output == expected

    def test_assign_performance_markers_multiple_code_sets(self):
        """
        Test assign_performance_markers in the case of >1 quality code per performance option.

        Verify that marker is assigned if both codes are present in claim lines.
        """
        performance_options = [
            PerformanceOption({
                'optionType': 'performanceMet',
                'qualityCodes': [
                    {'code': 'code_a'},
                    {'code': 'code_b'}
                ]
            })
        ]

        measure = qpp_measure.QPPMeasure(
            measure_definition=MeasureDefinition({
                'eligibility_options': [],
                'performance_options': performance_options
            })
        )

        claim_lines = [
            {
                'clm_line_hcpcs_cd': 'code_a',
                'mdfr_cds': [],
                'clm_pos_code': ''
            },
            {
                'clm_line_hcpcs_cd': 'code_b',
                'mdfr_cds': [],
                'clm_pos_code': ''
            }
        ]
        test_claim = claim.Claim({'claim_lines': claim_lines})

        output = measure._assign_performance_markers(test_claim)
        expected = set(['performanceMet'])

        assert output == expected

    def test_assign_performance_markers_multiple_code_sets_fails(self):
        """
        Test assign_performance_markers in the case of >1 quality code per performance option.

        Verify that marker is not assigned if not all required quality codes are present.
        """
        performance_options = [
            PerformanceOption({
                'optionType': 'performanceMet',
                'qualityCodes': [
                    {'code': 'code_a'},
                    {'code': 'code_b'}
                ]
            })
        ]

        measure = qpp_measure.QPPMeasure(
            measure_definition=MeasureDefinition({
                'eligibility_options': [],
                'performance_options': performance_options
            })
        )

        claim_lines = [
            {
                'clm_line_hcpcs_cd': 'code_a',
                'mdfr_cds': [],
                'clm_pos_code': ''
            },
            {
                'clm_line_hcpcs_cd': 'code_c',
                'mdfr_cds': [],
                'clm_pos_code': ''
            }
        ]
        test_claim = claim.Claim({'claim_lines': claim_lines})

        output = measure._assign_performance_markers(test_claim)
        expected = set()

        assert output == expected

    def test_get_most_advantageous_claim(self):
        """Test of get_most_advantageous_claim."""
        best_claim = claim.Claim({'claim_lines': [{'clm_line_hcpcs_cd': 'pn_code'}]})
        other_claim = claim.Claim({'claim_lines': [{'clm_line_hcpcs_cd': 'pn_x_code'}]})
        test_claims = [best_claim, other_claim]

        output = self.measure.get_most_advantageous_claim(test_claims)

        expected = (best_claim, 'performanceMet')
        assert output == expected

    def test_get_most_advantageous_claim_no_performance(self):
        """Test of get_most_advantageous_claim if it's None."""
        claim_a = claim.Claim({'claim_lines': [{'clm_line_hcpcs_cd': 'not_a_quality_code_a'}]})
        claim_b = claim.Claim({'claim_lines': [{'clm_line_hcpcs_cd': 'not_a_quality_code_b'}]})
        test_claims = [claim_a, claim_b]

        output = self.measure.get_most_advantageous_claim(test_claims)

        expected = (claim_a, None)
        # If no claim with a quality code exists, the function should just return the first claim.
        assert output == expected

    def test_get_most_advantageous_claim_inverse_measure(self):
        """Test of get_most_advantageous_claim with an inverse measure."""
        worst_claim = claim.Claim({'claim_lines': [{'clm_line_hcpcs_cd': 'pn_code'}]})
        okay_claim = claim.Claim({'claim_lines': [{'clm_line_hcpcs_cd': 'pd_x_code'}]})
        best_claim = claim.Claim({'claim_lines': [{'clm_line_hcpcs_cd': 'pn_x_code'}]})
        irrelevant_claim = claim.Claim({'claim_lines': [{'clm_line_hcpcs_cd': 'random_code'}]})

        test_claims = [best_claim, worst_claim, okay_claim, irrelevant_claim]
        output = self.inverse_measure.get_most_advantageous_claim(test_claims)

        expected = (best_claim, 'performanceNotMet')
        assert output == expected

    def test_get_performance_marker_ranking_inverse_measure(self):
        """Test that the hierarchy of performance markers is reversed for inverse measures."""
        output = self.inverse_measure.get_performance_marker_ranking()
        expected = {
            'performanceMet': 3,
            'eligiblePopulationExclusion': 2,
            'eligiblePopulationException': 1,
            'performanceNotMet': 0,
            None: 4
        }

        assert output == expected


def test_group_claims_by_field_values_with_single_field():
    """Test that claims with the same values are grouped together."""
    fields_to_group_by = 'bene_sk'

    claim_a = claim.Claim({'bene_sk': 'bene1'})
    claim_b = claim.Claim({'bene_sk': 'bene1'})
    claim_c = claim.Claim({'bene_sk': 'bene2'})

    claims_data = [claim_a, claim_b, claim_c]

    output = qpp_measure.QPPMeasure.group_claims_by_field_values(fields_to_group_by, claims_data)
    expected = [[claim_a, claim_b], [claim_c]]

    # output and expected should be equal, but their internal orders might differ.
    # Therefore, we check that each element of output is an element of expected (and vice versa).
    for claim_group in output:
        assert claim_group in expected
    for claim_group in expected:
        assert claim_group in output


def test_group_claims_by_field_values_with_multiple_fields():
    """Test that claims with the same values in multiple fields are grouped together."""
    fields_to_group_by = ['bene_sk', 'clm_from_dt']

    claim_a = claim.Claim({'bene_sk': 'bene1', 'clm_from_dt': '2017-04-22'})
    claim_b = claim.Claim({'bene_sk': 'bene1', 'clm_from_dt': '2017-04-21'})
    claim_c = claim.Claim({'bene_sk': 'bene2', 'clm_from_dt': '2017-04-22'})
    claim_d = claim.Claim({'bene_sk': 'bene2', 'clm_from_dt': '2017-04-22'})

    claims_data = [claim_a, claim_b, claim_c, claim_d]

    output = qpp_measure.QPPMeasure.group_claims_by_field_values(fields_to_group_by, claims_data)
    expected = [[claim_a], [claim_b], [claim_c, claim_d]]

    # output and expected should be equal, but their internal orders might differ.
    # Therefore, we check that each element of output is an element of expected (and vice versa).
    for claim_group in output:
        assert claim_group in expected
    for claim_group in expected:
        assert claim_group in output


def test_get_eligible_instances_raises_attribute_error():
    """
    Test that get_eligible_instances raises AttributeError.

    This method can only be called from subclasses of QPPMeasure that have
    the fields_to_group_by attribute.
    """
    claims = []

    measure = qpp_measure.QPPMeasure(
        measure_definition=MeasureDefinition({
            'eligibility_options': [],
            'performance_options': []
        })
    )

    with pytest.raises(AttributeError):
        measure.get_eligible_instances(claims)


def test_score_eligible_instances():
    """Test that score_eligible_instances correctly aggregates instances by performance marker."""
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

    measure = qpp_measure.QPPMeasure(
        measure_definition=MeasureDefinition({
            'eligibility_options': eligibility_options,
            'performance_options': performance_options
        })
    )

    claim_one = claim.Claim({
        'bene_sk': '1001',
        'claim_lines': [
            {'clm_line_hcpcs_cd': 'pn_code'},
            {'clm_line_hcpcs_cd': 'enc_code'}
        ]})
    claim_two = claim.Claim({
        'bene_sk': '1001',
        'claim_lines': [
            {'clm_line_hcpcs_cd': 'pn_x_code'},
            {'clm_line_hcpcs_cd': 'enc_code'}
        ]})
    claim_three = claim.Claim({
        'bene_sk': '2001',
        'claim_lines': [
            {'clm_line_hcpcs_cd': 'pd_x_code'},
            {'clm_line_hcpcs_cd': 'enc_code'}
        ]})
    claim_four = claim.Claim({
        'bene_sk': '3001',
        'claim_lines': [
            {'clm_line_hcpcs_cd': 'irrelevant_code'},
        ]})
    claim_five = claim.Claim({
        'bene_sk': '3001',
        'claim_lines': [
            {'clm_line_hcpcs_cd': 'enc_code'},
        ]})

    # For the sake of this test, assume that the claims for each beneficiary are grouped together
    # into a single eligible instance.
    eligible_instances = [[claim_one, claim_two], [claim_three], [claim_four, claim_five]]

    output = measure.score_eligible_instances(eligible_instances)

    expected = collections.defaultdict(int)
    expected['eligiblePopulationExclusion'] = 1
    expected['performanceMet'] = 1
    expected[None] = 1

    assert output == expected


def test_filter_by_presence_of_quality_codes():
    """Test filter_by_presence_of_quality_codes returns all claims with quality codes."""
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

    measure = qpp_measure.QPPMeasure(
        measure_definition=MeasureDefinition({
            'eligibility_options': [],
            'performance_options': performance_options
        })
    )

    claim_with_quality_code = claim.Claim({'claim_lines': [{'clm_line_hcpcs_cd': 'pn_code'}]})
    claim_without_quality_code = claim.Claim(
        {'claim_lines': [{'clm_line_hcpcs_cd': 'irrelevant_code'}]}
    )

    claims = [claim_with_quality_code, claim_without_quality_code]

    output = measure.filter_by_presence_of_quality_codes(claims)
    expected = [claim_with_quality_code]

    assert output == expected


def test_is_claim_in_date_range_simple_cases():
    """Test that _is_claim_in_date_range returns True when expected."""
    date_range = (
        datetime.date(2017, 6, 1),
        datetime.date(2017, 9, 1),
    )
    claim_too_early = claim.Claim({
        'clm_from_dt': datetime.date(2016, 1, 1),
        'clm_thru_dt': datetime.date(2016, 1, 1),
    })
    claim_too_late = claim.Claim({
        'clm_from_dt': datetime.date(2017, 12, 30),
        'clm_thru_dt': datetime.date(2017, 12, 30),
    })
    claim_just_right = claim.Claim({
        'clm_from_dt': datetime.date(2017, 7, 1),
        'clm_thru_dt': datetime.date(2017, 7, 1),
    })

    assert not qpp_measure.QPPMeasure._is_claim_in_date_range(claim_too_early, date_range)
    assert not qpp_measure.QPPMeasure._is_claim_in_date_range(claim_too_late, date_range)
    assert qpp_measure.QPPMeasure._is_claim_in_date_range(claim_just_right, date_range)


def test_is_claim_in_date_range_edge_cases():
    """Test that _is_claim_in_date_range returns True when the claim overlaps the date range."""
    date_range = (
        datetime.date(2017, 6, 1),
        datetime.date(2017, 9, 1),
    )
    claim_overlapping_start_date = claim.Claim({
        'clm_from_dt': datetime.date(2017, 5, 30),
        'clm_thru_dt': datetime.date(2017, 6, 1),
    })
    claim_overlapping_end_date = claim.Claim({
        'clm_from_dt': datetime.date(2017, 9, 1),
        'clm_thru_dt': datetime.date(2017, 9, 10),
    })

    assert qpp_measure.QPPMeasure._is_claim_in_date_range(claim_overlapping_start_date, date_range)
    assert qpp_measure.QPPMeasure._is_claim_in_date_range(claim_overlapping_end_date, date_range)


def test_filter_by_valid_dates_with_restrictions():
    """Test that filter by valid dates behaves correctly for measures with date restrictions."""
    measure = qpp_measure.QPPMeasure(
        measure_definition=MeasureDefinition({
            'eligibility_options': [],
            'performance_options': []
        })
    )

    measure.date_ranges = [
        (datetime.date(2017, 1, 1), datetime.date(2017, 3, 31)),
        (datetime.date(2017, 10, 1), datetime.date(2017, 12, 31))
    ]

    claims = [
        claim.Claim({
            'clm_from_dt': datetime.date(2017, month, 1),
            'clm_thru_dt': datetime.date(2017, month, 1),
        }) for month in range(1, 13)
    ]

    output = measure.filter_by_valid_dates(claims)
    expected = claims[:3] + claims[-3:]

    assert output == expected


def test_str():
    """Test that QPPMeasure objects can be represented as strings."""
    measure = qpp_measure.QPPMeasure(
        measure_definition=MeasureDefinition({
            'measure_number': '314159265',
            'eligibility_options': [],
            'performance_options': []
        })
    )

    assert measure.__str__() == '(Measure 314159265)'
