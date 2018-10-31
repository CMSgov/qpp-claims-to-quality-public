"""Tests for claim_reader methods."""
import datetime

from claims_to_quality.analyzer.datasource import claim_reader
from claims_to_quality.lib.helpers import mocking_config
from claims_to_quality.lib.teradata_methods import row_handling

import mock

import pytest

from tests.assets import test_helpers

# Constants for paths to test resources.
SINGLE_CLAIM_CSV_PATH = 'tests/assets/test_single_claim.csv'
TWO_CLAIMS_CSV_PATH = 'tests/assets/test_two_claims.csv'
TWO_CLAIMS_CSV_PATH_FROM_CSV = 'tests/assets/test_two_claims_from_csv.csv'
EMPTY_QUERY_CSV_PATH = 'tests/assets/test_empty_query.csv'
SPLIT_CLAIM_CSV_PATH = 'tests/assets/test_split_claim.csv'


def test_assert_split_claims_have_same_header_level_values():
    """The method should raise an error if two claims do not have the same header fields."""
    reader = claim_reader.ClaimsDataReader()
    sample_rows = test_helpers.fetch_sample_teradata_rows()
    with pytest.raises(AssertionError):
        reader._lines_to_claim(claim_lines=sample_rows, columns=sample_rows[0].columns)


def test_assert_split_claims_have_same_header_level_values_different_birth_date():
    """The method should NOT raise an error if two claims do not have the same birth date."""
    reader = claim_reader.ClaimsDataReader()
    columns, rows = row_handling.csv_to_query_output(SPLIT_CLAIM_CSV_PATH)
    # Change the first birth date so that the two are different.
    rows[0]['clm_ptnt_birth_dt'] = datetime.date(1000, 1, 1)
    claim = reader._lines_to_claim(claim_lines=rows, columns=columns)
    assert claim


class TestLoadFromCsv():
    """Test load_from_csv function."""

    def test_single_claim_data_reader(self):
        """Test the parsing of a single claim into the Claim model object."""
        reader = claim_reader.ClaimsDataReader()
        claims = reader.load_from_csv(SINGLE_CLAIM_CSV_PATH, 'tax_num', 'npi_num')

        assert len(claims) == 1
        claim = claims[0]
        assert len(claim.claim_lines) == 2
        assert len(claim.dx_codes) == 12
        assert len(claim.claim_lines[0].mdfr_cds) == 5

    def test_two_claim_data_reader(self):
        """Test the merging of claim lines into claims."""
        reader = claim_reader.ClaimsDataReader()
        claims = reader.load_from_csv(TWO_CLAIMS_CSV_PATH_FROM_CSV, 'tax_num', 'npi_num')

        assert len(claims) == 2
        for claim in claims:
            assert len(claim.claim_lines) == 2

    def test_query_returns_empty(self):
        """Verify list of claims is empty if csv contains no results."""
        reader = claim_reader.ClaimsDataReader()
        claims = reader.load_from_csv(EMPTY_QUERY_CSV_PATH, 'tax_num', 'npi_num')
        assert len(claims) == 0

    def test_filter_by_provider_npi(self):
        """Verify the claim is excluded if the provider npi does not match the one provided."""
        reader = claim_reader.ClaimsDataReader()
        claims = reader.load_from_csv(SINGLE_CLAIM_CSV_PATH, 'tax_num', 'non_matching_npi_num')
        assert len(claims) == 0

    def test_filter_by_provider_tax(self):
        """Verify the claim is excluded if the provider npi does not match the one provided."""
        reader = claim_reader.ClaimsDataReader()
        claims = reader.load_from_csv(SINGLE_CLAIM_CSV_PATH, 'non_matching_tax_num', 'npi_num')
        assert len(claims) == 0


class TestLoadFromDb():
    """Test load_batch_from_db function."""

    @mock.patch('claims_to_quality.config.config.get')
    @mock.patch(
        'claims_to_quality.analyzer.datasource.claim_reader.'
        'query_claims_from_teradata_batch_provider')
    def test_single_claim_data_reader(self, mock_query_claims_from_teradata_batch, get):
        """Test the parsing of a single claim into the Claim model object."""
        mock_query_claims_from_teradata_batch.return_value = row_handling.csv_to_query_output(
            SINGLE_CLAIM_CSV_PATH)
        get.side_effect = mocking_config.config_side_effect({'hide_sensitive_information': False})
        provider_identifier = ('tax_num', 'npi_num')

        reader = claim_reader.ClaimsDataReader()
        claims = reader.load_batch_from_db(
            provider_tin_list=['tax_num'],
            provider_npi_list=['npi_num'],
            start_date='start_date',
            end_date='end_date'
        )[provider_identifier]

        assert len(claims) == 1
        claim = claims[0]
        assert len(claim.claim_lines) == 2
        assert len(claim.dx_codes) == 12
        assert len(claim.claim_lines[0].mdfr_cds) == 5

    @mock.patch('claims_to_quality.config.config.get')
    @mock.patch(
        'claims_to_quality.analyzer.datasource.claim_reader.'
        'query_claims_from_teradata_batch_provider')
    def test_two_claim_data_reader(self, mock_query_claims_from_teradata_batch, get):
        """Test the merging of claim lines into claims."""
        mock_query_claims_from_teradata_batch.return_value = row_handling.csv_to_query_output(
            TWO_CLAIMS_CSV_PATH)
        get.side_effect = mocking_config.config_side_effect({'hide_sensitive_information': False})
        provider_identifier = ('tax_num', 'npi_num')

        reader = claim_reader.ClaimsDataReader()
        claims = reader.load_batch_from_db(
            provider_tin_list=['tax_num'],
            provider_npi_list=['npi_num'],
            start_date='start_date',
            end_date='end_date'
        )[provider_identifier]

        assert len(claims) == 2
        for claim in claims:
            assert len(claim.claim_lines) == 2

    @mock.patch(
        'claims_to_quality.analyzer.datasource.claim_reader.'
        'query_claims_from_teradata_batch_provider')
    def test_query_returns_empty(self, mock_query_claims_from_teradata_batch):
        """Verify list of claims is empty if query returns no results."""
        mock_query_claims_from_teradata_batch.return_value = row_handling.csv_to_query_output(
            EMPTY_QUERY_CSV_PATH)

        reader = claim_reader.ClaimsDataReader()
        claims = reader.load_batch_from_db(
            provider_tin_list=['tax_num'],
            provider_npi_list=['npi_num'],
            start_date='start_date',
            end_date='end_date'
        )

        assert len(claims) == 0


class TestLinesToClaim():
    """Test _lines_to_claim and associated functions."""

    def setup(self):
        """Setup values for lines to claim tests."""
        self.split_claim_columns = row_handling.csv_to_query_output(SPLIT_CLAIM_CSV_PATH)[0]
        self.split_claim_rows = row_handling.csv_to_query_output(SPLIT_CLAIM_CSV_PATH)[1]
        self.claim_reader = claim_reader.ClaimsDataReader()

    def test_lines_to_claim_split_claim(self):
        """Test that _lines_to_claim converts split claims to a single claim as expected."""
        claim = self.claim_reader._lines_to_claim(self.split_claim_rows, self.split_claim_columns)
        assert claim.clm_from_dt == datetime.date(2017, 2, 23)
        assert claim.clm_thru_dt == datetime.date(2017, 3, 5)
        assert all(code in claim.dx_codes for code in ['dgns1', 'dgns2', 'dgns1b', 'dgns2b'])
        assert len(claim.dx_codes) == 4

    def test_get_dx_codes_list(self):
        """Test that get_dx_codes_list works as expected."""
        input_line = self.split_claim_rows[0]
        dx_codes = self.claim_reader._get_dx_code_list(input_line, self.split_claim_columns)
        assert dx_codes == ['dgns1', 'dgns2']


class TestQueryClaimsFromTeradata():
    """Test query_claims_from_teradata_batch_provider function."""

    def setup(self):
        """Setup values for Teradata query tests."""
        self.sample_rows = test_helpers.fetch_sample_teradata_rows()
        self.sample_config = {
            'teradata.access_layer_name': 'access_layer_name',
            'hide_sensitive_information': False
        }

    @mock.patch(
        'claims_to_quality.analyzer.datasource.claim_reader.'
        'query_claims_from_teradata_batch_provider'
    )
    @mock.patch('claims_to_quality.analyzer.datasource.claim_reader.config')
    def test_query_hides_sensitive_information_fewer_than_fifty(
            self, mock_config, mock_query_claims_from_teradata_batch):
        """Test case when fewer than 50 claims and hide_sensitive_information is true."""
        mock_config.get.side_effect = mocking_config.config_side_effect(
            {'hide_sensitive_information': True}
        )
        provider_identifier = ('tax_num', 'npi_num')
        sample_columns, sample_rows = row_handling.csv_to_query_output(TWO_CLAIMS_CSV_PATH)
        mock_query_claims_from_teradata_batch.return_value = (sample_columns, sample_rows)

        reader = claim_reader.ClaimsDataReader()
        output = reader.load_batch_from_db(
            ['tax_num'], ['npi_num'], datetime.date.today(), datetime.date.today()
        )[provider_identifier]

        assert output == []

    @mock.patch(
        'claims_to_quality.analyzer.datasource.claim_reader.'
        'query_claims_from_teradata_batch_provider'
    )
    @mock.patch('claims_to_quality.analyzer.datasource.claim_reader.config')
    def test_query_hides_sensitive_information_more_than_fifty(
            self, mock_config, mock_query_claims_from_teradata_batch):
        """Test case when more than 50 claims and hide_sensitive_information is true."""
        mock_config.get.side_effect = mocking_config.config_side_effect(
            {'hide_sensitive_information': True}
        )
        provider_identifier = ('tax_num', 'npi_num')
        sample_columns, sample_rows = row_handling.csv_to_query_output(TWO_CLAIMS_CSV_PATH)
        # Need > 50 rows for them to pass through anonymization.
        sample_rows = sample_rows * 50
        mock_query_claims_from_teradata_batch.return_value = (sample_columns, sample_rows)

        reader = claim_reader.ClaimsDataReader()
        output = reader.load_batch_from_db(
            ['tax_num'], ['npi_num'], datetime.date.today(), datetime.date.today()
        )[provider_identifier]

        # The same number of claims should be returned.
        assert len(output) == 2 * 50  # Two claims in initial csv.
        # The values of the fields in the returned rows should be different.
        assert output[0]['clm_ptnt_birth_dt'] != sample_rows[0]['clm_ptnt_birth_dt']

    @mock.patch(
        'claims_to_quality.analyzer.datasource.claim_reader.'
        'query_claims_from_teradata_batch_provider')
    @mock.patch('claims_to_quality.analyzer.datasource.claim_reader.config')
    def test_batch_load(self, mock_config, query_claims_from_teradata_batch_provider):
        """Test that when hide_sensitive_information is true, the rows are anonymized."""
        mock_config.get.side_effect = mocking_config.config_side_effect(
            {'hide_sensitive_information': False}
        )
        query_claims_from_teradata_batch_provider.return_value = row_handling.csv_to_query_output(
            TWO_CLAIMS_CSV_PATH)

        reader = claim_reader.ClaimsDataReader()
        output = reader.load_batch_from_db(
            ['tax_num'], ['npi_num'],
            datetime.date.today(), datetime.date.today())

        assert len(output[('tax_num', 'npi_num')]) == 2

    @mock.patch('claims_to_quality.lib.teradata_methods.execute.execute')
    @mock.patch('claims_to_quality.analyzer.datasource.claim_reader.config')
    def test_batch_query(self, mock_config, mock_execute):
        """Test batch_query."""
        mock_config.get.side_effect = mocking_config.config_side_effect(
            {'hide_sensitive_information': False}
        )
        sample_rows = self.sample_rows * 50  # Need > 50 rows for anonymization to kick in.
        mock_execute.return_value = sample_rows
        output = claim_reader.query_claims_from_teradata_batch_provider(
            provider_tins=['tin'],
            provider_npis=['npi'],
            start_date=datetime.date.today(),
            end_date=datetime.date.today())

        assert len(output[1]) == len(sample_rows)
        assert output[1] == sample_rows

    @mock.patch('claims_to_quality.lib.teradata_methods.execute.execute')
    @mock.patch('claims_to_quality.analyzer.datasource.claim_reader.config')
    def test_batch_query_no_data(self, mock_config, mock_execute):
        """Test batch_query."""
        mock_config.get.side_effect = mocking_config.config_side_effect(
            {'hide_sensitive_information': False}
        )
        sample_rows = []
        mock_execute.return_value = sample_rows
        output = claim_reader.query_claims_from_teradata_batch_provider(
            provider_tins=['tin'],
            provider_npis=['npi'],
            start_date=datetime.date.today(),
            end_date=datetime.date.today())

        assert len(output[1]) == len(sample_rows)
        assert output[1] == sample_rows
        assert output[0] == []

    @mock.patch(
        'claims_to_quality.analyzer.datasource.claim_reader.'
        'query_claims_from_teradata_batch_provider')
    @mock.patch('claims_to_quality.analyzer.datasource.claim_reader.config')
    def test_batch_load_no_data(self, mock_config, query_claims_from_teradata_batch_provider):
        """Test that when hide_sensitive_information is true, the rows are anonymized."""
        mock_config.get.side_effect = mocking_config.config_side_effect(
            {'hide_sensitive_information': False}
        )
        query_claims_from_teradata_batch_provider.return_value = ([], None)

        reader = claim_reader.ClaimsDataReader()
        output = reader.load_batch_from_db(
            ['tax_num'], ['npi_num'],
            datetime.date.today(), datetime.date.today())

        assert output == {}
