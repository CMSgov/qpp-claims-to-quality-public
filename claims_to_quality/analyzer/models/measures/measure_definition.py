"""Models for measure definition."""
from claims_to_quality.analyzer.models.measures.eligibility_option import EligibilityOption
from claims_to_quality.analyzer.models.measures.performance_option import PerformanceOption
from claims_to_quality.analyzer.models.measures.stratum import Stratum
from claims_to_quality.lib.helpers import dict_utils

from schematics.models import Model
from schematics.types import BooleanType, StringType
from schematics.types.compound import ListType, ModelType


class MeasureDefinition(Model):
    """Top-level measure definition model."""

    measure_number = StringType(serialized_name='measureId')  # Formatted as e.g. '024'
    eligibility_options = ListType(
        ModelType(EligibilityOption), serialized_name='eligibilityOptions')
    performance_options = ListType(
        ModelType(PerformanceOption), serialized_name='performanceOptions')
    is_inverse = BooleanType(serialized_name='isInverse')
    strata = ListType(ModelType(Stratum), serialized_name='strata')

    def __init__(self, *args, **kwargs):
        """Initialize a MeasureDefinition object."""
        super(MeasureDefinition, self).__init__(*args, **kwargs)

        self.procedure_code_map = dict_utils.merge_dictionaries_with_list_values(
            [option.procedure_code_map for option in self.eligibility_options]
        )

        self.quality_code_map = dict_utils.merge_dictionaries_with_list_values(
            [option.quality_code_map for option in self.performance_options]
        )

    def get_measure_quality_codes(self):
        """Get quality codes from the measure definition."""
        return set([
            quality_code.code for option in self.performance_options
            for quality_code in option.quality_codes
        ])

    def __repr__(self):
        """Return a string representation of the measure."""
        return 'MeasureDefinition({})'.format(self.to_native())
