"""Methods for submitting to the qpp-measurement-sets API."""
import datetime
import json
import re

from claims_to_quality.config import config
from claims_to_quality.lib.pii_handling import pii_handling
from claims_to_quality.lib.qpp_logging import logging_config

logger = logging_config.get_logger(__name__)

TIN_REGEX = re.compile(r'^[0-9]{9}$')
NPI_REGEX = re.compile(r'^[0-9]{10}$')
FAKE_TIN_REGEX = re.compile(r'^0{3}[0-9]{6}$')
FAKE_NPI_REGEX = re.compile(r'^0[0-9]{9}$')


class TinFormatException(Exception):
    """Indicates that TIN is malformatted."""


class NpiFormatException(Exception):
    """Indicates that NPI is malformatted."""


class MeasurementSet(object):
    """
    Represents one JSON object for submission to the QPP Measurement Sets API.

    One JSON object will be constructed and sent for each TIN/NPI containing measurements for
    all of the claims-based quality measures.
    """

    def __init__(
            self,
            tin,
            npi,
            performance_start,
            performance_end):
        """Create a MeasurementSet object."""
        if config.get('submission.obscure_providers'):
            self.tin, self.npi = self._obscure_provider_identifers(tin, npi)
        else:
            self.tin = self._validate_tin(tin)
            self.npi = self._validate_npi(npi)

        self.performance_start = performance_start
        self.performance_end = performance_end

        # TODO: Read this template from a json file.
        self.data = {
            'submission': {
                'programName': 'mips',
                'entityType': 'individual',
                'taxpayerIdentificationNumber': self.tin,
                'nationalProviderIdentifier': self.npi,
                'performanceYear': performance_end.year,
            },
            'category': 'quality',
            'submissionMethod': 'claims',
            'performanceStart': performance_start,
            'performanceEnd': performance_end,
            'measurements': [],
        }

    def _obscure_provider_identifers(self, tin, npi):
        """Generate fake TIN/NPIs if they are not already fake."""
        if not FAKE_TIN_REGEX.match(tin):
            tin = pii_handling.generate_fake_tin()
        if not FAKE_NPI_REGEX.match(npi):
            npi = pii_handling.generate_fake_npi()

        return tin, npi

    def _validate_tin(self, tin):
        """Verify that TIN is a 9-digit numerical string."""
        if TIN_REGEX.match(tin):
            return tin
        elif TIN_REGEX.match(tin.strip()):
            return tin.strip()
        else:
            raise TinFormatException('Incorrectly formatted TIN')

    def _validate_npi(self, npi):
        """Verify that NPI is a 10-digit numerical string."""
        if NPI_REGEX.match(npi):
            return npi
        elif NPI_REGEX.match(npi.strip()):
            return npi.strip()
        else:
            raise NpiFormatException('Incorrectly formatted NPI')

    def is_empty(self):
        """Check if MeasurementSet contains any measures."""
        return len(self.data['measurements']) == 0

    @staticmethod
    def date_handler(x):
        """Serialize dates into YYYY-mm-dd."""
        if isinstance(x, datetime.date):
            return x.strftime('%Y-%m-%d')
        else:
            raise TypeError('Unknown type')

    def update_performance_period(self, performance_start, performance_end):
        """Update performance period."""
        self.performance_start = performance_start
        self.performance_end = performance_end
        self.data['performanceStart'] = performance_start
        self.data['performanceEnd'] = performance_end

    @staticmethod
    def has_non_zero_reporting(measure_number, measure_results):
        """
        Look for empty performance met/not met and performance exclusion/exception.

        This is to avoid submitting measures with no reporting.
        """
        reporting_keys = [
            'eligible_population_exclusion',
            'eligible_population_exception',
            'performance_met',
            'performance_not_met'
        ]

        if sum([measure_results[category] for category in reporting_keys]) == 0:
            logger.debug(
                'Reporting rate of 0 for measure {}. Not adding to measurement set.'.format(
                    measure_number
                )
            )
            return False

        return True

    def add_measure(self, measure_number, measure_results):
        """
        Add a measure score to the measurement set object.

        measure_results should be a mapping with the keys:
            - performance_met
            - performance_not_met
            - eligible_population_exclusion
            - eligible_population_exception
            - eligible_population
        returns: True if a measure was added to the measurement set.
        """
        if not measure_results['eligible_population']:
            return False

        if (config.get('submission.filter_out_zero_reporting') and
                not self.has_non_zero_reporting(measure_number, measure_results)):
            return False

        self.data['measurements'].append({
            'measureId': '{:03.0f}'.format(float(measure_number)),
            'value': {
                'isEndToEndReported': False,
                'performanceMet': measure_results['performance_met'],
                'eligiblePopulationExclusion': measure_results['eligible_population_exclusion'],
                'eligiblePopulationException': measure_results['eligible_population_exception'],
                'performanceNotMet': measure_results['performance_not_met'],
                'eligiblePopulation': measure_results['eligible_population']
            }
        })

        return True

    def add_measure_with_multiple_strata(self, measure_number, measure_results):
        """
        Add a measure score to the measurement set object for a measure with multiple strata.

        measure_results should be a list of dictionaries, each with the keys
            - name: stratum_name
            - results: measure results dictionary with the following keys:
                - performance_met
                - performance_not_met
                - eligible_population_exclusion
                - eligible_population_exception
                - eligible_population
            - returns True if a measure was added to the measurement set.
        """
        # If none of the strata contain eligible population, do not add the measure.
        if not any([
            stratum_dict['results']['eligible_population']
            for stratum_dict in measure_results
        ]):
            return False

        # If none of the strata contains relevant data, do not add the measure.
        if config.get('submission.filter_out_zero_reporting') and not any([
            self.has_non_zero_reporting(
                measure_number,
                stratum_dict['results']
            )
            for stratum_dict in measure_results
        ]):
            return False

        measurement = {
            'measureId': '{:03.0f}'.format(float(measure_number)),
            'value': {
                'isEndToEndReported': False,
                'strata': [],
            }
        }
        for stratum_dict in measure_results:
            measurement['value']['strata'].append({
                'stratum': stratum_dict['name'],
                'performanceMet':
                    stratum_dict['results']['performance_met'],
                'eligiblePopulationExclusion':
                    stratum_dict['results']['eligible_population_exclusion'],
                'eligiblePopulationException':
                    stratum_dict['results']['eligible_population_exception'],
                'performanceNotMet':
                    stratum_dict['results']['performance_not_met'],
                'eligiblePopulation':
                    stratum_dict['results']['eligible_population']
            })

        self.data['measurements'].append(measurement)

        return True

    def to_json(self, indent=None):
        """Return a JSON string representation of the measurement set object."""
        return json.dumps(self.data, indent=indent, default=self.date_handler)

    def prepare_for_scoring(self, indent=None):
        """Prepare MeasurementSets for scoring preview."""
        data = {
            'programName': 'mips',
            'entityType': 'individual',
            'taxpayerIdentificationNumber': self.tin,
            'nationalProviderIdentifier': self.npi,
            'performanceYear': self.performance_end.year,
            'measurementSets': [{
                k: self.data[k]
                for k in self.data
                if not k == 'submission'
            }]
        }
        return json.dumps(data, indent=indent, default=self.date_handler)
