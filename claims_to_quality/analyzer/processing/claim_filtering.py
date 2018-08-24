"""Methods for filtering claims, not associated with particular measures."""
import functools

from claims_to_quality.analyzer.datasource import code_reader
from claims_to_quality.lib.qpp_logging import logging_config

import newrelic.agent


logger = logging_config.get_logger(__name__)

QUALITY_CODES = set(code_reader.load_quality_codes())


def filter_claims_by_date(claims_data, from_date, to_date):
    """Return claims falling in the specified date range."""
    return [
        claim for claim in claims_data
        if (from_date <= claim.clm_from_dt <= to_date)
    ]


def does_claim_have_quality_codes(claim, quality_codes=QUALITY_CODES):
    """Ascertain whether a claim has any quality codes present on its lines."""
    return not quality_codes.isdisjoint(claim.get_procedure_codes())


def do_any_claims_have_quality_codes(claims_data, quality_codes=QUALITY_CODES):
    """Ascertain whether any claims have quality codes."""
    quality_code_set = set(quality_codes)
    return any((does_claim_have_quality_codes(claim, quality_code_set) for claim in claims_data))


def does_claim_have_relevant_procedure_codes(claim, procedure_codes):
    """Ascertain whether any claims have matching procedure codes."""
    return not procedure_codes.isdisjoint(claim.get_procedure_codes())


@newrelic.agent.function_trace(name='filter-claims-by-qpp-relevant-procedure-codes', group='Task')
def filter_claims_by_measure_procedure_codes(claims_data, measure_definitions):
    """Return claims containing any measure-relevant procedure codes."""
    procedure_codes = {
        code for measure in measure_definitions
        for code in measure.procedure_code_map
    }

    does_claim_meet_filter_condition = functools.partial(
        does_claim_have_relevant_procedure_codes,
        procedure_codes=procedure_codes
    )
    return list(filter(does_claim_meet_filter_condition, claims_data))
