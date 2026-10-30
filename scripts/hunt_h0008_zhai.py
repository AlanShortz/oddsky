"""H-0008: the ZTF microlensing catalogue of Zhai et al. (2024, ApJ; arXiv:2311.18627v2): 124 high-confidence and 54 possible
events in ZTF DR17 (2018-2023), parsed from the arXiv HTML (tables of events). usage: hunt_h0008_zhai.py HTML OUT_CSV"""

import html
import re
import sys

import pandas as pd


def first(s):
    m = re.match(r"\s*(-?\d+(\.\d+)?)", s.replace("−", "-"))
    return float(m.group(1)) if m else None


s = open(sys.argv[1], encoding="utf-8", errors="replace").read()
rows = []
for tab in re.findall(r"<table.*?</table>", s, flags=re.S):
    for tr in re.findall(r"<tr.*?</tr>", tab, flags=re.S):
        cells = [html.unescape(re.sub(r"\s+", " ", re.sub("<[^>]+>", " ", c))).strip()
                 for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, flags=re.S)]
        if len(cells) > 6 and cells[0].startswith("ZTF") and first(cells[2]) is not None and first(cells[4]) is not None:
            if first(cells[4]) < 5000 or first(cells[4]) > 11000:  # the lens-mass table has no t0 column
                continue
            rows.append({"name": cells[0], "gaia_alert": cells[1] if cells[1] != "…" else "", "ra": first(cells[2]),
                         "dec": first(cells[3]), "t0_mjd": first(cells[4]) + 2450000 - 2400000.5, "u0": first(cells[5]),
                         "tE": first(cells[6])})
d = pd.DataFrame(rows).drop_duplicates("name")
d.to_csv(sys.argv[2], index=False)
print(len(d), "ZTF events (Zhai et al. 2024)")
