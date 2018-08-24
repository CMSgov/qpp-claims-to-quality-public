"""Processes a provider's claims to assess whether they meet CT Scan criteria."""
from claims_to_quality.analyzer.calculation.qpp_measure import QPPMeasure
from claims_to_quality.analyzer.processing import claim_filtering
from claims_to_quality.lib.connectors import idr_queries
from claims_to_quality.lib.helpers.decorators import override
from claims_to_quality.lib.qpp_logging import logging_config
from claims_to_quality.lib.teradata_methods import execute

import newrelic.agent

logger = logging_config.get_logger(__name__)


class CTScanMeasure(QPPMeasure):
    """
    Represents measures 415 and 416.

    If a provider has submitted any G-codes relevant to the measure:
        1. check to see if there is a claim which includes relevant diagnosis and encounter
        codes, as usual.
        2. If there is, then check the IDR to see if the beneficiary received a CT scan on any of
        the same dates of service.
    """

    def __init__(self, *args, **kwargs):
        """Initialize CT Scan Measure instance."""
        super(CTScanMeasure, self).__init__(*args, **kwargs)
        self.fields_to_group_by = ['bene_sk']

        self.procedure_codes = [
            procedure_code.code
            for eligibility_option in self.eligibility_options
            for procedure_code in eligibility_option.procedure_codes
        ]

    @newrelic.agent.function_trace(name='execute-ct-scan-measure', group='Task')
    @override
    def execute(self, claims):
        """Execute CT Scan Measure calculation."""
        return super(CTScanMeasure, self).execute(claims)

    def _filter_by_ct_scan(self, claims):
        """
        Return a list of eligible claims based on measure criteria.

        For CT Scan best practice measures, this means instances for which CT scans were performed
        (perhaps by a different provider) on the same day.
        """
        bene_date_set = {
            (claim.bene_sk, claim_line.clm_line_from_dt)
            for claim in claims
            for claim_line in claim.claim_lines
            if claim_line.clm_line_hcpcs_cd in self.procedure_codes
        }

        ct_scan_benes_and_dates = self._get_ct_scan_beneficiaries_and_dates(bene_date_set)

        return [
            claim for claim in claims
            if any(
                (
                    (claim.bene_sk, claim_line.clm_line_from_dt) in ct_scan_benes_and_dates
                    for claim_line in claim.claim_lines
                    if claim_line.clm_line_hcpcs_cd in self.procedure_codes
                )
            )
        ]

    @override
    def filter_by_eligibility_criteria(self, claims):
        """Return a list of eligible claims based on measure criteria."""
        quality_codes = self.measure_definition.get_measure_quality_codes()

        if not claim_filtering.do_any_claims_have_quality_codes(
                claims_data=claims, quality_codes=quality_codes):
            return []

        prefilter_claims = super(CTScanMeasure, self).filter_by_eligibility_criteria(claims)
        return CTScanMeasure._filter_by_ct_scan(self, prefilter_claims)

    @newrelic.agent.function_trace(name='get-ct-scan-dates-by-beneficiary', group='Task')
    def _get_ct_scan_beneficiaries_and_dates(self, bene_date_set):
        """Query the IDR for matching CT scans for the given beneficiaries on the given dates."""
        if not bene_date_set:
            return {}

        logger.debug('Query IDR for CT scan dates.')

        ct_scan_query = idr_queries.get_ct_scan_query(bene_date_set=bene_date_set)
        rows = execute.execute(ct_scan_query)

        return {
            (row['bene_sk'], row['clm_line_from_dt']) for row in rows
        }
