"""Reads compiled IANA time zone data (TZif files under build/zoneinfo, made by
scripts/setup_data.sh) and the zone.tab list of zones with their principal cities."""
import bisect
import os
import struct

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZONEINFO = os.path.join(ROOT, "build", "zoneinfo")
ZONE_TAB = os.path.join(ROOT, "vendor-src", "tz", "zone.tab")


# ---------------------------------------------------------------- TZif reading
def read_tzif(path):
    """Return (transition_utc_seconds, offsets_seconds, initial_offset) from a TZif v2+ file."""
    with open(path, "rb") as f:
        data = f.read()

    def header(pos):
        counts = struct.unpack(">6l", data[pos + 20:pos + 44])
        return counts  # isutcnt, isstdcnt, leapcnt, timecnt, typecnt, charcnt

    isut, isstd, leap, timecnt, typecnt, charcnt = header(0)
    v1_len = 44 + timecnt * 5 + typecnt * 6 + charcnt + leap * 8 + isstd + isut
    pos = v1_len  # second header (64-bit data)
    isut, isstd, leap, timecnt, typecnt, charcnt = header(pos)
    pos += 44
    times = list(struct.unpack(f">{timecnt}q", data[pos:pos + 8 * timecnt]))
    pos += 8 * timecnt
    idx = list(data[pos:pos + timecnt])
    pos += timecnt
    types, dst = [], []
    for i in range(typecnt):
        off, isdst, _abbr = struct.unpack(">lBB", data[pos + 6 * i:pos + 6 * i + 6])
        types.append(off)
        dst.append(isdst)
    offsets = [types[i] for i in idx]
    flags = [dst[i] for i in idx]
    return times, offsets, types[0], flags, dst[0]


class Zone:
    def __init__(self, name):
        self.name = name
        self.times, self.offsets, self.initial, self.flags, self.initial_dst = \
            read_tzif(os.path.join(ZONEINFO, name))

    def offset_at(self, ts):
        i = bisect.bisect_right(self.times, ts) - 1
        return self.initial if i < 0 else self.offsets[i]

    def isdst_at(self, ts):
        i = bisect.bisect_right(self.times, ts) - 1
        return self.initial_dst if i < 0 else self.flags[i]

    def transitions(self):
        return list(zip(self.times, self.offsets))


# ---------------------------------------------------------------- zone.tab
def parse_coord(s):
    """'+5131-00008' or '+404251-0740023' -> (lat, lon) in decimal degrees."""
    for i in range(1, len(s)):
        if s[i] in "+-":
            break
    lat_s, lon_s = s[:i], s[i:]

    def dms(x, deg_digits):
        sign = -1 if x[0] == "-" else 1
        x = x[1:]
        d = int(x[:deg_digits])
        m = int(x[deg_digits:deg_digits + 2])
        sec = int(x[deg_digits + 2:deg_digits + 4]) if len(x) > deg_digits + 2 else 0
        return sign * (d + m / 60 + sec / 3600)

    return dms(lat_s, 2), dms(lon_s, 3)


def load_zone_tab():
    rows = []
    with open(ZONE_TAB) as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.rstrip("\n").split("\t")
            cc, coord, name = parts[0], parts[1], parts[2]
            comment = parts[3] if len(parts) > 3 else ""
            lat, lon = parse_coord(coord)
            rows.append({"cc": cc, "zone": name, "lat": lat, "lon": lon, "comment": comment})
    return rows
