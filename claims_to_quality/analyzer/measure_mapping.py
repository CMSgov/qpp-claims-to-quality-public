"""Methods to load measure calculation objects for implemented measure types."""
from claims_to_quality.analyzer.calculation.ct_scan_measure import CTScanMeasure
from claims_to_quality.analyzer.calculation.date_window_eoc_measure import DateWindowEOCMeasure
from claims_to_quality.analyzer.calculation.intersecting_diagnosis_measure import (
    IntersectingDiagnosisMeasure)
from claims_to_quality.analyzer.calculation.measure_226 import Measure226MultipleStrata
from claims_to_quality.analyzer.calculation.measure_407 import Measure407
from claims_to_quality.analyzer.calculation.measure_46 import Measure46
from claims_to_quality.analyzer.calculation.multiple_encounter_measure import (
    MultipleEncounterMeasure)
from claims_to_quality.analyzer.calculation.patient_intermediate_measure import (
    PatientIntermediateMeasure)
from claims_to_quality.analyzer.calculation.patient_periodic_measure import PatientPeriodicMeasure
from claims_to_quality.analyzer.calculation.patient_process_measure import PatientProcessMeasure
from claims_to_quality.analyzer.calculation.procedure_measure import ProcedureMeasure
from claims_to_quality.analyzer.calculation.visit_measure import VisitMeasure
from claims_to_quality.analyzer.datasource import measure_reader
from claims_to_quality.config import config

MEASURE_NUMBER_TO_CLASS = {
    2017: {
        '001': {'measure_type': PatientIntermediateMeasure},
        '012': {'measure_type': PatientProcessMeasure},
        '014': {'measure_type': PatientProcessMeasure},
        '019': {'measure_type': PatientProcessMeasure},
        '021': {'measure_type': ProcedureMeasure},
        '023': {'measure_type': ProcedureMeasure},
        '024': {'measure_type': IntersectingDiagnosisMeasure},
        '032': {'measure_type': VisitMeasure},
        '039': {'measure_type': PatientProcessMeasure},
        '046': {'measure_type': Measure46},
        '047': {'measure_type': PatientProcessMeasure},
        '048': {'measure_type': PatientProcessMeasure},
        '050': {'measure_type': PatientProcessMeasure},
        '051': {'measure_type': PatientIntermediateMeasure},
        '052': {'measure_type': PatientProcessMeasure},
        '076': {'measure_type': ProcedureMeasure},
        '091': {'measure_type': DateWindowEOCMeasure},
        '093': {'measure_type': DateWindowEOCMeasure},
        '099': {'measure_type': ProcedureMeasure},
        '100': {'measure_type': ProcedureMeasure},
        '109': {'measure_type': VisitMeasure},
        '110': {'measure_type': PatientPeriodicMeasure},
        '111': {'measure_type': PatientProcessMeasure},
        '112': {'measure_type': PatientProcessMeasure},
        '113': {'measure_type': PatientProcessMeasure},
        '117': {'measure_type': PatientProcessMeasure},
        '128': {'measure_type': PatientIntermediateMeasure},
        '130': {'measure_type': VisitMeasure},
        '131': {'measure_type': VisitMeasure},
        '134': {'measure_type': PatientProcessMeasure},
        '140': {'measure_type': PatientProcessMeasure},
        '141': {'measure_type': PatientProcessMeasure},
        '145': {'measure_type': ProcedureMeasure},
        '146': {'measure_type': ProcedureMeasure},
        '147': {'measure_type': ProcedureMeasure},
        '154': {'measure_type': PatientProcessMeasure},
        '155': {'measure_type': PatientProcessMeasure},
        '156': {'measure_type': PatientProcessMeasure},
        '181': {'measure_type': PatientProcessMeasure},
        '182': {'measure_type': VisitMeasure},
        '185': {'measure_type': ProcedureMeasure},
        '195': {'measure_type': ProcedureMeasure},
        '204': {'measure_type': PatientProcessMeasure},
        '225': {'measure_type': ProcedureMeasure},
        '226': {'measure_type': PatientProcessMeasure},
        '236': {'measure_type': PatientIntermediateMeasure},
        '249': {'measure_type': ProcedureMeasure},
        '250': {'measure_type': ProcedureMeasure},
        '251': {'measure_type': ProcedureMeasure},
        '254': {'measure_type': ProcedureMeasure},
        '255': {'measure_type': ProcedureMeasure},
        '261': {'measure_type': PatientProcessMeasure},
        '268': {'measure_type': PatientProcessMeasure},
        '317': {'measure_type': PatientProcessMeasure},
        '320': {'measure_type': PatientProcessMeasure},
        '326': {'measure_type': PatientProcessMeasure},
        '395': {'measure_type': ProcedureMeasure},
        '396': {'measure_type': ProcedureMeasure},
        '397': {'measure_type': ProcedureMeasure},
        '405': {'measure_type': ProcedureMeasure},
        '406': {'measure_type': ProcedureMeasure},
        '407': {'measure_type': Measure407},
        '410': {'measure_type': PatientProcessMeasure},
        '415': {'measure_type': CTScanMeasure},
        '416': {'measure_type': CTScanMeasure},
        '418': {'measure_type': IntersectingDiagnosisMeasure},
        '419': {'measure_type': VisitMeasure},
        '422': {'measure_type': ProcedureMeasure},
        '423': {'measure_type': ProcedureMeasure},
        '425': {'measure_type': ProcedureMeasure},
        '429': {'measure_type': ProcedureMeasure},
        '435': {'measure_type': MultipleEncounterMeasure},
        '436': {'measure_type': ProcedureMeasure},
        '437': {'measure_type': ProcedureMeasure}
    },
    2018: {
        '001': {'measure_type': PatientIntermediateMeasure},
        '012': {'measure_type': PatientProcessMeasure},
        '014': {'measure_type': PatientPeriodicMeasure},    # NOTE: This is only valid for 2018
        '019': {'measure_type': PatientProcessMeasure},
        '021': {'measure_type': ProcedureMeasure},
        '023': {'measure_type': ProcedureMeasure},
        '024': {'measure_type': IntersectingDiagnosisMeasure},
        '039': {'measure_type': PatientProcessMeasure},
        '046': {'measure_type': Measure46},
        '047': {'measure_type': PatientProcessMeasure},
        '048': {'measure_type': PatientProcessMeasure},
        '050': {'measure_type': PatientProcessMeasure},
        '051': {'measure_type': PatientIntermediateMeasure},
        '052': {'measure_type': PatientProcessMeasure},
        '076': {'measure_type': ProcedureMeasure},
        '091': {'measure_type': DateWindowEOCMeasure},
        '093': {'measure_type': DateWindowEOCMeasure},
        '099': {'measure_type': ProcedureMeasure},
        '100': {'measure_type': ProcedureMeasure},
        '109': {'measure_type': VisitMeasure},
        '110': {'measure_type': PatientPeriodicMeasure},
        '111': {'measure_type': PatientProcessMeasure},
        '112': {'measure_type': PatientProcessMeasure},
        '113': {'measure_type': PatientProcessMeasure},
        '117': {'measure_type': PatientProcessMeasure},
        '128': {'measure_type': PatientIntermediateMeasure},
        '130': {'measure_type': VisitMeasure},
        '131': {'measure_type': VisitMeasure},
        '134': {'measure_type': PatientProcessMeasure},
        '140': {'measure_type': PatientProcessMeasure},
        '141': {'measure_type': PatientProcessMeasure},
        '145': {'measure_type': ProcedureMeasure},
        '146': {'measure_type': ProcedureMeasure},
        '147': {'measure_type': ProcedureMeasure},
        '154': {'measure_type': PatientProcessMeasure},
        '155': {'measure_type': PatientProcessMeasure},
        '156': {'measure_type': PatientProcessMeasure},
        '181': {'measure_type': PatientProcessMeasure},
        '182': {'measure_type': VisitMeasure},
        '185': {'measure_type': ProcedureMeasure},
        '195': {'measure_type': ProcedureMeasure},
        '204': {'measure_type': PatientProcessMeasure},
        '225': {'measure_type': ProcedureMeasure},
        '226': {'measure_type': Measure226MultipleStrata},
        '236': {'measure_type': PatientIntermediateMeasure},
        '249': {'measure_type': ProcedureMeasure},
        '250': {'measure_type': ProcedureMeasure},
        '251': {'measure_type': ProcedureMeasure},
        '254': {'measure_type': ProcedureMeasure},
        '255': {'measure_type': ProcedureMeasure},
        '261': {'measure_type': PatientProcessMeasure},
        '268': {'measure_type': PatientProcessMeasure},
        '317': {'measure_type': PatientProcessMeasure},
        '320': {'measure_type': PatientProcessMeasure},
        '326': {'measure_type': PatientProcessMeasure},
        '395': {'measure_type': ProcedureMeasure},
        '396': {'measure_type': ProcedureMeasure},
        '397': {'measure_type': ProcedureMeasure},
        '405': {'measure_type': ProcedureMeasure},
        '406': {'measure_type': ProcedureMeasure},
        '407': {'measure_type': Measure407},
        '415': {'measure_type': CTScanMeasure},
        '416': {'measure_type': CTScanMeasure},
        '418': {'measure_type': IntersectingDiagnosisMeasure},
        '419': {'measure_type': VisitMeasure},
        '422': {'measure_type': ProcedureMeasure},
        '423': {'measure_type': ProcedureMeasure},
        '425': {'measure_type': ProcedureMeasure},
        '429': {'measure_type': ProcedureMeasure},
        '435': {'measure_type': MultipleEncounterMeasure},
        '436': {'measure_type': ProcedureMeasure},
        '437': {'measure_type': ProcedureMeasure}
    }
}


def get_measure_calculator(
    measure_number,
    year=config.get('calculation.measures_year'),
    single_source_json=measure_reader.load_single_source(),
):
    """Generate a measure calculator object with correct definition and type."""
    try:
        measure_definition = measure_reader.load_measure_definition(
            measure_number=measure_number,
            single_source_json=single_source_json
        )
        calculator_class = _get_measure_class(measure_number=measure_number, year=year)
        kwargs = _get_measure_args(measure_number=measure_number, year=year)
        return calculator_class(measure_definition=measure_definition, **kwargs)
    except KeyError:
        raise KeyError(
            'Measure number {measure_number} is not yet supported for {year}.'.format(
                measure_number=measure_number,
                year=config.get('calculation.measures_year')
            )
        )


def get_measure_calculators(measures, year=config.get('calculation.measures_year')):
    """Generate a dictionary of measure calculator object with correct definition and type."""
    json_path = config.get('assets.qpp_single_source_json')[year]
    single_source_json = measure_reader.load_single_source(json_path)
    return {
        measure: get_measure_calculator(
            measure_number=measure,
            year=year,
            single_source_json=single_source_json,
        )
        for measure in measures
    }


def _get_measure_class(measure_number, year=config.get('calculation.measures_year')):
    """Retrieve the measure class for the specified measure for the year defined in the config."""
    return MEASURE_NUMBER_TO_CLASS[year][measure_number]['measure_type']


def _get_measure_args(measure_number, year=config.get('calculation.measures_year')):
    """Retrieve the measure args for the specified measure for the year defined in the config."""
    return MEASURE_NUMBER_TO_CLASS[year][measure_number].get('kwargs', {})


def get_all_measure_ids(year=config.get('calculation.measures_year')):
    """Retrieve all measure IDs for the year specified."""
    return MEASURE_NUMBER_TO_CLASS[year].keys()


def get_measures(year=config.get('calculation.measures_year')):
    """Retrieve all measures for the year specified."""
    return MEASURE_NUMBER_TO_CLASS[year]
