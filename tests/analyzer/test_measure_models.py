"""Tests for measure-definition related models."""
import datetime

from claims_to_quality.analyzer.models import claim
from claims_to_quality.analyzer.models import claim_line
from claims_to_quality.analyzer.models.measures.eligibility_option import EligibilityOption
from claims_to_quality.analyzer.models.measures.measure_code import MeasureCode
from claims_to_quality.analyzer.models.measures.measure_definition import MeasureDefinition
from claims_to_quality.analyzer.models.measures.performance_option import (
    PerformanceOption, _is_valid_option_type, _is_valid_quality_code_list)
from claims_to_quality.analyzer.models.measures.stratum import Stratum
from claims_to_quality.analyzer.processing import claim_filtering

import mock

import pytest

from schematics.exceptions import ValidationError


@mock.patch.object(EligibilityOption, '_does_claim_meet_procedure_criteria')
def test_early_exit_during_filtering(procedure_check):
    """"Check that the eligibility option filtering exits early when possible."""
    claim_failing_sex_filtering = claim.Claim(
        {'clm_bene_sex_cd': '1'}
    )
    eligibility_option = EligibilityOption({
        'sexCode': 'F',
        'procedureCodes': [MeasureCode({'code': '99201'})],
    })

    eligibility_option._does_claim_meet_eligibility_option(claim_failing_sex_filtering)
    procedure_check.assert_not_called()


class TestPerformanceOptionValidation():
    """Test methods for validating performance options."""

    def setup(self):
        """Initialize performance options."""
        self.valid_performance_option = PerformanceOption({
            'optionType': 'performanceMet',
            'qualityCodes': [MeasureCode({'code': 'g-code'})]
        })

        self.invalid_performance_option = PerformanceOption({
            'optionType': 'typographical_error',
            'qualityCodes': []
        })

    def test_is_valid_performance_option_type(self):
        """Test that validation of option type works as expected."""
        assert _is_valid_option_type(self.valid_performance_option.option_type)
        with pytest.raises(ValidationError):
            _is_valid_option_type(self.invalid_performance_option.option_type)

    def test_is_valid_quality_code_list(self):
        """Test that validation of option type works as expected."""
        assert _is_valid_quality_code_list(self.valid_performance_option.option_type)
        with pytest.raises(ValidationError):
            _is_valid_quality_code_list(self.invalid_performance_option.quality_codes)


class TestMeasureCodeMatchesClaimLine():
    """Tests for methods matching lines to MeasureCodes."""

    def setup(self):
        claim_line_data = [
            {
                'clm_line_hcpcs_cd': 'code',
                'mdfr_cds': ['GQ', 'GY'],
                'clm_pos_code': '23',
                'clm_line_num': 1
            },
            {'clm_line_hcpcs_cd': 'code', 'mdfr_cds': ['GQ'], 'clm_pos_code': '24'},
            {'clm_line_hcpcs_cd': 'code', 'mdfr_cds': ['GY'], 'clm_pos_code': '25'},
            {'clm_line_hcpcs_cd': 'code', 'mdfr_cds': [], 'clm_pos_code': None}
        ]
        self.claim_lines = [claim_line.ClaimLine(line) for line in claim_line_data]

        self.claim_line_GQ_GY_23 = self.claim_lines[0]
        self.claim_line_GQ_24 = self.claim_lines[1]
        self.claim_line_GY_25 = self.claim_lines[2]
        self.claim_line_no_modifier_no_pos = self.claim_lines[3]

        self.plain_measure_code = MeasureCode({'code': 'code'})

        self.irrelevant_measure_code = MeasureCode({'code': 'bad_code'})

        self.measure_code_pos_24 = MeasureCode(
            {'code': 'code', 'placesOfService': ['24']}
        )
        self.measure_code_pos_26 = MeasureCode(
            {'code': 'code', 'placesOfService': ['26']}
        )
        self.measure_code_exclude_pos_24 = MeasureCode(
            {'code': 'code', 'placesOfServiceExclusions': ['24']}
        )
        self.measure_code_exclude_pos_26 = MeasureCode(
            {'code': 'code', 'placesOfServiceExclusions': ['26']}
        )

        self.measure_code_exclude_GQ = MeasureCode(
            {'code': 'code', 'modifierExclusions': ['GQ']}
        )
        self.measure_code_exclude_GT = MeasureCode(
            {'code': 'code', 'modifierExclusions': ['GT']}
        )

        self.measure_code_include_GQ = MeasureCode(
            {'code': 'code', 'modifiers': ['GQ']}
        )
        self.measure_code_include_GT = MeasureCode(
            {'code': 'code', 'modifiers': ['GT']}
        )

        self.measure_code_both_modifier_x_and_modifiers = MeasureCode(
            {'code': 'code', 'modifiers': ['GY'], 'modifierExclusions': ['GT', 'GQ']}
        )

    def test_matches_measure_code_no_constraints(self):
        filtered_lines = [
            line for line in self.claim_lines if self.plain_measure_code.matches_line(line)
        ]
        assert filtered_lines == self.claim_lines

    def test_matches_measure_code_no_code_match(self):
        """Test matches measure_code if the code doesn't match."""
        measure_code = MeasureCode({'code': 'bad_code'})
        filtered_lines = [
            line for line in self.claim_lines if measure_code.matches_line(line)
        ]
        assert filtered_lines == []

    def test_matches_measure_code_pos_x_true(self):
        filtered_lines = [
            line for line in self.claim_lines if self.measure_code_exclude_pos_24.matches_line(line)
        ]
        assert filtered_lines == [
            self.claim_line_GQ_GY_23, self.claim_line_GY_25, self.claim_line_no_modifier_no_pos]

    def test_matches_measure_code_pos_x_false(self):
        filtered_lines = [
            line for line in self.claim_lines if self.measure_code_exclude_pos_26.matches_line(line)
        ]
        assert filtered_lines == self.claim_lines

    def test_matches_measure_code_pos_true(self):
        filtered_lines = [
            line for line in self.claim_lines if self.measure_code_pos_24.matches_line(line)
        ]
        assert filtered_lines == [self.claim_line_GQ_24]

    def test_matches_measure_code_pos_false(self):
        filtered_lines = [
            line for line in self.claim_lines if self.measure_code_pos_26.matches_line(line)
        ]
        assert filtered_lines == []

    def test_matches_measure_code_mdfr_x_true(self):
        filtered_lines = [
            line for line in self.claim_lines if self.measure_code_exclude_GQ.matches_line(line)
        ]
        assert filtered_lines == [self.claim_line_GY_25, self.claim_line_no_modifier_no_pos]

    def test_matches_measure_code_mdfr_x_false(self):
        filtered_lines = [
            line for line in self.claim_lines if self.measure_code_exclude_GT.matches_line(line)
        ]
        assert filtered_lines == self.claim_lines

    def test_matches_measure_code_mdfr_true(self):
        filtered_lines = [
            line for line in self.claim_lines if self.measure_code_include_GQ.matches_line(line)
        ]
        assert filtered_lines == [self.claim_line_GQ_GY_23, self.claim_line_GQ_24]

    def test_matches_measure_code_mdfr_false(self):
        filtered_lines = [
            line for line in self.claim_lines if self.measure_code_include_GT.matches_line(line)
        ]
        assert filtered_lines == []

    def test_matches_measure_code_mdfr_x_multiple_constraints(self):
        filtered_lines = [
            line for line in self.claim_lines
            if self.measure_code_both_modifier_x_and_modifiers.matches_line(line)
        ]
        assert filtered_lines == [self.claim_line_GY_25]


def test_does_claim_meet_additional_procedure_criteria():
    """"Check that the eligibility option correctly filters by additional diagnosis codes."""
    measure_code = MeasureCode({
        'code': 'code'
    })
    additional_measure_code = MeasureCode({
        'code': 'additional_code'
    })
    option = EligibilityOption({
        'procedureCodes': [measure_code],
        'additionalProcedureCodes': [additional_measure_code]
    })

    claim_measure_code_only = claim.Claim({
        'claim_lines': [claim_line.ClaimLine({'clm_line_hcpcs_cd': 'code'})]
    })
    claim_additional_code_only = claim.Claim({
        'claim_lines': [claim_line.ClaimLine({'clm_line_hcpcs_cd': 'additional_code'})]
    })
    claim_both_codes = claim.Claim({
        'claim_lines': [
            claim_line.ClaimLine({'clm_line_hcpcs_cd': 'code'}),
            claim_line.ClaimLine({'clm_line_hcpcs_cd': 'additional_code'})]
    })

    assert option._does_claim_meet_additional_procedure_criteria(claim_additional_code_only)
    assert option._does_claim_meet_additional_procedure_criteria(claim_both_codes)
    assert not (option._does_claim_meet_additional_procedure_criteria(claim_measure_code_only))


def test_does_claim_meet_sex_criteria():
    """"Check that the eligibility option can determine what claims match its sex criteria."""
    matching_claim = claim.Claim({'clm_bene_sex_cd': '1'})
    non_matching_claim = claim.Claim({'clm_bene_sex_cd': '2'})
    null_claim = claim.Claim()

    eligibility_option = EligibilityOption({
        'sexCode': 'M'
    })

    assert (eligibility_option._does_claim_meet_sex_criteria(matching_claim))
    assert not (eligibility_option._does_claim_meet_sex_criteria(non_matching_claim))
    assert not (eligibility_option._does_claim_meet_sex_criteria(null_claim))


def test_does_claim_meet_age_criteria():
    """"Check that the eligibility option can determine what claims match its age criteria."""
    # This patient is 75.5 years old and should be counted.
    matching_claim = claim.Claim({
        'clm_ptnt_birth_dt': datetime.date(1942, 1, 1),
        'clm_from_dt': datetime.date(2017, 7, 1)
    })
    # This patient is 76.5 years old.
    claim_too_old = claim.Claim({
        'clm_ptnt_birth_dt': datetime.date(1941, 1, 1),
        'clm_from_dt': datetime.date(2017, 7, 1)
    })
    # This patient is 64.5 years old.
    claim_too_young = claim.Claim({
        'clm_ptnt_birth_dt': datetime.date(1953, 1, 1),
        'clm_from_dt': datetime.date(2017, 7, 1)
    })

    eligibility_option = EligibilityOption({
        'minAge': 65,
        'maxAge': 75
    })

    assert (eligibility_option._does_claim_meet_age_criteria(matching_claim))
    assert not (eligibility_option._does_claim_meet_age_criteria(claim_too_old))
    assert not (eligibility_option._does_claim_meet_age_criteria(claim_too_young))


def test_does_claim_meet_age_criteria_fractional_boundaries():
    """"Check that the eligibility option can determine what claims match its age criteria."""
    # This patient is 0.5 years old (exactly).
    matching_claim = claim.Claim({
        'clm_ptnt_birth_dt': datetime.date(2017, 1, 1),
        'clm_from_dt': datetime.date(2017, 7, 1)
    })
    # This patient is 1.51 years old.
    claim_too_old = claim.Claim({
        'clm_ptnt_birth_dt': datetime.date(2015, 12, 31),
        'clm_from_dt': datetime.date(2017, 7, 1)
    })
    # This patient is 0.41 years old.
    claim_too_young = claim.Claim({
        'clm_ptnt_birth_dt': datetime.date(2017, 2, 1),
        'clm_from_dt': datetime.date(2017, 7, 1)
    })

    eligibility_option = EligibilityOption({
        'minAge': 0.5,
        'maxAge': 1.5
    })

    assert (eligibility_option._does_claim_meet_age_criteria(matching_claim))
    assert not (eligibility_option._does_claim_meet_age_criteria(claim_too_old))
    assert not (eligibility_option._does_claim_meet_age_criteria(claim_too_young))


def test_eligibility_option_updated_diagnosis_codes():
    """Test that importing an eligibility option converts diagnosis type codes properly."""
    test_eligibility_option = {
        'diagnosisCodes': ['a.b.c'],
        'diagnosisExclusionCodes': ['d.e.f'],
        'additionalDiagnosisCodes': ['g.h.i'],
    }

    option = EligibilityOption(test_eligibility_option)

    assert option.diagnosis_codes == ['abc']
    assert option.diagnosis_exclusion_codes == ['def']
    assert option.additional_diagnosis_codes == ['ghi']


def test_measure_definition():
    """Make sure all of the measure definition code can be run without error."""
    sample_measure_code = {
        'code': 'code',
        'modifiers': ['a', 'b'],
        'placesOfService': ['a', 'b'],
        'modifierExclusions': ['a', 'b'],
        'placesOfServiceExclusions': ['a', 'b']
    }
    test_measure_definition = {
        'isInverse': True,
        'eligibilityOptions': [{
            'minAge': 0,
            'maxAge': 100,
            'sexCode': 'F',
            'diagnosisCodes': ['a.b.c'],
            'diagnosisExclusionCodes': ['d.e.f'],
            'additionalDiagnosisCodes': ['g.h.i'],
            'procedureCodes': [sample_measure_code]

        }],
        'performanceOptions': [{
            'optionType': 'performanceMet',
            'qualityCodes': [sample_measure_code]
        }]
    }

    MeasureDefinition(test_measure_definition)


class TestReprFunctionality():
    """Test to ensure that all models' representations can recreate the original object."""

    def setup(self):
        """Create sample models for use in the tests."""
        self.measure_code = MeasureCode({
            'code': 'code',
            'modifiers': ['a', 'b'],
            'placesOfService': ['a', 'b'],
            'modifierExclusions': ['a', 'b'],
            'placesOfServiceExclusions': ['a', 'b']
        })
        self.eligibility_option = EligibilityOption({
            'diagnosisCodes': ['a.b.c'],
            'diagnosisExclusionCodes': ['d.e.f'],
            'additionalDiagnosisCodes': ['g.h.i'],
        })
        self.performance_option = PerformanceOption({
            'optionType': 'performanceNotMet',
            'qualityCodes': [
                {'code': 'code_a'}
            ]
        })
        self.measure = MeasureDefinition({
            'isInverse': True,
            'eligibilityOptions': [{
                'minAge': 0,
                'maxAge': 100,
                'sexCode': 'F',
                'diagnosisCodes': ['a.b.c'],
                'diagnosisExclusionCodes': ['d.e.f'],
                'additionalDiagnosisCodes': ['g.h.i'],
                'procedureCodes': [self.measure_code]

            }],
            'performanceOptions': [{
                'optionType': 'performanceMet',
                'qualityCodes': [self.measure_code]
            }]
        })

        self.stratum = Stratum({'name': 'primary_stratum'})

    def test_repr_for_measure_codes(self):
        """Test that measure codes are represented correctly."""
        assert(self.measure_code == eval(self.measure_code.__repr__()))

    def test_repr_for_eligibility_option(self):
        """Test that eligibility options are represented correctly."""
        assert(self.eligibility_option == eval(self.eligibility_option.__repr__()))

    def test_repr_for_performance_option(self):
        """Test that performance options are represented correctly."""
        assert(self.performance_option == eval(self.performance_option.__repr__()))

    def test_repr_for_measure_definitions(self):
        """Test that measure definitions are represented correctly."""
        assert(self.measure == eval(self.measure.__repr__()))

    def test_repr_for_strata(self):
        """Test that strata are represented correctly."""
        assert(self.stratum == eval(self.stratum.__repr__()))


class TestQualityCodesFiltering():
    """Tests for the function do_claims_have_quality_codes."""

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
            })
        ]

        self.measure_definition = MeasureDefinition({
            'eligibility_options': [],
            'performance_options': performance_options
        })

    def test_get_measure_quality_codes(self):
        """Test _get_measure_quality_codes."""
        assert self.measure_definition.get_measure_quality_codes() == set(['pn_code', 'pn_x_code'])

    def test_claims_have_quality_codes_true(self):
        """Test do_claims_have_quality_codes if there are matching codes."""
        test_claims_with_quality_codes = [
            claim.Claim({'claim_lines': [{'clm_line_hcpcs_cd': 'G9607'}]}),
            claim.Claim({'claim_lines': [{'clm_line_hcpcs_cd': 'pn_code'}]}),
            claim.Claim({'claim_lines': [
                {'clm_line_hcpcs_cd': 'pn_x_code'},
                {'clm_line_hcpcs_cd': 'pn_code'}
            ]}),
        ]

        quality_codes = self.measure_definition.get_measure_quality_codes()
        assert claim_filtering.do_any_claims_have_quality_codes(
            test_claims_with_quality_codes, quality_codes=quality_codes)

    def test_claims_have_quality_codes_false(self):
        """Test do_claims_have_quality_codes return False if there are none."""
        test_claims_with_no_quality_codes = [
            claim.Claim({'claim_lines': [{'clm_line_hcpcs_cd': 'G9607'}]}),
            claim.Claim({'claim_lines': [{'clm_line_hcpcs_cd': 'G9607'}]}),
            claim.Claim({'claim_lines': [
                {'clm_line_hcpcs_cd': 'G9607'},
                {'clm_line_hcpcs_cd': 'G9607'}
            ]}),
        ]

        quality_codes = self.measure_definition.get_measure_quality_codes()
        assert not claim_filtering.do_any_claims_have_quality_codes(
            test_claims_with_no_quality_codes, quality_codes=quality_codes)
