"""Every VizieR catalogue entry within 4" of the main h0012b leads (IDIA mirror; CDS times out from here).

    uv run python hunts/H-0012/reviews/h0012b-referee/vizier_all.py
Writes vizier_all.json next to this script: {lead: {catalogue: [rows]}} (first 3 rows per catalogue, short columns).
"""
import json
import time
from pathlib import Path

import astropy.units as u
from astropy.coordinates import SkyCoord
from astroquery.vizier import Vizier

HERE = Path(__file__).resolve().parent
POS = {"NGC55_fsn7": (3.80788, -39.2148), "NGC2403_obs50": (114.228, 65.598), "NGC925_obs37": (36.7552, 33.5748),
       "NGC55_fsn13": (3.7601, -39.2179), "M81_fsn24": (148.924, 69.0145)}
v = Vizier(row_limit=3, columns=["*", "_r"], timeout=120)
v.VIZIER_SERVER = "vizier.idia.ac.za"
out = {}
for lab, (ra, dec) in POS.items():
    try:
        res = v.query_region(SkyCoord(ra, dec, unit="deg"), radius=4 * u.arcsec)
        out[lab] = {}
        for name in res.keys():
            t = res[name]
            cols = [c for c in t.colnames][:14]
            out[lab][name] = [{c: (str(r[c]) if r[c] is not None else "") for c in cols} for r in t]
        print(lab, len(res), sorted(res.keys())[:60], flush=True)
    except Exception as e:  # noqa: BLE001
        out[lab] = {"error": str(e)[:300]}
        print(lab, "ERR", str(e)[:200], flush=True)
    (HERE / "vizier_all.json").write_text(json.dumps(out, indent=1))
    time.sleep(5)
