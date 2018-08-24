"""Tests for pii_handling utlitities."""
from claims_to_quality.lib.pii_handling import pii_handling


def test_generate_fake_tin():
    """Verify that generate_fake_tin produces tins in the correct format."""
    fake_tin = pii_handling.generate_fake_tin()
    assert len(fake_tin) == 9
    assert fake_tin.startswith('000')


def test_generate_fake_npi():
    """Verify that generate_fake_tin produces npi in the correct format."""
    fake_tin = pii_handling.generate_fake_npi()
    assert len(fake_tin) == 10
    assert fake_tin.startswith('0')
