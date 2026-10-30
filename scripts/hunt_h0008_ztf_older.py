"""H-0008: the two earlier ZTF microlensing catalogues, parsed from their arXiv LaTeX sources (positions only; no t0):
Rodriguez et al. (2022, arXiv:2112.07684; ZTF DR5 Galactic plane) and Medford et al. (2023, arXiv:2201.08335; PUZLE, ZTF DR5).
usage: hunt_h0008_ztf_older.py RODRIGUEZ_MAIN_TEX MEDFORD_MAIN_TEX OUT_CSV"""

import re
import sys

import pandas as pd

rows = []
for line in open(sys.argv[1]).read().splitlines():
    m = re.match(r"\s*(ZTF\d\d[a-z]{7})\s*&\s*(-?\d+\.\d+)\s*&\s*(-?\d+\.\d+)\s*&", line)
    if m:
        rows.append({"name": m.group(1), "ra": float(m.group(2)), "dec": float(m.group(3)), "source": "ZTF (Rodriguez+2022)"})
for line in open(sys.argv[2]).read().splitlines():
    m = re.match(r"\s*(\d+\\_\d+)\s*&\s*-?[\d.]+\s*&\s*-?[\d.]+\s*&\s*(-?\d+\.\d+)\s*&\s*(-?\d+\.\d+)\s*&.*?(ZTF\d\d[a-z]{7})?\s*\\\\", line)
    if m:
        rows.append({"name": m.group(4) or "PUZLE " + m.group(1).replace("\\_", "_"), "ra": float(m.group(2)),
                     "dec": float(m.group(3)), "source": "ZTF (Medford+2023)"})
d = pd.DataFrame(rows).drop_duplicates(["name", "source"])
d.to_csv(sys.argv[3], index=False)
print(d.source.value_counts().to_dict())
