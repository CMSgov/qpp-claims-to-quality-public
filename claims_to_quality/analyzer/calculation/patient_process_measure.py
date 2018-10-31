"""Subclass of QPP Measure that's designed for patient process measures."""
from claims_to_quality.analyzer.calculation.qpp_measure import QPPMeasure
from claims_to_quality.lib.qpp_logging import logging_config

logger = logging_config.get_logger(__name__)


class PatientProcessMeasure(QPPMeasure):
    """
    Represents measures of the Patient-Process type.

    A Patient-Process measure is calculated once per patient per year.
    The most advantageous visit (in terms of QDCs) is used during scoring.
    """

    def __init__(self, *args, **kwargs):
        """Instantiate a PatientProcess Measure, grouping by beneficiary ID."""
        super(PatientProcessMeasure, self).__init__(*args, **kwargs)
        self.fields_to_group_by = ['bene_sk']
