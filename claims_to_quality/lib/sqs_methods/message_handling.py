"""Methods for handling sqs messages."""
import collections
import itertools
import logging

from claims_to_quality.lib.qpp_logging import logging_config

import newrelic.agent

import retrying

import ujson as json


logger = logging_config.get_logger(__name__)

# Make boto logger less noisy.
logging.getLogger('boto3').setLevel(logging.WARNING)
logging.getLogger('botocore').setLevel(logging.WARNING)
WAIT_TIME_FOR_QUEUE_SEND_FAILURE_RETRY = 10000  # 10 seconds in milliseconds
MAX_RETRY_ATTEMPTS = 10
BOTO_MAX_SEND_LIMIT = 10


def get_single_message(sqs_queue, wait_time_seconds=5):
    """Get a maximum of one message from the provided sqs queue."""
    messages = sqs_queue.receive_messages(
        MaxNumberOfMessages=1, WaitTimeSeconds=wait_time_seconds)
    if messages:
        return messages[0]
    else:
        return None


def get_messages(sqs_queue, pull_batch_size=10, wait_time_seconds=5):
    """Get n messages from the provided sqs queue."""
    messages = sqs_queue.receive_messages(
        MaxNumberOfMessages=pull_batch_size, WaitTimeSeconds=wait_time_seconds)
    return messages


def parse_message(message):
    """
    Parse provider information from an SQS message.

    Returns:
        A dictionary of the message, including the message itself.
    """
    try:
        parsed = json.loads(message.body)
        parsed.update({'message': message})
        return parsed
    except ValueError:
        logger.exception('Unable to process message.')
        return {'message': message}


def parse_messages(messages):
    """
    Parse provider information from SQS messages.

    Returns:
        A list of dictionaries of the messages.
    """
    return [parse_message(message) for message in messages]


def _verify_tin_npi(parsed_message):
    if parsed_message.get('tin', None) and parsed_message.get('npi', None):
        return True
    logger.warn(
        'Wrong format. could not extract TIN/NPI '
        'from message, moving on. (Not deleting).'
    )
    return False


def _tin_npi_verified(parsed_messages):
    return [message for message in parsed_messages if _verify_tin_npi(message)]


def decode_messages(messages):
    """Decode a list of SQS messages."""
    parsed_messages = parse_messages(messages)
    return _tin_npi_verified(parsed_messages)


def get_tin_npi_list(decoded_messages):
    """Decode messages and return lists of npis and tins."""
    if not decoded_messages:
        return (None, None)
    return zip(*[(provider.get('tin'), provider.get('npi')) for provider in decoded_messages])


@newrelic.agent.function_trace(name='send-sqs-messages', group='Task')
def send_messages(messages, sqs_queue):
    """
    Send messages to specified queue.

    Args:
        messages (iterator(str)): An iterator of messages to send to the queue.
        sqs_queue (boto3.Queue): A queue to send messages to.
    """
    response_counter = collections.Counter()
    for message_group in grouper(messages, chunk_size=BOTO_MAX_SEND_LIMIT):
        response_counter += _send_message_group(message_group, sqs_queue)

    return response_counter


def did_any_messages_fail_to_be_sent(response_counter):
    """Return True if the result has > 0 failures, False otherwise."""
    return response_counter['failed_total']


@retrying.retry(
    retry_on_result=did_any_messages_fail_to_be_sent,
    stop_max_attempt_number=MAX_RETRY_ATTEMPTS,
    wait_fixed=WAIT_TIME_FOR_QUEUE_SEND_FAILURE_RETRY
)
def _send_message_group(messages, sqs_queue):
    """
    Send a small group of messages to specified queue.

    Raises an AssertionError if the list of messages is too long.
    Raises a retrying.RetryError if the message cannot be sent after the given number of attempts.

    Args:
        messages (list(str)): A list of messages to send to the queue.
        sqs_queue (boto3.Queue): A queue to send messages to.
    """
    assert len(messages) <= BOTO_MAX_SEND_LIMIT
    # The message group may have been padded with None by `grouper`.
    entries = [
        create_entry(message, index)
        for index, message in enumerate(messages) if message is not None
    ]
    npis = [json.loads(message)['npi'] for message in messages if message is not None]

    # Create a warning message to log potential failures if necessary.
    warning_message = """
        Error during sending rows to SQS! NPIs potentially affected: {npis}. Retrying.
    """.format(npis=npis)

    try:
        response = sqs_queue.send_messages(Entries=entries)
    except Exception:
        logger.warning(warning_message)
        # Return a value so that retrying is initiated.
        return collections.Counter({
            'failed_total': len(npis),
        })

    # Log each failure individually. The log does not contain any message details.
    for failure in response.get('Failed', []):
        logging.warning('SQS message sending failed: {}'.format(failure))

    response_counter = count_responses(response)
    # If necessary, log all affected NPIs and retry.
    if did_any_messages_fail_to_be_sent(response_counter):
        logger.warning(warning_message)

    return response_counter


def create_entry(message_body, index):
    """Given a string message body, return a well-formatted entry for sending to SQS."""
    return {
        'Id': str(index),  # Needs to be unique within message group.
        'MessageBody': message_body
    }


def count_responses(response):
    """
    Count the number of failed messages due to sender error.

    Args:
        response (dict): Dictionary containing list of successful and failed messages
    """
    failed_messages = response.get('Failed', [])
    failed_total = len(failed_messages)
    failed_sender = sum(failure['SenderFault'] for failure in failed_messages)
    failed_other = failed_total - failed_sender

    return collections.Counter({
        'successful': len(response.get('Successful', [])),
        'failed_total': failed_total,
        'failed_sender': failed_sender,
        'failed_other': failed_other
    })


def grouper(iterable, chunk_size, fillvalue=None):
    """
    Collect data into fixed-length chunks or blocks.

    Sourced from itertools recipe.

    Args:
        iterable (iterator): Iterable to be grouped
        chunk_size (int): Size of groups to make
        fillvalue (object): Value to fill the group with if leftover spaces, defaults to None

    grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
    """
    args = [iter(iterable)] * chunk_size
    return itertools.zip_longest(*args, fillvalue=fillvalue)
