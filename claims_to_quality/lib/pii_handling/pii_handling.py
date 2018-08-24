"""Methods for handling Personally Identifiable Information (PII) securely."""

import random


def generate_fake_tin(seed=None):
    """
    Return a fake TIN in the format accepted by Nava's API.

    The API accepts 9-digit strings starting with '000'.
    """
    random.seed(seed)
    return str(random.randint(0, 10**6 - 1)).zfill(9)


def generate_fake_npi(seed=None):
    """
    Return a fake NPI in the format accepted by Nava's API.

    The API accepts 10-digit strings starting with '0'.
    """
    random.seed(seed)
    return str(random.randint(0, 10**9 - 1)).zfill(10)
