"""Which leads have archival HST imaging (MAST, science observations whose footprint contains the position).

    uv run python hunts/H-0012/reviews/claude-referee-triage-2026-11-01/hst_coverage.py
Writes hst_coverage.json (per lead: instrument/filter/date/obsid of HST images, and JWST if any).
"""
import json
from pathlib import Path

from astropy.coordinates import SkyCoord
from astroquery.mast import Observations

HERE = Path(__file__).resolve().parent
L = json.loads((HERE / "leads.json").read_text())
SEL = {"NGC4945 obs#3", "M81 obs#9", "NGC55 obs#14", "M101 obs#19", "IC342 fsn#1", "NGC2976 fsn#5", "NGC3239 obs#33",
       "UGCA127 obs#30", "IC342 obs#26", "M31 fsn#4", "M33 fsn#13", "HolmII obs#21"}
out = {}
for d in L:
    if d["lead"] not in SEL:
        continue
    try:
        t = Observations.query_region(SkyCoord(d["ra"], d["dec"], unit="deg"), radius="0.0003 deg")
        t = t[(t["dataproduct_type"] == "image") & ((t["obs_collection"] == "HST") | (t["obs_collection"] == "JWST"))
              & (t["intentType"] == "science")]
        rows = sorted({(str(r["obs_collection"]), str(r["instrument_name"]), str(r["filters"]), round(float(r["t_min"]), 1))
                       for r in t}, key=lambda x: x[3])
        out[d["lead"]] = dict(n=len(rows), obs=rows)
    except Exception as e:  # noqa: BLE001
        out[d["lead"]] = dict(error=str(e)[:200])
    o = out[d["lead"]]
    print(d["lead"], o.get("n"), o.get("error", ""), o.get("obs", [])[:3], "...", o.get("obs", [])[-3:], flush=True)
(HERE / "hst_coverage.json").write_text(json.dumps(out, indent=1))
