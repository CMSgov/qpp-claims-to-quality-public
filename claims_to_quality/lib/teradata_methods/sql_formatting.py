"""SQL formatting for Teradata queries."""


class SQLFormattingError(Exception):
    """Custom Exception handling for empty SQL lists."""

    pass


def to_sql_list(iterable):
    """
    Transform a Python list to a SQL list.

    input = [a1, a2]
    output = "('a1', 'a2')"
    """
    if iterable:
        return '(' + ', '.join("'" + str(item) + "'" for item in iterable) + ')'
    else:
        raise SQLFormattingError('No element in list. Cannot process IN statement.')
