"""Suite of methods used across multiple testing scripts."""
import datetime

from claims_to_quality.lib.teradata_methods import row_handling


def fetch_sample_teradata_rows():
    """Create sample Teradata rows to work with."""
    sample_row_values = [
        {
            'bene_sk': 10001,
            'clm_rndrg_prvdr_tax_num': '123456',
            'clm_line_rndrg_prvdr_npi_num': '123456',
            'clm_ptnt_birth_dt': datetime.date(1991, 4, 23),
            'clm_from_dt': datetime.date(2017, 3, 3),
            'splt_clm_id': '100'
        },
        {
            'bene_sk': 20001,
            'clm_rndrg_prvdr_tax_num': '123456',
            'clm_line_rndrg_prvdr_npi_num': '123456',
            'clm_ptnt_birth_dt': datetime.date(1991, 5, 17),
            'clm_from_dt': datetime.date(2017, 4, 4),
            'splt_clm_id': '100'
        },
        {
            'bene_sk': 30001,
            'clm_rndrg_prvdr_tax_num': '24680',
            'clm_line_rndrg_prvdr_npi_num': '123456',
            'clm_ptnt_birth_dt': datetime.date(1990, 6, 23),
            'clm_from_dt': datetime.date(2017, 5, 5),
            'splt_clm_id': '100'
        },
        {
            'bene_sk': 40001,
            'clm_rndrg_prvdr_tax_num': '24680',
            'clm_line_rndrg_prvdr_npi_num': '123456',
            'clm_ptnt_birth_dt': datetime.date(1974, 2, 23),
            'clm_from_dt': datetime.date(2017, 6, 6),
            'splt_clm_id': '100'
        }
    ]
    return row_handling.convert_dicts_to_teradata_rows(sample_row_values)
