#!/usr/local/bin/python3.6
"""
Submission API Interactor.

Script to interact with the submission API.
To use this file, define your own functions in this file:
- _submission_filter(submission) -> bool (defaults to True == to_process)
- _measurement_set_filter(measurement_set) -> bool (defaults to True == to_process)
- _processing(measurement_set_ids) -> NA. Eg. write to file or extract list of TIN/NPI.

They will be used to filter results at each level before processing the submission.
"""
import argparse
import csv
import json

from claims_to_quality.analyzer.submission import api_submitter
from claims_to_quality.config import config
from claims_to_quality.lib.qpp_logging import logging_config

logger = logging_config.get_logger(__name__)

api_interactor_logger = logging_config.get_results_logger(
    logger_name='api-interactor-rollback',
    log_filepath=config.get('logging.results_logger.filename'),
    max_results_bytes=config.get('logging.results_logger.max_bytes'),
    backup_count=config.get('logging.results_logger.backup_count'),
)

PERFORMANCE_YEAR = None


def _parse_csv_file(provider_csv):
    """
    Extract a list of npis from provided csv.

    Returns:
        List of npis
    """
    reader = csv.reader(provider_csv, delimiter=',', quotechar='"')
    header = next(reader)
    npi_index = header.index('npi')

    return [str(row[npi_index]) for row in reader]


def query_yes_no(message, default='y'):
    choices = 'Y/n' if default.lower() in ('y', 'yes') else 'y/N'
    choice = input('%s (%s) ' % (message, choices))
    values = ('y', 'yes', '') if choices == 'Y/n' else ('y', 'yes')
    return choice.strip().lower() in values


def _get_submission_data(submission_response, submission_filter=None):
    submissions = submission_response['data']['submissions']
    if submission_filter:
        submissions = [submission for submission in submissions if submission_filter(submission)]
    return submissions


def _measurement_set_has_empty_reporting(measurement_set, npi):
    """Test if a measurement set has an empty reporting."""
    if max(measure['value']['reportingRate'] for measure in measurement_set['measurements']) == 0:
        logger.warning('Empty reporting for provider: {}'.format(npi))
        return True
    return False


def _get_measurement_set_ids_from_submission(submissions, measurement_set_filter):
    return [
        measurement_set['id']
        for submission in submissions
        for measurement_set in submission['measurementSets']
        if (measurement_set_filter(
            measurement_set=measurement_set,
            npi=submission['nationalProviderIdentifier']
        ))
    ]


def _process_measurement_sets_by_npis(
        npis, submission_filter, measurement_set_filter, processing_function):
    logger.info('Processing measurements sets for %d providers.', len(npis))
    measurement_sets_processed = 0
    for npi in npis:
        submission_response = api_submitter.get_submissions(npi=npi)
        submissions = _get_submission_data(submission_response, submission_filter)
        measurement_set_ids = _get_measurement_set_ids_from_submission(
            submissions,
            measurement_set_filter
        )
        if len(measurement_set_ids) or not measurement_set_filter:
            api_interactor_logger.info(json.dumps(submissions))
        processing_function(measurement_set_ids)
        measurement_sets_processed += len(measurement_set_ids)
    logger.info(
        'Processed %(measurement_sets_processed)d measurement sets for %(providers)d providers',
        {'measurement_sets_processed': measurement_sets_processed, 'providers': len(npis)}
    )


def _process_all_measurement_sets(submission_filter, measurement_set_filter, processing_function):
    start_index = 0
    measurement_sets_processed = 0
    while True:
        logger.debug('Fetching submissions to process for start_index {}.'.format(start_index))
        submission_response = api_submitter.get_submissions(start_index=start_index)
        items_per_page = submission_response['data']['itemsPerPage']
        submissions = _get_submission_data(
            submission_response, submission_filter
        )
        if not submissions:
            break

        api_interactor_logger.info(submissions)

        measurement_set_ids = _get_measurement_set_ids_from_submission(
            submissions,
            measurement_set_filter
        )
        processing_function(measurement_set_ids)
        start_index += items_per_page
        if measurement_set_ids:
            api_interactor_logger.info(submissions)
            measurement_sets_processed += len(measurement_set_ids)
            print('Processed {} measurement_sets for {} submissions.'.format(
                len(measurement_set_ids), len(submissions)
            ))
        print(
            'Looped through {} submissions and processed {}.'.format(
                start_index, measurement_sets_processed
            )
        )


def submission_filter(submission):
    """REQUIRES IMPLEMENTATION BY USER IF NEEDED."""
    return True


def processing(measurement_set_ids):
    """REQUIRES IMPLEMENTATION BY USER."""
    raise NotImplementedError


def measurement_set_filter(measurement_set, *args, **kwargs):
    """REQUIRES IMPLEMENTATION BY USER IF NEEDED."""
    return True


def _submission_processing(arguments):
    providers = []
    if arguments.get('provider_npi', None):
        providers = [arguments['provider_npi']]
    elif arguments.get('provider_csv', None):
        providers = _parse_csv_file(arguments['provider_csv'])

    get_all_measurement_sets = not arguments.get('empty_measurement_sets_only', False)
    if not get_all_measurement_sets:
        logger.info('Processning only measurement sets with empty reporting.')

    if providers:
        _process_measurement_sets_by_npis(
            npis=providers,
            submission_filter=submission_filter,
            measurement_set_filter=measurement_set_filter,
            processing_function=processing
        )
        return

    if not arguments['all'] or not query_yes_no(
        message='This is your last chance. Confirm processing for ALL on {}?!'.format(
            config.get('environment'))):
        return

    _process_all_measurement_sets(
        submission_filter, measurement_set_filter, processing)


def _get_arguments():
    """Build argument parser."""
    parser = argparse.ArgumentParser(
        description='DANGER - This starts a rollback of measurement sets.'
    )

    parser.add_argument(
        '-npi', '--provider-npi',
        help='Provider NPI to rollback',
        required=False,
        type=str)

    parser.add_argument(
        '-csv', '--provider-csv',
        help='CSV with provider NPIs to rollback',
        required=False,
        type=argparse.FileType('r', encoding='UTF-8'))

    parser.add_argument(
        '-all', '--all',
        help='process all measurement sets',
        required=False,
        action='store_true')

    args = parser.parse_args()

    if not (args.provider_npi or args.provider_csv or args.all):
        parser.error(
            'Specify what you would like to rollback. -npi, -csv, or -all need to be specified.'
        )

    if sum(bool(argument) for argument in [args.provider_npi, args.provider_csv, args.all]) != 1:
        parser.error(
            'You must specify exactly one of -npi, -csv, or -all.'
        )

    return args.__dict__


if __name__ == '__main__':
    print('Starting processing on {}...'.format(config.get('environment')))
    if query_yes_no(message='Confirm processing.'):
        _submission_processing(_get_arguments())
