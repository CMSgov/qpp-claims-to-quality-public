"""Tests for date handling helpers."""
from datetime import datetime

from claims_to_quality.lib.helpers.date_handling import DateRange


# Tests for DateRange.
def test_date_range_init():
    """Test DateRange init."""
    earlier = datetime(2017, 1, 1)
    later = datetime(2017, 1, 4)
    date_range = DateRange(earlier, later)
    assert earlier == date_range.start
    assert later == date_range.end


def test_date_range_init_wrong_order():
    """Test init when dates in wrong order."""
    earlier = datetime(2017, 1, 1)
    later = datetime(2017, 1, 4)
    date_range = DateRange(later, earlier)
    assert earlier == date_range.start
    assert later == date_range.end


def test_contains_date():
    """Test DateRange contains_date."""
    date_range = DateRange(datetime(2017, 1, 1), datetime(2017, 1, 4))
    in_date = datetime(2017, 1, 1)
    out_date = datetime(2017, 1, 7)

    assert date_range.contains_date(in_date)
    assert not date_range.contains_date(out_date)


def test_contains_date_end():
    """Test DateRange contains_date."""
    date_range = DateRange(datetime(2017, 1, 1), datetime(2017, 1, 4))
    end_date = datetime(2017, 1, 4)

    assert date_range.contains_date(end_date)


def test_date_range_overlap():
    """Test if two DateRanges overlap."""
    date_range = DateRange(datetime(2017, 1, 4), datetime(2017, 1, 1))
    date_range_overlap = DateRange(datetime(2017, 1, 4), datetime(2017, 1, 8))
    date_range_no_overlap = DateRange(datetime(2017, 1, 5), datetime(2017, 1, 8))

    assert DateRange.date_range_overlap(date_range, date_range_overlap)
    assert not DateRange.date_range_overlap(date_range, date_range_no_overlap)


def test_merge_date_ranges_overlap():
    """Merge a list of DateRanges."""
    date_range_1 = DateRange(datetime(2017, 1, 1), datetime(2017, 1, 2))
    date_range_2 = DateRange(datetime(2017, 1, 1), datetime(2017, 1, 3))
    date_range_3 = DateRange(datetime(2017, 1, 3), datetime(2017, 1, 8))

    date_ranges = [date_range_1, date_range_2, date_range_3]

    merged_ranges = DateRange.merge_date_ranges(date_ranges)

    expected = [DateRange(datetime(2017, 1, 1), datetime(2017, 1, 8))]

    assert merged_ranges == expected


def test_merge_date_ranges_back_to_back():
    """Test that if two date ranges abut each other, they are merged."""
    date_range_1 = DateRange(datetime(2017, 5, 2), datetime(2017, 5, 5))
    date_range_2 = DateRange(datetime(2017, 5, 6), datetime(2017, 5, 6))

    merged_ranges = DateRange.merge_date_ranges([date_range_1, date_range_2])

    assert merged_ranges == [DateRange(datetime(2017, 5, 2), datetime(2017, 5, 6))]


def test_string_representation():
    """Test that string representations of DateRange objects return expected output."""
    date_range = DateRange(datetime(2017, 1, 1), datetime(2017, 1, 2))
    assert date_range.__repr__() == 'DateRange(2017-01-01 00:00:00 to 2017-01-02 00:00:00)'
