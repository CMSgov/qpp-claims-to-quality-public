"""Processes a provider's claims data against a measure definition."""
import collections

from claims_to_quality.lib.qpp_logging import logging_config

import newrelic.agent

logger = logging_config.get_logger(__name__)


class QPPMeasure(object):
    """
    Represents one QPP measure.

    TODO: Add documentation describing each type of measure that will extend this class.
    """

    def __init__(self, measure_definition, **kwargs):
        """Create a measure."""
        self.measure_definition = measure_definition
        self.eligibility_options = self.measure_definition['eligibility_options']
        self.performance_options = self.measure_definition['performance_options']
        self.has_multiple_strata = bool(
            measure_definition['strata'] is not None and len(measure_definition['strata']) > 1
        )
        self.performance_marker_ranking = self.get_performance_marker_ranking()

        self.__dict__.update(kwargs)

    def __str__(self):
        """Represent Measures by their measure number."""
        return '(Measure {measure_number})'.format(
            measure_number=self.measure_definition.measure_number)

    @newrelic.agent.function_trace(name='execute-measure-calculation', group='Task')
    def execute(self, claims):
        """
        Evaluate a provider dataset according to the measure specification.

        Order of operations:
        1) Filter claims data to relevant claims only.
            Ex.: filter by age, sex, diagnosis or encounter code.
        2) Group relevant claims into eligible instances according to measure logic.
            Ex.: group the claims for each beneficiary.
        3) Assign a performance marker to each eligible instance.
        4) Aggregate totals by performance marker across all eligible instances.
        """
        relevant_claims = self.filter_by_eligibility_criteria(claims)

        # If the measure has date range restrictions, filter further.
        if hasattr(self, 'date_ranges'):
            relevant_claims = self.filter_by_valid_dates(relevant_claims)

        if relevant_claims:
            logger.debug('Relevant claims found for measure {}.'.format(
                self.measure_definition.measure_number))
            eligible_instances = self.get_eligible_instances(relevant_claims)
        else:
            logger.debug('No relevant claims found for measure {}.'.format(
                self.measure_definition.measure_number))
            eligible_instances = []

        count_by_performance_marker = self.score_eligible_instances(eligible_instances)

        # TODO: evaluate switching to using the camelCase attribute names everywhere.
        return {
            'eligible_population_exclusion': count_by_performance_marker[
                'eligiblePopulationExclusion'],
            'eligible_population_exception': count_by_performance_marker[
                'eligiblePopulationException'],
            'performance_met': count_by_performance_marker['performanceMet'],
            'performance_not_met': count_by_performance_marker['performanceNotMet'],
            'eligible_population':
                sum(count_by_performance_marker.values())
        }

    def filter_by_eligibility_criteria(self, claims):
        """Filter out claims that do not meet any of the measure's eligibility options."""
        logger.debug('Filter by eligibility criteria.')
        return [claim for claim in claims if self._does_claim_meet_any_eligibility_options(claim)]

    def _does_claim_meet_any_eligibility_options(self, claim):
        """Return True if and only if the claim meets at least one eligibility option."""
        for eligibility_option in self.eligibility_options:
            if eligibility_option._does_claim_meet_eligibility_option(claim):
                return True
        else:
            return False

    def _assign_performance_markers(self, claim):
        """Return the set of performance markers that a claim belongs to."""
        logger.debug('Assign performance markers.')
        return {
            option.option_type for option in self.performance_options
            if all(
                any(
                    measure_code.matches_line(line)
                    for line in claim.claim_lines
                    if line.clm_line_hcpcs_cd in option.quality_code_map
                )
                for measure_code in option.quality_codes
            )
        }

    def get_performance_marker_ranking(self):
        """
        Return a mapping from performance markers to their advantageousness ranking.

        The ordering is reversed for inverse measures, but in both cases None is last.
        """
        if self.measure_definition.is_inverse:
            return {
                'performanceMet': 3,
                'eligiblePopulationExclusion': 2,
                'eligiblePopulationException': 1,
                'performanceNotMet': 0,
                None: 4
            }
        else:
            return {
                'performanceMet': 0,
                'eligiblePopulationExclusion': 1,
                'eligiblePopulationException': 2,
                'performanceNotMet': 3,
                None: 4
            }

    def get_most_advantageous_claim(self, claims):
        """
        Given a list of claims, return only the most advantageous claim.

        Performance results in order of advantageousness (reversed for inverse measures):
        - Performance Met
        - Performance Exclusion
        - Performance Exception
        - Performance Not Met
        - Population Total (no quality code specified)

        Returns:
            Tuple of (Claim, str) containing the best claim in the list, and the associated marker.
        """
        logger.debug('Get most advantageous claim.')
        marker_to_rank_map = self.performance_marker_ranking
        best_claim = claims[0]
        best_marker = None

        claims_with_markers = (
            (claim, marker)
            for claim in claims
            for marker in self._assign_performance_markers(claim)
        )

        for claim, marker in claims_with_markers:
            if marker_to_rank_map[marker] < marker_to_rank_map[best_marker]:
                best_claim = claim
                best_marker = marker
            # Exit early if the global best marker has been reached.
            if marker_to_rank_map[best_marker] == 0:
                return (best_claim, best_marker)

        return (best_claim, best_marker)

    @staticmethod
    def group_claims_by_field_values(fields_to_group_by, claims):
        """
        Combine claims from a given list according to the specified fields.

        For example, if fields_to_group_by = ['bene_sk', 'clm_from_dt'], all claims for the
        same beneficiary on the same date will be grouped together.

        Args:
            fields_to_group_by: List of field names (or single field name as a string).
            claims (list(Claim)): Claims to be grouped.
        Returns:
            List of list of claims, where each inner list has the same values in fields_to_group_by.
        """
        logger.debug('Group claims by field values.')
        # If a single field was provided as a string, wrap it in an iterable.
        if isinstance(fields_to_group_by, str):
            fields_to_group_by = [fields_to_group_by]

        # Assign each claim to a subset based on the contents of the provided fields.
        claims_map = collections.defaultdict(list)
        for claim in claims:
            field_contents = tuple(getattr(claim, field) for field in fields_to_group_by)
            claims_map[field_contents].append(claim)

        return list(claims_map.values())

    @newrelic.agent.function_trace(name='get-eligible-instances', group='Task')
    def get_eligible_instances(self, claims):
        """
        Group claims together into eligible instances.

        Returns a list of eligible instances, which are themselves lists of claims.

        Args:
            claims (list(Claim)): Claims to be grouped.
        Returns:
            list(list(Claim)), where each inner list is a single eligible instance.
        """
        logger.debug('Get eligible instances.')
        return self.group_claims_by_field_values(self.fields_to_group_by, claims)

    @newrelic.agent.function_trace(name='score-eligible-instances', group='Task')
    def score_eligible_instances(self, eligible_instances):
        """
        Assign performance markers to eligible instances, then aggregate counts for each marker.

        Args:
            eligible_instances (list(list(Claim))): instances to be scored.
        Returns:
            Dictionary with performance markers as keys and counts as values.
        """
        logger.debug('Score eligible instances.')
        return collections.Counter([
            self.get_most_advantageous_claim(instance)[1]
            for instance in eligible_instances
        ])

    def filter_by_presence_of_quality_codes(self, claims):
        """Given a list of claims, return only claims having valid quality codes."""
        logger.debug('Filter by presence of quality code.')
        return [
            claim
            for claim in claims
            if not {
                'performanceMet', 'performanceNotMet',
                'eligiblePopulationExclusion', 'eligiblePopulationException'
            }.isdisjoint(self._assign_performance_markers(claim))
        ]

    @staticmethod
    def _is_claim_in_date_range(claim, date_range):
        """
        Return True if the claim falls within the given date range, False otherwise.

        This method is lenient: any overlap whatsoever counts as a match.

        Args:
            claim (Claim): claim in consideration
            date_range (tuple(datetime.date)): (start_date, end_date) pair
        """
        return (
            date_range[0] <= claim['clm_from_dt'] <= date_range[1]
        ) or (
            date_range[0] <= claim['clm_thru_dt'] <= date_range[1]
        )

    def filter_by_valid_dates(self, claims):
        """
        Given a list of claims, return only claims with dates allowed by the measure.

        Raises an AttributeError if self.date_ranges is not defined.
        """
        return [
            claim for claim in claims
            if any(
                QPPMeasure._is_claim_in_date_range(claim, date_range)
                for date_range in self.date_ranges
            )
        ]
