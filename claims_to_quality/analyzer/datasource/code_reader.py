"""Read code objects from JSON."""
from claims_to_quality.config import config

import ujson as json


def load_quality_codes(
    measures=None,
    json_path=config.get('assets.qpp_single_source_json')[config.get('calculation.measures_year')]
):
    """
    Load quality codes from the single source JSON file and return them as a set of strings.

    If the measures parameter is provided, restrict to quality codes on those measures.
    """
    with open(json_path, encoding='utf-8') as file:
        single_source = json.load(file)

    # Filter out measures that are not claims-based quality measures with performanceOptions.
    single_source = filter(lambda measure: 'performanceOptions' in measure, single_source)

    return {
        code['code'] for measure in single_source
        for option in measure['performanceOptions']
        for code in option['qualityCodes']
        if (measures is None or measure['measureId'] in measures)
    }
