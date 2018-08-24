"""Helpful methods for interacting with Teradata databases."""
import claims_to_quality.lib.teradata_methods.execute as execute
from claims_to_quality.lib.qpp_logging import logging_config

logger = logging_config.get_logger(__name__)

CHECK_IF_TABLE_EXISTS_BASE_QUERY = """
    SELECT * FROM DBC.TABLES WHERE TABLENAME='{table}' AND DATABASENAME = '{database}';
"""
DROP_TABLE_BASE_QUERY = 'DROP TABLE {database}.{table};'


def _drop_table_if_exists(table_name, database_name):
    """Drop table if it exists."""
    if _if_table_exists(table_name):
        query = DROP_TABLE_BASE_QUERY.format(
            database=database_name,
            table=table_name
        )
        logger.debug('Dropping table {}.'.format(table_name))
        return execute.execute(query)


def _if_table_exists(table_name, database_name):
    """Check if the given table exists."""
    query = CHECK_IF_TABLE_EXISTS_BASE_QUERY.format(table=table_name, database=database_name)
    rows = execute.execute(query)
    return len(rows) > 0
