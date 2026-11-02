"""Sun times on a clock, and the cities that stand in for each time zone's people.

A clock set to UTC offset Z hours, at longitude L degrees east, runs ahead of local mean
solar time by

    minutes_ahead = (Z - L / 15) * 60

so every sunrise and sunset happens that many minutes later on the clock than in mean
solar time. Sunrise and sunset in mean solar time come from NOAA's solar-position
approximations (declination and equation of time from the fractional year) with the
standard -0.833 degree horizon (refraction plus the sun's radius); they match published
tables to about a minute. Places with polar night have no sunrise on some days; those
count as infinitely late.

Cities: every city of 15,000+ people in GeoNames (CC BY 4.0, via the geonamescache
package). Each belongs to exactly one time zone whose clock history was swept (its own, or
the zone tz's "backward" file links it to), so no one is counted twice.
"""
import os
from datetime import datetime, timezone
from functools import lru_cache

import geonamescache

from .tz import ROOT, Zone, ZONEINFO


def minutes_ahead(utc_offset_hours, longitude_east_deg):
    m = (utc_offset_hours - longitude_east_deg / 15.0) * 60.0
    # Places near the date line (Samoa, Tonga, Kiribati) can be a whole day "ahead";
    # only the time of day matters, so wrap into [-720, 720) minutes.
    return (m + 720.0) % 1440.0 - 720.0


@lru_cache(maxsize=None)
def _links():
    links = {}
    path = os.path.join(ROOT, "vendor-src", "tz", "backward")
    with open(path) as f:
        for line in f:
            parts = line.split()
            if len(parts) >= 3 and parts[0] == "Link":
                links[parts[2]] = parts[1]
    return links


@lru_cache(maxsize=None)
def zone(name):
    path = os.path.join(ZONEINFO, name)
    if not os.path.exists(path):
        name = _links().get(name, name)
    return Zone(name)


@lru_cache(maxsize=None)
def cities():
    gc = geonamescache.GeonamesCache(min_city_population=15000)
    return list(gc.get_cities().values())


@lru_cache(maxsize=None)
def _swept_zones():
    from .tz import load_zone_tab
    return frozenset(r["zone"] for r in load_zone_tab() if os.path.exists(os.path.join(ZONEINFO, r["zone"])))


def home_zone(c):
    """The swept zone whose clock history a city follows: its own zone if that zone is in
    zone.tab and has compiled data (and so was swept), otherwise the zone its name links to in tz's 'backward' file.
    Each city has exactly one home zone, so no city is counted under two zones."""
    tz = c["timezone"]
    return tz if tz in _swept_zones() else _links().get(tz, tz)


def select_cities(country_codes=None, zones=None, admin1=None):
    """Cities filtered by ISO country codes, tz zone names (matched by home zone), and/or
    (country, admin1) pairs."""
    out = []
    zset = set(zones or [])
    a1 = {tuple(x) for x in (admin1 or [])}
    for c in cities():
        if country_codes and c["countrycode"] not in country_codes:
            continue
        if zset and home_zone(c) not in zset:
            continue
        if a1 and (c["countrycode"], c["admin1code"]) not in a1:
            continue
        out.append(c)
    return out


# ---------------------------------------------------------------- sunrise and sunset
# On a fixed clock the offset is the same every day, so the latest sunrise on the clock is
# the latest sunrise in mean solar time plus minutes_ahead (and likewise for sunsets).
import math as _m


def _sunrise_lmt_minutes(lat_deg, doy):
    g = 2 * _m.pi / 365 * (doy - 1)
    decl = (0.006918 - 0.399912 * _m.cos(g) + 0.070257 * _m.sin(g)
            - 0.006758 * _m.cos(2 * g) + 0.000907 * _m.sin(2 * g)
            - 0.002697 * _m.cos(3 * g) + 0.00148 * _m.sin(3 * g))
    eot = 229.18 * (0.000075 + 0.001868 * _m.cos(g) - 0.032077 * _m.sin(g)
                    - 0.014615 * _m.cos(2 * g) - 0.040849 * _m.sin(2 * g))
    phi = _m.radians(lat_deg)
    cos_h = ((_m.sin(_m.radians(-0.833)) - _m.sin(phi) * _m.sin(decl))
             / (_m.cos(phi) * _m.cos(decl)))
    if cos_h > 1:
        return float("inf")          # sun never rises
    if cos_h < -1:
        return float("-inf")         # sun never sets
    h = _m.degrees(_m.acos(cos_h))
    return 720 - 4 * h - eot         # minutes after local mean midnight


@lru_cache(maxsize=None)
def latest_sunrise_lmt(lat_deg):
    """Latest sunrise of the year in local mean solar time, minutes after midnight."""
    return max(_sunrise_lmt_minutes(lat_deg, d) for d in range(1, 366))


def latest_clock_sunrise(utc_offset_hours, lat_deg, lon_deg):
    """Latest sunrise of the year on a fixed clock, minutes after clock midnight."""
    return latest_sunrise_lmt(round(lat_deg, 2)) + minutes_ahead(utc_offset_hours, lon_deg)


def _sunset_lmt_minutes(lat_deg, doy):
    r = _sunrise_lmt_minutes(lat_deg, doy)
    if r in (float("inf"), float("-inf")):
        return -r
    g = 2 * _m.pi / 365 * (doy - 1)
    eot = 229.18 * (0.000075 + 0.001868 * _m.cos(g) - 0.032077 * _m.sin(g)
                    - 0.014615 * _m.cos(2 * g) - 0.040849 * _m.sin(2 * g))
    noon = 720 - eot
    return 2 * noon - r


@lru_cache(maxsize=None)
def latest_sunset_lmt(lat_deg):
    return max(_sunset_lmt_minutes(lat_deg, d) for d in range(1, 366))


def latest_clock_sunset(utc_offset_hours, lat_deg, lon_deg):
    """Latest sunset of the year on a clock, minutes after clock midnight."""
    return latest_sunset_lmt(round(lat_deg, 2)) + minutes_ahead(utc_offset_hours, lon_deg)
