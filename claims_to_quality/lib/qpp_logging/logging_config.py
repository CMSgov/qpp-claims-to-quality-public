"""Shared setup file for logging."""
import logging
import logging.handlers
import socket

from claims_to_quality.config import config
from claims_to_quality.lib.qpp_logging import formatter


def get_logger(logger_name):
    """Configure and return default logger."""
    logger = logging.getLogger(logger_name)
    logger.setLevel(config.get('logging.log_level'))

    # Set log handling to JSON.
    handler = logging.StreamHandler()
    handler.setFormatter(formatter.JsonFormatter(
        extra={
            'hostname': socket.gethostname(),
            'app': 'qpp-claims-to-quality',
            'environment': config.get('environment'),
            'team': config.get('logging.team'),
            'contact': config.get('logging.contact')
        }))
    logger.addHandler(handler)

    return logger


# TODO: Make it possible to log these files outside of docker on a host file.
def get_results_logger(
        logger_name,
        log_filepath,
        max_results_bytes,
        backup_count):
    """Configure and return logger for handling results."""
    results_logger = logging.getLogger(logger_name)
    results_logger.propagate = False
    results_logger.setLevel(config.get('logging.log_level'))

    log_handler = logging.handlers.RotatingFileHandler(
        filename=log_filepath,
        maxBytes=max_results_bytes,
        backupCount=backup_count
    )

    results_logger.addHandler(log_handler)

    return results_logger
