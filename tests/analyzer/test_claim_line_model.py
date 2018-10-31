"""Tests for claim_line model and the associated functions."""
from claims_to_quality.analyzer.models import claim_line


def test_str_method():
    """Test that claim lines are represented in a readable format."""
    line = claim_line.ClaimLine(
        {'clm_line_hcpcs_cd': 'code', 'mdfr_cds': ['GQ'], 'clm_pos_code': '24', 'clm_line_num': 1}
    )
    assert line.__str__() == 'ClaimLine - line_number: 1'
