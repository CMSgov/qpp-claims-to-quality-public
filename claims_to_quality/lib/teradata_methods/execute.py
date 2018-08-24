"""Methods for executing queries against a Teradata connection."""
from claims_to_quality.lib.connectors import teradata_connector
from claims_to_quality.lib.helpers import iterators
from claims_to_quality.lib.qpp_logging import logging_config
from claims_to_quality.lib.teradata_methods import teradata_errors

import newrelic.agent

import teradata

logger = logging_config.get_logger(__name__)


def execute(command, session=None):
    """Wrapper for SQL executions in a context manager."""
    session_needs_to_be_closed = session is None
    session = session or teradata_connector.teradata_connection()

    try:
        with session.cursor() as cursor:
            cursor.arraysize = 100
            cursor.execute(command)
            results = cursor.fetchall()
    except teradata.api.DatabaseError:
        raise teradata_errors.TeradataError('DatabaseError')

    if session_needs_to_be_closed:
        session.close()

    logger.debug('Teradata execute returned {} rows.'.format(len(results)))
    return results


def explain(command, session=None):
    """
    Run the EXPLAIN PLAN for a particular query, returning Teradata row objects.

    The EXPLAIN PLAN describes how Teradata's query optimizer intends to execute the query.
    It also provides time and row estimates for each execution step.

    This does not execute the query itself.
    """
    explain_query = ' EXPLAIN ' + command
    return execute(explain_query, session=session)


@newrelic.agent.function_trace(name='execute-with-batch-output', group='Task')
def execute_with_batch_output(command, session=None, batch_size=200):
    """
    Iterator for returning query results in batches.

    The query results are stored in memory in entirety.
    """
    return iterators.iterate_in_slices(
        iterable=execute(command, session=session),
        batch_size=batch_size
    )


@newrelic.agent.function_trace(name='execute-with-batch-fetch-and-output', group='Task')
def execute_with_batch_fetch_and_output(command, session=None, db_fetch_size=1000, batch_size=200):
    """
    Iterator for fetching query results in batches and returning them in batches.

    The query results are not stored in memory, so the session must remain open.
    """
    return iterators.iterate_in_slices(
        iterable=_execute_iterator(command, session=session, arraysize=db_fetch_size),
        batch_size=batch_size
    )


def _execute_iterator(command, arraysize, session=None):
    """Iterator for fetching query results from the database in batches."""
    session_needs_to_be_closed = session is None
    session = session or teradata_connector.teradata_connection()

    with session.cursor() as cursor:
        cursor.execute(command)
        # TODO: Improve this by adding a more meaningful loop condition.
        while True:
            results = cursor.fetchmany(arraysize)
            if not results:
                break
            for result in results:
                yield result

    if session_needs_to_be_closed:
        session.close()
