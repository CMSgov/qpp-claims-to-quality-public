"""
Methods to process a single TIN/NPI combination.

For a TIN, NPI, start_date, end_date, measures, the processor will:
- grab the data from Teradata
- loop over the measures to:
    - calculate the measure
    - log the results
- submit the results
"""
import sys
import traceback

from claims_to_quality.analyzer import measure_mapping
from claims_to_quality.analyzer.datasource import claim_reader
from claims_to_quality.analyzer.processing import claim_filtering, performance_period_handling
from claims_to_quality.analyzer.submission import qpp_measurement_set
from claims_to_quality.lib import newrelic_application
from claims_to_quality.lib.connectors import teradata_connector
from claims_to_quality.lib.qpp_logging import logging_config
from claims_to_quality.lib.sqs_methods import message_handling
from claims_to_quality.lib.teradata_methods import teradata_errors

import newrelic.agent

logger = logging_config.get_logger(__name__)


class Processor(object):
    """
    Processor for SQS messages of TIN/NPIS.

    Takes one message at a time through its 'safe_process_message' function.
    """

    def __init__(
            self,
            start_date,
            end_date,
            measures,
            infer_performance_period):
        """
        Initialize Processor.

        :param start_date: Processing start date
        :type start_date: date
        :param end_date: Processing end date
        :type end_date: date
        :param measures: Measures to calcuate
        :type measures: list
        """
        self.start_date = start_date
        self.end_date = end_date
        self.measures = measures
        self.measure_calculators = measure_mapping.get_measure_calculators(measures)
        self.measure_definitions = [
            calculator.measure_definition for calculator in self.measure_calculators.values()
        ]
        self.infer_performance_period = infer_performance_period
        self.claim_reader = claim_reader.ClaimsDataReader()
        self.session = teradata_connector.teradata_connection()
        self.count = 0
        self.count_no_claims = 0
        self.count_errors = 0

    def process_batch_messages(self, messages):
        """Process a batch of SQS messages."""
        logger.debug('Starting processing for batch.')
        decoded_messages = message_handling.decode_messages(messages)
        logger.info('Processing batch of {batch_size} providers.'.format(batch_size=len(messages)))
        batch_claims_data = self._safe_get_batch(decoded_messages)

        if '046' in self.measures:
            self.measure_calculators['046'].get_batch_discharge_dates(batch_claims_data)

        return [
            self._safe_process_provider(batch_claims_data, provider)
            for provider in decoded_messages
        ]

    @newrelic.agent.background_task(
        newrelic_application.get(),
        name='safe-process-provider',
        group='Task')
    def _safe_process_provider(self, batch_claims_data, provider):
        """
        Safely process a provider.

        Input is a {tin, npi, message} dict.
        """
        try:
            provider_tin = provider.get('tin')
            provider_npi = provider.get('npi')
            claims_data = Processor._get_data_from_batch(
                batch_claims_data, provider_tin, provider_npi)
            if not claims_data:
                logger.info('No claims to process for NPI: {}.'.format(provider_npi))
                measurement_set = None
                self.count = self._count(self.count, 'processed')
                self.count_no_claims = self._count(self.count_no_claims, 'with no claims')
            else:
                measurement_set = self.process_provider(
                    provider_tin,
                    provider_npi,
                    claims_data=claims_data
                )
                self.count = self._count(self.count, 'processed')
        except Exception as error:
            self.count_errors = self._count(self.count_errors, 'errored out')
            logger.error(self._get_error_message_details(error))
            # Set this flag to True for provider handling in Submitter.
            provider['processing_error'] = True
            return provider

        provider['measurement_set'] = measurement_set
        provider['processing_error'] = False
        return provider

    @newrelic.agent.function_trace(name='process-provider', group='Task')
    def process_provider(
            self,
            tin,
            npi,
            claims_data):
        """
        Process a provider.

        Given a tin, npi combination and the associated list of claims, determine
        performance_handling dates, calculate measures and submit results if asked.

        Args:
            npi (str): Provider national provider identification number.
            tin (str): Provider tax identification number.
            claims_data [claims]: claim data associated with the provider.
        Returns:
            measurement_set {measurement_set}
        """
        logger.debug('Processing NPI: {} from {} to {}'.format(npi, self.start_date, self.end_date))

        performance_start = self.start_date
        performance_end = self.end_date

        measurement_set = qpp_measurement_set.MeasurementSet(
            tin=tin,
            npi=npi,
            performance_start=performance_start,
            performance_end=performance_end
        )

        # If no quality codes were submitted, exit early.
        if not claim_filtering.do_any_claims_have_quality_codes(claims_data):
            logger.info('No quality codes submitted for provider NPI: {} within {} claims'.format(
                npi, len(claims_data)))
            return measurement_set

        # If using the inferred performance period, filter claims as necessary
        # and use the new performance start and end dates when building the submission.
        if self.infer_performance_period:
            logger.debug('Inferring performance period.')
            performance_start, performance_end = \
                performance_period_handling.determine_performance_period(
                    claims_data=claims_data,
                    min_date=self.start_date,
                    max_date=self.end_date,
                )

            claims_data = claim_filtering.filter_claims_by_date(
                claims_data=claims_data,
                from_date=performance_start,
                to_date=performance_end,
            )

            measurement_set.update_performance_period(
                performance_start=performance_start, performance_end=performance_end)

        measurement_set = self._calculate_measures(
            measurement_set, claims_data, tin, npi, performance_start, performance_end)

        return measurement_set

    @newrelic.agent.function_trace(name='calculate-measures', group='Task')
    def _calculate_measures(
            self, measurement_set, claims_data, tin, npi, performance_start, performance_end):
        """
        Calculate measures for given provider.

        Returns a MeasurementSet object for submission to the Nava API.
        """
        logger.debug('Calculating measures - {}'.format(self.measures))
        measures_added = 0
        for measure_number in self.measures:
            logger.debug('Calculating measure - {}'.format(measure_number))

            measure_calculator, results = self._calculate_measure(
                claims_data=claims_data,
                measure_number=measure_number
            )

            if measure_calculator.has_multiple_strata:
                measure_added = measurement_set.add_measure_with_multiple_strata(
                    measure_number=measure_number,
                    measure_results=results
                )
            else:
                measure_added = measurement_set.add_measure(
                    measure_number=measure_number,
                    measure_results=results
                )

            measures_added += measure_added

        logger.info('{} measure{} recorded for this provider.'.format(
            measures_added,
            '' if measures_added == 1 else 's'))

        return measurement_set

    @newrelic.agent.function_trace(name='calculate-measure', group='Task')
    def _calculate_measure(self, claims_data, measure_number):
        """
        Calculate numerator and denominator for given provider/measure.

        Returns results in the form: {'eligible_population': 0,
            'performance_met': 0, 'performance_not_met': 0, 'reporting_met': 0}.
        """
        # Build the JSON object for qpp-measurement-sets-api.
        measure_calculator = self.measure_calculators[measure_number]
        results = measure_calculator.execute(claims_data)
        return measure_calculator, results

    # TODO - Move data handling functions to their own file or to claim_reader.py.
    def _get_batch(self, tin_list, npi_list):
        batch_claims_data = self.claim_reader.load_batch_from_db(
            provider_tin_list=tin_list,
            provider_npi_list=npi_list,
            start_date=self.start_date,
            end_date=self.end_date,
            session=self.session
        )

        # Restrict attention to the claims with measure-relevant procedure codes.
        return {
            identifier: claim_filtering.filter_claims_by_measure_procedure_codes(
                claims_data=claims, measure_definitions=self.measure_definitions
            )
            for identifier, claims in batch_claims_data.items()
        }

    @newrelic.agent.background_task(
        newrelic_application.get(),
        name='get-safe-batch',
        group='Task')
    def _safe_get_batch(self, decoded_messages):
        tin_list, npi_list = message_handling.get_tin_npi_list(decoded_messages)
        logger.info(
            'Load batch of {batch_size} providers.'.format(batch_size=len(decoded_messages))
        )
        try:
            return self._get_batch(tin_list=tin_list, npi_list=npi_list)
        except teradata_errors.TeradataError:
            self.session = teradata_connector.teradata_connection()
        return self._get_batch(tin_list=tin_list, npi_list=npi_list)

    @staticmethod
    @newrelic.agent.function_trace(name='get-data-from-batch', group='Task')
    def _get_data_from_batch(batch_claims_data, provider_tin, provider_npi):
        identifier = (provider_tin, provider_npi)
        claims_data = batch_claims_data.get(identifier, None)
        if claims_data is None:
            logger.error('No result in batch_claims_data for NPI: {}!'.format(provider_npi))
        return claims_data

    @staticmethod
    def _get_error_message_details(error):
        error_traceback = sys.exc_info()[-1]
        stk = traceback.extract_tb(error_traceback, 1)

        return (
            '{error_class} processing TIN / NPI message! '
            'In {function}, the following error happened - {detail} at line {line}. '
        ).format(
            error_class=error.__class__.__name__,
            function=stk[0][2],
            detail=error.args[0],
            line=stk[-1][1]
        )

    @staticmethod
    def _count(count, message='processed'):
        COUNTER_LOG_INTERVAL = 1
        count += 1
        if count and count % COUNTER_LOG_INTERVAL == 0:
            logger.info('{} providers {}.'.format(COUNTER_LOG_INTERVAL, message))
        return count
