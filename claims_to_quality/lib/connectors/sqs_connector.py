"""Wrapper to connect to SQS queue."""
import boto3

from claims_to_quality.config import config
from claims_to_quality.lib.qpp_logging import logging_config

logger = logging_config.get_logger(__name__)


def get_queue(queue_name=None):
    """Create and return an SQS Queue."""
    if not queue_name:
        queue_name = config.get('aws.sqs.queue_name')

    logger.info('Getting SQS queue - {queue}.'.format(queue=queue_name))

    access_key_id = config.get('aws.sqs.access_key_id')
    secret_access_key = config.get('aws.sqs.secret_access_key')

    session = boto3.session.Session(
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        region_name='us-east-1')

    sqs = session.resource('sqs')
    queue = sqs.get_queue_by_name(QueueName=queue_name)

    logger.info('Returning SQS queue - {queue}.'.format(queue=queue_name))
    return queue
