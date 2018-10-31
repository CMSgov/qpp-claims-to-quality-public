""""Model representing one measure eligibility option."""
from claims_to_quality.analyzer.models.measures import measure_code

import newrelic.agent

from schematics.models import Model
from schematics.types import BaseType, FloatType, StringType
from schematics.types.compound import ListType, ModelType

SEX_CODE_MAP = {'M': '1', 'F': '2'}


class DiagnosisCodeType(BaseType):
    """
    This is used to ensure that ICD-10 codes in the measure definition contain no dots.

    The format of ICD-10 codes used in the measure definitions contains dots,
    however, the diagnosis codes are stored in the IDR without dots. We remove dots
    to make the measure definition compatible with IDR.
    """

    # TODO: Potentially add to_primitive to convert back to json successfully (add dots back).
    def to_native(self, value, mapping=None):
        """Remove the '.' character from the diagnosis code."""
        return value.replace('.', '')


class EligibilityOption(Model):
    """This model represents eligibility option in a measure definition."""

    sex_code = StringType(serialized_name='sexCode')
    min_age = FloatType(serialized_name='minAge')
    max_age = FloatType(serialized_name='maxAge')
    diagnosis_codes = ListType(DiagnosisCodeType(), serialized_name='diagnosisCodes')
    diagnosis_exclusion_codes = ListType(
        DiagnosisCodeType(), serialized_name='diagnosisExclusionCodes')
    additional_diagnosis_codes = ListType(
        DiagnosisCodeType(), serialized_name='additionalDiagnosisCodes')
    procedure_codes = ListType(
        ModelType(measure_code.MeasureCode), serialized_name='procedureCodes')
    additional_procedure_codes = ListType(
        ModelType(measure_code.MeasureCode), serialized_name='additionalProcedureCodes')

    def __init__(self, *args, **kwargs):
        """Initialize an EligibilityOption, pre-calculating which steps to use to filter claims."""
        super(EligibilityOption, self).__init__(*args, **kwargs)

        self.procedure_code_map = self._get_procedure_code_map_from_measure_codes(
            self.procedure_codes)
        self.additional_procedure_code_map = self._get_procedure_code_map_from_measure_codes(
            self.additional_procedure_codes)

        self._min_age_for_filtering = self.min_age or 0.0
        # We use half-open intervals to compare ages, so that a measure with a max_age of 75
        # is compared using age < 76. This counts people whose age is 75.8 as being 75.
        if not self.max_age:
            self._max_age_for_filtering = float('inf')
        # If max_age is an integer, round up to the next integer as described above.
        elif int(self.max_age) == self.max_age:
            self._max_age_for_filtering = self.max_age + 1.0
        # If max_age is not an integer, treat this as a hard limit for the age.
        else:
            self._max_age_for_filtering = self.max_age

        # Only filter using the methods relevant to the eligibility option.
        self.filter_methods = []

        if self.min_age or self.max_age:
            self.filter_methods.append(self._does_claim_meet_age_criteria)

        if self.sex_code:
            self.filter_methods.append(self._does_claim_meet_sex_criteria)

        if self.diagnosis_codes or self.diagnosis_exclusion_codes:
            self.filter_methods.append(self._does_claim_meet_all_diagnosis_criteria)
            self._diagnosis_filter_methods = []

            if self.diagnosis_exclusion_codes:
                self.diagnosis_exclusion_codes_set = set(self.diagnosis_exclusion_codes)
                self._diagnosis_filter_methods.append(self._does_claim_meet_diagnosis_exclusion)

            if self.diagnosis_codes:
                self.diagnosis_codes_set = set(self.diagnosis_codes)
                self._diagnosis_filter_methods.append(self._does_claim_meet_diagnosis)

            if self.additional_diagnosis_codes:
                self.additional_diagnosis_codes_set = set(self.additional_diagnosis_codes)
                self._diagnosis_filter_methods.append(self._does_claim_meet_additional_diagnoses)

        # Filter by additional procedure codes first, guided by the hypothesis that these will be
        # less common than ordinary measure codes (e.g., "Outpatient office visit, 30 minutes").
        if self.additional_procedure_codes:
            self.filter_methods.append(self._does_claim_meet_additional_procedure_criteria)

        if self.procedure_codes:
            self.filter_methods.append(self._does_claim_meet_procedure_criteria)

    @staticmethod
    def _get_procedure_code_map_from_measure_codes(procedure_code_list):
        """Convert a list of procedure codes into a mapping 'code_str': MeasureCode instance."""
        # TODO: Determine if the same code string ever appears twice for two distinct measure codes
        # within the same eligibility option.
        procedure_code_strings = {
            measure_code.code
            for measure_code in procedure_code_list
        } if procedure_code_list else set()

        return {
            code_string: [
                measure_code
                for measure_code in procedure_code_list
                if measure_code.code == code_string
            ]
            for code_string in procedure_code_strings
        }

    def __repr__(self):
        """Return a string representation of the eligibility option."""
        return 'EligibilityOption({})'.format(self.to_native())

    def _does_claim_meet_eligibility_option(self, claim):
        return all(method(claim) for method in self.filter_methods)

    @newrelic.agent.function_trace(name='filter-by-diagnosis-codes', group='Task')
    def _does_claim_meet_all_diagnosis_criteria(self, claim):
        """Return True if and only if the claim has all codes required by the eligibility option."""
        return all(diagnosis_method(claim) for diagnosis_method in self._diagnosis_filter_methods)

    def _does_claim_meet_diagnosis(self, claim):
        """Return True if and only if the claim has the required diagnoses."""
        return not self.diagnosis_codes_set.isdisjoint(claim.dx_codes)

    def _does_claim_meet_diagnosis_exclusion(self, claim):
        """Return True if and only if the claim does not have the excluded diagnoses."""
        return self.diagnosis_exclusion_codes_set.isdisjoint(claim.dx_codes)

    def _does_claim_meet_additional_diagnoses(self, claim):
        """Return True if and only if the claim has the additional required diagnoses."""
        return not self.additional_diagnosis_codes_set.isdisjoint(claim.dx_codes)

    @newrelic.agent.function_trace(name='filter-by-procedure', group='Task')
    def _does_claim_meet_procedure_criteria(self, claim):
        """Return True if the claim contains a matching procedure code."""
        potential_matching_lines_by_measure_codes = (
            (self.procedure_code_map[line.clm_line_hcpcs_cd], line)
            for line in claim.claim_lines
            if line.clm_line_hcpcs_cd in self.procedure_code_map
        )
        return any(
            measure_code.matches_line(line)
            for measure_code_list, line in potential_matching_lines_by_measure_codes
            for measure_code in measure_code_list
        )

    @newrelic.agent.function_trace(name='filter-by-additional-procedure-codes', group='Task')
    def _does_claim_meet_additional_procedure_criteria(self, claim):
        """
        Return True if the claim contains a code from the list of additional procedure codes.

        Relevant for measures 155, 226 in 2018.
        """
        potential_matching_lines_by_measure_codes = (
            (self.additional_procedure_code_map[line.clm_line_hcpcs_cd], line)
            for line in claim.claim_lines
            if line.clm_line_hcpcs_cd in self.additional_procedure_code_map
        )
        return any(
            measure_code.matches_line(line)
            for measure_code_list, line in potential_matching_lines_by_measure_codes
            for measure_code in measure_code_list
        )

    @newrelic.agent.function_trace(name='filter-by-age', group='Task')
    def _does_claim_meet_age_criteria(self, claim):
        """Return True when the age falls in the range specified by the eligibility option."""
        return (
            self._min_age_for_filtering <= claim.bene_age < self._max_age_for_filtering
        )

    @newrelic.agent.function_trace(name='filter-by-sex', group='Task')
    def _does_claim_meet_sex_criteria(self, claim):
        """Return True when the claim's sex code matches one specified by the eligibility option."""
        return claim.clm_bene_sex_cd == SEX_CODE_MAP[self.sex_code]
