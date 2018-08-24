"""Setup New Relic Application."""
from claims_to_quality.config import config

import newrelic.agent

_application = None


def get():
    """
    Get the New Relic application Object.

    If New Relic has not already been initialized, initialize New Relic.
    """
    global _application
    if _application is None:
        _application = _initialize()
    return _application


def _initialize(newrelic_agent=newrelic.agent):
    """Initialize the New Relic Application."""
    if config.get('environment') not in ['DEV', 'IMPL', 'PRD']:
        return None
    newrelic_agent.initialize('newrelic.ini', environment=config.get('environment'))
    return newrelic_agent.register_application(timeout=10.0)
