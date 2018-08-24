"""Tests methods within measure_46.py."""
from datetime import date

from claims_to_quality.analyzer import measure_mapping
from claims_to_quality.analyzer.calculation import measure_46
from claims_to_quality.analyzer.models import claim
from claims_to_quality.analyzer.models import claim_line
from claims_to_quality.analyzer.models.measures.eligibility_option import EligibilityOption
from claims_to_quality.analyzer.models.measures.measure_code import MeasureCode
from claims_to_quality.analyzer.models.measures.measure_definition import MeasureDefinition
from claims_to_quality.analyzer.models.measures.performance_option import PerformanceOption

import mock


class TestMeasure46MultipleStrata():
    """Test Measure46 strata handling."""

    def setup(self):
        """Initialisation of measure 46."""
        self.measure = measure_mapping.get_measure_calculator('046')
        self.senior_patient_claim_performance_met = claim.Claim({
            'bene_sk': 'elderly_patient_id',
            'clm_ptnt_birth_dt': date(1920, 1, 1),
            'clm_from_dt': date(2017, 1, 1),
            'claim_lines': [
                claim_line.ClaimLine(
                    {'clm_line_hcpcs_cd': '1111F'},
                    {'mdfr_cds': []}
                ),
                claim_line.ClaimLine(
                    {'clm_line_hcpcs_cd': '99344'},
                )
            ]
        })

        self.senior_patient_claim_not_performance_met = claim.Claim({
            'bene_sk': 'elderly_patient_id',
            'clm_ptnt_birth_dt': date(1920, 1, 1),
            'clm_from_dt': date(2017, 1, 2),
            'claim_lines': [
                claim_line.ClaimLine(
                    {'clm_line_hcpcs_cd': '1111F'},
                    {'mdfr_cds': ['8P']}
                ),
                claim_line.ClaimLine(
                    {'clm_line_hcpcs_cd': '99344'},
                )
            ]
        })

        self.borderline_senior_patient_claim_performance_met = claim.Claim({
            'bene_sk': 'elderly_patient_id',
            'clm_ptnt_birth_dt': date(1953, 1, 30),
            'clm_from_dt': date(2017, 5, 20),
            'claim_lines': [
                claim_line.ClaimLine(
                    {'clm_line_hcpcs_cd': '1111F'},
                    {'mdfr_cds': []}
                ),
                claim_line.ClaimLine(
                    {'clm_line_hcpcs_cd': '99344'},
                )
            ]
        })

        self.middle_aged_patient_claim_performance_not_met = claim.Claim({
            'bene_sk': 'middle_aged_patient_id',
            'clm_ptnt_birth_dt': date(1977, 1, 1),
            'clm_from_dt': date(2017, 1, 1),
            'claim_lines': [
                claim_line.ClaimLine(
                    {'clm_line_hcpcs_cd': '1111F'},
                    {'mdfr_cds': ['8P']}
                ),
                claim_line.ClaimLine(
                    {'clm_line_hcpcs_cd': '99344'},
                )
            ]
        })

        self.too_young_patient_claim_no_strata = claim.Claim({
            'bene_sk': 'young_patient_id',
            'clm_ptnt_birth_dt': date(2010, 1, 1),
            'clm_from_dt': date(2017, 1, 1),
            'claim_lines': [
                claim_line.ClaimLine(
                    {'clm_line_hcpcs_cd': '1111F'},
                    {'mdfr_cds': []}
                ),
                claim_line.ClaimLine(
                    {'clm_line_hcpcs_cd': '99344'},
                )
            ]
        })

        self.claims = [
            self.senior_patient_claim_performance_met,
            self.middle_aged_patient_claim_performance_not_met,
            self.too_young_patient_claim_no_strata
        ]

    def _set_bene_discharge_dates(self, bene_discharge_date_map):
        """Set bene discharge dates as a side effect for use during mocking."""
        for bene_sk in bene_discharge_date_map:
            self.measure.discharge_dates_by_beneficiary[bene_sk] = bene_discharge_date_map[bene_sk]

    def test_assign_eligible_instances_to_strata(self):
        """Test that eligible instances are assigned to the correct strata according to age."""
        instances = [[self.senior_patient_claim_performance_met]]
        output = self.measure.assign_eligible_instances_to_strata(eligible_instances=instances)
        assert output == [
            {
                'name': '18-64',
                'instances': []
            },
            {
                'name': '65+',
                'instances': instances
            },
            {
                'name': 'overall',
                'instances': instances
            },
        ]

        instances = [[self.too_young_patient_claim_no_strata]]
        output = self.measure.assign_eligible_instances_to_strata(eligible_instances=instances)
        assert output == [
            {
                'name': '18-64',
                'instances': []
            },
            {
                'name': '65+',
                'instances': []
            },
            {
                'name': 'overall',
                'instances': []
            },
        ]

    def test_assign_eligible_instances_to_strata_64yo(self):
        """Test that eligible instances are assigned to the correct strata when a patient is 64."""
        instances = [[self.borderline_senior_patient_claim_performance_met]]
        output = self.measure.assign_eligible_instances_to_strata(eligible_instances=instances)
        assert output == [
            {
                'name': '18-64',
                'instances': instances
            },
            {
                'name': '65+',
                'instances': []
            },
            {
                'name': 'overall',
                'instances': instances
            },
        ]

    @mock.patch(
        'claims_to_quality.analyzer.calculation.measure_46.'
        'Measure46.filter_by_eligibility_criteria')
    def test_execute(self, filter_by_eligibility_criteria):
        """Test that the execute method returns the correct results for each stratum."""
        filter_by_eligibility_criteria.return_value = [
            self.senior_patient_claim_not_performance_met,
            self.senior_patient_claim_performance_met,
            self.middle_aged_patient_claim_performance_not_met,
        ]

        self._set_bene_discharge_dates(
            bene_discharge_date_map={
                'elderly_patient_id': {date(2016, 12, 25), date(2016, 12, 31)},
                'middle_aged_patient_id': {date(2016, 12, 25)},
            }
        )

        output = self.measure.execute(self.claims)
        expected = [
            {
                'name': 'overall',
                'results': {
                    'performance_met': 1,
                    'performance_not_met': 2,
                    'eligible_population': 3,
                    'eligible_population_exception': 0,
                    'eligible_population_exclusion': 0
                }
            },
            {
                'name': '18-64',
                'results': {
                    'performance_met': 0,
                    'performance_not_met': 1,
                    'eligible_population': 1,
                    'eligible_population_exception': 0,
                    'eligible_population_exclusion': 0
                }
            },
            {
                'name': '65+',
                'results': {
                    'performance_met': 1,
                    'performance_not_met': 1,
                    'eligible_population': 2,
                    'eligible_population_exception': 0,
                    'eligible_population_exclusion': 0
                }
            }
        ]

        # The two lists may be in different orders, but they should contain the same elements.
        assert all([strata_results in output for strata_results in expected])
        assert all([strata_results in expected for strata_results in output])

    def test_clear_discharge_cache(self):
        """Test that the cached discharge dates can be successfully cleared."""
        # Set the cached discharge dates.
        self._set_bene_discharge_dates(
            bene_discharge_date_map={
                'elderly_patient_id': {date(2016, 12, 25), date(2016, 12, 31)},
                'middle_aged_patient_id': {date(2016, 12, 25)},
            }
        )
        # The cache should now be non-empty.
        assert any(self.measure.discharge_dates_by_beneficiary)
        self.measure.clear_discharge_date_cache()
        # After clearing, the cache should be empty.
        assert not any(self.measure.discharge_dates_by_beneficiary)

    @mock.patch('claims_to_quality.lib.teradata_methods.execute.execute')
    def test_get_discharge_dates_by_provider(self, mock_execute):
        """Empty lists of providers should exit early without querying the IDR."""
        self.measure._get_discharge_dates_by_provider(tins=[], npis=['a'], bene_sks=['b'])
        self.measure._get_discharge_dates_by_provider(tins=['a'], npis=[], bene_sks=['b'])
        self.measure._get_discharge_dates_by_provider(tins=['a'], npis=['b'], bene_sks=[])

        mock_execute.assert_not_called()


class TestMeasure46EligibilityFiltering():
    """Test Measure46 eligibility filtering."""

    def setup(self):
        """Initialisation of measure 46."""
        performance_options = [
            PerformanceOption({
                'optionType': 'performanceMet',
                'qualityCodes': [
                    {'code': 'pn_code'}
                ]
            }),
            PerformanceOption({
                'optionType': 'performanceNotMet',
                'qualityCodes': [
                    {'code': 'pn_x_code'}
                ]
            }),
            PerformanceOption({
                'optionType': 'performanceExclusion',
                'qualityCodes': [
                    {'code': 'pd_x_code'}
                ]
            })
        ]

        eligibility_options = [
            EligibilityOption({
                'procedureCodes': [MeasureCode({'code': 'enc_code'})]
            })
        ]

        self.measure = measure_46.Measure46(
            measure_definition=MeasureDefinition({
                'eligibility_options': eligibility_options,
                'performance_options': performance_options
            })
        )

        self.bene_1_claim_1 = claim.Claim({
            'bene_sk': 'bene_1',
            'clm_ptnt_birth_dt': date(1940, 1, 1),
            'clm_from_dt': date(2017, 1, 1),
            'claim_lines': [
                {'clm_line_hcpcs_cd': 'pn_code'},
                {'clm_line_hcpcs_cd': 'enc_code'}
            ]})

        self.bene_1_claim_2 = claim.Claim({
            'bene_sk': 'bene_1',
            'clm_ptnt_birth_dt': date(1940, 1, 1),
            'clm_from_dt': date(2017, 1, 1),
            'claim_lines': [
                {'clm_line_hcpcs_cd': 'pn_x_code'},
                {'clm_line_hcpcs_cd': 'enc_code'}
            ]})

        self.bene_2_claim_2 = claim.Claim({
            'bene_sk': 'bene_2',
            'clm_ptnt_birth_dt': date(1940, 1, 1),
            'clm_from_dt': date(2017, 1, 1),
            'claim_lines': [
                {'clm_line_hcpcs_cd': 'pd_x_code'},
                {'clm_line_hcpcs_cd': 'enc_code'}
            ]})

        self.bene_3_claim_1 = claim.Claim({
            'bene_sk': 'bene_3',
            'clm_ptnt_birth_dt': date(1940, 1, 1),
            'clm_from_dt': date(2017, 1, 1),
            'claim_lines': [
                {'clm_line_hcpcs_cd': 'no'},
                {'clm_line_hcpcs_cd': 'no'}
            ]})

        self.claims = [
            self.bene_1_claim_1, self.bene_1_claim_2,
            self.bene_2_claim_2, self.bene_3_claim_1
        ]

    def _side_effect_of_get_discharge_dates(self, bene_sk, discharge_dates):
        """Set bene discharge dates as a side effect for use during mocking."""
        self.measure.discharge_dates_by_beneficiary[bene_sk] = discharge_dates

    def test_discharge_period(self):
        """Test that discharge period is set properly."""
        assert self.measure._discharge_period == 30

    @mock.patch(
        'claims_to_quality.analyzer.calculation.measure_46.'
        'Measure46._get_discharge_dates_by_provider')
    def test_filter_by_eligibility_criteria(self, _get_discharge_dates_by_provider):
        """Test that filter_by_eligibility_criteria returns the expected number of claims."""
        _get_discharge_dates_by_provider.side_effect = self._side_effect_of_get_discharge_dates(
            bene_sk='bene_1',
            discharge_dates={date(2016, 12, 25)}
        )
        filtered_claims = self.measure.filter_by_eligibility_criteria(self.claims)

        assert filtered_claims == [self.bene_1_claim_1, self.bene_1_claim_2]

    @mock.patch('claims_to_quality.lib.teradata_methods.execute.execute')
    def test_get_discharge_dates_by_provider(self, execute):
        """Test discharge date fetching."""
        execute.return_value = [{'bene_sk': 'bene_1', 'clm_line_from_dt': date(2017, 1, 1)}]

        self.measure._get_discharge_dates_by_provider(
            tins=['123'], npis=['456'], bene_sks=['bene_1']
        )

        assert self.measure.discharge_dates_by_beneficiary['bene_1'] == {date(2017, 1, 1)}
        assert self.measure.discharge_dates_by_beneficiary['bene_2'] == set()

    @mock.patch('claims_to_quality.lib.teradata_methods.execute.execute')
    def test_get_discharge_dates_by_beneficiary_date(self, execute):
        """Test discharge filter when date is not eligible."""
        execute.return_value = [{'bene_sk': 'bene_1', 'clm_line_from_dt': date(2017, 1, 1)}]

        self.measure._get_discharge_dates_by_provider(
            tins=['123'], npis=['456'], bene_sks=['bene_1']
        )

        assert self.measure.discharge_dates_by_beneficiary['bene_1'] == {date(2017, 1, 1)}
        assert self.measure.discharge_dates_by_beneficiary['bene_2'] == set()

    @mock.patch('claims_to_quality.lib.teradata_methods.execute.execute')
    def test_filter_by_eligibility_criteria_from_execute(self, execute):
        """Test discharge filter."""
        execute.return_value = [{'bene_sk': 'bene_1', 'clm_line_from_dt': date(2017, 1, 1)}]
        filtered_claims = self.measure.filter_by_eligibility_criteria(self.claims)

        assert filtered_claims == [self.bene_1_claim_1, self.bene_1_claim_2]

    @mock.patch('claims_to_quality.lib.teradata_methods.execute.execute')
    def test_filter_by_eligibility_criteria_from_execute_empty(self, execute):
        """Test empty results."""
        execute.return_value = []
        filtered_claims = self.measure.filter_by_eligibility_criteria(self.claims)
        assert filtered_claims == []

    @mock.patch('claims_to_quality.lib.teradata_methods.execute.execute')
    def test_no_g_codes(self, execute):
        """Test empty results."""
        claims = [self.bene_3_claim_1]
        execute.return_value = [{'bene_sk': 'bene_3', 'clm_line_from_dt': date(2017, 1, 1)}]
        filtered_claims = self.measure.filter_by_eligibility_criteria(claims)
        assert filtered_claims == []
