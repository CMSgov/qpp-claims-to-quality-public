"""
Classes and methods for converting Teradata SQL datatypes into Python ones.

Note that Teradata stores dates, times, and datetimes in a non-POSIX format.
"""
import datetime
import decimal
import json

import ciso8601

from teradata import datatypes
from teradata import util


NUMBER = datatypes.NUMBER
Time = datatypes.Time
Timestamp = datatypes.Timestamp
Date = datatypes.Date
BINARY = datatypes.BINARY


class DataTypeConverter(datatypes.DefaultDataTypeConverter):
    """
    Class for converting Teradata SQL datatypes into Python datatypes.

    This converter overrides the default Teradata converter on UdaExec initialization.
    Whereas the Teradata Python library uses only Python standard libraries, this converter uses
    C-based libraries for faster date parsing.
    """

    def convertValue(self, dbType, dataType, typeCode, value):
        """
        Convert the value returned by the database into the desired Python object.

        Overrides the default method from `teradata.datatypes.DefaultDataTypeConverter`.
        `dataType` is the SQL type, whereas `typeCode` is the Python type.
        """
        if value is not None:
            if typeCode == str:
                return value
            try:
                converter = TYPE_CODE_TO_CONVERSION_METHOD[typeCode]
                return converter(value)
            except KeyError:
                if dataType.startswith('INTERVAL'):
                    return datatypes.convertInterval(dataType, value)
                elif dataType.startswith('JSON') and util.isString(value):
                    return json.loads(value, parse_int=decimal.Decimal, parse_float=decimal.Decimal)
                elif dataType.startswith('PERIOD'):
                    return datatypes.convertPeriod(dataType, value)
        return value


def _convert_value_to_timestamp(value):
    """Convert SQL value to Python datetime object."""
    # TODO: Use ciso8601 for faster conversions.
    if util.isString(value):
        return datatypes.convertTimestamp(value)
    else:
        return datetime.datetime.fromtimestamp(value / datatypes.SECS_IN_MILLISECS)


def _convert_value_to_time(value):
    """Convert SQL value to Python time object."""
    # TODO: Use ciso8601 for faster conversions.
    if util.isString(value):
        return datatypes.convertTime(value)
    else:
        return datetime.datetime.fromtimestamp(value / datatypes.SECS_IN_MILLISECS).time()


def _convert_value_to_date(value):
    """
    Convert SQL value to Python date object.

    Note that Teradata measures time in a non-POSIX format, requiring
    conversion into seconds from milliseconds.
    """
    if util.isString(value):
        try:
            return ciso8601.parse_datetime(value).date()
        except AttributeError:
            raise datatypes.InterfaceError('INVALID_DATE', 'Date format invalid: {}'.format(value))
    else:
        return datetime.datetime.fromtimestamp(value / 1000).date()  # 1000 milliseconds in 1 second


TYPE_CODE_TO_CONVERSION_METHOD = {
    NUMBER: lambda value: NUMBER(value),
    float: lambda value: float(value) if util.isString(value) else value,
    Timestamp: _convert_value_to_timestamp,
    Time: _convert_value_to_time,
    Date: _convert_value_to_date,
    BINARY: lambda value: bytearray.fromhex(value) if util.isString else None,
}
