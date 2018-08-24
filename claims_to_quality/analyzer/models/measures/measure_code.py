"""Model representing one encounter/procedure/quality code in a measure definition."""
from schematics.models import Model
from schematics.types import StringType
from schematics.types.compound import ListType


class MeasureCode(Model):
    """This model represents each encounter/procedure/quality code in a measure definition."""

    code = StringType()
    modifiers = ListType(StringType())
    modifier_exclusions = ListType(StringType(), serialized_name='modifierExclusions')
    places_of_service = ListType(StringType(), serialized_name='placesOfService')
    places_of_service_exclusions = ListType(
        StringType(), serialized_name='placesOfServiceExclusions')

    def __repr__(self):
        """Return a string representation of the measure code."""
        return 'MeasureCode({})'.format(self.to_native())

    def __init__(self, *args, **kwargs):
        """Initialize a MeasureCode, pre-calculating which steps to use to filter claim lines."""
        super(MeasureCode, self).__init__(*args, **kwargs)

        self.constraints = [self._does_line_match_hcpcs_string]
        # Only apply constraints relevant to the measure code.
        if self.places_of_service:
            self.pos_set = set(self.places_of_service)
            self.constraints.append(self._does_line_meet_pos_constraint)

        if self.places_of_service_exclusions:
            self.pos_x_set = set(self.places_of_service_exclusions)
            self.constraints.append(self._does_line_meet_pos_exclusion_constraint)

        if self.modifiers:
            self.modifier_set = set(self.modifiers)
            self.constraints.append(self._does_line_meet_modifier_constraint)

        if self.modifier_exclusions:
            self.modifier_x_set = set(self.modifier_exclusions)
            self.constraints.append(self._does_line_meet_modifier_exclusion_constraint)

    def matches_line(self, line):
        """Apply measure code constraints to the claim line."""
        return all(constraint(line) for constraint in self.constraints)

    def _does_line_match_hcpcs_string(self, line):
        return self.code == line.clm_line_hcpcs_cd

    def _does_line_meet_pos_constraint(self, line):
        """Validate place of service."""
        return line.clm_pos_code in self.pos_set

    def _does_line_meet_pos_exclusion_constraint(self, line):
        """Validate place of service exclusions."""
        return line.clm_pos_code not in self.pos_x_set

    def _does_line_meet_modifier_constraint(self, line):
        """Validate code against modifiers."""
        return not self.modifier_set.isdisjoint(line.mdfr_cds)

    def _does_line_meet_modifier_exclusion_constraint(self, line):
        """Validate code against modifier exclusions."""
        return self.modifier_x_set.isdisjoint(line.mdfr_cds)
