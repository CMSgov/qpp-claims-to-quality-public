""""This class is used to read claims data from db into the claims model."""
import itertools
from collections import defaultdict

from claims_to_quality.analyzer.models import claim
from claims_to_quality.config import config
from claims_to_quality.lib.connectors import idr_queries
from claims_to_quality.lib.qpp_logging import logging_config
from claims_to_quality.lib.teradata_methods import deidentification, execute, row_handling

import newrelic.agent

logger = logging_config.get_logger(__name__)

# TODO: Return dict(row) instead of row to allow for dictionary access.


class ClaimsDataReader(object):
    """
    Read data from a Teradata DB into claims model objects.

    The reader takes query parameters as input, parses the lines
    into the claim model, and returns a claim object.
    """

    def __init__(self):
        """Initialize ClaimsDataReader."""
        self.hide_sensitive_information = config.get('hide_sensitive_information')

    # Column headers that should be the same for all lines in a claim.
    CLAIM_LEVEL_COLUMNS = {
        'splt_clm_id': 'splt_clm_id',
        'bene_sk': 'bene_sk',
        'clm_ptnt_birth_dt': 'clm_ptnt_birth_dt',
        'clm_bene_sex_cd': 'clm_bene_sex_cd',
        'clm_line_rndrg_prvdr_npi_num': 'clm_rndrg_prvdr_npi_num',
        'clm_rndrg_prvdr_tax_num': 'clm_rndrg_prvdr_tax_num',
    }

    # Dx_codes are diagnosis codes associated with a claim.
    # Each claim can have multiple diagnosis codes.
    DX_CODE_COLUMNS = [
        'clm_dgns_1_cd',
        'clm_dgns_2_cd',
        'clm_dgns_3_cd',
        'clm_dgns_4_cd',
        'clm_dgns_5_cd',
        'clm_dgns_6_cd',
        'clm_dgns_7_cd',
        'clm_dgns_8_cd',
        'clm_dgns_9_cd',
        'clm_dgns_10_cd',
        'clm_dgns_11_cd',
        'clm_dgns_12_cd'
    ]

    # Column headers for line-specific levels.
    LINE_LEVEL_COLUMNS = {
        'clm_line_from_dt': 'clm_line_from_dt',
        'clm_line_thru_dt': 'clm_line_thru_dt',
        'clm_line_num': 'clm_line_num',
        'clm_line_hcpcs_cd': 'clm_line_hcpcs_cd',
        'clm_pos_cd': 'clm_pos_code'
    }

    # Modifier codes are codes used to add more information to a claim line's HCPCS code.
    # Each HCPCS code can have up to 5 modifiers.
    MODIFIER_CODE_COLUMNS = [
        'hcpcs_1_mdfr_cd',
        'hcpcs_2_mdfr_cd',
        'hcpcs_3_mdfr_cd',
        'hcpcs_4_mdfr_cd',
        'hcpcs_5_mdfr_cd'
    ]

    def load_from_csv(self, csv_path, provider_tin, provider_npi):
        """
        Load claims data from csv, filter on provider. Input data must be sorted by claim_uniq_id.

        Args:
            csv_path (str): Path of csv data to load.
            provider_tin (str): Provider tax identification number to filter on.
            provider_npi (str): Provider national provider identifier to filter on.
        Returns:
            List of claims objects containing the relevant data.
        """
        logger.debug('Load from csv - {}.'.format(csv_path))
        columns, rows = row_handling.csv_to_query_output(csv_path)

        filtered_rows = [
            row for row in rows
            if ((row['clm_line_rndrg_prvdr_npi_num'] == provider_npi) and (
                row['clm_rndrg_prvdr_tax_num'] == provider_tin
            ))
        ]

        sorted_rows = sorted(filtered_rows, key=lambda row: row['splt_clm_id'])
        claims = []
        for unique_id, group in itertools.groupby(sorted_rows, lambda x: x['splt_clm_id']):
            claims.append(self._lines_to_claim(list(group), columns))
        return claims

    def _get_dx_code_list(self, row, columns):
        """Given a claim line, return a list of all diagnosis codes for that line."""
        return [
            row[columns[col]]
            for col in self.DX_CODE_COLUMNS
            if row[columns[col]]
        ]

    def _assert_split_claims_have_same_header_level_values(self, claim_lines, columns):
        """
        Raise an error if the header-level columns vary across components of a split claim.

        This method makes sure that claims being merged into a single claim have the same
        top-level fields.
        """
        message = ''
        first_row = claim_lines[0]
        for col in self.CLAIM_LEVEL_COLUMNS:
            if any(first_row[columns[col]] != line[columns[col]] for line in claim_lines):
                message = '{col} varies across lines in a split claim with NPI {npi}!'.format(
                    col=col,
                    npi=first_row['clm_line_rndrg_prvdr_npi_num']
                )
                if col == 'clm_ptnt_birth_dt' or col == 'clm_ptnt_sex_cd':
                    # In this case, the BENE_SKs match. A warning is logged but no error is raised.
                    logger.warning(message)
                else:
                    # In this case, the mismatched column is critical to determining the identity.
                    # The claims cannot be safely merged, so an error is raised.
                    raise AssertionError(message)

    def _lines_to_claim(self, claim_lines, columns):
        """
        Convert set of lines of a claim into a claim model.

        TODO: Add null / empty string handling for each of the values in case they don't exist.
        """
        # If major header columns are different among the lines being merged, raise an error.
        self._assert_split_claims_have_same_header_level_values(claim_lines, columns)

        # Assign claim-level values.
        top = claim_lines[0]

        tmp_claim = {
            new_col: top[columns[old_col]]
            for old_col, new_col in self.CLAIM_LEVEL_COLUMNS.items()
        }

        # Collect diagnosis codes from every line (in case of varying codes across split claims).
        tmp_claim['dx_codes'] = list({
            code for row in claim_lines
            for code in self._get_dx_code_list(row, columns)
        })

        # Collect claim start and thru dates accounting for split claims.
        # Take the earliest and latest dates if there is more than one claim.
        tmp_claim['clm_from_dt'] = min([line[columns['clm_from_dt']] for line in claim_lines])
        tmp_claim['clm_thru_dt'] = max([line[columns['clm_thru_dt']] for line in claim_lines])

        # Collect line-level values.
        procedure_codes = {}
        tmp_claim['claim_lines'] = []
        for claim_line in claim_lines:
            line = {
                new_col: claim_line[columns[old_col]]
                for old_col, new_col in self.LINE_LEVEL_COLUMNS.items()
            }

            line['mdfr_cds'] = [
                claim_line[columns[col]]
                for col in self.MODIFIER_CODE_COLUMNS
                if claim_line[columns[col]]
            ]

            procedure_codes[line['clm_line_hcpcs_cd']] = True

            tmp_claim['claim_lines'].append(line)

        tmp_claim['aggregated_procedure_codes'] = procedure_codes
        return claim.Claim(tmp_claim)

    def _group_claim_by_lines(self, rows, columns, id_column):
        if self.hide_sensitive_information and len(rows) < 50:
            # TIN/NPIs with fewer than 50 claims should be hidden due to rare-values.
            logger.debug('Fewer than 50 claims, dropping provider')
            return []

        claims = []
        # Group claim lines into claims based on splt_clm_id.
        for unique_id, group in itertools.groupby(rows, lambda x: x[id_column]):
            claims.append(self._lines_to_claim(list(group), columns))

        logger.debug('{} claim lines loaded as {} claims.'.format(len(rows), len(claims)))
        return claims

    @newrelic.agent.function_trace(name='load-batch-from-db', group='Task')
    def load_batch_from_db(
            self, provider_tin_list, provider_npi_list,
            start_date, end_date, session=None):
        """
        Query the database and convert results into claim objects.

        Args:
            provider_tin_list ([str]): List of provider tax identification number to load.
            provider_npi_list ([str]): List of national provider identifier to load.
            start_date (date): Start date of data to load.
            end_date (date): End date of data to load.
        Returns:
            Dict of list of claims objects containing the relevant data.
            The key is a (tin, npi) tuple identifier.
        """
        (columns, rows) = query_claims_from_teradata_batch_provider(
            provider_tin_list, provider_npi_list, start_date, end_date, session=session)

        if not columns:
            return {}

        id_column = 'splt_clm_id'

        anonymization_filter = deidentification.AnonymizationFilter()

        batch_dict = defaultdict(list)
        for row in rows:
            identifier = (row['clm_rndrg_prvdr_tax_num'], row['clm_line_rndrg_prvdr_npi_num'])
            if self.hide_sensitive_information:
                row = anonymization_filter.anonymize_row(row)
            batch_dict[identifier].append(row)
        logger.debug('{} claim lines loaded for this batch of {} providers.'.format(
            sum([len(lines) for lines in batch_dict.values()]),
            len(batch_dict.values()))
        )

        return {
            identifier: self._group_claim_by_lines(records_for_provider, columns, id_column)
            for identifier, records_for_provider in batch_dict.items()
        }


@newrelic.agent.function_trace(name='execute-query-claims-batch', group='Task')
def query_claims_from_teradata_batch_provider(
        provider_tins, provider_npis,
        start_date, end_date,
        session=None):
    """
    Query claims table for the analyzer for a batch of providers.

    Args:
        provider_tin_list ([str]): List of tax identification numbers to query for.
        provider_npi_list ([str]): List of national provider identification numbers to query for.
        start_date (date): Start date of data to load.
        end_date (date): End date of data to load.
        session (session): Teradata session to use to access IDR.
    Returns:
        (column_names, rows) (list(str), list(tuple)):  Tuple of list of headers, and
                list of tuples containing claim line values.
    """
    logger.debug('Query claims from TERADATA in env - {}.'.format(config.get('environment')))

    query = idr_queries.get_access_layer_batch_query(
        tins=provider_tins,
        npis=provider_npis,
        start_date=start_date,
        end_date=end_date
    )

    rows = execute.execute(query, session)
    if rows:
        columns = rows[0].columns
        return (columns, rows)

    return ([], rows)
