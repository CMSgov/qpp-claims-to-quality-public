"""Date handling tools."""
import datetime

from claims_to_quality.lib.qpp_logging import logging_config

logger = logging_config.get_logger(__name__)


class DateRange(object):
    """
    DateRange object.

    Taking start, end as input.
    """

    def __init__(self, start, end):
        """Create a DateRange object."""
        self.start = min(start, end)
        self.end = max(start, end)

    def __repr__(self):
        """Representation for DateRange objects."""
        return 'DateRange({start} to {end})'.format(start=self.start, end=self.end)

    def __eq__(self, other):
        """Define DateRange equality."""
        return self.start == other.start and self.end == other.end

    def __lt__(self, other):
        """Define DateRange less than method."""
        return self.start < other.start

    def contains_date(self, date):
        """Test if DateRange contains date."""
        return self.start <= date <= self.end

    @staticmethod
    def date_range_overlap(date_range_1, date_range_2):
        """Test if two DateRanges overlap."""
        return max(date_range_1.start, date_range_2.start) <=\
            min(date_range_1.end, date_range_2.end)

    @staticmethod
    def merge_date_ranges(date_ranges):
        """
        Merge a list of DateRanges by merging together overlapping ranges.

        Returns a reduced list of non-overlapping date ranges.
        """
        sorted_by_lower_bound = sorted(date_ranges)
        merged = []

        for later_start_date in sorted_by_lower_bound:
            if not merged:
                merged.append(later_start_date)
            else:
                earlier_start_date = merged[-1]
                # Test for intersection between earlier_start_date and later_start_date:
                # we know via sorting that earlier_start_date[0] <= later_start_date[0]
                # We also want to combine date ranges with consecutive days.
                if later_start_date.start <= (earlier_start_date.end + datetime.timedelta(1)):
                    upper_bound = max(earlier_start_date.end, later_start_date.end)
                    # Replace by merged interval.
                    merged[-1] = DateRange(earlier_start_date.start, upper_bound)
                else:
                    merged.append(later_start_date)
        return merged
