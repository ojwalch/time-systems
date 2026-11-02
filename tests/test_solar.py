import math

from permanent_time.solar import minutes_ahead


def test_on_meridian_is_zero():
    assert minutes_ahead(1, 15.0) == 0


def test_istanbul_permanent_utc3():
    # Istanbul 28.98 E on UTC+3: about 64 minutes ahead of the sun
    assert math.isclose(minutes_ahead(3, 28.98), 64.08, abs_tol=0.01)


def test_new_york_1974_edt():
    # New York 74.0 W on UTC-4: 56 minutes ahead
    assert math.isclose(minutes_ahead(-4, -74.0), 56.0, abs_tol=0.01)


def test_date_line_wraps():
    # Tonga 175.2 W on UTC+13 is ~41 minutes ahead, not a day
    assert math.isclose(minutes_ahead(13, -175.2), 40.8, abs_tol=0.01)


def test_behind_the_sun_is_negative():
    # Kolkata 88.36 E on UTC+5:30 runs ~23 minutes behind
    assert minutes_ahead(5.5, 88.36) < 0
