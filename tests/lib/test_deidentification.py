"""Ensure that the deidentification module correctly handles sensitive information."""
import re

import claims_to_quality.lib.teradata_methods.deidentification as deidentification
from claims_to_quality.lib.teradata_methods import row_handling

import teradata

from tests.assets import test_helpers


TWO_CLAIMS_CSV_PATH = 'tests/assets/test_two_claims.csv'


class TestAnonymizationFilterScramblesColumnsCorrectly():
    """Check to see that the AnonymizationFilter creates fake values for each sensitive column."""

    def setup(self):
        """Recreate fresh sample data and anonymizer before each test."""
        self.sample_rows = test_helpers.fetch_sample_teradata_rows()
        self.pii_filter = deidentification.AnonymizationFilter()

    def test_hashed_columns_changed(self):
        """The anonymizer should hash certain columns containing PII."""
        anonymized_rows = self.pii_filter.anonymize_rows(self.sample_rows)
        for column in deidentification.COLUMNS_TO_HASH:
            for new_row, old_row in zip(anonymized_rows, self.sample_rows):
                if column in old_row.columns:
                    assert new_row.values[column] != old_row.values[column]

    def test_randomly_generated_values_differ_from_original_values(self):
        """The anonymizer should randomly generate new values for fields containing PII."""
        anonymized_rows = self.pii_filter.anonymize_rows(self.sample_rows)
        for column in deidentification.COLUMNS_TO_RANDOMLY_GENERATE:
            for new_row, old_row in zip(anonymized_rows, self.sample_rows):
                if column in old_row.columns:
                    assert new_row.values[column] != old_row.values[column]

    def test_randomly_generated_values_agree_when_original_values_agree(self):
        """The anonymizer should generate the same new value when fed identical original values."""
        sample_row_values = [
            {
                'BENE_SK': 10001,
                'CLM_RNDRG_PRVDR_TAX_NUM': '123456',
            },
            {
                'BENE_SK': 20001,
                'CLM_RNDRG_PRVDR_TAX_NUM': '123456',
            }
        ]
        sample_rows = [
            teradata.util.Row(row.keys(), values=row, rowNum=1) for row in sample_row_values
        ]
        anonymized_rows = list(self.pii_filter.anonymize_rows(sample_rows))
        pii_column = 'CLM_RNDRG_PRVDR_TAX_NUM'

        assert(anonymized_rows[0][pii_column] == anonymized_rows[1][pii_column])

    def test_all_dates_changed(self):
        """The anonymizer should convert dates to the year only with date values."""
        anonymized_rows = self.pii_filter.anonymize_rows(self.sample_rows)
        for date_column in deidentification.DATE_COLUMNS:
            for new_row, old_row in zip(anonymized_rows, self.sample_rows):
                if date_column in old_row.columns:
                    assert new_row.values[date_column] != old_row.values[date_column]

    def test_all_dates_changed_with_string_dates(self):
        """The anonymizer should convert dates to the year only with string values."""
        sample_columns, sample_rows = row_handling.csv_to_query_output(TWO_CLAIMS_CSV_PATH)
        anonymized_rows = self.pii_filter.anonymize_rows(sample_rows)
        for date_column in deidentification.DATE_COLUMNS:
            for new_row, old_row in zip(anonymized_rows, self.sample_rows):
                if date_column in old_row.columns:
                    assert new_row.values[date_column] != old_row.values[date_column]


class TestRemovingSensitiveFieldsFromQueries():
    """Check to see that the deidentification module changes queries touching sensitive columns."""

    def test_hash_pii_fields_covers_all_sensitive_fields(self):
        """Ensure modify_query_to_hash_pii_fields wraps all sensitive fields in HASH functions."""
        sample_query = 'SELECT {} FROM db.table;'.format(
            ' , '.join(deidentification.COLUMNS_TO_HASH)
        )
        new_query = deidentification.modify_query_to_hash_pii_fields(sample_query)

        for pii_column in deidentification.COLUMNS_TO_HASH:
            pattern = '(?<!HASHROW\(){}'.format(pii_column)
            potentially_hazardous_match = re.search(pattern, new_query)
            assert potentially_hazardous_match is None

    def test_suppress_rare_values_covers_all_small_cell_fields(self):
        """Ensure modify_query_to_suppress_rare_values adds conditions to the WHERE clause."""
        sample_query = 'SELECT {} FROM db.table;'.format(
            ' , '.join(deidentification.SMALL_CELL_COLUMNS)
        )
        new_query = deidentification.modify_query_to_suppress_rare_values(
            query_string=sample_query,
            database='db',
            table='table'
        )

        for small_cell_column in deidentification.SMALL_CELL_COLUMNS:
            pattern = 'GROUP\s+BY\s+{}\s+HAVING\s+COUNT\(\*\)'.format(small_cell_column)
            small_cell_match = re.search(pattern, new_query)
            assert small_cell_match is not None
