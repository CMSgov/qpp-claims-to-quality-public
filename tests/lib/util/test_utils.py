"""Test util files."""
import json

from claims_to_quality.lib.util import new_relic_insights, slack

import mock


def test_new_relic_insights_payload():
    """Test NR insights payload creation."""
    event = {
        'environment': 'TEST',
        'success': 'True'
    }
    payload = new_relic_insights.build_new_relic_insights_payload(
        event_type='analyzerStartup', event_body=event
    )
    event['eventType'] = 'analyzerStartup'
    assert json.loads(payload) == event


@mock.patch('subprocess.call')
def test_new_relic_insights_post(call):
    """Test NR insights post."""

    payload = json.dumps({
        'environment': 'TEST',
        'success': 'True',
        'eventType': 'analyzerStartup'
    })

    new_relic_insights.post_to_new_relic(payload=payload)
    subprocess_calls = call.call_args_list
    # Check that subprocess.call was triggered only once.
    assert len(subprocess_calls) == 1
    _, kwargs = subprocess_calls[0]
    checks = [
        '{"environment": "TEST", "success": "True", "eventType": "analyzerStartup"}',
    ]
    for check in checks:
        assert check in kwargs['args'][0]


@mock.patch('subprocess.call')
def test_slack_post(call):
    """Test Slack."""
    slack.post_to_slack(message='hello')
    subprocess_calls = call.call_args_list
    # Check that subprocess.call was triggered only once.
    assert len(subprocess_calls) == 1
    _, kwargs = subprocess_calls[0]
    checks = [
        "curl -X POST -H 'Content-type: application/json'",
        """--data \'{"text":"hello"}\'"""
    ]
    for check in checks:
        assert check in kwargs['args'][0]


@mock.patch('subprocess.call')
def test_slack_post_here(call):
    """Test Slack."""
    slack.post_to_slack_tagging_here(message='hello')
    subprocess_calls = call.call_args_list
    # Check that subprocess.call was triggered only once.
    assert len(subprocess_calls) == 1
    _, kwargs = subprocess_calls[0]
    checks = [
        "curl -X POST -H 'Content-type: application/json'",
        """--data \'{"text":"<!here> hello"}\'"""
    ]
    for check in checks:
        assert check in kwargs['args'][0]
