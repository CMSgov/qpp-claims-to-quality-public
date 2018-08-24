"""QPP Measure subclass where eligible instances are defined via intersecting diagnosis logic."""
from claims_to_quality.analyzer.calculation.qpp_measure import QPPMeasure
from claims_to_quality.lib.helpers.decorators import override
from claims_to_quality.lib.qpp_logging import logging_config

logger = logging_config.get_logger(__name__)


class IntersectingDiagnosisMeasure(QPPMeasure):
    """
    Represents episode of care measures of the IntersectingDiagnosis type.

    All claims that share diagnosis codes are combined into one episode, given they have the same
    TIN/NPI/Bene.
    """

    def __init__(self, *args, **kwargs):
        """Instantiate a IntersectingDiagnosisMeasure, grouping by beneficiary and diagnosis."""
        super(IntersectingDiagnosisMeasure, self).__init__(*args, **kwargs)
        self.fields_to_group_by = ['bene_sk']
        self.diagnosis_codes = {
            diagnosis_code for option in self.eligibility_options
            for diagnosis_code in option.diagnosis_codes
        }

    @override
    def get_eligible_instances(self, claims):
        """
        Group claims together into eligible instances.

        Returns a list of eligible instances, which are themselves lists of claims.

        Args:
            claims (list(Claim)): claims to be grouped by benefificary then split by diagnosis code.
        Returns:
            list(list(Claim)), where each inner list is a single eligible instance.
        """
        logger.debug('Get eligible instances.')
        # Group claims by beneficiary.
        claims_by_beneficiary = self.group_claims_by_field_values(self.fields_to_group_by, claims)

        # Within each beneficiary's subset of claims, split and regroup the subset
        # to ensure that each eligible instance consists of claims sharing diagnosis codes.
        eligible_instances = []
        for beneficiary_claims_subset in claims_by_beneficiary:
            episodes_of_care = self.group_claims_by_common_diagnosis(beneficiary_claims_subset)
            eligible_instances += episodes_of_care

        return eligible_instances

    def group_claims_by_common_diagnosis(self, claims):
        """
        Given a list of claims, group claims that share diagnosis codes together into episodes.

        To avoid duplication, each claim is assigned to at most one episode of care.

        Args:
            claims (list(Claim)): list of claims to be grouped into episodes of care.
        Returns:
            list(list(Claim)), where each inner list forms a single episode.
        """
        logger.debug('Group claims by common diagonisis.')
        claims_by_common_diagnosis = []
        for claim in claims:
            claim_dx_codes = self._get_relevant_diagnosis_codes([claim])
            # For each subset of claims we've already seen, check to see if the current claim
            # has any overlapping diagnosis codes.
            for claim_subset in claims_by_common_diagnosis:
                other_dx_codes = self._get_relevant_diagnosis_codes(claim_subset)
                # If a common code is present, add the current claim to the existing subset.
                # If there were no common codes, use the current claim to start a new subset.
                # Break to ensure that each claim is assigned to at most one subset.
                if not claim_dx_codes.isdisjoint(other_dx_codes):
                    claim_subset.append(claim)
                    break
                else:
                    claims_by_common_diagnosis.append([claim])
                    break
            # If no claims have been seen yet, start with a single subset.
            if claims_by_common_diagnosis == []:
                claims_by_common_diagnosis.append([claim])

        return claims_by_common_diagnosis

    def _get_relevant_diagnosis_codes(self, claims):
        """Given a list of claims, return a set of diagnosis codes relevant to the measure."""
        logger.debug('Get relevant diagnosis codes.')

        relevant_codes = set()
        for claim in claims:
            relevant_codes.update(self.diagnosis_codes.intersection(claim.dx_codes))

        return relevant_codes
