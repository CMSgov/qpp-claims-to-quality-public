"""
Runner for calculating measure from a csv for auditing purposes.

Note - This file can only process data for one TIN/NPI combination and one measure at a time.
The script outputs measure results as JSON.
"""
import argparse
import json
import datetime

from claims_to_quality.analyzer.datasource import claim_reader
from claims_to_quality.analyzer import measure_mapping
from claims_to_quality.analyzer.processing import claim_filtering


def _main(**kwargs):
    """Calculate measures for a given provider's data."""
    if kwargs['measure'] in ['046', '407', '415', '416']:
        raise NotImplementedError(
            'Unable to calulate measure {} at this time. Calculation requires access to IDR.'
        )

    reader = claim_reader.ClaimsDataReader()
    claims = reader.load_from_csv(
        kwargs['csv_input_path'],
        provider_tin=kwargs['provider_tin'],
        provider_npi=kwargs['provider_npi'])

    measure = measure_mapping.get_measure_calculator(kwargs['measure'])

    if all(key in kwargs for key in ['start_date', 'end_date']):
        claims = claim_filtering.filter_claims_by_date(
            claims_data=claims,
            from_date=kwargs['start_date'],
            to_date=kwargs['end_date'],
        )

    results = measure.execute(claims)

    print(json.dumps(results, indent=4))


def _get_arguments():
    """Build argument parser."""
    parser = argparse.ArgumentParser(description='This starts a measure calculation.')

    parser.add_argument(
        '-m', '--measure',
        help='ID of measure to calculate (e.g. 047).',
        required=True,
        type=str)

    parser.add_argument(
        '-tin', '--provider-tin',
        help='Provider tax id to calculate for',
        required=True,
        type=str)

    parser.add_argument(
        '-npi', '--provider-npi',
        help='Provider NPI to calculate for',
        required=True,
        type=str)

    parser.add_argument(
        '-csv', '--csv-input-path',
        help='CSV filepath to read claims from',
        default='test_validation.csv',
        type=str)

    parser.add_argument(
        '-sd', '--start-date',
        help='Calculation start date - format YYYY-MM-DD',
        type=_valid_date)

    parser.add_argument(
        '-ed', '--end-date',
        help='Calculation end date - format YYYY-MM-DD',
        type=_valid_date)

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
