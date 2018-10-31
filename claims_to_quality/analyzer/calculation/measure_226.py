"""Subclass of QPPMeasure to calculate measure 226."""
from claims_to_quality.analyzer.calculation.patient_process_measure import PatientProcessMeasure
from claims_to_quality.analyzer.models.measures.measure_definition import MeasureDefinition
from claims_to_quality.lib.helpers.decorators import override
from claims_to_quality.lib.qpp_logging import logging_config

import newrelic.agent

logger = logging_config.get_logger(__name__)


class Measure226MultipleStrata(PatientProcessMeasure):
    """
    Represents measure 226: Preventive Care and Screening: Tobacco Use in 2018 and beyond.

    Note that in 2017 and earlier measure 226 is an ordinary patient process measure.

    Since 2018, measure 226 is a patient-process measure with multiple strata,
    each of which corresponds to a distinct eligibility option.

    Accordingly, we break the measure down into submeasures, one for each eligibility option.
    The calculated results for each submeasure are then aggregated together.
    """

    # FIXME: Avoid hard-coding this information. This requires a major update to the
    # the single source parsing script within the qpp-measures-data repo
    # to allow measures to have multiple eligibility options and multiple performance options
    # that DO NOT INTERACT with each other.
    PERFORMANCE_OPTION_BY_STRATUM_NAME = {
        'screenedForUse': [
            {'optionType': 'performanceMet', 'qualityCodes': [{'code': 'G9902'}]},
            {'optionType': 'performanceMet', 'qualityCodes': [{'code': 'G9903'}]},
            {'optionType': 'eligiblePopulationException', 'qualityCodes': [{'code': 'G9904'}]},
            {'optionType': 'performanceNotMet', 'qualityCodes': [{'code': 'G9905'}]},
        ],
        'intervention': [
            {'optionType': 'performanceMet', 'qualityCodes': [{'code': 'G9906'}]},
            {'optionType': 'eligiblePopulationException', 'qualityCodes': [{'code': 'G9907'}]},
            {'optionType': 'performanceNotMet', 'qualityCodes': [{'code': 'G9908'}]},
        ],
        'overall': [
            {
                'optionType': 'performanceMet',
                'qualityCodes': [
                    {
                        'code': '1036F',
                        'modifierExclusions': ['1P', '2P', '3P', '8P']
                    }
                ]
            },
            {
                'optionType': 'eligiblePopulationException',
                'qualityCodes': [
                    {
                        'code': '4004F',
                        'modifierExclusions': ['2P', '3P', '8P'],
                        'modifiers': ['1P']
                    }
                ]
            },
            {
                'optionType': 'performanceMet',
                'qualityCodes': [
                    {
                        'code': '4004F',
                        'modifierExclusions': ['1P', '2P', '3P', '8P']
                    }
                ]
            },
            {
                'optionType': 'performanceNotMet',
                'qualityCodes': [
                    {
                        'code': '4004F',
                        'modifierExclusions': ['1P', '2P', '3P'],
                        'modifiers': ['8P']
                    }
                ],
            },
            {
                'optionType': 'eligiblePopulationException',
                'qualityCodes': [
                    {
                        'code': 'G9909',
                        'modifierExclusions': ['1P', '2P', '3P', '8P']
                    }
                ]
            }
        ]
    }

    def __init__(self, *args, **kwargs):
        """Instantiate a Measure226 calculator."""
        super(Measure226MultipleStrata, self).__init__(*args, **kwargs)
        # Raise an error if the measure definition doesn't indicate the presence of multiple strata.
        assert self.has_multiple_strata
        # Split eligibility options into separate submeasures.
        self.submeasures = {
            stratum.name: PatientProcessMeasure(
                measure_definition=MeasureDefinition({
                    'eligibility_options': [option],
                    'performance_options': self.PERFORMANCE_OPTION_BY_STRATUM_NAME[stratum.name]
                })
            )
            for stratum, option in zip(self.measure_definition.strata, self.eligibility_options)
        }

        # Check that the three strata names appear as expected.
        for name in ['screenedForUse', 'intervention', 'overall']:
            assert name in self.submeasures

        # Check that the 'intervention' stratum has additional procedure codes (but not the others).
        assert self.submeasures['intervention'].eligibility_options[0].additional_procedure_codes
        assert not (
            self.submeasures['overall'].eligibility_options[0].additional_procedure_codes or
            self.submeasures['screenedForUse'].eligibility_options[0].additional_procedure_codes
        )

        #

    @newrelic.agent.function_trace(name='execute-measure-calculation', group='Task')
    @override
    def execute(self, claims):
        """
        Evaluate a provider dataset according to the measure specification.

        Because measure 226 has multiple strata to score on, the implementation of this method
        from QPPMeasure is overridden in Measure226.

        Measure 226 has three strata, each of which has a corresponding eligibility option.
        Accordingly, we create three submeasures, calculating the results for each stratum
        independently.

        Returns the measure results as a list of dictionaries, each with the form:
            - name: stratum_name
            - results: stratum results dictionary with the following keys:
                - performance_met
                - performance_not_met
                - eligible_population_exclusion
                - eligible_population_exception
                - eligible_population
        """
        return [
            {
                'name': name,
                'results': submeasure.execute(claims=claims)
            }
            for name, submeasure in self.submeasures.items()
        ]
