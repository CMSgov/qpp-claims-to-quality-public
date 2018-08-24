"""Test helpers for mocking configuration file."""
import datetime

from claims_to_quality.config import config


def config_side_effect(value_mapping):
    """Return mock config values using input value_mapping."""
    def side_effect(value):
        if value in value_mapping:
            return value_mapping[value]
        else:
            return config.get(value)

    return side_effect


def config_measures_year(measures_year):
    """Return mock config values for measures_year related fields."""
    return config_side_effect({
        'calculation.measures_year': measures_year,
        'calculation.start_date': datetime.date(year=measures_year, month=1, day=1),
        'calculation.end_date': datetime.date(year=measures_year, month=12, day=31)
    })
