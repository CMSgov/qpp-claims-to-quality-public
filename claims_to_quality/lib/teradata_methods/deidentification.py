"""Objects and routines to deidentify IDR data for development use."""

import collections
import copy
import datetime
import hashlib
import uuid

import teradata

"""
In order to remove personally identifiable information (PII),
we need to replace the contents of certain columns with fake values.
There are two ways to achieve this: via hashing or universally unique identifiers (UUIDS).

Hashing is sufficient when the field contains enough entropy (e.g., for strings like addresses).
However, fields like social security number do not contain enough entropy for successful hashing.
For example, a malicious actor could generate hashes for all billion distinct SSNs,
then use this lookup table to reverse engineer the original value from the hashed value.

For this reason, fields like SSN need to be anonymized via UUID instead of hashing.
"""


# These columns will be randomly generated from scratch.
# When two claims contain the same original value for one of these columns,
# the anonymizer will return the same randomly generated UUID for both claims.
COLUMNS_TO_RANDOMLY_GENERATE = [
    'CLM_RNDRG_PRVDR_NPI_NUM',
    'CLM_LINE_RNDRG_PRVDR_NPI_NUM',
    'PRVDR_RNDRNG_PRVDR_NPI_NUM',
    'PRVDR_FAC_PRVDR_NPI_NUM',
    'CLM_RNDRG_PRVDR_TAX_NUM',
    'CLM_ATNDG_PRVDR_NPI_NUM',
    'CLM_CNTRCTR_NUM',
    'CLM_HIC_NUM',
    'BENE_CTGRY_EQTBL_BIC_CD',
    'BENE_EQTBL_HIC_NUM',
    'CLM_CNTL_NUM',
    'CLM_ORIG_CNTL_NUM',
    'BENE_BIC_CD',
    'BENE_CAN_NUM',
    'BENE_EQTBL_BIC_CD',
    'BENE_EQTBL_BIC_HICN_NUM',
    'BENE_HIC_NUM',
    'BENE_LINE_1_ADR',
    'BENE_LINE_2_ADR',
    'BENE_LINE_3_ADR',
    'BENE_LINE_4_ADR',
    'BENE_LINE_5_ADR',
    'BENE_LINE_6_ADR',
    'BENE_MDCD_NUM',
    'BENE_MDCD_RCPNT_NUM',
    'BENE_MIDL_NAME',
    'BENE_NAME_GNRTN_SFX',
    'BENE_PHNE_NUM',
    'BENE_RP_NAME',
    'BENE_SSN_NUM',
    'SPLT_CLM_ID'
]

# These columns will be replaced with their HASH values.
COLUMNS_TO_HASH = []

# These columns will have month and day removed.
DATE_COLUMNS = [
    'CLM_PTNT_BIRTH_DT',
    'CLM_FROM_DT',
    'CLM_LINE_FROM_DT',
    'CLM_THRU_DT',
    'CLM_LINE_THRU_DT',
    'CLM_PD_DT',
    'CLM_LINE_MDCR_PMT_DT',
    'BENE_DEATH_DT'
]

# These columns must have at least the specified number of records.
SMALL_CELL_COLUMNS = {
    'CLM_LINE_RNDRG_PRVDR_NPI_NUM': 50,
    'CLM_RNDRG_PRVDR_TAX_NUM': 50,
}


class AnonymizationFilter(object):
    """Scramble PII fields from records."""

    def __init__(self):
        """Set default values to use during de-identification process."""
        self.current_year = datetime.date.today().year
        self.random_column_mappings = collections.defaultdict(dict)

    def anonymize_row(self, row):
        """Replace PII fields with new values for one row."""
        new_row = teradata.util.Row(row.columns, copy.deepcopy(row.values), row.rowNum)
        for column in row.columns:
            # Use the hash function to scramble the specified column.
            if column.upper() in COLUMNS_TO_HASH:
                new_row[column] = self._hash_function(row[column])

            # Create unique ids for columns with insufficient entropy to hash.
            if column.upper() in COLUMNS_TO_RANDOMLY_GENERATE:
                new_row[column] = self._fake_column_value(column, row[column])

            # All elements of a date besides year are considered PII.
            # Dates more than 90 years ago are grouped together.
            if column.upper() in DATE_COLUMNS:
                value = row[column]
                try:
                    year = value.year
                except AttributeError:
                    value = datetime.datetime.strptime(row[column], '%Y-%m-%d').date()
                    year = value.year

                year = max(value.year, self.current_year - 90)
                new_row[column] = value.replace(year=year, month=1, day=1)

        return new_row

    def anonymize_rows(self, rows):
        """Replace PII fields with new values one row at a time."""
        for row in rows:
            yield self.anonymize_row(row)

    def _hash_function(self, x):
        """Hash the given value."""
        return hashlib.sha1(x).hexdigest()

    def _fake_column_value(self, column_name, raw_value):
        """
        Generate a fake replacement value for an original value within a specific column.

        If the original value has already been encountered in the given column, return the
        previously generated value instead of generating a new one.

        The mapping is of the form column --> (original_value --> new_value).
        This prevents malicious actors from using domain knowledge about one specific
        column (e.g., that NULL is the most common value) to derive new information
        about other fields.
        """
        if raw_value not in self.random_column_mappings[column_name]:
            self.random_column_mappings[column_name][raw_value] = uuid.uuid4().hex
        return self.random_column_mappings[column_name][raw_value]


def modify_query_to_hash_pii_fields(query_string):
    """Replace all PII columns in query_string with a HASH of that column."""
    for pii_column in COLUMNS_TO_HASH:
        replace_pattern = 'HASHBUCKET(HASHROW({col}))'.format(col=pii_column)
        query_string = query_string.replace(pii_column, replace_pattern)

    return query_string


def modify_query_to_suppress_rare_values(query_string, database, table):
    """
    Append a condition to the input query to hide uncommon rows.

    The resulting query is guaranteed to have more than min_records rows for each
    value of the specified column. This enacts small cell suppression.

    Example:
        >>> modify_query_to_suppress_rare_values('SELECT * FROM db.claims', db, claims)
        '''SELECT * FROM db.claims WHERE 1=1
        AND CLM_RNDRG_PRVDR_TAX_NUM IN (SELECT CLM_RNDRG_PRVDR_TAX_NUM
        FROM db.claims GROUP BY CLM_RNDRG_PRVDR_TAX_NUM
        HAVING COUNT(*) >= 50 )'''
    """
    # Prepare the query for adding more conditions.
    strict_query = query_string.replace(';', '')
    if 'WHERE' not in strict_query:
        strict_query += ' WHERE 1=1 '

    # Add a condition to the query for each small cell column.
    for col in SMALL_CELL_COLUMNS:
        if col in strict_query:
            condition = """
                AND {col} IN (SELECT {col}
                FROM {db}.{tbl}
                GROUP BY {col}
                HAVING COUNT(*) >= {min} )
            """.format(col=col, db=database, tbl=table, min=SMALL_CELL_COLUMNS[col])
            strict_query += condition

    return strict_query
