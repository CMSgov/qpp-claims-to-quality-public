"""
Methods for determining reporting periods.

This module is used during 90-day-window determination.
"""
# TODO: Create Provider class to handle this logic.
import datetime

from claims_to_quality.analyzer.datasource import code_reader
from claims_to_quality.analyzer.processing import claim_filtering
from claims_to_quality.lib.qpp_logging import logging_config

import newrelic.agent


logger = logging_config.get_logger(__name__)

MINIMUM_REPORTING_PERIOD = datetime.timedelta(days=90)
QUALITY_CODES = set(code_reader.load_quality_codes())


class MissingCodeException(Exception):
    """Indicates that a particular code could not be found."""


def _determine_quality_code_submission_period(claims_data, min_date, max_date):
    """
    Calculate first and last submission of quality codes in the provided claims.

    Returns a tuple (first_date, last_date).
    """
    quality_code_dates = [
        claim.clm_from_dt for claim in claims_data
        if (
            claim_filtering.does_claim_have_quality_codes(claim=claim) and
            (min_date <= claim.clm_from_dt <= max_date)
        )
    ]
    try:
        first_submission_date = min(quality_code_dates)
        last_submission_date = max(quality_code_dates)
    except ValueError:
        raise MissingCodeException('No quality codes found for the provided date range.')

    return (first_submission_date, last_submission_date)


@newrelic.agent.function_trace(name='determine-performance-period', group='Task')
def determine_performance_period(claims_data, min_date, max_date):
    """
    Determine the extended reporting period given information about a provider's claims.

    When no quality codes are found, a MissingCodeException is raised.

    When the reporting period is shorter than the minimum allowed period, expand it as follows:
        - If possible, move the end date later
        - Otherwise, move the start date earlier

    Args:
        - claims_data (list(claim)): the claims for the provider
        - min_date (date): the earliest date considered for quality code submission
        - max_date (date): the latest date considered for quality code submission
    Returns:
        - performance_start (date): the start of the true reporting period
        - performance_end (date): the end of the true reporting period
    """
    first_submission_date, last_submission_date = _determine_quality_code_submission_period(
        claims_data=claims_data,
        min_date=min_date,
        max_date=max_date
    )
    # The latest possible start date is the minimum_period_in_days before the max_date.
    last_possible_start_date = max_date - MINIMUM_REPORTING_PERIOD
    # If the observed start date was after the latest possible start date, move it earlier.
    performance_start = min(first_submission_date, last_possible_start_date)

    # The end date defaults to the last date of quality codes.
    performance_end = last_submission_date

    # If necessary, move the end date later to make the period long enough.
    # Do not move the end date beyond the max_date.
    if (last_submission_date - performance_start) < MINIMUM_REPORTING_PERIOD:
        performance_end = min(max_date, performance_start + MINIMUM_REPORTING_PERIOD)

    return (performance_start, performance_end)
