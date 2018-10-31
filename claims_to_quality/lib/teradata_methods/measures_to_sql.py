"""Methods to convert measure definitions to SQL conditions."""
from claims_to_quality.lib.teradata_methods import sql_formatting


def _convert_procedure_codes_to_sql_condition(procedure_codes):
    """Convert a list of procedure codes to a SQL condition."""
    return 'CLM_LINE_HCPCS_CD IN {}'.format(sql_formatting.to_sql_list(procedure_codes))
