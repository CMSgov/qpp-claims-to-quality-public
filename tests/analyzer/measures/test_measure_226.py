"""Tests for methods within measure_226.py."""
import datetime

from claims_to_quality.analyzer import measure_mapping
from claims_to_quality.analyzer.models import claim
from claims_to_quality.analyzer.models import claim_line
from claims_to_quality.analyzer.models.measures.measure_definition import MeasureDefinition


class TestMeasure226WithActualMeasureDefinition():
    """Test Measure226 using the actual measure definition."""

    def setup(self):
        """Initialization of a Measure226 object and sample claims."""
        self.measure = measure_mapping.get_measure_calculator('226')

        # Initialize claims for use in the tests.
        self.claim_0_1_performance_met = claim.Claim({
            'clm_from_dt': datetime.date(2018, 1, 1),
            'clm_ptnt_birth_dt': datetime.date(2000, 1, 1),
            'claim_lines': [
                claim_line.ClaimLine({
                    'clm_line_hcpcs_cd': '90791',
                    'mdfr_cds': [],
                }),
                claim_line.ClaimLine({
                    'clm_line_hcpcs_cd': 'G9902',
                    'mdfr_cds': [],
                }),
            ]
        })
        self.claim_2_eligible = claim.Claim({
            'clm_from_dt': datetime.date(2018, 1, 1),
            'clm_ptnt_birth_dt': datetime.date(2000, 1, 1),
            'claim_lines': [
                claim_line.ClaimLine({
                    'clm_line_hcpcs_cd': '90791',
                    'mdfr_cds': [],
                }),
                claim_line.ClaimLine({
                    'clm_line_hcpcs_cd': 'G9902',
                    'mdfr_cds': [],
                }),
                claim_line.ClaimLine({
                    'clm_line_hcpcs_cd': 'G9906',
                    'mdfr_cds': [],
                }),
            ]
        })
        self.claim_irrelevant = claim.Claim({
            'clm_from_dt': datetime.date(2018, 1, 1),
            'clm_ptnt_birth_dt': datetime.date(2000, 1, 1),
            'claim_lines': [
                claim_line.ClaimLine({
                    'clm_line_hcpcs_cd': '90791',
                    'mdfr_cds': [],
                }),
                claim_line.ClaimLine({
                    'clm_line_hcpcs_cd': '4004F',
                    'mdfr_cds': ['8P'],
                }),
            ]
        })
        self.claims = [self.claim_0_1_performance_met, self.claim_2_eligible, self.claim_irrelevant]

    def test_init_submeasure_names(self):
        """Test that the initialized measure has correctly named submeasures."""
        submeasure_names = set(self.measure.submeasures.keys())
        expected = {stratum.name for stratum in self.measure.measure_definition.strata}
        assert submeasure_names == expected

    def test_init_submeasure_classes(self):
        """Test that the initialized measure has the correct submeasure definitions."""
        submeasure_definitions = {
            submeasure_name: submeasure.measure_definition
            for submeasure_name, submeasure in self.measure.submeasures.items()
        }
        expected = {
            stratum.name: MeasureDefinition({
                'eligibility_options': [eligibility_option],
                'performance_options': self.measure.PERFORMANCE_OPTION_BY_STRATUM_NAME[stratum.name]
            })
            for stratum, eligibility_option in zip(
                self.measure.measure_definition.strata, self.measure.eligibility_options
            )
        }
        assert submeasure_definitions == expected

    def test_execute(self):
        """Test that execute returns correct results for each stratum."""
        output = self.measure.execute(claims=self.claims)
        expected = [
            {
                'name': 'screenedForUse',
                'results': {
                    'eligible_population_exclusion': 0,
                    'eligible_population_exception': 0,
                    'performance_met': 1,
                    'performance_not_met': 0,
                    'eligible_population': 1
                }
            },
            {
                'name': 'intervention',
                'results': {
                    'eligible_population_exclusion': 0,
                    'eligible_population_exception': 0,
                    'performance_met': 1,
                    'performance_not_met': 0,
                    'eligible_population': 1
                }
            },
            {
                'name': 'overall',
                'results': {
                    'eligible_population_exclusion': 0,
                    'eligible_population_exception': 0,
                    'performance_met': 0,
                    'performance_not_met': 1,
                    'eligible_population': 1
                }
            },
        ]
        assert output == expected
