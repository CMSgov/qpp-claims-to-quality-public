"""Models for stratum definition."""
from schematics.models import Model
from schematics.types import StringType


class Stratum(Model):
    """Definition of model for a single measure stratum."""

    # TODO: Handle Unicode correctly to add description.
    # description = StringType(serialized_name='description')
    name = StringType(serialized_name='name')

    def __repr__(self):
        """Return a string representation of the stratum."""
        return 'Stratum({})'.format(self.to_native())
