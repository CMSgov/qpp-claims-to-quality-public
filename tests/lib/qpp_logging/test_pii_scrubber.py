"""Test for PII scrubber."""
from claims_to_quality.lib.qpp_logging import logging_config
from claims_to_quality.lib.qpp_logging import pii_scrubber

import mock

logger = logging_config.get_logger(__name__)
SCRUBBER = pii_scrubber.RedactingPIIFilter()


def test_tin_scrubber():
    """Test PII scrubber - TINs should be redacted."""
    tin = '234567890'
    assert SCRUBBER.redact(tin) == '{{TIN}}'


def test_email_scrubber():
    """Test PII scrubber - Emails should not be redacted."""
    mail = 'ericboucher@bayesimpact.org'
    assert SCRUBBER.redact(mail) == 'ericboucher@bayesimpact.org'


def test_number_scrubber():
    """Test PII scrubber - Long numbers should not be redacted."""
    number = '123456789102'
    assert SCRUBBER.redact(number) == '123456789102'


def test_short_number_scrubber():
    """Test PII scrubber - Short numbers should not be redacted."""
    number = '1234'
    assert SCRUBBER.redact(number) == '1234'


@mock.patch.object(pii_scrubber.RedactingPIIFilter, 'redact')
def test_logger(mock_redact):
    """Test that redact is being called by logger."""
    logger.critical('Aloha.')
    mock_redact.assert_called_once()
