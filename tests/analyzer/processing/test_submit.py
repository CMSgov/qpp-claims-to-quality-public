"""Test processing provider."""
from datetime import date

from claims_to_quality.analyzer.processing import submit
from claims_to_quality.analyzer.submission import qpp_measurement_set
from claims_to_quality.config import config
from claims_to_quality.lib.sqs_methods.mock_message import MockMessage

import mock


def get_submitter():
    """Build a Submitter object to use in tests."""
    return submit.Submitter(
        remove_messages=False,
        send_submissions=False,)


def get_empty_measurement_set():
    """Build an empty measurement set for testing."""
    return qpp_measurement_set.MeasurementSet(
        tin='tin',
        npi='npi',
        performance_start=date(2017, 1, 1),
        performance_end=date(2017, 12, 31))


def get_measurement_set():
    """Build a measurement set with a result in it for testing."""
    measurement_set = qpp_measurement_set.MeasurementSet(
        tin='tin',
        npi='npi',
        performance_start=date(2017, 1, 1),
        performance_end=date(2017, 12, 31))

    measure_results = {
        'eligible_population_exclusion': 0,
        'eligible_population_exception': 0,
        'performance_met': 0,
        'performance_not_met': 1,
        'eligible_population': 42
    }

    measurement_set.add_measure(
        measure_number='047',
        measure_results=measure_results,
    )

    return measurement_set


def get_measurement_set_no_reporting():
    """Build a measurement set with a result but no reporting for testing."""
    measurement_set = qpp_measurement_set.MeasurementSet(
        tin='tin',
        npi='npi',
        performance_start=date(2017, 1, 1),
        performance_end=date(2017, 12, 31))

    measure_results = {
        'eligible_population_exclusion': 0,
        'eligible_population_exception': 0,
        'performance_met': 0,
        'performance_not_met': 0,
        'eligible_population': 42
    }

    measurement_set.add_measure(
        measure_number='047',
        measure_results=measure_results,
    )

    return measurement_set


class TestSendSubmissions:
    """Tests for _send_submissions."""

    def setup(self):
        """Setup resources for process provider."""
        self.submitter = get_submitter()

    @mock.patch('claims_to_quality.analyzer.processing.submit.api_submitter')
    def test_send_submissions_nothing_to_submit(self, mock_api_submitter):
        """Test submission sending if there are no results."""
        self.submitter.send_submissions = True
        measurement_set = get_empty_measurement_set()
        self.submitter._send_submissions('tin', 'npi', measurement_set)
        mock_api_submitter.submit_to_measurement_sets_api.assert_not_called()

    @mock.patch('claims_to_quality.analyzer.processing.submit.api_submitter')
    def test_send_submissions_no_pop_to_submit(self, mock_api_submitter):
        """Test submission not sent with 0 reporting."""
        self.submitter.send_submissions = True
        measurement_set = get_measurement_set_no_reporting()
        self.submitter._send_submissions('tin', 'npi', measurement_set)
        if config.get('submission.filter_out_zero_reporting'):
            mock_api_submitter.submit_to_measurement_sets_api.assert_not_called()
        else:
            mock_api_submitter.submit_to_measurement_sets_api.assert_called_once()

    @mock.patch('claims_to_quality.analyzer.processing.submit.api_submitter')
    def test_send_submissions_actually_sending(self, mock_api_submitter):
        """Test that submissions are sent if send_submissions is true."""
        self.submitter.send_submissions = True
        measurement_set = get_measurement_set()
        self.submitter._send_submissions('tin', 'npi', measurement_set)
        mock_api_submitter.submit_to_measurement_sets_api.assert_called_once_with(
            measurement_set, patch_update=False
        )

    def test_process_after_submission_delete(self):
        mock_message = MockMessage(
            body='{{"tin": "{tin}", "npi": "{npi}"}}'.format(tin='tax_num', npi='npi_num'))
        mock_provider_processed = {
            'tin': 'tax_num', 'npi': 'npi_num', 'message': mock_message, 'processing_error': False
        }
        self.submitter.remove_messages = True
        self.submitter._process_after_submission(mock_provider_processed)
        assert mock_provider_processed['message'].deleted is True

    def test_process_after_submission_no_delete(self):
        """Remove message after submission."""
        self.submitter.remove_messages = False
        mock_message = MockMessage(
            body='{{"tin": "{tin}", "npi": "{npi}"}}'.format(tin='tax_num', npi='npi_num'))
        mock_provider_processed = {
            'tin': 'tax_num', 'npi': 'npi_num', 'message': mock_message, 'processing_error': False
        }
        self.submitter._process_after_submission(mock_provider_processed)
        assert mock_provider_processed['message'].deleted is False

    @mock.patch('claims_to_quality.analyzer.processing.submit.api_submitter')
    def test_submit_batch(self, mock_api_submitter):
        """Test batch submission."""
        self.submitter.send_submissions = True
        self.submitter.remove_messages = True
        mock_message = MockMessage(
            body='{{"tin": "{tin}", "npi": "{npi}"}}'.format(tin='tax_num', npi='npi_num'))

        # Provider processed nominally.
        mock_provider_processed = {
            'tin': 'tax_num', 'npi': 'npi_num', 'message': mock_message, 'processing_error': False
        }
        mock_provider_processed['measurement_set'] = get_measurement_set()

        # No claims data.
        mock_provider_processed_no_measurement_set = {
            'tin': 'tax_num', 'npi': 'npi_num', 'message': mock_message, 'processing_error': False
        }

        # Empty measurement set.
        mock_provider_processed_empty_measurement_set = {
            'tin': 'tax_num', 'npi': 'npi_num', 'message': mock_message, 'processing_error': False
        }
        mock_provider_processed_empty_measurement_set['measurement_set'] =\
            get_empty_measurement_set()

        # Error processing provider.
        mock_provider_processed_error = {
            'tin': 'tax_num', 'npi': 'npi_num', 'message': mock_message, 'processing_error': True
        }

        # None represents a provider that had an error.
        providers = [
            mock_provider_processed,
            mock_provider_processed_no_measurement_set,
            mock_provider_processed_empty_measurement_set,
            mock_provider_processed_error
        ]

        self.submitter.submit_batch(providers)

        assert len(mock_api_submitter.mock_calls) == 1
        assert mock_provider_processed['message'].deleted is True
        assert mock_provider_processed_no_measurement_set['message'].deleted is True
        assert mock_provider_processed_empty_measurement_set['message'].deleted is True
