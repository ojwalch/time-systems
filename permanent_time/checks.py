"""Checks on the sunrise chart, for the daylight bands that cover the contiguous US.
Writes output/checks.md.

1. What is in each cell: the countries that make up most of the people who ever had that
   sunrise, and most of those who still do. Some cells rest on a few decisions.
2. Only cities whose winter clock has changed at least once since 1946. Cities that never
   changed count as "still have it" automatically; this leaves them out.
3. With China included. China keeps one clock across about 60 degrees of longitude, so its
   western cities have late sunrises by fiat; it is left out of the charts.

python -m permanent_time.checks
"""
import os
from collections import defaultdict

import geonamescache

from .data import ROOT, Population, load_config
from .daylight import BANDS, MIN_PEOPLE, SUNRISES, US_BANDS
from .winters import clock, daylight, ends, histories, people


def cell(hist, pop, band, x, changed_only=False):
    lo, hi = BANDS[band][:2]
    had, still = defaultdict(float), defaultdict(float)
    for h in hist:
        if h["recent"] or not lo <= daylight(h["city"]) < hi:
            continue
        if changed_only and len(set(h["offs"])) < 2:
            continue
        rises = [ends(o, h["city"])[0] for o in h["offs"]]
        if max(rises) > x:
            n = people(h, pop)
            had[h["cc"]] += n
            still[h["cc"]] += n * (rises[-1] > x)
    return had, still


def main():
    cfg, pop = load_config(), Population()
    names = geonamescache.GeonamesCache().get_countries()
    name = lambda cc: names.get(cc, {}).get("name", cc)
    hist = histories(cfg)
    with_china = histories({**cfg, "excluded_countries": {}})
    out = ["# Checks on the sunrise chart", "",
           "For the daylight bands that cover the contiguous US. Each cell of the chart is: of people "
           "who ever had a winter sunrise later than the time shown since 1946, the share who still do.", ""]

    def top(d, k=3):
        tot = sum(d.values())
        return ", ".join(f"{name(cc)} {100 * v / tot:.0f}%" for cc, v in sorted(d.items(), key=lambda kv: -kv[1])[:k]
                         if v / tot >= 0.05) if tot else "-"

    out += ["## What is in each cell", "",
            "The countries that make up most of each cell (5% or more), by population.", ""]
    for b in US_BANDS:
        out += [f"### {BANDS[b][2]} ({BANDS[b][3].replace(chr(10), ' ')})", "",
                "| Sunrise later than | Still have it | Who ever had it | Who still has it |", "|---|---|---|---|"]
        for x in SUNRISES:
            had, still = cell(hist, pop, b, x)
            tot = sum(had.values())
            if tot < MIN_PEOPLE:
                continue
            out.append(f"| {clock(x)} | {100 * sum(still.values()) / tot:.0f}% of {tot / 1e6:.0f}M | {top(had)} | {top(still)} |")
        out.append("")

    def table(title, note, h, changed_only=False):
        rows = [f"## {title}", "", note, "",
                "| Sunrise later than | " + " | ".join(BANDS[b][2] for b in US_BANDS) + " |",
                "|---|" + "---|" * len(US_BANDS)]
        for x in SUNRISES:
            cells = []
            for b in US_BANDS:
                had, still = cell(h, pop, b, x, changed_only)
                tot = sum(had.values())
                cells.append(f"{100 * sum(still.values()) / tot:.0f}% ({tot / 1e6:.0f}M)" if tot >= MIN_PEOPLE else "-")
            rows.append(f"| {clock(x)} | " + " | ".join(cells) + " |")
        return rows + [""]

    out += table("Only cities whose winter clock has changed",
                 "Cities that have never changed their winter clock since 1946 count as still having whatever "
                 "sunrise they have. Leaving them out:", hist, changed_only=True)
    out += table("With China included",
                 "China keeps one clock across about 60 degrees of longitude, unchanged since 1949, so its "
                 "western cities have late sunrises by fiat. Including it:", with_china)
    with open(os.path.join(ROOT, "output", "checks.md"), "w") as f:
        f.write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
