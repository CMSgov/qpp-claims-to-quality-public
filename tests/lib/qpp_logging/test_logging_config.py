"""Test logging helper."""
from claims_to_quality.lib.qpp_logging import logging_config


def test_logging():
    """Test that the logger object is created successfully."""
    logger = logging_config.get_logger(__name__)
    logger.info('Successful INFO logging.')
