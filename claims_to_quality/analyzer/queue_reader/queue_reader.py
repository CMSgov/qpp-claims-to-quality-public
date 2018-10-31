"""
Method to read and process the tin/npi queue.

This will start a measure caclulation / submission process for each message.
"""
from datetime import datetime

from claims_to_quality.lib import newrelic_application
from claims_to_quality.lib.connectors import sqs_connector
from claims_to_quality.lib.qpp_logging import logging_config
from claims_to_quality.lib.sqs_methods import message_handling

import newrelic.agent

logger = logging_config.get_logger(__name__)


class QueueReader(object):
    """Read SQS queue and yield messages with TIN/NPI."""

    def __init__(
            self,
            queue_name,
            pull_batch_size):
        """Initiating a QueueReader.

        :param queue_name: SQS queue name
        :type queue_name: str
        :param pull_batch_size: Max number of messages to pull at once
        :type pull_batch_size: int
        # Note: pull_batch_size needs to be < 10.
        """
        self._queue = sqs_connector.get_queue(queue_name=queue_name)
        self._pull_batch_size = pull_batch_size

        logger.debug('Initiated queue reader {queue} at {time}'.format(
            queue=self._queue, time=datetime.now()))

    @newrelic.agent.function_trace(name='pull-batch-messages', group='Task')
    def _pull_next_batch(self):
        """Pull next batch from SQS queue."""
        messages = message_handling.get_messages(
            self._queue, pull_batch_size=self._pull_batch_size)
        logger.debug('Fetched {} messages to process.'.format(len(messages)))
        return messages

    @newrelic.agent.background_task(newrelic_application.get(), name='read-queue', group='Task')
    def read(self):
        """Start reading the SQS queue."""
        logger.debug('Start reading...')
        while True:
            messages = self._pull_next_batch()
            for message in messages:
                # TODO: Test messages and discard badly formatted ones.
                yield message
            if len(messages) > 0:
                logger.info('Passed {} messages from queue.'.format(len(messages)))

    @newrelic.agent.background_task(
        newrelic_application.get(), name='read-queue-batch', group='Task')
    def read_batch(self, batch_size):
        """Start reading the SQS queue."""
        logger.debug('Start reading in batches...')
        batch = []
        while True:
            messages = self._pull_next_batch()
            for message in messages:
                if len(batch) < batch_size:
                    batch.append(message)
                else:
                    yield batch
                    logger.debug('Passed {} messages batch from queue.'.format(len(batch)))
                    batch = [message]

            if len(messages) == 0 and len(batch) > 0:
                yield batch
                logger.debug('Passed {} messages batch from queue.'.format(len(batch)))
                batch = []
