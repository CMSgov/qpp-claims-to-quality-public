"""
Methods to submit results after processing of TIN/NPI.

- submit the results
- delete SQS message if processed.
"""
from claims_to_quality.analyzer.submission import api_submitter
from claims_to_quality.lib import newrelic_application
from claims_to_quality.lib.qpp_logging import logging_config

import newrelic.agent

import requests

logger = logging_config.get_logger(__name__)


class Submitter(object):
    """
    Processor for SQS messages of TIN/NPIS.

    Takes one message at a time through its 'safe_process_message' function.
    """

    def __init__(
            self,
            remove_messages,
            send_submissions,
            patch_update=False):
        """
        Initialize Submitter.

        :param remove_messages: Remove messages from queue when DONE with no error
        :type remove_messages: bool
        :param send_submissions: Activate sending submissions to the Submission API.
        :type send_submissions: bool
        """
        self.remove_messages = remove_messages
        self.send_submissions = send_submissions
        self.patch_update = patch_update

    @newrelic.agent.background_task(
        newrelic_application.get(),
        name='submit-batch',
        group='Task')
    def submit_batch(self, providers):
        """
        Submit batch of processed providers.

        Expecting a list of provider dicts with measurement_set info.
        Provider should contain the following keys:
            - tin
            - npi
            - message (SQS message)
            - processing_error
            - measurement_set (if available)
        """
        for provider in providers:
            # If there is a processing error, do not submit and do not delete the SQS message.
            if provider['processing_error']:
                continue

            measurement_set = provider.get('measurement_set', None)
            provider_tin = provider.get('tin')
            provider_npi = provider.get('npi')

            try:
                self._send_submissions(provider_tin, provider_npi, measurement_set)
            except requests.exceptions.HTTPError as e:
                # If there is a submission error, do not delete the SQS message from the queue.
                logger.warning(str(e) + 'NPI: {}'.format(provider_npi))
                logger.info('1 providers errored out.')
                continue

            # If processing and submission were successful and `remove_messages` is True,
            # remove the SQS messages and log the removal.
            self._process_after_submission(provider)

    @newrelic.agent.function_trace(name='send-submissions-if-not-empty', group='Task')
    def _send_submissions(self, tin, npi, measurement_set):
        if not measurement_set:
            # The following log message happens when providers have no claims with measure-relevant
            # procedure codes.
            logger.info(
                'No measurement set to submit after processing for provider NPI: {}'.format(npi)
            )
            return

        if measurement_set.is_empty():
            # The following log message happens when providers have no claims with both
            # measure-relevant procedure and quality codes.
            logger.info('Empty measurement. Not submitting for provider NPI: {}'.format(npi))
            return

        if self.send_submissions:
            logger.info('Submitting results for provider NPI: {}'.format(npi))
            api_submitter.submit_to_measurement_sets_api(
                measurement_set, patch_update=self.patch_update
            )
            logger.info('Submitted results successfully for provider NPI: {}'.format(npi))

    def _process_after_submission(self, provider):
        if self.remove_messages:
            provider_npi = provider.get('npi', None)
            provider['message'].delete()
            logger.info('Deleted message from SQS for provider NPI: {}'.format(provider_npi))
