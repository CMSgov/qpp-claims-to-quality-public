"""Test Measure407 (MSSA)."""
from datetime import date

from claims_to_quality.analyzer.calculation import measure_407
from claims_to_quality.analyzer.models import claim
from claims_to_quality.analyzer.models.measures.eligibility_option import EligibilityOption
from claims_to_quality.analyzer.models.measures.measure_code import MeasureCode
from claims_to_quality.analyzer.models.measures.measure_definition import MeasureDefinition
from claims_to_quality.analyzer.models.measures.performance_option import PerformanceOption
from claims_to_quality.lib.helpers.date_handling import DateRange

import mock

import pytest


class TestVisitMeasure407():
    """Test Measure407 class."""

    def setup(self):
        """Initialisation of measure 407."""
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
                'optionType': 'eligiblePopulationExclusion',
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

        self.measure = measure_407.Measure407(
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

    def test_procedure_codes(self):
        """Test that procedure codes are populated."""
        assert self.measure.procedure_codes == {'enc_code'}

    @mock.patch('claims_to_quality.lib.teradata_methods.execute.execute')
    def test_get_mssa_date_ranges_one_provider(self, execute):
        """Test _get_mssa_date_ranges."""
        execute.return_value = [
            {'bene_sk': 'bene_1', 'min_date': date(2017, 1, 1), 'max_date': date(2017, 1, 1)}
        ]
        mssa_date_ranges = self.measure._get_mssa_date_ranges(self.claims)
        expected = {'bene_1': [DateRange(date(2017, 1, 1), date(2017, 1, 1))]}
        assert mssa_date_ranges == expected

    @mock.patch('claims_to_quality.lib.teradata_methods.execute.execute')
    def test_get_mssa_date_ranges_multiple_providers(self, execute):
        """Test _get_mssa_date_ranges."""
        execute.return_value = [
            {'bene_sk': 'bene_1', 'min_date': date(2017, 1, 1), 'max_date': date(2017, 1, 1)},
            {'bene_sk': 'bene_1', 'min_date': date(2017, 1, 1), 'max_date': date(2017, 1, 1)},
            {'bene_sk': 'bene_2', 'min_date': date(2017, 1, 1), 'max_date': date(2017, 1, 1)}
        ]
        mssa_date_ranges = self.measure._get_mssa_date_ranges(self.claims)
        expected = {
            'bene_1': [
                DateRange(date(2017, 1, 1), date(2017, 1, 1)),
                DateRange(date(2017, 1, 1), date(2017, 1, 1))
            ],
            'bene_2': [DateRange(date(2017, 1, 1), date(2017, 1, 1))]
        }
        assert mssa_date_ranges == expected

    def test_merge_mssa_date_ranges(self):
        """Test dict merging of mssa_date_ranges."""
        mssa_date_ranges = {
            'bene_1': [
                DateRange(date(2017, 1, 1), date(2017, 1, 1)),
                DateRange(date(2017, 1, 1), date(2017, 1, 1))
            ],
            'bene_2': [
                DateRange(date(2017, 1, 1), date(2017, 1, 1)),
                DateRange(date(2017, 3, 1), date(2017, 3, 3))
            ]
        }

        reduced_mssa_date_ranges = self.measure._merge_mssa_date_ranges(mssa_date_ranges)

        expected = {
            'bene_1': [
                DateRange(date(2017, 1, 1), date(2017, 1, 1))
            ],
            'bene_2': [
                DateRange(date(2017, 1, 1), date(2017, 1, 1)),
                DateRange(date(2017, 3, 1), date(2017, 3, 3))
            ]
        }

        assert reduced_mssa_date_ranges == expected

    @mock.patch('claims_to_quality.lib.teradata_methods.execute.execute')
    def test_get_mssa_episode_date_ranges(self, execute):
        """Test _get_mssa_episode_date_ranges."""
        execute.return_value = [
            {'bene_sk': 'bene_1', 'min_date': date(2017, 1, 1), 'max_date': date(2017, 1, 1)},
            {'bene_sk': 'bene_1', 'min_date': date(2017, 1, 1), 'max_date': date(2017, 1, 5)},
            {'bene_sk': 'bene_2', 'min_date': date(2017, 1, 1), 'max_date': date(2017, 1, 3)}
        ]

        expected = {
            'bene_1': [
                DateRange(date(2017, 1, 1), date(2017, 1, 5))
            ],
            'bene_2': [
                DateRange(date(2017, 1, 1), date(2017, 1, 3))
            ]
        }

        assert self.measure._get_mssa_episode_date_ranges(self.claims) == expected

    def test_find_episode_id(self):
        """Test _find_episode_id."""
        date_ranges = [DateRange(date(2017, 1, 1), date(2017, 1, 1))]
        assert self.measure._find_episode_id(self.bene_1_claim_1, date_ranges) == 0

        date_ranges = [
            DateRange(date(2016, 1, 1), date(2016, 1, 1)),
            DateRange(date(2017, 1, 1), date(2017, 1, 1))
        ]
        assert self.measure._find_episode_id(self.bene_1_claim_1, date_ranges) == 1

    @mock.patch('claims_to_quality.lib.teradata_methods.execute.execute')
    def test_get_eligible_instances(self, execute):
        """Test get_eligible_instances."""
        execute.return_value = [
            {'bene_sk': 'bene_1', 'min_date': date(2017, 1, 1), 'max_date': date(2017, 1, 1)},
            {'bene_sk': 'bene_1', 'min_date': date(2017, 1, 1), 'max_date': date(2017, 1, 1)},
            {'bene_sk': 'bene_2', 'min_date': date(2017, 1, 1), 'max_date': date(2017, 1, 1)},
            {'bene_sk': 'bene_3', 'min_date': date(2017, 1, 1), 'max_date': date(2017, 1, 1)}
        ]

        claims = [
            self.bene_1_claim_1, self.bene_1_claim_2, self.bene_2_claim_2, self.bene_3_claim_1
        ]
        episodes = self.measure.get_eligible_instances(claims)
        expected = [
            [self.bene_1_claim_1, self.bene_1_claim_2], [self.bene_2_claim_2], [self.bene_3_claim_1]
        ]
        assert episodes == expected

    @mock.patch('claims_to_quality.lib.teradata_methods.execute.execute')
    def test_get_eligible_instances_missing_bene(self, execute):
        """Test get_eligible_instances when a bene does not have any MSSA data returned."""
        execute.return_value = [
            {'bene_sk': 'bene_1', 'min_date': date(2017, 1, 1), 'max_date': date(2017, 1, 1)},
            {'bene_sk': 'bene_1', 'min_date': date(2017, 1, 1), 'max_date': date(2017, 1, 1)},
            {'bene_sk': 'bene_2', 'min_date': date(2017, 1, 1), 'max_date': date(2017, 1, 1)},
        ]

        claims = [
            self.bene_1_claim_1, self.bene_1_claim_2, self.bene_2_claim_2, self.bene_3_claim_1
        ]
        with pytest.raises(measure_407.MSSADateRangeException):
            self.measure.get_eligible_instances(claims)

    def test_find_episode_id_claim_lines(self):
        """Test _find_episode_id if the start date doesn't overlap with date range."""
        date_ranges = [DateRange(date(2017, 5, 2), date(2017, 5, 6))]

        test_claim = claim.Claim({
            'bene_sk': 'bene',
            'clm_ptnt_birth_dt': date(1954, 1, 1),
            'clm_bene_sex_cd': '1',
            'clm_from_dt': date(2017, 5, 1),
            'clm_thru_dt': date(2017, 5, 6),
            'dx_codes': [
                'A4101',
            ],
            'claim_lines': [
                {
                    'clm_line_num': 3,
                    'clm_line_hcpcs_cd': '93325',
                    'mdfr_cds': [
                        '26'
                    ],
                    'clm_pos_code': '21',
                    'clm_line_from_dt': date(2017, 5, 1),
                    'clm_line_thru_dt': date(2017, 5, 1)
                },
                {
                    'clm_line_num': 2,
                    'clm_line_hcpcs_cd': '93320',
                    'mdfr_cds': [
                        '26'
                    ],
                    'clm_pos_code': '21',
                    'clm_line_from_dt': date(2017, 5, 1),
                    'clm_line_thru_dt': date(2017, 5, 1)
                },
                {
                    'clm_line_num': 4,
                    'clm_line_hcpcs_cd': '99232',
                    'mdfr_cds': [],
                    'clm_pos_code': '21',
                    'clm_line_from_dt': date(2017, 5, 6),
                    'clm_line_thru_dt': date(2017, 5, 6)
                },
                {
                    'clm_line_num': 1,
                    'clm_line_hcpcs_cd': '93312',
                    'mdfr_cds': [
                        '26'
                    ],
                    'clm_pos_code': '21',
                    'clm_line_from_dt': date(2017, 5, 1),
                    'clm_line_thru_dt': date(2017, 5, 1)
                }
            ]})
        assert self.measure._find_episode_id(test_claim, date_ranges) == 0
