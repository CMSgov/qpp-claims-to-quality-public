"""Tests for connecting to SQS."""
from claims_to_quality.lib.connectors import sqs_connector

import mock


class MockBotoSession():
    """Class to mock a Boto Session capable of calling `resource`."""

    def resource(self, resource_name):
        """Return the given resource from the internal mapping."""
        if resource_name == 'sqs':
            return MockSQSResource()
        else:
            raise NotImplementedError


class MockSQSResource():
    """Class to mock an SQS resource capable of calling `get_queue`."""

    def get_queue_by_name(self, QueueName):
        """Return a fake queue."""
        return 'Not a real queue'


@mock.patch('boto3.session.Session')
def test_get_queue(mock_session):
    """Test that get_queue interfaces with Boto as expected."""
    mock_session.return_value = MockBotoSession()
    queue = sqs_connector.get_queue()
    assert queue == 'Not a real queue'
