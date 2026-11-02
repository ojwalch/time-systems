"""The city histories and the chart rules on cases whose history is well known."""
import os

import pytest

from permanent_time import solar

needs_tz = pytest.mark.skipif(not os.path.exists(solar.ZONEINFO), reason="run scripts/setup_data.sh first")


@pytest.fixture(scope="module")
def cities():
    from permanent_time.data import load_config
    from permanent_time.winters import histories
    return {(h["city"]["name"], h["cc"]): h for h in histories(load_config())}


def sunrises(h):
    from permanent_time.winters import ends
    return [ends(o, h["city"])[0] for o in h["offs"]]


@needs_tz
def test_new_york_1974(cities):
    r = sunrises(cities[("New York City", "US")])
    assert max(r) > 8 * 60 + 15 and r[-1] < 7 * 60 + 30     # one winter of year-round DST; standard time today


@needs_tz
def test_istanbul(cities):
    r = sunrises(cities[("Istanbul", "TR")])
    assert 8 * 60 + 25 < r[-1] < 8 * 60 + 30                 # permanent UTC+3 since 2016: 8:29 am


@needs_tz
def test_moscow(cities):
    r = sunrises(cities[("Moscow", "RU")])
    assert max(r) > 9 * 60 + 45 and 8 * 60 + 55 < r[-1] < 9 * 60 + 5   # 10 am in 2011-14, 9 am since


@needs_tz
def test_recent_changes_are_too_soon(cities):
    assert cities[("Casablanca", "MA")]["recent"]            # back to GMT, September 2026
    assert not cities[("Istanbul", "TR")]["recent"]


@needs_tz
def test_china_excluded(cities):
    assert not any(cc == "CN" for _, cc in cities)


def test_daylight_bands():
    from permanent_time.winters import daylight
    assert 8.5 * 60 < daylight({"latitude": 42.36}) < 9 * 60    # Boston: 8 1/2 to 9 hours
    assert 9 * 60 < daylight({"latitude": 40.71}) < 9.5 * 60    # New York: 9 to 9 1/2 hours
    assert 7.5 * 60 < daylight({"latitude": 51.51}) < 8 * 60    # London: 7 1/2 to 8 hours
