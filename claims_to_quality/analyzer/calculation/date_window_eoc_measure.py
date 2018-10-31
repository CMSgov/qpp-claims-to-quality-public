"""Subclass of QPP Measure where episodes of care (EOC) are defined via 30-day-window logic."""
from claims_to_quality.analyzer.calculation.qpp_measure import QPPMeasure
from claims_to_quality.lib.qpp_logging import logging_config

logger = logging_config.get_logger(__name__)


class DateWindowEOCMeasure(QPPMeasure):
    # TODO: Account for separate date columns for episode kick-off and episode grouping.
    """
    Represents episode of care measures of the 30-day-window type.

    From the eMeasure tag Excel document:
        The 30-day window continues forward to include any subsequent claim(s) where the
        1st expense date on qualifying line items (denominator dx or procedure codes)
        is within 30-days of the last expense date on that 1st claim.
    """

    def __init__(self, *args, **kwargs):
        """Instantiate an DateWindowEOCMeasure, grouping by beneficiary."""
        super(DateWindowEOCMeasure, self).__init__(*args, **kwargs)
        self.fields_to_group_by = ['bene_sk']

    @staticmethod
    def get_claims_from_earliest_date(claims, date_column='clm_from_dt'):
        """
        Given a list of claims, return only the earliest claim based on date_column.

        In the case where two claims have the earliest date, returns all claims from that date.
        """
        logger.debug('Get claims from earliest data using date_column - {}'.format(date_column))
        if not claims:
            return []

        earliest_date = min(claims, key=lambda x: x.clm_from_dt).clm_from_dt
        earliest_claims = [
            claim for claim in claims if claim[date_column] == earliest_date
        ]
        return earliest_claims

    @staticmethod
    def _sort_claims_by_date(claims, date_column='clm_from_dt', reverse=False):
        return sorted(
            claims,
            key=lambda claim: claim[date_column], reverse=reverse
        )

    def group_claims_by_date(self, claims, date_column='clm_from_dt', window_length=30):
        """
        Given a list of claims, group claims into episodes by claim expense date.

        To avoid duplication, each claim is assigned to at most one episode of care.

        Args:
            claims (list(Claim)): list of claims to be grouped into episodes of care
            date_column (str): name of the column to use as date for claims
            window_length (int): number of days to analyze and look for additional claims
        Returns:
            list(list(Claim)), where each inner list forms a single episode.
        """
        logger.debug('Group claims by date using date_column - {}, window_length - {}'.format(
            date_column, window_length))
        if not claims:
            return []

        sorted_claims = self._sort_claims_by_date(claims)

        # Start with the first claim as its own episode.
        episodes = [[sorted_claims[0]]]
        current_episode_start_date = sorted_claims[0][date_column]

        # For each subsequent claim, check whether it falls within the current window.
        # If so, add it to the current episode.
        # If not, start a new episode with the current claim.
        for claim in sorted_claims[1:]:
            claim_date = claim[date_column]
            date_diff = (claim_date - current_episode_start_date).days

            if date_diff <= 30:
                episodes[-1].append(claim)
            else:
                episodes.append([claim])
                current_episode_start_date = claim[date_column]

        return episodes

    def get_eligible_instances(self, claims, date_column='clm_from_dt', window_length=30):
        """
        Group claims together into eligible instances.

        Returns a list of eligible instances, which are themselves lists of claims.

        Args:
            claims (list(Claim)): claims to be grouped by benefificary and assigned into episodes
            date_column (str): name of the column to use as date for claims
            window_length (int): number of days to analyze and look for additional claims
        Returns:
            list(list(Claim)), where each inner list is a single eligible instance.
        """
        logger.debug('Get eligible instances using date_column - {}, window_length - {}'.format(
            date_column, window_length))

        eligible_instances = []

        claims_by_beneficiary = self.group_claims_by_field_values(self.fields_to_group_by, claims)
        # Within each beneficiary's subset of claims, group the subset so that each
        # each eligible instance consists of claims within the specified date window.
        for beneficiary_claims_subset in claims_by_beneficiary:
            # Get the episodes for the current beneficiary.
            beneficiary_episodes = self.group_claims_by_date(
                beneficiary_claims_subset, date_column='clm_from_dt', window_length=30
            )
            for episode in beneficiary_episodes:
                # Within each episode, consider only the earliest claim that has a QDC.
                # If multiple claims have QDCs on the earliest date, use the most advantageous QDC.
                # If no claims have QDCs, consider the claims from the earliest date.
                all_relevant_claims = (
                    self.filter_by_presence_of_quality_codes(episode) or episode
                )
                earliest_relevant_claims = self.get_claims_from_earliest_date(all_relevant_claims)
                eligible_instances.append(earliest_relevant_claims)

        return eligible_instances
