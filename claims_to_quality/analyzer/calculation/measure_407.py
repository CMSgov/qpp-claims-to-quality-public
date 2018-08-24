"""Subclass of QPP Measure to calculate measure 407 (MSSA)."""
import collections

from claims_to_quality.analyzer.calculation.qpp_measure import QPPMeasure
from claims_to_quality.analyzer.processing import claim_filtering
from claims_to_quality.config import config
from claims_to_quality.lib.connectors import idr_queries
from claims_to_quality.lib.helpers.date_handling import DateRange
from claims_to_quality.lib.helpers.decorators import override
from claims_to_quality.lib.qpp_logging import logging_config
from claims_to_quality.lib.teradata_methods import execute

import newrelic.agent

logger = logging_config.get_logger(__name__)


class MSSADateRangeException(Exception):
    """Error finding an MSSA date range for a claim."""

    pass


class Measure407(QPPMeasure):
    """
    Represents measures of the MSSA Measure 407 type.

    Calculation Strategy
    1. Iterate through all claims for provider A.
    2. Check if provider A has submitted any g-codes relevant to this measure
       (demonstrating intent to report this measure). If not, do not report this measure.
    3. Iterate through all instances in which a claim for provider A includes the relevant
       encounter and diagnosis codes.
    4. Query the IDR to find all claim lines in which the beneficiary has a diagnosis of sepsis
       due to MSSA and one of the relevant encounter codes for each instance.
    5. Build episodes of continuous MSSA claims using claim_line_from_date and
       claim_line_through_date.
    6. Determine if provider A has reported a g-code for each episodes and assign the claim to the
       episode.
    7. Group claims by bene_sk and mssa_bene_id and score accordingly.

    Further Considerations
    1. Each provider is responsible for reporting the g-code for each
       episode if they intend to report the measure.
    2. This measure is not part of an EMA cluster
    3. Claim line level dates should be used for this measure.

    """

    def __init__(self, *args, **kwargs):
        """Instantiate a MSSA Measure407, grouping by beneficiary ID and idk."""
        super(Measure407, self).__init__(*args, **kwargs)
        self.procedure_codes = {
            procedure_code.code for eligibility_option in self.eligibility_options
            for procedure_code in eligibility_option.procedure_codes
        }

    @newrelic.agent.function_trace(name='execute-measure-407', group='Task')
    @override
    def execute(self, claims):
        """Execute Measure 407 calculation."""
        return super(Measure407, self).execute(claims)

    @override
    def filter_by_eligibility_criteria(self, claims):
        """
        Filter out claims that do not meet any of the measure's eligibility options.

        In the case of this measure, we will not calculate if the provider has not
        submitted any quality data codes for this measure.
        """
        quality_codes = self.measure_definition.get_measure_quality_codes()
        if not claim_filtering.do_any_claims_have_quality_codes(
                claims, quality_codes=quality_codes):
            return []

        return super(Measure407, self).filter_by_eligibility_criteria(claims)

    @newrelic.agent.function_trace(name='get-mssa-date-ranges', group='Task')
    def _get_mssa_date_ranges(self, claims):
        """
        Get mssa_date ranges by querying the IDR.

        Returns a dict of {bene_sk: [date_ranges]} that will need to be merged
        to keep only non-overlapping intervals.
        """
        bene_sks = {claim.bene_sk for claim in claims}
        start_date = config.get('calculation.start_date')
        end_date = config.get('calculation.end_date')
        mssa_query = idr_queries.get_mssa_query(
            bene_sks=bene_sks,
            encounter_codes=self.procedure_codes,
            start_date=start_date,
            end_date=end_date
        )

        rows = execute.execute(mssa_query)
        if not rows:
            logger.error(
                'No MSSA date found despite provider '
                'having submitted quality codes for Measure 407.'
            )
            return {}

        mssa_date_ranges = collections.defaultdict(list)
        for row in rows:
            mssa_date_ranges[row['bene_sk']].append(
                DateRange(row['min_date'], row['max_date'])
            )
        return mssa_date_ranges

    @staticmethod
    def _merge_mssa_date_ranges(mssa_date_ranges):
        """
        Reduce lists of ranges by merging overlapping date ranges.

        Returns a dict of {bene_sk: [date_ranges]}.
        """
        return {
            bene_sk: DateRange.merge_date_ranges(date_ranges)
            for bene_sk, date_ranges in mssa_date_ranges.items()
        }

    @staticmethod
    def _find_episode_id(claim, date_ranges):
        """Find index of first matching MSSA DateRange."""
        indices = [
            i for i, date_range in enumerate(date_ranges)
            if date_range.contains_date(claim.clm_from_dt)
        ]
        # In case there is no overlap, we try to look at the line level.
        if not indices:
            for claim_line in claim.claim_lines:
                indices = [
                    i for i, date_range in enumerate(date_ranges)
                    if date_range.contains_date(claim_line.clm_line_from_dt)
                ]
                if indices:
                    break
        # This will raise an IndexError if there
        # still is no overlapping date_range.
        return indices[0]

    @staticmethod
    def _group_claims_by_episode(claims, mssa_date_ranges):
        eligible_instances = collections.defaultdict(list)
        for claim in claims:
            try:
                bene_sk_date_ranges = mssa_date_ranges.get(claim.bene_sk)
                episode_id = Measure407._find_episode_id(claim, bene_sk_date_ranges)
                eligible_instances[(claim.bene_sk, episode_id)].append(claim)
            except (KeyError, IndexError, TypeError) as e:
                raise MSSADateRangeException('Error assigning MSSA DateRange!') from e
        return list(eligible_instances.values())

    def _get_mssa_episode_date_ranges(self, claims):
        """Get MSSA date ranges and reduce them by episodes."""
        mssa_date_ranges = self._get_mssa_date_ranges(claims)
        return Measure407._merge_mssa_date_ranges(mssa_date_ranges)

    @override
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
        mssa_episode_date_ranges = self._get_mssa_episode_date_ranges(claims)
        return self._group_claims_by_episode(claims, mssa_episode_date_ranges)
