"""H-0008: parse KMTNet's public microlensing event pages (https://kmtnet.kasi.re.kr/~ulens/event/YEAR/) into one table.

Columns kept: name, ra, dec (deg), t0_mjd (from HJD-2450000), tE, u0, I_base, and the related (OGLE/MOA) event ids. Pages are fetched to a
directory first (curl), then parsed: usage: hunt_h0008_kmt.py HTML_DIR OUT_CSV
"""

import glob
import html
import re
import sys

import pandas as pd


def sexa(s, hours):
    sign = -1 if s.strip().startswith("-") else 1
    a, b, c = (float(x) for x in s.strip().lstrip("+-").split(":"))
    v = a + b / 60 + c / 3600
    return sign * v * (15 if hours else 1)


rows = []
for f in sorted(glob.glob(f"{sys.argv[1]}/kmt*.html")):
    s = open(f, encoding="utf-8", errors="replace").read()
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", s, flags=re.S):
        cells = [html.unescape(re.sub("<[^>]+>", "", c)).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", row, flags=re.S)]
        if len(cells) < 12 or not re.match(r"KMT-\d{4}-BLG-\d+", cells[0]):
            continue
        try:
            # the RA column moved between page layouts: find it, then read the next columns in order
            i = next(k for k, c in enumerate(cells) if re.match(r"^\d{2}:\d{2}:\d{2}(\.\d+)?$", c))
            ra, dec, t0, te, u0, _isrc, ibase = cells[i:i + 7]
            t0 = float(t0)
            rows.append({"name": cells[0], "ra": sexa(ra, True), "dec": sexa(dec, False),
                         "t0_mjd": t0 + 2450000 - 2400000.5 if t0 > 1000 else None,
                         "tE": float(te) if re.match(r"^-?\d+(\.\d+)?$", te) else None,
                         "u0": float(u0) if re.match(r"^-?\d+(\.\d+)?$", u0) else None,
                         "I_base": float(ibase) if re.match(r"^-?\d+(\.\d+)?$", ibase) else None,
                         "related": cells[-1]})
        except (ValueError, IndexError, StopIteration):
            continue
out = pd.DataFrame(rows).drop_duplicates("name")
out.to_csv(sys.argv[2], index=False)
print(len(out), "events;", out.groupby(out.name.str[4:8]).size().to_dict())
