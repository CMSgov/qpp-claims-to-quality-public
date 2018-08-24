"""Model representing one measure performance option."""
from claims_to_quality.analyzer.models.measures import measure_code

from schematics.exceptions import ValidationError
from schematics.models import Model
from schematics.types import StringType
from schematics.types.compound import ListType, ModelType


def _is_valid_option_type(value):
    """Check to see if a string is one of the valid performance option types."""
    if value not in {
        'performanceMet', 'eligiblePopulationExclusion', 'eligiblePopulationException',
        'performanceNotMet'
    }:
            raise ValidationError('Option type must be valid!')
    return True


def _is_valid_quality_code_list(value):
    """
    Check to see if a list is non-empty.

    Used to ensure every performance option has quality codes.
    """
    if not value:
        raise ValidationError('Performance option must have quality codes!')
    return True


class PerformanceOption(Model):
    """This model represents one performance option in a measure definition."""

    option_type = StringType(serialized_name='optionType', validators=[_is_valid_option_type])
    quality_codes = ListType(
        ModelType(measure_code.MeasureCode),
        serialized_name='qualityCodes',
        validators=[_is_valid_quality_code_list]
    )

    def __repr__(self):
        """Return a string representation of the performance option."""
        return 'PerformanceOption({})'.format(self.to_native())

    def __init__(self, *args, **kwargs):
        """Initialize a PerformanceOption with quality codes as a set."""
        super(PerformanceOption, self).__init__(*args, **kwargs)

        quality_code_strings = {
            measure_code.code for measure_code in self.quality_codes
        } if self.quality_codes else set()

        self.quality_code_map = {
            code_string: [
                measure_code
                for measure_code in self.quality_codes if measure_code.code == code_string
            ]
            for code_string in quality_code_strings
        }
