"""Tests for sqs_methods."""
from claims_to_quality.lib.sqs_methods import message_handling

import mock


class TestGetMessage():
    """Tests for receiving SQS messages."""

    def test_get_message(self):
        """Test get_single_message function."""
        queue = mock.Mock()
        queue.receive_messages.return_value = ['message']
        assert message_handling.get_single_message(queue) == 'message'

    def test_get_message_no_message(self):
        """Verify that None is returned if no messages are received."""
        queue = mock.Mock()
        queue.receive_messages.return_value = None
        assert message_handling.get_single_message(queue) is None

    def test_parse_message(self):
        """Test that parse_message gets provider npi and tin when there is a space between."""
        mock_message = mock.Mock()
        fake_tin = '0' * 9
        fake_npi = '0' * 10
        mock_message.body = '{{"tin": "{tin}", "npi": "{npi}"}}'.format(tin=fake_tin, npi=fake_npi)
        output = message_handling.parse_message(mock_message)
        assert output.get('tin') == fake_tin
        assert output.get('npi') == fake_npi
        assert output.get('message') == mock_message

    def test_parse_message_invalid_format(self):
        """Test parse_message in the case where the message is not valid json."""
        mock_message = mock.Mock()
        mock_message.body = 'not a json'
        output = message_handling.parse_message(mock_message)
        assert output == {'message': mock_message}

    def test_get_messages(self):
        """Test get_messages function."""
        queue = mock.Mock()
        queue.receive_messages.return_value = ['message1', 'message2']
        assert message_handling.get_messages(queue) == ['message1', 'message2']


class TestSendMessages():
    """Tests of functions related to sending messages."""

    def _create_failed_message(self, id='id', sender_fault=True):
        """Create a sample failed message."""
        return {
            'Id': id,
            'SenderFault': sender_fault,
            'Code': 'string',
            'Message': 'message'
        }

    def _create_successful_message(self, id='id'):
        """Create a sample successful message."""
        return {
            'Id': id,
            'MessageId': 'success',
            'MD5OfMessageBody': 'string',
            'MD5OfMessageAttributes': 'string',
            'SequenceNumber': 'string'
        }

    def _response_side_effect_success(self, Entries=None):
        """Return a response with length equal to length of entries."""
        return {'Successful': [self._create_successful_message()] * len(Entries)}

    def test_send_messages_all_success(self):
        """Test that send messages calls queue correctly."""
        messages = [
            '{{"tin": "{num}", "npi": "{num}"}}'.format(num=num)
            for num in range(0, 23)
        ]
        mock_queue = mock.MagicMock()
        mock_queue.send_messages = mock.MagicMock(side_effect=self._response_side_effect_success)
        output = message_handling.send_messages(messages, mock_queue)
        expected = {'successful': 23}

        assert output == expected
        assert mock_queue.send_messages.call_count == 3

    def _response_side_effect_failure(self, Entries=None):
        """Return a response with length equal to length of entries."""
        return {'Failed': [self._create_failed_message(sender_fault=True)] * len(Entries)}

    def test_send_messages_all_failure(self):
        """Test that send messages calls queue correctly."""
        messages = [
            '{{"tin": "{num}", "npi": "{num}"}}'.format(num=num)
            for num in range(0, 23)
        ]
        mock_queue = mock.MagicMock()
        mock_queue.send_messages = mock.MagicMock(side_effect=self._response_side_effect_failure)

        # To avoid retrying during tests, we mock the wrapped function with the unwrapped version.
        unwrapped_send_message_group = message_handling._send_message_group.__wrapped__
        with mock.patch(
            'claims_to_quality.lib.sqs_methods.message_handling._send_message_group'
        ) as mock_send_message_group:
            mock_send_message_group.side_effect = unwrapped_send_message_group
            output = message_handling.send_messages(messages, mock_queue)
            expected = {'failed_sender': 23, 'failed_total': 23}

        assert output == expected
        assert mock_queue.send_messages.call_count == 3

    def test_create_entry(self):
        """Test that create_entry returns the expected message."""
        output = message_handling.create_entry('message_body', 0)
        expected = {'MessageBody': 'message_body', 'Id': '0'}

        assert output == expected

    def test_count_responses(self):
        """Test that count responses counts successes and failures as expected."""
        test_response = {
            'Successful': [self._create_successful_message()],
            'Failed': [
                self._create_failed_message(sender_fault=True),
                self._create_failed_message(sender_fault=False),
            ]
        }
        output = message_handling.count_responses(test_response)
        expected = {'successful': 1, 'failed_other': 1, 'failed_sender': 1, 'failed_total': 2}
        assert output == expected

    def test_count_responses_no_failures(self):
        """Test count_responses in the case of no failures."""
        test_response = {'Successful': [self._create_successful_message()]}
        output = message_handling.count_responses(test_response)
        expected = {'successful': 1, 'failed_other': 0, 'failed_sender': 0, 'failed_total': 0}
        assert output == expected

    def test_count_responses_no_successes(self):
        """Test count_responses in the case of no successes."""
        test_response = {'Failed': [self._create_failed_message(sender_fault=True)]}
        output = message_handling.count_responses(test_response)

        expected = {'failed_sender': 1, 'failed_other': 0, 'successful': 0, 'failed_total': 1}
        assert output == expected

    def test_grouper(self):
        """Test that grouper groups values as expected."""
        test_values = iter(['test1', 'test2', 'test3', 'test4'])
        output = message_handling.grouper(test_values, chunk_size=2)

        expected = [('test1', 'test2'), ('test3', 'test4')]
        assert list(output) == expected

    def test_grouper_fill_value(self):
        """Test grouper in case that fill value is needed."""
        test_values = iter(['test1', 'test2', 'test3', 'test4'])
        output = message_handling.grouper(test_values, chunk_size=3, fillvalue='filled')

        expected = [('test1', 'test2', 'test3'), ('test4', 'filled', 'filled')]
        assert list(output) == expected
