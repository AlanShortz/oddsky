"""Build a Librarian shelf (src/oddsky/shelves/<name>.csv) from a VizieR catalogue: every row's J2000 position, named by
its coordinates. The CfA mirror is used because the CDS server times out from here.
usage: build_shelf.py VIZIER_ID SHELF_NAME BIBCODE TOPICS "TITLE"     e.g. J/ApJS/252/32 jiang2021_mirong 2021ApJS..252...32J transient "..." """
import re
import sys

import requests

cat, name, bibcode, topics, title = sys.argv[1:6]
t = requests.get("https://vizier.cfa.harvard.edu/viz-bin/asu-tsv", params={"-source": cat, "-out.max": "99999", "-out": "_RAJ2000,_DEJ2000"},
                 timeout=120).text
if "Error=" in t:
    sys.exit("VizieR: " + re.search(r"Error=([^\t\n]*)", t).group(1))
rows = []
for line in t.splitlines():
    m = re.match(r"^\s*(-?\d+\.\d+)\s+([+-]?\d+\.\d+)\s*$", line)
    if m:
        ra, dec = float(m.group(1)), float(m.group(2))
        h, d = ra / 15, abs(dec)
        sign = "+" if dec >= 0 else "-"
        des = f"J{int(h):02d}{int(h * 60 % 60):02d}{h * 3600 % 60:05.2f}{sign}{int(d):02d}{int(d * 60 % 60):02d}{d * 3600 % 60:04.1f}"
        rows.append((des, ra, dec))
rows = sorted(set(rows))
if not rows:
    sys.exit("no rows with positions")
out = f"src/oddsky/shelves/{name}.csv"
with open(out, "w") as f:
    f.write(f"# title: {title}\n# bibcode: {bibcode}\n# topics: {topics}\n# source: VizieR {cat} (every table row with a position), fetched from vizier.cfa.harvard.edu\nname,ra,dec\n")
    for des, ra, dec in rows:
        f.write(f"{des},{ra:.5f},{dec:.5f}\n")
print(out, len(rows), "rows")
