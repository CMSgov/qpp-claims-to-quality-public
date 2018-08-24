"""Model definition for claim line."""
from __future__ import absolute_import

from schematics.models import Model
from schematics.types import DateType, IntType, StringType
from schematics.types.compound import ListType


class ClaimLine(Model):
    """
    This model contains the claim-line specific information.

    Each claim will have multiple claim lines. Claim lines contain all of the encounter
    or procedure codes that took place in a visit.
    """

    clm_line_num = IntType()  # Claim line number
    clm_line_hcpcs_cd = StringType()  # HCPCS or C4 CPT code at the claim line level
    mdfr_cds = ListType(StringType)  # Come from 5 columns, some of which will be null
    clm_pos_code = StringType()  # Place of service
    clm_line_from_dt = DateType()  # Beginning date of service for the line item
    clm_line_thru_dt = DateType()  # Final date of service for the line item

    def __str__(self):
        """Return a string representation of the claim."""
        # TODO - Add more relevant info to __repr__.
        return 'ClaimLine - line_number: {clm_line_num}'.format(clm_line_num=self.clm_line_num)
