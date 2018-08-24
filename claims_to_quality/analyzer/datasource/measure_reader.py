"""Read measure definitions from JSON."""
from claims_to_quality.analyzer.models.measures.measure_definition import MeasureDefinition
from claims_to_quality.config import config

import ujson as json


def load_single_source(
    json_path=config.get('assets.qpp_single_source_json')[
        config.get('calculation.measures_year')
    ]
):
    """
    Load the single source file as JSON keyed by measure number.

    Only load claims-based measures by using the 'performanceOptions' key.
    """
    with open(json_path, encoding='utf-8') as file:
        single_source_as_list = json.load(file)

    return {
        measure_json['measureId']: measure_json
        for measure_json in single_source_as_list
        if 'performanceOptions' in measure_json
    }


def load_measure_definition(measure_number, single_source_json=load_single_source()):
    """
    Load a MeasureDefinition model describing a single measure.

    Arguments:
        measure_number: A string, e.g. '046'
        single_source_json: a mapping measure_number-->measure_definition
    """
    measure_definition = single_source_json.get(measure_number, None)
    if measure_definition:
        return MeasureDefinition(measure_definition, strict=False)
    else:
        raise KeyError('Measure number {} does not exist.'.format(measure_number))


def _get_all_procedure_codes_in_eligibility_options(measure_numbers):
    """Return a list of all procedure codes mentioned in eligibility options."""
    measure_definitions = []

    for measure_number in measure_numbers:
        measure_definitions.append(load_measure_definition(measure_number))

    procedure_codes = [
        code['code'] for code_list in [
            option.procedure_codes for measure in measure_definitions
            for option in measure.eligibility_options
            if option.procedure_codes
        ]
        for code in code_list
    ]

    # Remove duplicates.
    return list(set(procedure_codes))
