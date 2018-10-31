"""Test date handling and performance window determination."""
import datetime

from claims_to_quality.analyzer.models.claim import Claim
from claims_to_quality.analyzer.models.claim_line import ClaimLine
from claims_to_quality.analyzer.processing import performance_period_handling

import pytest


class TestPerformancePeriodHandling():
    """Tests for the performance_period_handling module."""

    def setup(self):
        """Initialize useful values."""
        self.performance_year = 2017

        self.line_with_quality_code = ClaimLine({'clm_line_hcpcs_cd': 'G9607'})
        self.line_without_quality_code = ClaimLine({'clm_line_hcpcs_cd': 'not_a_real_code'})

        self.claim_with_quality_code_january = Claim({
            'clm_from_dt': datetime.date(self.performance_year, 1, 1),
            'claim_lines': [self.line_with_quality_code]
        })
        self.claim_without_quality_code_january = Claim({
            'clm_from_dt': datetime.date(self.performance_year, 1, 1),
            'claim_lines': [self.line_without_quality_code]
        })
        self.claim_too_late = Claim({
            'clm_from_dt': datetime.date(self.performance_year + 1, 1, 1),
            'claim_lines': [self.line_with_quality_code]
        })
        self.claim_too_early = Claim({
            'clm_from_dt': datetime.date(self.performance_year - 1, 1, 1),
            'claim_lines': [self.line_with_quality_code]
        })
        self.claim_with_quality_code_december = Claim({
            'clm_from_dt': datetime.date(self.performance_year, 12, 1),
            'claim_lines': [self.line_with_quality_code]
        })

    def test_determine_quality_code_submission_period_raises_error(self):
        """The function should raise an error whenever no quality codes are present."""
        with pytest.raises(performance_period_handling.MissingCodeException):
            performance_period_handling._determine_quality_code_submission_period(
                claims_data=[
                    self.claim_without_quality_code_january,
                    self.claim_too_early,
                    self.claim_too_late
                ],
                min_date=datetime.date(self.performance_year, 1, 1),
                max_date=datetime.date(self.performance_year, 12, 31)
            )

    def test_determine_performance_period_preserves_valid_date_ranges(self):
        """Valid date ranges longer than the minimum number of days should remain unchanged."""
        claims = [self.claim_with_quality_code_january, self.claim_with_quality_code_december]
        start_date, end_date = performance_period_handling.determine_performance_period(
            claims_data=claims,
            min_date=datetime.date(self.performance_year, 1, 1),
            max_date=datetime.date(self.performance_year, 12, 31)
        )

        assert start_date == self.claim_with_quality_code_january['clm_from_dt']
        assert end_date == self.claim_with_quality_code_december['clm_from_dt']

    def test_determine_performance_period_when_window_is_too_short(self):
        """
        Reporting periods should be extended to the minimum length if they are below it.

        By default, the periods should be extended by moving the right endpoint later in the year.
        """
        claims = [self.claim_with_quality_code_january]
        start_date, end_date = performance_period_handling.determine_performance_period(
            claims_data=claims,
            min_date=datetime.date(self.performance_year, 1, 1),
            max_date=datetime.date(self.performance_year, 12, 31)
        )

        assert start_date == self.claim_with_quality_code_january['clm_from_dt']
        assert end_date == self.claim_with_quality_code_january['clm_from_dt'] + \
            performance_period_handling.MINIMUM_REPORTING_PERIOD

    def test_determine_performance_period_when_window_is_too_short_at_end_of_year(self):
        """
        Reporting periods should be extended to the minimum length if they are below it.

        When the left endpoint is too late in the year, it should be moved earlier to ensure
        that the minimum reporting period length is met.
        """
        claims = [self.claim_with_quality_code_december]
        start_date, end_date = performance_period_handling.determine_performance_period(
            claims_data=claims,
            min_date=datetime.date(self.performance_year, 1, 1),
            max_date=datetime.date(self.performance_year, 12, 31)
        )

        assert start_date == datetime.date(self.performance_year, 12, 31) - \
            performance_period_handling.MINIMUM_REPORTING_PERIOD
        assert end_date == datetime.date(self.performance_year, 12, 31)

    def test_determine_performance_period_no_quality_code_present(self):
        """Reporting periods with no quality codes should raise an exception."""
        claims = [
            self.claim_without_quality_code_january, self.claim_too_early, self.claim_too_late]

        with pytest.raises(performance_period_handling.MissingCodeException):
            start_date, end_date = performance_period_handling.determine_performance_period(
                claims_data=claims,
                min_date=datetime.date(self.performance_year, 1, 1),
                max_date=datetime.date(self.performance_year, 12, 31)
            )
