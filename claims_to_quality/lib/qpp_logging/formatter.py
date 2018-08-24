"""Json log formatter."""
import datetime

from claims_to_quality.lib.qpp_logging import pii_scrubber

from pythonjsonlogger import jsonlogger


class JsonFormatter(jsonlogger.JsonFormatter, object):
    """
    Json formatter for logging.

    It can be added to a logging handler as follows:
    handler.setFormatter(formatter.JsonFormatter(
        extra={
            'hostname': socket.gethostname(),
            'app': 'qpp-claims-to-quality',
            'environment': config.get('environment'),
            'team': config.get('logging.team'),
            'contact': config.get('logging.contact')
        })
    )
    """

    def __init__(
        self,
        fmt=(
            '%(asctime) %(name) %(processName) %(filename) '
            '%(funcName) %(levelname) %(lineno) %(module) %(threadName) %(message)'),
            fields_to_redact=['message', 'exc_info'],
            redacting_filter=pii_scrubber.RedactingPIIFilter(),
            datefmt='%Y-%m-%dT%H:%M:%SZ%z',
            extra={}, *args, **kwargs):
        """
        Initalize JsonFormatter for logging.

        Note - fmt defines the order in which fields appear.
        """
        self._extra = extra
        self._datefmt = datefmt
        self._redacting_filter = redacting_filter
        self._fields_to_redact = fields_to_redact
        jsonlogger.JsonFormatter.__init__(self, fmt=fmt, datefmt=datefmt, *args, **kwargs)

    def _redact_field(self, log_record, field):
        if field in log_record:
            log_record[field] = self._redacting_filter.redact(log_record[field])

    def process_log_record(self, log_record):
        """Process log records and apply PII logger."""
        # Scrub PIIs.
        if self._redacting_filter:
            for field in self._fields_to_redact:
                self._redact_field(log_record, field)

        # Enforce the presence of a timestamp.
        if 'asctime' in log_record:
            log_record['timestamp'] = log_record['asctime']
        else:
            log_record['timestamp'] = datetime.datetime.utcnow().strftime(self._datefmt)

        if self._extra is not None:
            for key, value in self._extra.items():
                log_record[key] = value
        return super(JsonFormatter, self).process_log_record(log_record)
