"""Loaders shared by the analysis: settings, hand-curated notes and population."""
import csv
import os
from collections import defaultdict

import geonamescache
import yaml

from .tz import ROOT

GEN = os.path.join(ROOT, "data", "generated")


def load_config():
    with open(os.path.join(ROOT, "config.yaml")) as f:
        return yaml.safe_load(f)


def load_curation():
    path = os.path.join(ROOT, "data", "curation.yaml")
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


class Population:
    """World Bank total population (SP.POP.TOTL) by country and year."""

    def __init__(self):
        self.data = defaultdict(dict)
        with open(os.path.join(ROOT, "vendor-src", "population", "data", "population.csv")) as f:
            for r in csv.DictReader(f):
                if r["Value"]:
                    self.data[r["Country Code"]][int(r["Year"])] = float(r["Value"])
        self.countries = geonamescache.GeonamesCache().get_countries()

    def get(self, cc, year):
        """(population, year used, source) for ISO2 country code `cc` in `year` (or "latest").
        Years outside the World Bank series (which starts in 1960) use the nearest year."""
        c = self.countries.get(cc, {})
        iso3 = c.get("iso3")
        series = self.data.get(iso3)
        if series:
            y = max(series) if year == "latest" else min(max(year, min(series)), max(series))
            note = "" if year in ("latest", y) else f" (nearest available year to {year})"
            return series[y], y, f"World Bank SP.POP.TOTL {iso3} {y}{note}"
        if c:
            return float(c.get("population", 0)), None, "GeoNames country population (no World Bank series)"
        return 0.0, None, "no population source"
