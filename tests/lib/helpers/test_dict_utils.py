"""Methods to test dictionary utility functionality."""
from claims_to_quality.lib.helpers import dict_utils


def test_nested_update_mapping():
    """The nested_update method should recursively update nested collections as expected."""
    base_dict = {
        'mapping_valued_key': {
            'list_valued_key': [0, 1, 2],
            'int_valued_key': 10,
        },
        'unshared_key': -33
    }

    new_dict = {
        'mapping_valued_key': {
            'list_valued_key': [3, 4],
            'int_valued_key': 1000,
            'missing_key': [2, 26, 91]
        },
        'new_key': 9999
    }

    output = dict_utils.nested_update(base_dict, new_dict)
    expected = {
        'mapping_valued_key': {
            'list_valued_key': [0, 1, 2, 3, 4],
            'int_valued_key': 1000,
            'missing_key': [2, 26, 91]
        },
        'unshared_key': -33,
        'new_key': 9999
    }
    assert output == expected
