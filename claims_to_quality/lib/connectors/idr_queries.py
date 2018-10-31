"""This module contains various queries for extracting data from the IDR."""
from datetime import datetime, timedelta

from claims_to_quality.config import config
from claims_to_quality.lib.teradata_methods import sql_formatting


"""
ACCESS_LAYER_BASE_QUERY_BATCH
This query allows you to query the IDR for claims data for multiple providers.
You will need to provide a list of NPIs, a list of TINs, as well as a start_date and end_date.
The provider lists must coincide in length and be in the same order.
It will first query for all claims that contain one of the TINs and one of the NPIs
and then be filtered down to claims containing the exact combinations that we were looking for.
"""
# Queries are masked as PRIVATE to avoid exposing the data structure of IDR tables.
ACCESS_LAYER_BASE_QUERY_BATCH = "PRIVATE"


class InputError(Exception):
    """Input Error."""

    pass


def get_access_layer_batch_query(tins, npis, start_date, end_date):
    """Populate the Teradata SQL statement to query the IDR for provider information in batches.

     Args:
        npis ([str]): National provider identifiers to load.
        tins ([str]): Provider tax identification numbers to load.
        start_date (datetime): Start date of data to load.
        end_date (datetime): End date of data to load.
    Returns:
        SQL query to retrieve data from the IDR.
    """
    if len(tins) != len(npis):
        raise InputError('The TINs and NPIs list must be of the same size.')

    npi_tins = ['{}{}'.format(npi, tin) for npi, tin in zip(npis, tins)]

    return ACCESS_LAYER_BASE_QUERY_BATCH.format(
        npis=sql_formatting.to_sql_list(npis),
        tins=sql_formatting.to_sql_list(tins),
        npi_tins=sql_formatting.to_sql_list(npi_tins),
        start_date=datetime.strftime(start_date, '%Y-%m-%d'),
        end_date=datetime.strftime(end_date, '%Y-%m-%d'),
        as_was_date=datetime.strftime(
            config.get('calculation.as_was_date'), '%Y-%m-%d'
        ),
        access_layer_name=config.get('teradata.access_layer_name'),
        medicare_vdm_name=config.get('teradata.medicare_vdm_name')
    )


"""
DISCHARGE_QUERY
This query allows you to query the IDR for any discharge dates for beneficiaries seen by
a list of providers. This information is necessary to calculate measure 46.
You will need to provide a list of NPIs, a list of TINs, as well as a start_date and end_date.
In addition, a list of procedure codes indicating discharge must be provided as hidden_codes.
The provider lists must coincide in length and be in the same order.
Note that claim type codes 40, 50, 71, 72 are the only ones with any claims that have
the corresponding hidden codes.
"""
# Queries are masked as PRIVATE to avoid exposing the data structure of IDR tables.
DISCHARGE_QUERY = "PRIVATE"


def get_discharge_date_query(tins, npis, discharge_period, hidden_codes):
    """
    Query the IDR to determine discharge eligibility for a list of providers.

    Return query to filter list of eligible (bene, discharge_date).
    """
    start_date = config.get('calculation.start_date') - timedelta(days=discharge_period)
    end_date = config.get('calculation.end_date')

    # Note - hidden_codes are quoted in the query by to_sql_list.
    return DISCHARGE_QUERY.format(
        start_date=datetime.strftime(start_date, '%Y-%m-%d'),
        end_date=datetime.strftime(end_date, '%Y-%m-%d'),
        as_was_date=datetime.strftime(
            config.get('calculation.as_was_date'), '%Y-%m-%d'
        ),
        tins=sql_formatting.to_sql_list(tins),
        npis=sql_formatting.to_sql_list(npis),
        access_layer_name=config.get('teradata.access_layer_name'),
        hidden_codes=sql_formatting.to_sql_list(hidden_codes)
    )


# Queries are masked as PRIVATE to avoid exposing the data structure of IDR tables.
CT_SCAN_QUERY = "PRIVATE"


# TODO - Select only necessary dates.
def get_ct_scan_query(bene_date_set):
    """
    Query the IDR to determine when beneficiaries had a CT scan.

    Return query to get CT scan dates for the beneficiaries.
    Note - The list returned then needs to be filtered to only keep
    CT scans which happened on the specified claim date.
    """
    bene_sks, from_dates = zip(*bene_date_set)
    start_date = min(from_dates)
    # TODO - Pass in thru_dates as well and use max instead of config.
    end_date = config.get('calculation.end_date')

    return CT_SCAN_QUERY.format(
        access_layer_name=config.get('teradata.access_layer_name'),
        start_date=datetime.strftime(start_date, '%Y-%m-%d'),
        end_date=datetime.strftime(end_date, '%Y-%m-%d'),
        as_was_date=datetime.strftime(
            config.get('calculation.as_was_date'), '%Y-%m-%d'
        ),
        bene_sks=sql_formatting.to_sql_list(bene_sks)
    )


# Queries are masked as PRIVATE to avoid exposing the data structure of IDR tables.
MSSA_QUERY = "PRIVATE"


def get_mssa_query(bene_sks, encounter_codes, start_date, end_date):
    """
    Query the IDR to find all claim lines related to hospitalization due to MSSA.

    Return query to get all MSSA claim lines for the beneficiaries.
    Note - The list returned needs to be grouped into episodes.
    """
    access_layer_name = config.get('teradata.access_layer_name')
    medicare_vdm_name = config.get('teradata.medicare_vdm_name')

    return MSSA_QUERY.format(
        access_layer_name=access_layer_name,
        medicare_vdm_name=medicare_vdm_name,
        start_date=datetime.strftime(start_date, '%Y-%m-%d'),
        end_date=datetime.strftime(end_date, '%Y-%m-%d'),
        as_was_date=datetime.strftime(
            config.get('calculation.as_was_date'), '%Y-%m-%d'
        ),
        bene_sks=sql_formatting.to_sql_list(bene_sks),
        encounter_codes=sql_formatting.to_sql_list(encounter_codes)
    )
