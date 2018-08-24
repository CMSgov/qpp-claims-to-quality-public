"""Methods to submit a MeasurementSet object to Nava's API."""
import urllib.parse

from claims_to_quality.config import config
from claims_to_quality.lib.qpp_logging import logging_config

import newrelic.agent

import requests

from retrying import retry


logger = logging_config.get_logger(__name__)

STOP_MAX_ATTEMPT_NUMBER = 2
WAIT_FIXED_MILLISECONDS = 15 * 60 * 1000  # This must be >10 minutes due to rate limits.

STATUS_CODES_TO_RETRY_ON = {
    403: 'Forbidden',    # This is in fact the response for rate-limiting.
    408: 'Request Timeout',
    429: 'Too Many Requests',
    500: 'Internal Server Error',
    502: 'Bad Gateway',
    503: 'Service Unavailable',
    504: 'Gateway Timeout',
}


class NoMatchingMeasurementSetsException(Exception):
    """Indicates that no C2Q measurement sets can be found within a QPP submission."""


class NoMatchingSubmissionsException(Exception):
    """Indicates that no matching QPP submissions exist in the submission API."""


def _retry_on_fixable_request_errors(exception):
    """
    Return True for exceptions that could be fixed by retrying.

    Used by the retrying module to attempt to re-submit for certain errors only.
    """
    return (
        isinstance(exception, requests.exceptions.HTTPError) and
        exception.response.status_code in STATUS_CODES_TO_RETRY_ON
    ) or (
        isinstance(exception, requests.exceptions.ConnectTimeout)
    )


def _handle_http_error(response, message):
    """Handler for http errors."""
    http_error = False
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        http_error = True
    if http_error:
        logger.warning(
            'HTTP error {status_code} during {msg}.'.format(
                status_code=response.status_code,
                msg=message
            )
        )
        raise requests.exceptions.HTTPError(
            'HTTP error {status_code} during {msg}.'.format(
                status_code=response.status_code,
                msg=message
            ), response=response
        )


@newrelic.agent.function_trace(name='submit-to-measurement-sets-api', group='Task')
@retry(stop_max_attempt_number=STOP_MAX_ATTEMPT_NUMBER, wait_fixed=WAIT_FIXED_MILLISECONDS)
def submit_to_measurement_sets_api(measurement_set, patch_update):
    """
    Send the submission object to the appropriate API endpoint.

    Retry using exponential backoff.
    """
    return _submit_to_measurement_sets_api(measurement_set, patch_update=patch_update)


def _submit_to_measurement_sets_api(measurement_set, patch_update):
    """Send the submission object to the appropriate API endpoint."""
    # TODO: Add a separate method to validate submission without sending it.
    # Attempt to find existing measurement sets if any exist.
    try:
        matching_submission = get_existing_submissions(measurement_set)
        measurement_set_id = get_measurement_set_id_from_submission(matching_submission)
    except(NoMatchingSubmissionsException, NoMatchingMeasurementSetsException):
        # If no measurement sets exist, we can safely POST.
        response = _post_to_measurement_sets_api(measurement_set)
    else:
        # If a measurement set does exist, we use the existing id to PUT or PATCH.
        if patch_update:
            response = _patch_to_measurement_sets_api(measurement_set, measurement_set_id)
        else:
            response = _put_to_measurement_sets_api(measurement_set, measurement_set_id)

    _handle_http_error(response, message='submit_to_measurement_sets_api')

    return response


@newrelic.agent.function_trace(name='get-verify-submissions', group='Task')
@retry(stop_max_attempt_number=STOP_MAX_ATTEMPT_NUMBER, wait_fixed=WAIT_FIXED_MILLISECONDS)
def get_submissions(npi=None, tin=None, start_index=0):
    """
    Simple GET request to check if submissions have been made.

    If NPI is provided, return submissions for this NPI.
    If start_index is provided, return submissions after the start_index.
    Else, simply return the first 10 submissions starting at start_index=0.

    FIXME: Move this into a different file, this is not part of the api submitter.
    """
    logger.debug('Making a simple GET request to verify submissions.')

    endpoint_url = urllib.parse.urljoin(
        config.get('submission.endpoint'),
        'submissions'
    )

    params = {
        'startIndex': start_index,
    }

    if npi:
        params['nationalProviderIdentifier'] = npi
    headers = get_headers()

    if tin:
        headers.update({'qpp-taxpayer-identification-number': tin})

    response = requests.get(endpoint_url, params=params, headers=headers)

    # If the request failed, raise an error.
    http_error = False
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        http_error = True
    if http_error:
        logger.warning('HTTP error {} during get_existing_submissions.'.format(
            response.status_code
        ))
        raise requests.exceptions.HTTPError(
            'HTTP error {} during get_existing_submissions.'.format(
                response.status_code
            ), response=response
        )

    return response.json()


@newrelic.agent.function_trace(name='get-existing-submissions', group='Task')
def get_existing_submissions(measurement_set):
    """
    Check to see if a submission already exists for the given identifiers.

    Returns None if no submission exists. Otherwise, returns the existing submissionId.
    """
    logger.debug('Making GET request to the submissions API.')

    endpoint_url = urllib.parse.urljoin(
        config.get('submission.endpoint'),
        'submissions'
    )

    params = {
        'itemsPerPage': 99999,
        'nationalProviderIdentifier':
            measurement_set.data['submission']['nationalProviderIdentifier']
    }

    headers = get_headers()
    headers.update(
        {'qpp-taxpayer-identification-number':
            measurement_set.data['submission']['taxpayerIdentificationNumber']}
    )

    # Look for matching submissions.
    response = requests.get(endpoint_url, params=params, headers=headers)

    # If the request failed, raise an error.
    http_error = False
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        http_error = True
    if http_error:
        raise requests.exceptions.HTTPError(
            'HTTP error {} during get_existing_submissions.'.format(
                response.status_code
            ), response=response
        )

    existing_submissions = response.json()['data']['submissions']
    existing_submissions_in_same_year = [
        s for s in existing_submissions
        if s['performanceYear'] == measurement_set.data['submission']['performanceYear']
    ]

    # If at least one submission already exists for performance year, return the first match.
    if len(existing_submissions_in_same_year) > 0:
        return existing_submissions_in_same_year[0]
    # Otherwise, raise an exception.
    else:
        raise NoMatchingSubmissionsException


def get_measurement_set_id_from_submission(submission):
    """Return the C2Q measurement_set ID from a given JSON submission."""
    measurement_sets = [
        measurement_set for measurement_set in submission['measurementSets']
        if (
            measurement_set['category'] == 'quality' and
            measurement_set['submissionMethod'] == 'claims'
        )
    ]

    if measurement_sets:
        return measurement_sets[0]['id']
    else:
        raise NoMatchingMeasurementSetsException


def _patch_to_measurement_sets_api(measurement_set, existing_measurement_set_id):
    logger.debug('Making PATCH request to the measurement-sets API.')

    endpoint_url = urllib.parse.urljoin(config.get('submission.endpoint'), 'measurement-sets/')
    url = urllib.parse.urljoin(endpoint_url, str(existing_measurement_set_id))

    return requests.patch(
        url=url,
        data=measurement_set.to_json(),
        headers=get_headers(),
    )


def _put_to_measurement_sets_api(measurement_set, existing_measurement_set_id):
    logger.debug('Making PUT request to the measurement-sets API.')

    endpoint_url = urllib.parse.urljoin(config.get('submission.endpoint'), 'measurement-sets/')
    url = urllib.parse.urljoin(endpoint_url, str(existing_measurement_set_id))

    return requests.put(
        url=url,
        data=measurement_set.to_json(),
        headers=get_headers(),
    )


def delete_measurement_set_api(measurement_set_id):
    """Delete a measuremet set by id."""
    logger.warning('DELETING measurement {} set using the measurement-sets API.'.format(
        measurement_set_id)
    )
    endpoint_url = urllib.parse.urljoin(
        config.get('submission.endpoint'),
        'measurement-sets/'
    )
    url = urllib.parse.urljoin(endpoint_url, str(measurement_set_id))

    response = requests.delete(
        url=url,
        headers=get_headers()
    )

    _handle_http_error(response, 'delete_measurement_set')


def _post_to_measurement_sets_api(measurement_set):
    logger.debug('Making POST request to the measurement-sets API.')

    endpoint_url = urllib.parse.urljoin(config.get('submission.endpoint'), 'measurement-sets/')

    return requests.post(
        url=endpoint_url,
        data=measurement_set.to_json(),
        headers=get_headers()
    )


def get_headers():
    """Return base headers for Nava's APIs."""
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': 'Bearer {api_token}'.format(
            api_token=config.get('submission.api_token'))
    }
    if config.get('submission.cookie'):
        headers['Cookie'] = config.get('submission.cookie')

    return headers


def get_scoring_preview(measurement_set):
    """Send the submission object to the appropriate API endpoint and get scoring preview."""
    logger.debug('Sending measurement set to the score-preview endpoint.')
    endpoint_url = urllib.parse.urljoin(
        config.get('submission.endpoint'),
        'submissions/score-preview'
    )
    response = requests.post(
        url=endpoint_url,
        data=measurement_set.prepare_for_scoring(),
        headers=get_headers()
    )

    _handle_http_error(response, 'scoring_preview')

    return response.json()
