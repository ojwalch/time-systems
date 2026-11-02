"""The main charts. A clock change slides sunrise and sunset together; it cannot change how
much daylight a place has. So cities are grouped by their usable winter daylight (latest
sunrise to earliest sunset, set by latitude), and sunrise and sunset are asked about
separately: of people who have ever had a winter sunrise later than a given time since 1946,
the share who still do (output/chart_daylight_sunrise.png); likewise for sunsets earlier than
a given time (output/chart_daylight_sunset.png). output/chart_post.png is the sunrise chart
trimmed to the daylight bands that cover the contiguous US. Sunrise times span US winter
sunrises on year-round daylight saving time; sunset times span US winter sunsets on standard
time. Cells are shaded where at least US_SHARE of the people in contiguous-US cities in that
band would get that time.

python -m permanent_time.daylight
"""
import csv
import glob
import logging
import os
import textwrap

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

from matplotlib import font_manager  # noqa: E402

from .data import ROOT, Population, load_config  # noqa: E402
from .winters import clock, daylight, ends, histories  # noqa: E402

SURFACE, INK, INK2, GRID, TRACK = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df", "#efeeea"
MORNING_COLOR, AFTERNOON_COLOR = "#2a78d6", "#eb6834"


def _fonts():
    for font in glob.glob("/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyreheros-*.otf"):
        font_manager.fontManager.addfont(font)
    # Helvetica if installed; otherwise TeX Gyre Heros, a free Helvetica clone
    plt.rcParams["font.family"] = ["Helvetica", "TeX Gyre Heros", "Liberation Sans", "DejaVu Sans"]
    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)

SUNRISES = list(range(465, 541, 15))      # later than 7:45 ... 9:00 am
SUNSETS = list(range(975, 1066, 15))      # earlier than 4:15 ... 5:45 pm
BANDS = [(0, 450, "Under 7½ hours", "Dublin, Moscow,\nStockholm"),
         (450, 480, "7½ to 8 hours", "London, Berlin,\nAmsterdam, Warsaw"),
         (480, 510, "8 to 8½ hours", "Seattle, Paris,\nVienna, Munich"),
         (510, 540, "8½ to 9 hours", "Boston, Detroit,\nMinneapolis, Toronto"),
         (540, 570, "9 to 9½ hours", "New York, Chicago,\nIstanbul, Madrid"),
         (570, 600, "9½ to 10 hours", "Los Angeles, Atlanta,\nTehran, Tokyo"),
         (600, 630, "10 to 10½ hours", "Houston, Miami,\nCairo, Delhi")]
US_BANDS = [2, 3, 4, 5]                   # the daylight bands that cover the contiguous US
MIN_PEOPLE = 10e6                         # cells with fewer people who ever had it show "-"


US_SHARE = 0.05       # a cell is marked if at least this share of US city people in its band would get it
NOT_CONTIGUOUS = {"America/Phoenix", "Pacific/Honolulu", "America/Anchorage", "America/Juneau", "America/Sitka",
                  "America/Nome", "America/Yakutat", "America/Metlakatla", "America/Adak"}


def us_exposure(hist):
    """{(band, 'sunrise'|'sunset', time): share of people in contiguous-US cities in that band who
    would get a winter sunrise later than `time` on year-round daylight saving time (sunrise),
    or a winter sunset earlier than `time` on standard time (sunset)."""
    out = {}
    for b, (lo, hi, *_) in enumerate(BANDS):
        rows = []
        for h in hist:
            if h["cc"] != "US" or h["zone"] in NOT_CONTIGUOUS or not lo <= daylight(h["city"]) < hi:
                continue
            standard = min(h["offs"][-5:])          # US winters are on standard time
            rows.append((h["city"]["population"], ends(standard + 1, h["city"])[0], ends(standard, h["city"])[1]))
        total = sum(n for n, *_ in rows) or 1
        for x in SUNRISES:
            out[b, "sunrise", x] = sum(n for n, rise, _ in rows if rise > x) / total
        for y in SUNSETS:
            out[b, "sunset", y] = sum(n for n, _, sset in rows if sset < y) / total
    return out


def by_daylight(hist, pop):
    """{(band, 'sunrise'|'sunset', time): (share who still do, people who ever had it)}"""
    out = {}
    for b, (lo, hi, *_) in enumerate(BANDS):
        rows = []
        for h in hist:
            if h["recent"] or not lo <= daylight(h["city"]) < hi:
                continue
            sun = [ends(o, h["city"]) for o in h["offs"]]
            rows.append((pop.get(h["cc"], "latest")[0] * h["share"], [r for r, _ in sun], [s for _, s in sun]))
        for x in SUNRISES:
            had = sum(n for n, r, _ in rows if max(r) > x)
            still = sum(n for n, r, _ in rows if max(r) > x and r[-1] > x)
            out[b, "sunrise", x] = (still / had if had else float("nan"), had)
        for y in SUNSETS:
            had = sum(n for n, _, s in rows if min(s) < y)
            still = sum(n for n, _, s in rows if min(s) < y and s[-1] < y)
            out[b, "sunset", y] = (still / had if had else float("nan"), had)
    return out


US_PANEL = "#ecebe6"
US_CLOCK = {"sunrise": "on year-round daylight saving time", "sunset": "on standard time"}
PANELS = {
    "sunrise": (SUNRISES, "Did they stick with a dark morning\nor move earlier?",
                "Of people who ever had a winter sunrise later than the time listed,\nwhat percent still have it today?",
                AFTERNOON_COLOR, "am", "Times span US winter sunrises on year-round daylight saving time."),
    "sunset": (SUNSETS, "Did they stick with a dark afternoon\nor move later?",
               "Of people who ever had a winter sunset earlier than the time listed,\nwhat percent still have it today?",
               MORNING_COLOR, "pm", "Times span US winter sunsets on standard time."),
}


def draw_daylight(res, key, path, us=None, bands=None):
    bands = list(range(len(BANDS))) if bands is None else bands
    nb = len(bands)
    """One chart: rows are times, columns are bands of usable winter daylight."""
    times, title, caption, color, ampm, span = PANELS[key]
    _fonts()
    width = 76 - 14.6 * (4 - nb)            # four columns at 76 units wide
    extra = 4.0 if nb < 5 else 0            # a narrower figure wraps the footer onto more lines
    base = 6.6 * (7 - len(times))           # rows removed below the grid
    fig = plt.figure(figsize=(width / 10, (84.6 + extra - base) / 10), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, width)
    ax.set_ylim(-4 - extra + base, 80.6)
    ax.axis("off")

    def text(x, y, s, size, color=INK, weight="normal", **kw):
        ax.text(x, y, s, fontsize=size, color=color, weight=weight, va="top", linespacing=1.35, **kw)

    text(4, 77.6, title, 18, weight="bold")
    text(4, 69.0, caption, 11, INK2)
    col_w, x0 = 14.6, 15
    text(x0, 62.4, "Hours of winter daylight", 9, INK2)
    for j, b in enumerate(bands):
        _, _, name, eg = BANDS[b]
        cx = x0 + j * col_w
        text(cx, 59.8, name.replace(" hours", "h").replace("Under ", "Under "), 10.5, weight="bold")
        text(cx, 57.0, eg, 8, INK2)
    for i, t in enumerate(times):
        y = 49.8 - i * 6.6
        ax.plot([4, x0 + nb * col_w - 1.6], [y + 3.3, y + 3.3], color=GRID, linewidth=1)
        ax.text(4, y, f"{clock(t).replace(' ' + ampm, '')} {ampm}", fontsize=12, color=INK,
                weight="bold", va="baseline")
        for j, b in enumerate(bands):
            share, had = res[b, key, t]
            cx = x0 + j * col_w
            marked = us is None or us[b, key, t] >= US_SHARE
            if marked and us is not None:            # a light panel behind cells US cities would get
                ax.add_patch(FancyBboxPatch((cx - 1.0, y - 3.4), col_w - 0.6, 6.0,
                                            boxstyle="round,pad=0,rounding_size=0.6",
                                            facecolor=US_PANEL, edgecolor="none", zorder=0))
            if had < MIN_PEOPLE:
                ax.text(cx, y, "\u2013", fontsize=12, color=INK2, va="baseline")
                continue
            alpha = 1 if marked else 0.4
            ax.text(cx, y, f"{100 * share:.0f}%", fontsize=12, color=INK, weight="bold", va="baseline", alpha=alpha)
            ax.text(cx + 6.4, y, f"of {had / 1e6:,.0f}M", fontsize=7.5, color=INK2, va="baseline", alpha=alpha)
            w = col_w - 2.6
            ax.add_patch(FancyBboxPatch((cx, y - 2.5), w, 1.2, boxstyle="round,pad=0,rounding_size=0.3",
                                        facecolor=TRACK, edgecolor="none"))
            if share > 0:
                ax.add_patch(FancyBboxPatch((cx, y - 2.5), w * share, 1.2, boxstyle="round,pad=0,rounding_size=0.3",
                                            facecolor=color, edgecolor="none", alpha=alpha))
    if us is not None:
        ax.add_patch(FancyBboxPatch((4, 4.6 + base), 2.2, 1.6, boxstyle="round,pad=0,rounding_size=0.3",
                                    facecolor=US_PANEL, edgecolor="none"))
        key_text = (f"Shaded: US cities with this much daylight would get a winter {key} this "
                    f"{'late' if key == 'sunrise' else 'early'} {US_CLOCK[key]} (at least {US_SHARE:.0%} of their people).")
        ax.text(7.2, 5.4 + base, "\n".join(textwrap.wrap(key_text, int(width * 1.45))), fontsize=8, color=INK,
                va="center", linespacing=1.3)
    note = ("Winter daylight: from the latest sunrise to the earliest sunset, around the shortest days of the year; "
            "set by latitude. " + span + f" \u2013 : fewer than {MIN_PEOPLE / 1e6:.0f} million people ever had it. "
            "Every city of 15,000+ people outside China, every winter since 1946, counted by population; "
            "places whose winter clock changed in the last 3 years left out.")
    text(4, 0.9 + base, "\n".join(textwrap.wrap(note, int(width * 1.5))), 7.5, INK2)
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)


def main():
    cfg = load_config()
    hist, pop = histories(cfg), Population()
    out = os.path.join(ROOT, "output")
    res, us = by_daylight(hist, pop), us_exposure(hist)
    for key in PANELS:
        draw_daylight(res, key, os.path.join(out, f"chart_daylight_{key}.png"), us)
    # the figure for the post: sunrises only, the three daylight bands that cover the US debate
    draw_daylight(res, "sunrise", os.path.join(out, "chart_post.png"), us, bands=US_BANDS)
    with open(os.path.join(out, "chart_daylight_data.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["daylight_band", "end", "time", "share_still", "people_ever_had", "us_share_would_get"])
        for (b, key, t), (share, had) in sorted(res.items()):
            w.writerow([BANDS[b][2], key, clock(t), round(share, 6) if had else "", round(had), round(us[b, key, t], 4)])



if __name__ == "__main__":
    main()
