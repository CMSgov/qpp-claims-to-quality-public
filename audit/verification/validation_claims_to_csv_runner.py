#!/usr/local/bin/python3.6
"""Script for pulling claims data for a given provider and writing to csv."""
import argparse
from datetime import datetime

from claims_to_quality.analyzer.datasource import claim_reader
from claims_to_quality.lib.teradata_methods import row_handling
from claims_to_quality.config import config


def _main(**kwargs):
    """Query the IDR for a given provider's data, write results to csv file."""
    # TODO: Add ability to tune columns, details of deidentification.
    (_, rows) = claim_reader.query_claims_from_teradata_batch_provider(
        [kwargs['provider_tin']],
        [kwargs['provider_npi']],
        kwargs['start_date'],
        kwargs['end_date'])

    row_handling.to_csv(rows=rows, csv_path=kwargs['csv_path'])


def _get_arguments():
    """Build argument parser."""
    parser = argparse.ArgumentParser(
        description='Query for provider claims and output them to csv.')

    parser.add_argument(
        '-npi', '--provider-npi',
        help='Provider NPI to query for',
        required=True,
        type=str)

    parser.add_argument(
        '-tin', '--provider-tin',
        help='Provider tax id to query for',
        required=True,
        type=str)

    parser.add_argument(
        '-sd', '--start-date',
        help='Claim range start date - format YYYY-MM-DD',
        default=config.get('calculation.start_date'),
        type=_valid_date)

    parser.add_argument(
        '-ed', '--end-date',
        help='Claim range end date - format YYYY-MM-DD',
        default=config.get('calculation.end_date'),
        type=_valid_date)

    parser.add_argument(
        '-csv', '--csv-path',
        help='CSV filepath to write results to',
        default='test_validation.csv',
        type=str)

    return parser.parse_args().__dict__


def _valid_date(s):
    """Validate date format."""
    try:
        return datetime.strptime(s, '%Y-%m-%d')
    except ValueError:
        msg = "Not a valid date: '{0}'.".format(s)
        raise argparse.ArgumentTypeError(msg)


if __name__ == '__main__':
    _main(**_get_arguments())
