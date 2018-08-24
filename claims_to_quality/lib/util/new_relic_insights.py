"""Utility functions for posting events using the New Relic Insights API."""
# TODO: Use Python requests instead of curl.
import json
import subprocess

from claims_to_quality.config import config


def post_to_new_relic(payload):
    """
    Function to post event to New Relic.

    Payload should be a string representation of a valid event.
    """
    rest_key = config.get('new_relic_insights.event_key')  # Key for NewRelic Insights POST API
    url = config.get('new_relic_insights.url')  # URL for NewRelic Insights POST API
    post = ('echo \'{payload}\' | curl -d @- -X POST -H "Content-Type: application/json" '
            '-H "X-Insert-Key: {rest_key}" '
            '{url}')
    post = post.format(payload=payload, rest_key=rest_key, url=url)
    subprocess.call(args=[post], shell=True)


def build_new_relic_insights_payload(event_type, event_body):
    """
    Build New Relic Insights event of the specified event type.

    Args:
        event_type (str): eventType value to use for constructed event payload.
        event_body (dict): Native Dictionary representation of event attributes.

    Returns:
        str: JSON string containing event attributes with specified event type.

    TODO: Add validation of event attributes as needed.
    """
    event_body['eventType'] = event_type
    return json.dumps(event_body)
