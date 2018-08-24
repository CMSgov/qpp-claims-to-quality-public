"""PII Scrubber."""
import logging
import re

import scrubadub


class TINFilth(scrubadub.filth.base.RegexFilth):
    """TIN filth class for scrubadub."""

    type = 'tin'
    # Match any series of exactly 9 digits.
    regex = re.compile(r'(?<!0x...)(?<!\d)\d{9}(?!\d)', re.VERBOSE)


class TINDetector(scrubadub.detectors.base.RegexDetector):
    """TIN detector class for scrubadub."""

    filth_cls = TINFilth


class RedactingPIIFilter(logging.Filter):
    """Redacting filter to remove PII information."""

    def __init__(self, patterns=[]):
        """Initialize PII filter. New patterns can be given as input."""
        super(RedactingPIIFilter, self).__init__()
        self.scrubber = self._get_scrubber()
        self._patterns = patterns

    @staticmethod
    def _get_scrubber():
        """Initialize a scrubber with phone, skype, ssn, tin and url detector."""
        scrubber = scrubadub.Scrubber()
        # We are not looking at names and emails.
        # To prevent false positives, we remove these detectors for now.
        scrubber.remove_detector('email')
        scrubber.remove_detector('name')
        scrubber.remove_detector('phone')
        scrubber.add_detector(TINDetector)
        return scrubber

    def filter(self, record):
        """Filter messages to redact."""
        record.msg = self.redact(record.msg)
        if isinstance(record.args, dict):
            for k in record.args.keys():
                record.args[k] = self.redact(record.args[k])
        else:
            record.args = tuple(self.redact(arg) for arg in record.args)
        return True

    def redact(self, msg):
        """Redact messages and apply PII scrubber."""
        msg = msg if isinstance(msg, str) else str(msg)
        msg = self.scrubber.clean(msg)
        for pattern in self._patterns:
            msg = re.sub(pattern=pattern['pattern'], repl=pattern['mask'], string=msg)
        return msg
