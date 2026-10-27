"""Hunt H-0001, step 3: vet the shortlist against the outside world.

For each shortlisted star: Gaia's own classifier verdict, whether VSX or SIMBAD already knows it,
how many papers mention it, close Gaia neighbours, and fresh NEOWISE (2014-2024) and ZTF
(2018-) light curves. Writes hunts/H-0001/vetted.csv and per-star JSON in hunts/H-0001/vet/.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from oddsky.analysis.stats import robust_std
from oddsky.data import gaia, neowise, ztf
from oddsky.data.http import request

here = Path("hunts/H-0001")
out_dir = here / "vet"
out_dir.mkdir(exist_ok=True)
tri = pd.read_csv(here / "scored.csv")
# Dips deeper than 0.8 mag (more than an eclipse by a similar star can do), confirmed on >= 2 transits,
# and not the 3+ mag single-transit window artifacts.
short = tri[(tri.max_depth >= 0.8) & (tri.max_depth < 3) & (tri.n_confirmed >= 1)].copy()
short = short.sort_values("max_depth", ascending=False)
print(len(short), "shortlisted", flush=True)

ids = ",".join(str(s) for s in short.source_id)
cls = gaia.adql(f"SELECT source_id, best_class_name, best_class_score FROM gaiadr3.vari_classifier_result "
                f"WHERE source_id IN ({ids})")
short = short.merge(cls, on="source_id", how="left")


def vsx(ra, dec):
    r = request("GET", "https://www.aavso.org/vsx/index.php", timeout=60,
                params={"view": "api.list", "ra": ra, "dec": dec, "radius": 10 / 3600, "format": "json"})
    try:
        objs = r.json().get("VSXObjects", {}).get("VSXObject", [])
    except ValueError:
        return []
    return objs if isinstance(objs, list) else [objs]


def simbad(ra, dec):
    from astroquery.simbad import Simbad
    q = ("SELECT TOP 5 basic.main_id, basic.otype, DISTANCE(POINT('ICRS', basic.ra, basic.dec), "
         f"POINT('ICRS', {ra}, {dec}))*3600 AS sep, (SELECT COUNT(*) FROM has_ref WHERE has_ref.oidref = basic.oid) AS nref "
         f"FROM basic WHERE CONTAINS(POINT('ICRS', basic.ra, basic.dec), CIRCLE('ICRS', {ra}, {dec}, {5 / 3600})) = 1 "
         "ORDER BY sep")
    try:
        t = Simbad.query_tap(q)
        return [dict(main_id=str(r["main_id"]), otype=str(r["otype"]), sep=float(r["sep"]), nref=int(r["nref"])) for r in t]
    except Exception as e:  # noqa: BLE001
        return [{"error": str(e)[:200]}]


rows = []
for _, s in short.iterrows():
    f = out_dir / f"{s.source_id}.json"
    if f.exists():
        rows.append(json.loads(f.read_text()))
        continue
    rec = {"source_id": int(s.source_id), "ra": s.ra, "dec": s.dec}
    rec["vsx"] = [{k: o.get(k) for k in ("Name", "VariabilityType", "MaxMag", "MinMag", "Period")} for o in vsx(s.ra, s.dec)]
    rec["simbad"] = simbad(s.ra, s.dec)
    cone, _ = gaia.cone(s.ra, s.dec, 10.0)
    nb = cone[cone.source_id != s.source_id]
    rec["neighbors_10as"] = nb[["sep_arcsec", "phot_g_mean_mag"]].round(2).to_dict(orient="records")
    try:
        nw, _ = neowise.lightcurve(s.ra, s.dec)
        good = nw[nw.flag == ""]
        for band in ("W1", "W2"):
            b = good[good.band == band]
            rec[f"{band}_n"] = len(b)
            if len(b) >= 4:
                rec[f"{band}_med"] = float(np.median(b.mag))
                rec[f"{band}_range"] = float(np.ptp(b.mag))
                rec[f"{band}_rstd"] = robust_std(b.mag.to_numpy())
        if rec.get("W1_n", 0) >= 4 and rec.get("W2_n", 0) >= 4:
            rec["W1_W2"] = rec["W1_med"] - rec["W2_med"]
    except Exception as e:  # noqa: BLE001
        rec["neowise_error"] = str(e)[:200]
    try:
        z, zp = ztf.lightcurve(s.ra, s.dec)
        zg = z[z.flag == ""]
        rec["ztf_n"] = len(zg)
        for band in ("ZTF_g", "ZTF_r"):
            b = zg[zg.band == band]
            if len(b) >= 20:
                med = np.median(b.mag)
                rec[f"{band}_med"] = float(med)
                rec[f"{band}_rstd"] = robust_std(b.mag.to_numpy())
                rec[f"{band}_n_dim"] = int((b.mag > med + max(0.1, 5 * robust_std(b.mag.to_numpy()))).sum())
                rec[f"{band}_max_depth"] = float(b.mag.max() - med)
    except Exception as e:  # noqa: BLE001
        rec["ztf_error"] = str(e)[:200]
    f.write_text(json.dumps(rec, default=float))
    rows.append(rec)
    print(s.source_id, "vsx", len(rec["vsx"]), "simbad", [x.get("otype") for x in rec["simbad"]][:2],
          "ztf", rec.get("ztf_n"), flush=True)

vet = short.merge(pd.json_normalize(rows, max_level=0)[["source_id"] + [c for c in pd.json_normalize(rows, max_level=0).columns
                                                                     if c not in short.columns]], on="source_id")
vet.to_csv(here / "vetted.csv", index=False)
print("done", len(vet), flush=True)
