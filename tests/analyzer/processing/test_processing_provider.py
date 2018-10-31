"""Test processing provider."""
from datetime import date

from claims_to_quality.analyzer.datasource import claim_reader
from claims_to_quality.analyzer.processing import process
from claims_to_quality.analyzer.submission import qpp_measurement_set
from claims_to_quality.lib.helpers import mocking_config
from claims_to_quality.lib.sqs_methods.mock_message import MockMessage
from claims_to_quality.lib.teradata_methods import row_handling

import mock


@mock.patch('claims_to_quality.lib.connectors.teradata_connector.teradata_connection')
def get_processor(teradata_connection):
    """Build a Processor object to use in tests."""
    teradata_connection.return_value = None
    return process.Processor(
        start_date=date(2017, 1, 1),
        end_date=date.today(),
        measures=['047'],
        infer_performance_period=False,)


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


def get_single_claim_with_quality_codes():
    """Load single claim list from test_single_claim.csv."""
    reader = claim_reader.ClaimsDataReader()
    claims = reader.load_from_csv(
        csv_path='tests/assets/test_single_claim.csv',
        provider_tin='tax_num',
        provider_npi='npi_num')
    return claims


class TestProcessBatchMessages:
    """Test process batch messages."""

    def setup(self):
        """Setup resources for process batch messages."""
        self.processor = get_processor()

    @mock.patch('claims_to_quality.analyzer.processing.process.Processor._safe_process_provider')
    @mock.patch('claims_to_quality.analyzer.datasource.claim_reader.config')
    @mock.patch(
        'claims_to_quality.analyzer.datasource.claim_reader.'
        'query_claims_from_teradata_batch_provider')
    @mock.patch(
        'claims_to_quality.lib.connectors.teradata_connector.test_teradata_connection')
    def test_process_batch_messages(
            self, test_connection, query_claims_from_teradata_batch_provider,
            mock_config, safe_process_provider):
        """Test process_batch_messages."""
        test_connection.return_value = True

        query_claims_from_teradata_batch_provider.return_value = row_handling.csv_to_query_output(
            'tests/assets/test_single_claim.csv')

        mock_config.get.side_effect = mocking_config.config_side_effect({
            'teradata.access_layer_name': 'access_layer_name',
            'hide_sensitive_information': False
        })

        processor = self.processor
        processor.claim_reader.hide_sensitive_information = False

        mock_message = MockMessage(
            body='{{"tin": "{tin}", "npi": "{npi}"}}'.format(tin='tax_num', npi='npi_num'))

        processor.process_batch_messages([mock_message])

        expected_provider = {'tin': 'tax_num', 'npi': 'npi_num', 'message': mock_message}
        expected_batch_claims_data = {('tax_num', 'npi_num'): get_single_claim_with_quality_codes()}

        safe_process_provider.assert_called_once_with(expected_batch_claims_data, expected_provider)

    @mock.patch('claims_to_quality.analyzer.processing.process.Processor._safe_process_provider')
    @mock.patch('claims_to_quality.analyzer.datasource.claim_reader.config')
    @mock.patch(
        'claims_to_quality.analyzer.datasource.claim_reader.'
        'query_claims_from_teradata_batch_provider')
    @mock.patch(
        'claims_to_quality.lib.connectors.teradata_connector.test_teradata_connection')
    def test_process_batch_messages_error(
            self, test_connection,
            query_claims_from_teradata_batch_provider, mock_config, safe_process_provider):
        """Test process_batch_messages with error does not process provider."""
        test_connection.return_value = True
        query_claims_from_teradata_batch_provider.return_value = row_handling.csv_to_query_output(
            'tests/assets/test_single_claim.csv')

        mock_config.get.side_effect = mocking_config.config_side_effect({
            'teradata.access_layer_name': 'access_layer_name',
            'hide_sensitive_information': False
        })

        processor = self.processor
        processor.remove_messages = True
        processor.claim_reader.hide_sensitive_information = False

        mock_message = MockMessage(body='{"unparsable":}')

        processor.process_batch_messages([mock_message])

        assert not safe_process_provider.called


class TestSafeProcessProvider:
    """Tests for _safe_process_provider."""

    def setup(self):
        """Setup resources for safe_process_provider."""
        self.processor = get_processor()

    @mock.patch(
        'claims_to_quality.analyzer.datasource.claim_reader.'
        'query_claims_from_teradata_batch_provider')
    @mock.patch('claims_to_quality.analyzer.datasource.claim_reader.config')
    def test_safe_process_provider(
            self, mock_config, query_claims_from_teradata_batch_provider):
        """Test _safe_process_provider."""
        mock_config.get.side_effect = mocking_config.config_side_effect({
            'teradata.access_layer_name': 'access_layer_name',
            'hide_sensitive_information': False
        })

        query_claims_from_teradata_batch_provider.return_value = row_handling.csv_to_query_output(
            'tests/assets/test_two_claims.csv')

        processor = self.processor
        initial_count = processor.count
        processor.remove_messages = True
        processor.claim_reader.hide_sensitive_information = False

        batch_claims_data = processor.claim_reader.load_batch_from_db(
            ['tax_num'], ['npi_num'], date.today(), date.today())

        mock_message = MockMessage(
            body='{{"tin": "{tin}", "npi": "{npi}"}}'.format(tin='tax_num', npi='npi_num'))

        provider = {'tin': 'tax_num', 'npi': 'npi_num', 'message': mock_message}
        processed_provider = processor._safe_process_provider(batch_claims_data, provider)

        measurement_set = processed_provider.get('measurement_set', None)

        assert processed_provider.get('message', None) is not None
        assert measurement_set is not None
        assert not processed_provider['processing_error']
        assert processor.count == initial_count + 1

    @mock.patch('claims_to_quality.lib.connectors.teradata_connector.teradata_connection')
    def test_safe_process_provider_error(self, teradata_connection):
        """Test _safe_process_provider with error."""

        claims_data = row_handling.csv_to_query_output('tests/assets/test_single_claim.csv')
        batch_claims_data = {('tax_num', 'npi_num'): claims_data}

        processor = self.processor
        initial_count = processor.count
        initial_error_count = processor.count_errors
        processor.remove_messages = True

        mock_message = MockMessage(body='{"unparsable":}')

        provider = {'tin': 'tax_num', 'npi': 'npi_num', 'message': mock_message}
        processed_provider = processor._safe_process_provider(batch_claims_data, provider)

        assert processed_provider['processing_error']
        assert processor.count == initial_count
        assert processor.count_errors == initial_error_count + 1

    @mock.patch('claims_to_quality.analyzer.processing.process.Processor.process_provider')
    def test_safe_process_provider_no_claims(self, process_provider):
        """Test _safe_process_provider exits early if there are no claims."""
        batch_claims_data = {('tin', 'npi'): []}

        processor = self.processor
        initial_count = processor.count
        processor.remove_messages = True
        initial_count_no_claims = processor.count_no_claims

        mock_message = MockMessage(
            body='{{"tin": "{tin}", "npi": "{npi}"}}'.format(tin='tin', npi='npi'))

        provider = {'tin': 'tin', 'npi': 'npi', 'message': mock_message}
        processed_provider = processor._safe_process_provider(batch_claims_data, provider)
        measurement_set = processed_provider.get('measurement_set', None)

        assert processed_provider.get('message', None) is not None
        assert measurement_set is None
        assert not process_provider.called
        assert processor.count == initial_count + 1
        assert processor.count_no_claims == initial_count_no_claims + 1
        assert not processed_provider['processing_error']


class TestProcessProvider:
    """Tests for process_provider."""

    def setup(self):
        """Setup resources for process provider."""
        self.processor = get_processor()

    @mock.patch(
        'claims_to_quality.analyzer.processing.claim_filtering.do_any_claims_have_quality_codes')
    def test_process_provider_no_quality_codes(self, mock_quality_filter):
        """Test process_provider."""
        claims_data = get_single_claim_with_quality_codes()
        mock_quality_filter.return_value = False

        measurement_set = self.processor.process_provider(
            tin='0' * 9,
            npi='0' * 10,
            claims_data=claims_data,
        )
        assert measurement_set.is_empty()

    @mock.patch('claims_to_quality.analyzer.submission.qpp_measurement_set.config')
    def test_process_provider_has_quality_codes_zero_reporting_unfiltered(self, mock_config):
        """Test process_provider, quaity codes but no reporting. Zero reporting not filtered."""
        claims_data = get_single_claim_with_quality_codes()

        mock_config.get.side_effect = mocking_config.config_side_effect({
            'submission.filter_out_zero_reporting': False
        })

        measurement_set = self.processor.process_provider(
            tin='tax_num',
            npi='npi_num',
            claims_data=claims_data,
        )

        assert measurement_set is not None
        assert not measurement_set.is_empty()

    @mock.patch('claims_to_quality.analyzer.submission.qpp_measurement_set.config')
    def test_process_provider_has_quality_codes_zero_reporting_filtered(self, mock_config):
        """Test process_provider, quaity codes but no reporting. Zero reporting filtered."""
        claims_data = get_single_claim_with_quality_codes()

        mock_config.get.side_effect = mocking_config.config_side_effect({
            'submission.filter_out_zero_reporting': True
        })

        measurement_set = self.processor.process_provider(
            tin='tax_num',
            npi='npi_num',
            claims_data=claims_data,
        )

        assert measurement_set is not None
        assert measurement_set.is_empty()

    @mock.patch('claims_to_quality.analyzer.submission.qpp_measurement_set.config')
    def test_process_provider_infer_performance_period(self, mock_config):
        """Test process_provider if infer_performance_period is True."""
        # FIXME: This test does not test infer_performance_period.
        self.processor.infer_performance_period = True
        claims_data = get_single_claim_with_quality_codes()

        mock_config.get.side_effect = mocking_config.config_side_effect({
            'submission.filter_out_zero_reporting': False
        })

        measurement_set = self.processor.process_provider(
            tin='tax_num',
            npi='npi_num',
            claims_data=claims_data,
        )
        assert not measurement_set.is_empty()
