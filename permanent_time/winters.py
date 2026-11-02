"""What every analysis here starts from: each city's winter clock, every winter since 1946,
and what that clock does to the sun on the darkest days of the year.

For every city of 15,000+ people (GeoNames), the clock in force in mid-winter (15 January
north of the equator, 15 July south of it) is read from the IANA time zone database for
every year from `period_start` to the coming winter, whether or not the place also changes
clocks for summer. Each city stands for its share of its country's city population, times
the country's population (World Bank, latest year).

Sun times are the standard published ones (the sun's upper edge on the horizon, allowing
for refraction), from NOAA's solar position formulas. The latest sunrise and the earliest
sunset of the year fall a few weeks either side of the solstice.
"""
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache

from . import solar
from .data import load_config


def clock(m):
    h, mm = divmod(int(m), 60)
    return f"{h % 12 or 12}:{mm:02d} {'pm' if h >= 12 else 'am'}"


@lru_cache(maxsize=None)
def earliest_sunset_lmt(lat):
    return min(solar._sunset_lmt_minutes(lat, d) for d in range(1, 366))


def ends(offset, city):
    """(latest sunrise, earliest sunset) of the year on a fixed clock, minutes after midnight."""
    lat, lon = round(city["latitude"], 2), city["longitude"]
    ahead = solar.minutes_ahead(offset, lon)
    return solar.latest_sunrise_lmt(lat) + ahead, earliest_sunset_lmt(lat) + ahead


def daylight(city):
    """Usable winter daylight in minutes: from the latest sunrise to the earliest sunset.
    Set by latitude; no clock can change it."""
    lat = round(city["latitude"], 2)
    return earliest_sunset_lmt(lat) - solar.latest_sunrise_lmt(lat)


@lru_cache(maxsize=None)
def _zone_cities(zone):
    return tuple(solar.select_cities(zones=[zone]))


def _mid_winter(city, year):
    return datetime(year, 7 if city["latitude"] < 0 else 1, 15, 12, tzinfo=timezone.utc)


def _change_date(zone, city, year):
    """Date of the last clock change before the city's mid-winter of `year` (the change that
    put that winter on a different clock)."""
    z = solar.zone(zone)
    t = int(_mid_winter(city, year).timestamp())
    off = z.offset_at(t)
    last = None
    for ts, o in z.transitions():
        if ts > t:
            break
        if o == off and (last is None or z.offset_at(ts - 1) != off):
            last = ts
    return datetime.fromtimestamp(last, tz=timezone.utc).date().isoformat() if last else f"{year}-01-01"


def histories(cfg=None):
    """One record per city: `offs`, its winter clock offset (hours from UTC) for every winter
    in `years`; `share`, its share of its country's city population; `recent`, whether its
    winter clock changed in the last `stuck_min_years` years (too soon to tell)."""
    cfg = cfg or load_config()
    excluded = set((cfg.get("excluded_countries") or {}).keys())
    as_of = date.fromisoformat(str(cfg["as_of"]))
    first = int(cfg["period_start"])
    cutoff = as_of - timedelta(days=round(365.25 * cfg["stuck_min_years"]))
    out, city_total = [], {}
    for z in sorted({solar.home_zone(c) for c in solar.cities()}):
        try:
            zz = solar.zone(z)
        except FileNotFoundError:
            continue
        cache = {}
        for city in _zone_cities(z):
            cc = city["countrycode"]
            if cc in excluded:
                continue
            if cc not in city_total:
                city_total[cc] = sum(c["population"] for c in solar.select_cities(country_codes=[cc])) or 1
            south = city["latitude"] < 0
            last = as_of.year if south else (as_of.year + 1 if as_of.month >= 3 else as_of.year)
            years = list(range(first, last + 1))
            offs = []
            for y in years:
                k = (south, y)
                if k not in cache:
                    cache[k] = zz.offset_at(int(_mid_winter({"latitude": -1 if south else 1}, y).timestamp())) / 3600
                offs.append(cache[k])
            recent = any(offs[i] != offs[i - 1] and
                         date.fromisoformat(_change_date(z, city, years[i])) > cutoff
                         for i in range(1, len(offs)) if years[i] >= cutoff.year)
            out.append({"city": city, "cc": cc, "zone": z, "years": years, "offs": offs,
                        "share": city["population"] / city_total[cc], "recent": recent})
    return out


def people(h, pop):
    return pop.get(h["cc"], "latest")[0] * h["share"]
