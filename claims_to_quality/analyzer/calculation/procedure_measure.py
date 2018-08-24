"""Subclass of QPP Measure that's designed for procedure measures."""
from claims_to_quality.analyzer.calculation.qpp_measure import QPPMeasure
from claims_to_quality.lib.qpp_logging import logging_config

logger = logging_config.get_logger(__name__)


class ProcedureMeasure(QPPMeasure):
    """
    Represents measures of the Procedure type.

    Procedure is one of the types of measures. A Procedure measure is calculated each time
    a procedure is performed.

    Each beneficiary / date of service combination counts as a single eligible instance.

    - If multiple qualifying procedures are on one claim (by TIN/NPI/Bene/Date of Service-level),
    this counts as only one procedure. For example a provider with 2 denominator eligible
    CPT procedure codes on the same Bene/Date of Service would have a denominator of 1.

    - If multiple measure specific QDCs or QDC combinations are listed on the claim,
    performance rates shall be calculated using the most advantageous QDC or QDC combination.

    This class can be extended for implementation of all Procedure type measures.
    """

    def __init__(self, *args, **kwargs):
        """Instantiate a ProcedureMeasure, grouping by beneficiary and date of service."""
        super(ProcedureMeasure, self).__init__(*args, **kwargs)
        self.fields_to_group_by = ['bene_sk', 'clm_from_dt']
