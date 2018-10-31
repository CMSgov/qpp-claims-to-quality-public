"""Methods for creating, manipulating, and storing Teradata row objects."""
import csv

from claims_to_quality.lib.qpp_logging import logging_config
from claims_to_quality.lib.teradata_methods import deidentification

import teradata


logger = logging_config.get_logger(__name__)


def csv_to_query_output(csv_path):
    """
    Use csv input to mock SQL query results.

    This is used to allow claim_reader to read from csv.
    """
    rows = []
    with open(csv_path) as file:
        reader = csv.reader(file, delimiter=',', quotechar='"')
        header = next(reader)
        rows = convert_list_of_lists_to_teradata_rows(reader, header)

    columns = {column_name: idx for idx, column_name in enumerate(header)}
    return (columns, rows)


def convert_list_of_lists_to_teradata_rows(data, columns):
    """
    Given a list of iterables, convert to Teradata row objects with the specified columns.

    :param data: List of iterables to convert to Teradata row objects.
    :param columns: List of column names for the returned rows.
    """
    columns = {key: index for index, key in enumerate(columns)}

    return [
        teradata.util.Row(columns=columns, values=entry, rowNum=idx)
        for idx, entry in enumerate(data)
    ]


def convert_dicts_to_teradata_rows(data):
    """
    Convert a list of dictionaries to a list of Teradata row objects.

    All dictionaries in the list should have the same keys.
    """
    if not data:
        return []

    columns = {key: index for index, key in enumerate(data[0].keys())}
    # Convert rows to list format as expected by the Teradata library.
    rows_as_lists = []
    for row in data:
        row_as_list = ['0'] * len(columns)
        for column_name, column_idx in columns.items():
            row_as_list[column_idx] = row[column_name]
        rows_as_lists.append(row_as_list)

    return [
        teradata.util.Row(columns=columns, values=row, rowNum=idx)
        for idx, row in enumerate(rows_as_lists)
    ]


def to_csv(rows, csv_path, anonymize=True):
    """
    Given a list of Teradata rows, output to csv with the given columns.

    TODO: Specify specific columns to write to csv.
    :param rows: List of Teradata row objects to be written to csv.
    :param csv_path: Path of csv file to create and write to.
    """
    if not rows:
        logger.warn('No data to save.')
        return

    if anonymize:
        anonymization_filter = deidentification.AnonymizationFilter()
        rows = list(anonymization_filter.anonymize_rows(rows))

    with open(csv_path, 'w') as f:
        fieldnames = [column for column in rows[0].columns]
        writer = csv.writer(f)
        writer.writerow(fieldnames)
        writer.writerows([row.values for row in rows])
