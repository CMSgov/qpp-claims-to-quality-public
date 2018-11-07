"""Test api_submitter methods."""
# TODO: Add test for bad data format returned by get requests?
import datetime

from claims_to_quality.analyzer.submission import api_submitter
from claims_to_quality.analyzer.submission import qpp_measurement_set
from claims_to_quality.lib.helpers import mocking_config

import mock

import pytest

import requests


class MockResponse:
    """Mock HTTP responses."""

    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        return self.json_data

    def raise_for_status(self):
        if self.status_code != 200:
            raise requests.exceptions.HTTPError(
                '{}'.format(self.status_code),
                response=self
            )


def mocked_requests_get(*args, **kwargs):
    """Function to mock requests.get."""
    data_perfyear_2017 = {
        'data': {
            'submissions': [
                {'performanceYear': 2017}
            ]
        }
    }

    empty_data = {
        'data': {
            'submissions': []
        }
    }

    bad_format = {
        'no_data_key': {
            'no_submission_key': []
        }
    }

    if args[0] == 'http://test_endpoint/submissions':
        return MockResponse(data_perfyear_2017, 200)
    elif args[0] == 'http://test_endpoint/no_submission/submissions':
        return MockResponse(empty_data, 200)
    elif args[0] == 'http://rate_limiting/':
        return MockResponse(empty_data, 429)

    return MockResponse(bad_format, 404)


class TestAPISubmitterFunctions():
    """Tests for the api_submitter methods."""

    no_cookie_header = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': 'Bearer api_token',
    }

    cookie_header = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': 'Bearer api_token',
        'Cookie': 'cookie'
    }

    def setup(self):
        """Setup base submission object for these tests."""
        self.measurement_set = qpp_measurement_set.MeasurementSet(
            tin='9' * 9,
            npi='8' * 10,
            performance_start=datetime.date(2017, 1, 1),
            performance_end=datetime.date(2017, 12, 31))

    @mock.patch('claims_to_quality.analyzer.submission.api_submitter.config')
    def test_get_headers_no_cookie(self, mock_config):
        """Verify headers are returned if no cookie is defined."""
        mock_config.get.side_effect = mocking_config.config_side_effect({
            'submission.api_token': 'api_token',
            'submission.cookie': None,
            'submission.endpoint': 'http://test_endpoint/no_submission/'
        })

        actual = api_submitter.get_headers()
        assert actual == self.no_cookie_header

    @mock.patch('claims_to_quality.analyzer.submission.api_submitter.config')
    def test_get_headers_with_cookie(self, mock_config):
        """Verify cookie is included in header if present."""
        mock_config.get.side_effect = mocking_config.config_side_effect({
            'submission.api_token': 'api_token',
            'submission.cookie': 'cookie',
            'submission.endpoint': 'http://test_endpoint'
        })

        actual = api_submitter.get_headers()
        assert actual == self.cookie_header

    @mock.patch('requests.post')
    @mock.patch('claims_to_quality.analyzer.submission.api_submitter.config')
    def test_post_to_measurement_sets_api(self, mock_config, mock_post):
        mock_config.get.side_effect = mocking_config.config_side_effect({
            'submission.api_token': 'api_token',
            'submission.cookie': None,
            'submission.endpoint': 'http://test_endpoint/no_submission/'
        })
        endpoint_url = 'http://test_endpoint/no_submission/measurement-sets/'
        api_submitter._post_to_measurement_sets_api(measurement_set=self.measurement_set)
        mock_post.assert_called_with(
            url=endpoint_url,
            data=self.measurement_set.to_json(),
            headers=self.no_cookie_header)

    @mock.patch('requests.put')
    @mock.patch('claims_to_quality.analyzer.submission.api_submitter.config')
    def test_put_to_measurement_sets_api(self, mock_config, mock_put):
        mock_config.get.side_effect = mocking_config.config_side_effect({
            'submission.api_token': 'api_token',
            'submission.cookie': None,
            'submission.endpoint': 'http://test_endpoint/no_submission/'
        })
        existing_measurement_set_id = 10
        endpoint_url = 'http://test_endpoint/no_submission/measurement-sets/10'
        api_submitter._put_to_measurement_sets_api(
            measurement_set=self.measurement_set,
            existing_measurement_set_id=existing_measurement_set_id)
        mock_put.assert_called_with(
            url=endpoint_url,
            data=self.measurement_set.to_json(),
            headers=self.no_cookie_header)

    @mock.patch('requests.get')
    @mock.patch('claims_to_quality.analyzer.submission.api_submitter.config')
    def test_get_existing_submissions_exists(self, mock_config, mock_get):
        mock_config.get.side_effect = mocking_config.config_side_effect({
            'submission.api_token': 'api_token',
            'submission.cookie': 'cookie',
            'submission.endpoint': 'http://test_endpoint'
        })
        endpoint_url = 'http://test_endpoint/submissions'

        params = {
            'itemsPerPage': 99999,
            'nationalProviderIdentifier':
                self.measurement_set.data['submission']['nationalProviderIdentifier'],
            'performanceYear': str(self.measurement_set.data['submission']['performanceYear']),
        }

        headers = api_submitter.get_headers()
        headers.update(
            {'qpp-taxpayer-identification-number':
                self.measurement_set.data['submission']['taxpayerIdentificationNumber']}
        )

        mock_get.side_effect = mocked_requests_get
        existing_submissions_in_same_year = api_submitter.get_existing_submissions(
            self.measurement_set
        )
        mock_get.assert_called_with(
            endpoint_url,
            params=params,
            headers=headers)

        assert existing_submissions_in_same_year == {'performanceYear': 2017}

    @mock.patch('requests.get')
    @mock.patch('claims_to_quality.analyzer.submission.api_submitter.config')
    def test_get_existing_submissions_does_not_exist(self, mock_config, mock_get):
        mock_config.get.side_effect = mocking_config.config_side_effect({
            'submission.api_token': 'api_token',
            'submission.cookie': None,
            'submission.endpoint': 'http://test_endpoint/no_submission/'
        })
        endpoint_url = 'http://test_endpoint/no_submission/submissions'

        params = {
            'itemsPerPage': 99999,
            'nationalProviderIdentifier':
                self.measurement_set.data['submission']['nationalProviderIdentifier'],
            'performanceYear': str(self.measurement_set.data['submission']['performanceYear'])
        }

        headers = api_submitter.get_headers()
        headers.update(
            {'qpp-taxpayer-identification-number':
                self.measurement_set.data['submission']['taxpayerIdentificationNumber']}
        )
        mock_get.side_effect = mocked_requests_get

        with pytest.raises(api_submitter.NoMatchingSubmissionsException):
            api_submitter.get_existing_submissions(
                self.measurement_set)

        mock_get.assert_called_with(
            endpoint_url,
            params=params,
            headers=headers)

    def test_get_measurement_set_id_from_submission(self):
        submission = {
            'performanceYear': 2017,
            'measurementSets': [
                {'category': 'quality', 'submissionMethod': 'claims', 'id': '007'}
            ]
        }
        measurement_set_id = api_submitter.get_measurement_set_id_from_submission(submission)
        assert measurement_set_id == '007'

    def test_get_measurement_set_id_from_submission_no_match(self):
        submission = {
            'performanceYear': 2017,
            'measurementSets': [
                {'category': 'no_quality', 'submissionMethod': 'not_claims'}
            ]
        }
        with pytest.raises(api_submitter.NoMatchingMeasurementSetsException):
            api_submitter.get_measurement_set_id_from_submission(submission)

    @mock.patch('claims_to_quality.analyzer.submission.api_submitter.get_existing_submissions')
    @mock.patch('claims_to_quality.analyzer.submission.api_submitter._put_to_measurement_sets_api')
    def test_submit_to_measurement_sets_api_data_exists(self, mock_put_to_api, mock_get_submission):
        """Test submission API."""
        valid_submission = {
            'performanceYear': 2017,
            'measurementSets': [
                {'category': 'quality', 'submissionMethod': 'claims', 'id': '007'}
            ]
        }
        mock_get_submission.return_value = valid_submission
        mock_put_to_api.return_value = MockResponse(json_data={}, status_code=200)
        response = api_submitter._submit_to_measurement_sets_api(
            self.measurement_set, patch_update=False
        )
        assert response.status_code == 200
        mock_put_to_api.assert_called_with(self.measurement_set, '007')

    @mock.patch('claims_to_quality.analyzer.submission.api_submitter.get_existing_submissions')
    @mock.patch(
        'claims_to_quality.analyzer.submission.api_submitter._patch_to_measurement_sets_api')
    def test_submit_to_measurement_sets_api_patching(self, mock_patch_to_api, mock_get_submission):
        """Test submission API."""
        valid_submission = {
            'performanceYear': 2017,
            'measurementSets': [
                {'category': 'quality', 'submissionMethod': 'claims', 'id': '007'}
            ]
        }
        mock_get_submission.return_value = valid_submission
        mock_patch_to_api.return_value = MockResponse(json_data={}, status_code=200)
        response = api_submitter._submit_to_measurement_sets_api(
            self.measurement_set, patch_update=True
        )
        assert response.status_code == 200
        mock_patch_to_api.assert_called_with(self.measurement_set, '007')

    @mock.patch('claims_to_quality.analyzer.submission.api_submitter.get_existing_submissions')
    @mock.patch('claims_to_quality.analyzer.submission.api_submitter._post_to_measurement_sets_api')
    def test_submit_to_measurement_sets_api_no_data_exists(
            self, mock_post_to_api, mock_get_submission):
        """Test submission API."""
        mock_get_submission.side_effect = api_submitter.NoMatchingMeasurementSetsException()
        mock_post_to_api.return_value = MockResponse(json_data={}, status_code=200)
        response = api_submitter._submit_to_measurement_sets_api(
            self.measurement_set, patch_update=False
        )
        assert response.status_code == 200
        mock_post_to_api.assert_called_with(self.measurement_set)

    @mock.patch('claims_to_quality.analyzer.submission.api_submitter.get_existing_submissions')
    @mock.patch('claims_to_quality.analyzer.submission.api_submitter._post_to_measurement_sets_api')
    def test_submit_to_measurement_sets_api_handle_early_errors(
            self, mock_post_to_api, mock_get_submission):
        """Test submission API."""
        mock_get_submission.side_effect = Exception()
        mock_post_to_api.return_value = MockResponse(json_data={}, status_code=200)
        with pytest.raises(Exception):
            api_submitter._submit_to_measurement_sets_api(
                self.measurement_set, patch_update=False
            )
        assert not mock_post_to_api.called

    @mock.patch('claims_to_quality.analyzer.submission.api_submitter.get_existing_submissions')
    @mock.patch('claims_to_quality.analyzer.submission.api_submitter._post_to_measurement_sets_api')
    def test_submit_to_measurement_sets_api_handle_http_errors(
            self, mock_post_to_api, mock_get_submission):
        """Test submission API."""
        mock_get_submission.side_effect = api_submitter.NoMatchingMeasurementSetsException()
        mock_post_to_api.return_value = MockResponse(json_data={}, status_code=400)
        with pytest.raises(requests.HTTPError):
            api_submitter._submit_to_measurement_sets_api(
                self.measurement_set, patch_update=False
            )
        mock_post_to_api.assert_called_with(self.measurement_set)

    @mock.patch('requests.post')
    def test_scoring_preview(self, mock_post):
        """Test scoring preview."""
        json_data = {'test_key': 'test_value'}
        mock_post.return_value = MockResponse(json_data=json_data, status_code=200)
        try:
            response_json = api_submitter.get_scoring_preview(self.measurement_set)
        except Exception:
            pytest.fail('Unexpected Error...')

        assert response_json == json_data

    @mock.patch('requests.post')
    def test_scoring_preview_bad_response(self, mock_post):
        """Test scoring preview."""
        json_data = {'test_key': 'test_value'}
        mock_post.return_value = MockResponse(json_data=json_data, status_code=400)
        with pytest.raises(requests.exceptions.HTTPError):
            api_submitter.get_scoring_preview(self.measurement_set)


def test_retry_on_fixable_request_errors():
    """Test that the retry condition returns True for relevant status codes."""
    response = mocked_requests_get('http://rate_limiting/')
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        exception = exc

    assert api_submitter._retry_on_fixable_request_errors(exception)
