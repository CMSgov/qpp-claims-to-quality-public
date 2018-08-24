"""Model definition for Claim."""
from __future__ import absolute_import

from claims_to_quality.analyzer.models import claim_line

from dateutil.relativedelta import relativedelta

from schematics.models import Model
from schematics.types import BooleanType, DateType, DictType, StringType
from schematics.types.compound import ListType, ModelType


class Claim(Model):
    """This model represents each claim submitted by a provider."""

    splt_clm_id = StringType()  # Split claim ID
    clm_rndrg_prvdr_npi_num = StringType()  # Unique ID of the provider
    clm_rndrg_prvdr_tax_num = StringType()  # Tax ID of the provider

    bene_sk = StringType()  # Unique ID of beneficiary
    clm_ptnt_birth_dt = DateType()  # Date of birth of beneficiary
    clm_bene_sex_cd = StringType()  # Sex of beneficiary. 1 for male, 2 for female
    clm_from_dt = DateType()  # Claim from date
    clm_thru_dt = DateType()  # Claim through date

    dx_codes = ListType(StringType)  # List of diagnosis codes
    claim_lines = ListType(ModelType(claim_line.ClaimLine))  # The associated claim lines

    aggregated_procedure_codes = DictType(BooleanType)  # Map of procedure codes in all claim lines.

    def __init__(self, *args, **kwargs):
        """Initialize a Claim object, calculating and storing beneficiary age as float."""
        super(Claim, self).__init__(*args, **kwargs)
        # Store patient age in years at date of service.
        age_delta = relativedelta(self.clm_from_dt, self.clm_ptnt_birth_dt)
        self.bene_age = age_delta.years + age_delta.months / 12.0 + age_delta.days / 365.0

    def get_procedure_codes(self):
        """
        Return the map of procedure codes present in all claim lines under this claim.

        Check that codes exist. If this claim was not created by claim_reader (e.g. in a unit test)
        then aggregated_procedure_codes will be null so we need to populate it.
        """
        if not self.aggregated_procedure_codes:
            self.aggregated_procedure_codes = {
                line.clm_line_hcpcs_cd: True for line in self.claim_lines
            }

        return self.aggregated_procedure_codes

    def __str__(self):
        """Return a string representation of the claim."""
        return 'Claim-Split Claim ID: {splt_clm_id}, npi: {npi}, claim_lines: {claim_lines}'.format(
            splt_clm_id=self.splt_clm_id,
            npi=self.clm_rndrg_prvdr_npi_num,
            claim_lines=len(self.claim_lines or [])
        )
