"""Tests for the file decorators.py."""
from claims_to_quality.lib.helpers.decorators import override

import pytest


class LowerString(str):
    """Simple class to test the override decorator."""

    @override
    def islower(self):
        """A LowerString is always lowercase, even when it isn't as a str object."""
        return True

    @override
    def is_pleasant_to_the_ears(self):
        """
        An example of an inappropriate use of the override decorator.

        str instances do not have this method.
        """
        return True


class TestOverride(object):
    """Simple tests for the override decorator."""

    def setup(self):
        """Initialize parent and child instances."""
        self.parent_instance = 'Sphinx of black quartz, judge my vow!'
        self.child_instance = LowerString(self.parent_instance)

    def test_override(self):
        """Test that overriden functions behave as expected."""
        assert not self.parent_instance.islower()
        assert self.child_instance.islower()

    def test_override_raises_error_when_used_incorrectly(self):
        """Test functions not present on the parent class raise an error."""
        with pytest.raises(AttributeError):
            self.child_instance.is_pleasant_to_the_ears()
