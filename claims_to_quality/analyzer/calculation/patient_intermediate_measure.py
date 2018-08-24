"""Subclass of QPP Measure that's designed for patient intermediate measures."""
from claims_to_quality.analyzer.calculation.qpp_measure import QPPMeasure
from claims_to_quality.lib.helpers.decorators import override
from claims_to_quality.lib.qpp_logging import logging_config

logger = logging_config.get_logger(__name__)


class PatientIntermediateMeasure(QPPMeasure):
    """
    Represents measures of the Patient-Intermediate type.

    Patient-Intermediate is one of the types of measures. A Patient-Intermediate measure is
    calculated once per patient per year using the most recent visit where quality codes are
    submitted for scoring.

    This class can be extended for implementation of all Patient-Intermediate type measures.
    """

    def __init__(self, *args, **kwargs):
        """Instantiate a PatientIntermediateMeasure, grouping by beneficiary ID."""
        super(PatientIntermediateMeasure, self).__init__(*args, **kwargs)
        self.fields_to_group_by = ['bene_sk']

    @staticmethod
    def get_claims_from_latest_date(claims):
        """
        Given a list of claims, return only the most recent claim based on clm_from_dt.

        In the case of two claims on the same most recent date, returns all claims from that date.
        """
        logger.debug('Get claims from latest date.')
        if not claims:
            return []

        latest_date = max(claims, key=lambda x: x.clm_from_dt).clm_from_dt
        latest_claims = [claim for claim in claims if claim.clm_from_dt == latest_date]

        return latest_claims

    @override
    def get_eligible_instances(self, claims):
        """
        Group claims together into eligible instances.

        This overrides a method from QPPMeasure, since the "most recent claim"
        logic is unique to measures of this type.

        For Patient Intermediate measures, an eligible instance consists of either
        (a) the most recent claim with a QDC for a particular beneficiary, or
        (b) the most recent claim for a beneficiary if they had no claims with QDCs.

        Returns a list of eligible instances, which are themselves lists of claims.

        Args:
            claims (list(Claim)): Claims to be grouped.
        Returns:
            list(list(Claim)), where each inner list is a single eligible instance.
        """
        logger.debug('Get eligible instances.')
        result = []

        claims_by_beneficiary = self.group_claims_by_field_values(self.fields_to_group_by, claims)
        for beneficiary_claims_subset in claims_by_beneficiary:
            filtered_subset = (self.filter_by_presence_of_quality_codes(
                beneficiary_claims_subset) or beneficiary_claims_subset)

            latest_relevant_claims = self.get_claims_from_latest_date(filtered_subset)
            result.append(latest_relevant_claims)

        return result
