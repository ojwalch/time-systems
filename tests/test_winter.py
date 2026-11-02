"""Checks of the sun calculator and the winter groups against known values."""
import os

import pytest

from permanent_time import solar
from permanent_time.winters import ends

BOSTON = {"latitude": 42.36, "longitude": -71.06}
PHOENIX = {"latitude": 33.45, "longitude": -112.07}
ISTANBUL = {"latitude": 41.01, "longitude": 28.98}
MOSCOW = {"latitude": 55.75, "longitude": 37.62}
SINGAPORE = {"latitude": 1.29, "longitude": 103.85}

needs_tz = pytest.mark.skipif(not os.path.exists(solar.ZONEINFO), reason="run scripts/setup_data.sh first")


def near(minutes, hh, mm, tol=3):
    return abs(minutes - (hh * 60 + mm)) <= tol


def test_boston_standard_time():
    # published: latest sunrise ~7:13 am (early Jan), earliest sunset ~4:12 pm (early Dec)
    rise, sset = ends(-5, BOSTON)
    assert near(rise, 7, 13) and near(sset, 16, 12)


def test_boston_permanent_dst_is_one_hour_later():
    r5, s5 = ends(-5, BOSTON)
    r4, s4 = ends(-4, BOSTON)
    assert abs((r4 - r5) - 60) < 0.01 and abs((s4 - s5) - 60) < 0.01


def test_phoenix_latest_summer_sunset():
    assert near(solar.latest_clock_sunset(-7, 33.45, -112.07), 19, 42)


def test_polar_night_counts_as_dark():
    assert solar.latest_sunrise_lmt(70.0) == float("inf")
