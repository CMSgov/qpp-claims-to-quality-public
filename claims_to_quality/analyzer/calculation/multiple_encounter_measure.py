"""Subclass of QPP Measure to calculate measures requiring multiple encounters."""
from claims_to_quality.analyzer.calculation.patient_process_measure import PatientProcessMeasure
from claims_to_quality.lib.helpers.decorators import override
from claims_to_quality.lib.qpp_logging import logging_config

logger = logging_config.get_logger(__name__)


class MultipleEncounterMeasure(PatientProcessMeasure):
    """
    Represents measures of the Patient-Process type that require multiple encounters.

    These measures are to be reported once per patient per year, provided that the
    patient has had multiple encounters during the reporting period.

    Patients with fewer than the minimum number of encounters during the reporting period
    do not contribute eligible instances.

    Measure 435 uses this logic.
    """

    MINIMUM_NUMBER_OF_ENCOUNTERS = 2

    @override
    def get_eligible_instances(self, claims):
        """
        Group claims together into eligible instances.

        Returns a list of eligible instances, which are themselves lists of claims.
        Each eligible instance must contain at least as many claims as the value of the
        attribute `self.minimum_number_of_encounters`.

        Only claims past this minimum threshold count for performance.

        Args:
            claims (list(Claim)): Claims to be grouped.
        Returns:
            list(list(Claim)), where each inner list is a single eligible instance.
        """
        instances = super(MultipleEncounterMeasure, self).get_eligible_instances(claims)
        return self._filter_instances_by_multiple_encounters(
            instances=instances,
            minimum_number_of_encounters=self.MINIMUM_NUMBER_OF_ENCOUNTERS
        )

    @staticmethod
    def _filter_instances_by_multiple_encounters(
        instances,
        minimum_number_of_encounters,
        date_column='clm_from_dt'
    ):
        """
        Return only the instances that consist of a sufficient number of encounters.

        Removes the initial claims from each instance since G-codes on claims that occurred
        before the minimum number of encounters have been reached should not count toward
        measure performance.
        """
        # TODO: Evaluate the likelihood of a measure requiring > 2 separate encounters.
        # If this outcome seems possible, revamp this method accordingly.
        logger.debug('Filter eligible instances by the presence of multiple encounters.')
        first_dates_per_instance = [
            min(claim.__getattribute__(date_column) for claim in instance)
            for instance in instances
        ]

        instances_excluding_first_encounters = [
            [claim for claim in instance if claim.__getattribute__(date_column) > start_date]
            for instance, start_date in zip(instances, first_dates_per_instance)
        ]

        return [
            instance for instance in instances_excluding_first_encounters
            if len(instance) > 0
        ]
