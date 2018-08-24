"""Tests for claim model and the associated functions."""
import datetime

from claims_to_quality.analyzer.models.claim import Claim


class TestClaim():

    def setup(self):
        claim_data = {
            'clm_ptnt_birth_dt': datetime.datetime(1990, 1, 1),
            'clm_from_dt': datetime.datetime(2017, 7, 1),
            'splt_clm_id': 123456789,
            'clm_rndrg_prvdr_npi_num': '0' * 10,
            'claim_lines': [{
                'clm_line_hcpcs_cd': '99210'
            }]
        }
        self.claim = Claim(claim_data)

    def test_bene_age_is_populated_on_init(self):
        assert self.claim.bene_age == 27.5

    def test_str_method(self):
        assert self.claim.__str__() == (
            'Claim-Split Claim ID: 123456789, npi: 0000000000, claim_lines: 1'
        )

    def test_get_procedure_codes(self):
        """The method should return a dict of procedure codes and set the claim's attribute."""
        output = self.claim.get_procedure_codes()
        expected = {'99210': True}

        assert output == expected
        assert self.claim.aggregated_procedure_codes == expected
