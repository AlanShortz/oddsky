"""H-0008: parse OGLE-IV Early Warning System event pages (https://ogle.astrouw.edu.pl/ogle4/ews/YEAR/ews.html) into a table
with the same columns as the KMTNet one: name, ra, dec, t0_mjd, tE, u0, I_base. usage: hunt_h0008_ogle.py HTML_DIR OUT_CSV"""

import glob
import html
import re
import sys

import pandas as pd


def sexa(s, hours):
    sign = -1 if s.strip().startswith("-") else 1
    a, b, c = (float(x) for x in s.strip().lstrip("+-").split(":"))
    return sign * (a + b / 60 + c / 3600) * (15 if hours else 1)


num = re.compile(r"^-?\d+(\.\d+)?$")
rows = []
for f in sorted(glob.glob(f"{sys.argv[1]}/ogle*.html")):
    s = open(f, encoding="latin-1").read()
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", s, flags=re.S | re.I):
        # OGLE's pages leave <TD> unclosed: split on the opening tags
        cells = [html.unescape(re.sub("<[^>]+>", "", c)).strip() for c in re.split(r"<td[^>]*>", row, flags=re.I)[1:]]
        cells = [c for c in cells if c != ""]
        if len(cells) < 13 or not re.match(r"^\d{4}-(BLG|DG|GD)-\d+$", cells[0]):
            continue
        try:
            i = next(k for k, c in enumerate(cells) if re.match(r"^\d{2}:\d{2}:\d{2}(\.\d+)?$", c))
            ra, dec, tmax, _ut, tau, umin = cells[i:i + 6]
            ibl = cells[i + 9] if i + 9 < len(cells) else ""
            rows.append({"name": "OGLE-" + cells[0], "ra": sexa(ra, True), "dec": sexa(dec, False),
                         "t0_mjd": float(tmax) - 2400000.5, "tE": float(tau) if num.match(tau) else None,
                         "u0": float(umin) if num.match(umin) else None, "I_base": float(ibl) if num.match(ibl) else None})
        except (ValueError, StopIteration):
            continue
out = pd.DataFrame(rows).drop_duplicates("name")
out.to_csv(sys.argv[2], index=False)
print(len(out), "events;", out.groupby(out.name.str[5:9]).size().to_dict())
