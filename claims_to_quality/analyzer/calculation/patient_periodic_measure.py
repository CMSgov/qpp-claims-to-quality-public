"""Subclass of QPPMeasure designed for patient-periodic measures."""
import collections
import datetime

from claims_to_quality.analyzer.calculation.qpp_measure import QPPMeasure
from claims_to_quality.config import config
from claims_to_quality.lib.helpers.decorators import override
from claims_to_quality.lib.qpp_logging import logging_config

logger = logging_config.get_logger(__name__)


class PatientPeriodicMeasure(QPPMeasure):
    """
    Represents measures of the patient-periodic type.

    Patient-periodic measures are calculated once per patient per relevant time period.

    For example, each performance year contains two flu seasons: January-March and October-December.
    Certain actions (e.g., immunization) should be performed for each patient in each flu season.
    """

    def __init__(self, *args, **kwargs):
        """Instantiate a PatientPeriodic Measure, grouping by beneficiary and date range."""
        super(PatientPeriodicMeasure, self).__init__(*args, **kwargs)
        self.fields_to_group_by = ['bene_sk']
        self.date_ranges = self.get_relevant_date_ranges()

    @override
    def get_eligible_instances(self, claims):
        """
        Group claims together into eligible instances.

        Returns a list of eligible instances, which are themselves lists of claims.

        For patient-periodic measures, an eligible instance consists of all claims for a given
        patient within each distinct date range specified by the measure definition.
        Consider a measure with two date ranges: January-March and October-December.
        If a patient has a claim in January and a separate claim in October,
        these will count as two distinct eligible instances.

        Args:
            claims (list(Claim)): Claims to be grouped.
        Returns:
            list(list(Claim)), where each inner list is a single eligible instance.
        """
        logger.debug('Get eligible instances.')
        instances_by_claim_attributes = collections.defaultdict(list)
        for claim in claims:
            # Determine which date ranges the claim belongs to.
            matching_date_range_indexes = self._select_date_ranges_claim_belongs_to(
                claim, self.date_ranges
            )
            # If the claim matches at least one date range, it qualifies as an eligible instance.
            if matching_date_range_indexes:
                claim_attributes = tuple(claim[field] for field in self.fields_to_group_by)

                # If a claim matches multiple date ranges, count each match as a separate instance.
                for index in matching_date_range_indexes:
                    combined_claim_attributes = claim_attributes + (index,)
                    instances_by_claim_attributes[combined_claim_attributes].append(claim)

        return list(instances_by_claim_attributes.values())

    def get_relevant_date_ranges(self):
        """
        Determine the relevant date ranges from the measure definition.

        Because this information is not available in the measure definition JSON itself,
        this function provides an enumeration of all patient periodic measures and their
        associated date ranges.
        """
        # Use the flu season for Measure 110.
        if self.measure_definition['measure_number'] == '110':
            return self._get_flu_season_from_start_and_end_dates(
                start_date=config.get('calculation.start_date'),
                end_date=config.get('calculation.end_date')
            )
        # Due to incorrect codes, Measure 14 in 2018 only applies from February onward.
        if (
            self.measure_definition['measure_number'] == '014' and
            config.get('calculation.measures_year') == 2018
        ):
            return PatientPeriodicMeasure._get_measure_14_dates_2018(
                performance_year=config.get('calculation.measures_year')
            )
        # Raise an error if the measure is not on the list of known patient-periodic measures.
        raise AssertionError(
            'Measure {measure} is not a patient-periodic measure in year {year}!'.format(
                measure=self.measure_definition['measure_number'],
                year=config.get('calculation.measures_year')
            )
        )

    @staticmethod
    def _select_date_ranges_claim_belongs_to(claim, date_ranges):
        """
        Return a list of indexes for the date ranges that the claim belongs to.

        Args:
            claim (Claim): claim in consideration
            date_ranges list(tuple(datetime.date)): list of (start_date, end_date) for each range
        Returns:
            list(int): A list of all date ranges the claim belongs to (by index).
        """
        return [
            index for index, date_range in enumerate(date_ranges)
            if PatientPeriodicMeasure._is_claim_in_date_range(claim, date_range)
        ]

    @staticmethod
    def _get_flu_season_from_start_and_end_dates(start_date, end_date):
        """
        Return all date ranges overlapping the given start and end date.

        In addition, returns possibly extraneous date ranges in the same year.
        """
        date_ranges = []
        min_year = start_date.year
        max_year = end_date.year

        years = range(min_year, max_year + 1)
        for year in years:
            january_season_start_date = datetime.date(year=year, month=1, day=1)
            january_season_end_date = datetime.date(year=year, month=3, day=31)
            date_ranges.append(
                (january_season_start_date, january_season_end_date)
            )
            december_season_start_date = datetime.date(year=year, month=10, day=1)
            december_season_end_date = datetime.date(year=year, month=12, day=31)

            date_ranges.append(
                (december_season_start_date, december_season_end_date)
            )

        return date_ranges

    @staticmethod
    def _get_measure_14_dates_2018(performance_year):
        """
        Return a restricted date range for Measure 14 in performance year 2018.

        Due to an error in the single source document, incorrect codes were used for this measure.
        The codes were corrected in February 2018, so the performance period for this measure
        in 2018 excludes the month of January.
        """
        # Raise an AssertionError if any year besides 2018 is passed to this function.
        assert performance_year == 2018
        # Otherwise, return February through December of 2018.
        return [
            (datetime.date(year=2018, month=2, day=1), datetime.date(year=2018, month=12, day=31))
        ]
