"""Subclass of QPP Measure to calculate measure 46."""
import collections
import datetime
from math import floor

from claims_to_quality.analyzer.calculation.visit_measure import VisitMeasure
from claims_to_quality.analyzer.processing import claim_filtering
from claims_to_quality.lib import newrelic_application
from claims_to_quality.lib.connectors import idr_queries
from claims_to_quality.lib.helpers.decorators import override
from claims_to_quality.lib.qpp_logging import logging_config
from claims_to_quality.lib.teradata_methods import execute

import newrelic.agent

logger = logging_config.get_logger(__name__)


class Measure46(VisitMeasure):
    """
    Represents measure 46: Medication Reconciliation Post-Discharge.

    This measure concerns the reconciliation of lists of medications for patients who were recently
    (within 30 days) discharged from a hospital. Each provider who sees a patient within 30 days
    from discharge and wishes to report this measure must document that they have reconciled the
    list of the patient's medications.

    # Calculation Strategy
    1. Iterate through all claims for provider A.
    2. Check if provider A has submitted any g-codes relevant to this measure
        (demonstrating intention to report this measure). If not, do not report this measure.
    3. Filter to instances in which a claim for provider includes relevant encounter codes.
    4. Query the IDR to determine all beneficiary discharge events for the beneficiaries on the
        above list of claims.
    5. For each beneficiary discharge event, determine which claims fall within 30 subsequent days.
    6. Score each discharge event according to the g-codes submitted on the corresponding claims,
        taking the most advantageous claim for each discharge event.

    # Further Considerations
    - More than one provider can be scored for this measure per discharge.
    - An individual provider may be scored more than once per discharge event. This has been
        confirmed by the measure stewards at PQMM despite the language in the measure PDFs.
    - This measure is not part of an EMA cluster.
    """

    HIDDEN_CODES = [
        '99221',
        '99222',
        '99223',
        '99231',
        '99232',
        '99233',
        '99234',
        '99235',
        '99236',
        '99238',
        '99239',
        '99251',
        '99252',
        '99253',
        '99254',
        '99255',
    ]

    STRATA_NAME_TO_AGE_RANGES_MAP = {
        '18-64': {
            'min_age': 18,
            'max_age': 64
        },
        '65+': {
            'min_age': 65,
        },
        'overall': {
            'min_age': 18
        }
    }

    def __init__(self, *args, **kwargs):
        """Instantiate a Measure46."""
        super(Measure46, self).__init__(*args, **kwargs)
        self._discharge_period = 30  # Discharge period to consider in days.
        self.discharge_dates_by_beneficiary = collections.defaultdict(set)

    @newrelic.agent.function_trace(name='execute-measure-46', group='Task')
    @override
    def execute(self, claims):
        """
        Evaluate a provider dataset according to the measure specification.

        Because measure 46 has multiple strata to score on, the implementation of this method
        from QPPMeasure is overridden in Measure46.

        Order of operations:
            1) Filter claims data to relevant claims only.
                Filter by age, sex, diagnosis or encounter code.
            2) Query the IDR to see which claims came within 30 days of a discharge event.
            3) Group claims into eligible instances.
            4) Sort eligible instances into strata based on patient age at date of service.
            5) Assign performance markers to each eligible instance.
            6) Aggregate totals by performance marker across all eligible instances and strata.

        Returns the measure results as a list of dictionaries, each with the form:
            - name: stratum_name
            - results: stratum results dictionary with the following keys:
                - performance_met
                - performance_not_met
                - eligible_population_exclusion
                - eligible_population_exception
                - eligible_population
        """
        relevant_claims = self.filter_by_eligibility_criteria(claims)
        eligible_instances = self.get_eligible_instances(relevant_claims)
        eligible_instances_by_stratum = self.assign_eligible_instances_to_strata(eligible_instances)

        measure_results = []
        for stratum_dict in eligible_instances_by_stratum:
            stratum_results = self.score_eligible_instances(stratum_dict['instances'])
            measure_results.append(
                {
                    'name': stratum_dict['name'],
                    'results': {
                        'eligible_population_exclusion': stratum_results[
                            'eligiblePopulationExclusion'],
                        'eligible_population_exception': stratum_results[
                            'eligiblePopulationException'],
                        'performance_met': stratum_results['performanceMet'],
                        'performance_not_met': stratum_results['performanceNotMet'],
                        'eligible_population':
                            sum(stratum_results.values())
                    }
                }
            )
        return measure_results

    @newrelic.agent.background_task(
        newrelic_application.get(), name='get-batch-discharge-dates', group='Task')
    def get_batch_discharge_dates(self, batch_claims_data):
        """
        Query the IDR for discharge dates relevant to Measure 46 for a batch of providers.

        The results are stored in the Measure46 calculator object for use during calculation.
        """
        logger.info(
            'Finding discharge dates for batch of {} providers'.format(len(batch_claims_data)))
        # Reset attribute with new batch.
        self.clear_discharge_date_cache()
        tins_to_query = []
        npis_to_query = []
        bene_sks_to_query = []
        quality_codes = self.measure_definition.quality_code_map

        for provider in batch_claims_data:
            claims = batch_claims_data[provider]
            if claim_filtering.do_any_claims_have_quality_codes(claims, quality_codes):
                tins_to_query.extend([provider[0]])
                npis_to_query.extend([provider[1]])
                bene_sks_to_query.extend([claim.bene_sk for claim in claims])

        self._get_discharge_dates_by_provider(
            tins=tins_to_query,
            npis=npis_to_query,
            bene_sks=bene_sks_to_query
        )

    def assign_eligible_instances_to_strata(self, eligible_instances):
        """
        Assign eligible instances to different measure strata.

        Args:
            eligible_instances (list(list(Claim))): Claims to be assign to different strata.
        Returns:
            List of dictionaries, where each dictionary has the form:
                - name: stratum_name
                - instances: eligible instances for that stratum
        """
        logger.debug('Assign eligible instances to different strata.')

        eligible_instances_by_stratum = []

        for stratum in self.measure_definition.strata:
            age_ranges = self.STRATA_NAME_TO_AGE_RANGES_MAP[stratum.name]
            eligible_instances_by_stratum.append(
                {
                    'name': stratum.name,
                    'instances': self._filter_eligible_instances_by_patient_age(
                        eligible_instances=eligible_instances,
                        min_age=age_ranges.get('min_age', 0),
                        max_age=age_ranges.get('max_age', float('inf'))
                    )
                }
            )
        return eligible_instances_by_stratum

    @staticmethod
    def _filter_eligible_instances_by_patient_age(eligible_instances, min_age, max_age):
        """Return the instances where the beneficiary's age is falls in the given range."""
        logger.debug('Filter eligible instances by patient age.')
        return [
            instance for instance in eligible_instances
            if min_age <= floor(instance[0].bene_age) <= max_age
        ]

    @override
    def filter_by_eligibility_criteria(self, claims):
        """Filter out claims that do not meet any of the measure's eligibility options."""
        quality_codes = self.measure_definition.get_measure_quality_codes()
        if not claim_filtering.do_any_claims_have_quality_codes(
                claims, quality_codes=quality_codes):
            return []

        prefilter_claims = super(Measure46, self).filter_by_eligibility_criteria(claims)
        return self._filter_by_qualifying_discharge(prefilter_claims)

    def _filter_by_qualifying_discharge(self, claims):
        """
        Filter the given list of claims and return only the claims that followed a discharge event.

        This method uses cached information, limiting the IDR queries to only the TINs, NPIs, and
        beneficiaries not already contained in the attribute `discharge_dates_by_beneficiary`.
        """
        missing_bene_sks = {
            claim.bene_sk
            for claim in claims
            if claim.bene_sk not in self.discharge_dates_by_beneficiary
        }
        missing_tins = {
            claim.clm_rndrg_prvdr_tax_num
            for claim in claims
            if claim.bene_sk in missing_bene_sks
        }
        missing_npis = {
            claim.clm_rndrg_prvdr_npi_num
            for claim in claims
            if claim.bene_sk in missing_bene_sks
        }

        self._get_discharge_dates_by_provider(
            tins=set(missing_tins),
            npis=set(missing_npis),
            bene_sks=missing_bene_sks
        )

        return [
            claim for claim in claims
            if self._in_date_range(
                claim, self.discharge_dates_by_beneficiary[claim.bene_sk]
            )
        ]

    def _in_date_range(self, claim, date_set):
        return any((
            [
                datetime.timedelta(
                    days=0
                ) <= claim.clm_from_dt - date <= datetime.timedelta(
                    days=self._discharge_period
                )
                for date in date_set
            ]))

    @newrelic.agent.function_trace(name='get-discharge-date', group='Task')
    def _get_discharge_dates_by_provider(self, tins, npis, bene_sks):
        """Query the IDR to find discharge dates for the given providers and beneficiaries."""
        logger.debug('Querying IDR for discharge dates for {} providers.'.format(len(tins)))

        if not tins or not npis or not bene_sks:
            return

        discharge_date_query = idr_queries.get_discharge_date_query(
            tins=tins,
            npis=npis,
            discharge_period=self._discharge_period,
            hidden_codes=self.HIDDEN_CODES
        )

        rows = execute.execute(discharge_date_query)
        discharge_dates_by_beneficiary = collections.defaultdict(set)

        if not rows:
            logger.debug('No discharge dates found.')

        for row in rows:
            discharge_dates_by_beneficiary[row['bene_sk']].add(row['clm_line_from_dt'])

        # For any beneficiaries with discharges, record their discharge dates.
        for bene_sk in discharge_dates_by_beneficiary:
            self.discharge_dates_by_beneficiary[bene_sk].update(
                discharge_dates_by_beneficiary[bene_sk]
            )

        for bene_sk in bene_sks:
            if bene_sk not in self.discharge_dates_by_beneficiary:
                self.discharge_dates_by_beneficiary[bene_sk] = set()

    def clear_discharge_date_cache(self):
        """Clear the cache of discharge dates to prevent it from growing too large."""
        self.discharge_dates_by_beneficiary = collections.defaultdict(set)
