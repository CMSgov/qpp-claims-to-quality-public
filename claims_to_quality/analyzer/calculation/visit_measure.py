"""Subclass of QPP Measure to calculate measures using Visit logic."""
import collections

from claims_to_quality.analyzer.calculation.qpp_measure import QPPMeasure
from claims_to_quality.lib.helpers.decorators import override
from claims_to_quality.lib.qpp_logging import logging_config

logger = logging_config.get_logger(__name__)


class VisitMeasure(QPPMeasure):
    """
    Represents measures of the Visit type.

    Visit measures are reported each time a patient is seen by the eligible professional.
    Each beneficiary / date of service combination counts as a single eligible instance.

    If there are multiple denominator eligible instances with the same date of service,
    all instances are counted in the denominator. Performance rates are calculated using the most
    advantageous QDC or QDC combination and applied to each denominator eligible instance on that
    claim.

    This class can be extended for implementation of all Visit type measures.
    """

    def __init__(self, *args, **kwargs):
        """Instantiate a VisitMeasure, grouping by beneficiary and date of service."""
        super(VisitMeasure, self).__init__(*args, **kwargs)
        self.fields_to_group_by = ['bene_sk', 'clm_from_dt']

    def _compute_eligible_instance_weight(self, claims):
        """
        Count the contribution of a single eligible instance to the overall score.

        For Visit measures, each relevant line contributes once to the score for a particular
        performance marker. If a claim has three measure-relevant lines and the most advantageous
        marker is performanceMet, the provider's performanceMet count should increase by three.
        """
        logger.debug('Compute eligible instance weight.')

        potential_matching_lines_and_measure_codes = (
            (self.measure_definition.procedure_code_map[line.clm_line_hcpcs_cd], line)
            for claim in claims
            for line in claim.claim_lines
            if line.clm_line_hcpcs_cd in self.measure_definition.procedure_code_map
        )

        line_matches = [
            any(
                measure_code.matches_line(line) for measure_code in measure_code_list
            )
            for measure_code_list, line in potential_matching_lines_and_measure_codes
        ]

        return sum(line_matches)

    @override
    def score_eligible_instances(self, eligible_instances):
        """
        Assign performance markers to eligible instances, then aggregate counts for each marker.

        Each eligible instance for Visit measures can count multiple times toward a particular
        performance marker, whereas each eligible instance counts once in QPPMeasure.

        The _compute_eligible_instance_weight method is used to determine how many times each
        eligible instance should be counted for the most advantageous performance marker.

        This overrides the method of the same name from the QPPMeasure class.

        Args:
            eligible_instances (list(list(Claim))): instances to be scored.
        Returns:
            Dictionary with performance markers as keys and counts as values.
        """
        logger.debug('Score eligible instances.')
        most_advantageous_markers_with_weights = (
            (
                self.get_most_advantageous_claim(instance)[1],
                self._compute_eligible_instance_weight(instance)
            ) for instance in eligible_instances
        )

        counts_by_marker = collections.Counter()

        for marker, weight in most_advantageous_markers_with_weights:
            counts_by_marker[marker] += weight

        return counts_by_marker
