"""Hunt H-0004, step 4: vet the picks against the outside world before anyone gets excited.

For each rcb_pick / eclipse_pick in scored.csv: VSX (type, period, who found it), SIMBAD in 2026 (type and
paper count; the pool carried 2018 types), the R CrB catalogues, Gaia neighbours within 10", the Gaia
variability classifier, and NEOWISE W1-W2 (is there the dust excess an R CrB star must have?).
Writes hunts/H-0004/vet/<id>.json (resumable) and hunts/H-0004/vetted.csv.

  .venv/bin/python scripts/hunt_h0004_vet.py [--all-verdicts rcb_like,eclipse_like,unclassified]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import httpx
import numpy as np
import pandas as pd

from oddsky.analysis.color import wise_color
from oddsky.data import gaia, neowise
from oddsky.data.http import request

here = Path("hunts/H-0004")
out_dir = here / "vet"
out_dir.mkdir(exist_ok=True)

RCB_CATALOGUES = ("J/A+A/667/A84/objects", "J/A+A/635/A14/list", "J/AJ/156/148/table1", "J/ApJ/747/102/stars")


def vsx(ra, dec):
    try:
        r = request("GET", "https://www.aavso.org/vsx/index.php", timeout=60,
                    params={"view": "api.list", "ra": ra, "dec": dec, "radius": 10 / 3600, "format": "json"})
        j = r.json()
    except Exception as e:  # noqa: BLE001
        return [{"error": str(e)[:100]}]
    objs = j
    if isinstance(j, dict):
        objs = j.get("VSXObjects", j)
        if isinstance(objs, dict):
            objs = objs.get("VSXObject", [])
    objs = objs if isinstance(objs, list) else [objs]
    objs = [o for o in objs if isinstance(o, dict)]
    return [{k: o.get(k) for k in ("Name", "VariabilityType", "Period", "MaxMag", "MinMag", "Discoverer", "AUID")} for o in objs]


def simbad(ra, dec):
    from astroquery.simbad import Simbad
    q = ("SELECT TOP 5 basic.main_id, basic.otype, DISTANCE(POINT('ICRS', basic.ra, basic.dec), "
         f"POINT('ICRS', {ra}, {dec}))*3600 AS sep, basic.nbref AS nref "
         f"FROM basic WHERE CONTAINS(POINT('ICRS', basic.ra, basic.dec), CIRCLE('ICRS', {ra}, {dec}, {5 / 3600})) = 1 "
         "ORDER BY sep")
    try:
        t = Simbad.query_tap(q)
        return [dict(main_id=str(r["main_id"]), otype=str(r["otype"]), sep=float(r["sep"]), nref=int(r["nref"])) for r in t]
    except Exception as e:  # noqa: BLE001
        return [{"error": str(e)[:200]}]


def rcb_catalogues(ra, dec):
    hits = []
    for tab in RCB_CATALOGUES:
        q = (f'SELECT TOP 1 * FROM "{tab}" WHERE 1=CONTAINS(POINT(\'ICRS\', RAJ2000, DEJ2000), '
             f"CIRCLE('ICRS', {ra}, {dec}, {10 / 3600}))")
        try:
            r = httpx.post("https://tapvizier.cds.unistra.fr/TAPVizieR/tap/sync", timeout=60,
                           data=dict(REQUEST="doQuery", LANG="ADQL", FORMAT="csv", QUERY=q))
            if r.status_code == 200 and len(r.text.strip().splitlines()) > 1:
                hits.append(tab)
        except Exception:  # noqa: BLE001
            pass
    return hits


def gaia_bits(ra, dec, source_id):
    out = {}
    try:
        cone, _ = gaia.cone(ra, dec, 10.0)
        if cone.empty:
            out["neighbours_10arcsec"] = []
        elif source_id and not np.isnan(source_id):
            nb = gaia.neighbors(cone, int(source_id))
            out["neighbours_10arcsec"] = nb[["source_id", "sep_arcsec", "phot_g_mean_mag", "flux_ratio_G"]].round(3).to_dict(orient="records")[:6]
            out["variability"] = gaia.variability(int(source_id))
        else:
            out["neighbours_10arcsec"] = cone[["source_id", "sep_arcsec", "phot_g_mean_mag"]].round(3).to_dict(orient="records")[:6]
    except Exception as e:  # noqa: BLE001
        out["gaia_error"] = str(e)[:120]
    return out


def wise_bits(ra, dec):
    try:
        df, prov = neowise.lightcurve(ra, dec)
    except Exception as e:  # noqa: BLE001
        return {"neowise_error": str(e)[:120]}
    if df.empty:
        return {"neowise_status": prov.status}
    good = df[df.flag == ""]
    out = {"neowise_status": prov.status, "n_visits": int(len(good)) // 2}
    for b in ("W1", "W2"):
        g = good[good.band == b]
        if len(g):
            out[f"{b.lower()}_median"] = float(g.mag.median())
            out[f"{b.lower()}_range"] = float(g.mag.max() - g.mag.min())
            out[f"{b.lower()}_first"] = float(g.mag.iloc[0])
            out[f"{b.lower()}_last"] = float(g.mag.iloc[-1])
    wc = wise_color(df)
    out["w1_w2_median"] = wc.get("w1_minus_w2_median", (out.get("w1_median") or np.nan) - (out.get("w2_median") or np.nan))
    out["w1_w2_range"] = wc.get("w1_minus_w2_range")
    out["w1_w2_corr"] = wc.get("corr_W1_vs_color")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verdicts", default="rcb_like,eclipse_like")
    ap.add_argument("--scored", default="scored.csv")
    a = ap.parse_args()
    sc = pd.read_csv(here / a.scored)
    pick = sc[sc.verdict.isin(a.verdicts.split(","))].copy()
    print(len(pick), "to vet", flush=True)
    rows = []
    for _, s in pick.iterrows():
        f = out_dir / f"{s.id}.json"
        if f.exists():
            rows.append(json.loads(f.read_text()))
            continue
        rec = {"id": s.id, "ra": float(s.ra), "dec": float(s.dec), "verdict": s.verdict}
        rec["vsx"] = vsx(s.ra, s.dec)
        rec["simbad"] = simbad(s.ra, s.dec)
        rec["rcb_catalogues"] = rcb_catalogues(s.ra, s.dec)
        rec.update(gaia_bits(s.ra, s.dec, s.get("source_id")))
        rec.update(wise_bits(s.ra, s.dec))
        f.write_text(json.dumps(rec, indent=1, default=str))
        rows.append(rec)
        vt = ",".join(f"{v.get('Name')}[{v.get('VariabilityType')}]" for v in rec["vsx"] if isinstance(v, dict) and v.get("Name"))
        st = ",".join(f"{v.get('main_id')}({v.get('otype')},{v.get('nref')})" for v in rec["simbad"] if "main_id" in v)
        print(s.id, s.verdict, f"depth {s.depth:.2f}" if pd.notna(s.depth) else "", "| VSX:", vt or "-", "| SIMBAD:", st or "-",
              "| RCB cats:", rec["rcb_catalogues"] or "-", "| W1-W2:", rec.get("w1_w2_median"), flush=True)
    flat = []
    for r in rows:
        flat.append({
            "id": r["id"], "verdict": r["verdict"],
            "vsx_names": ";".join(f"{v.get('Name')} [{v.get('VariabilityType')}]" for v in r["vsx"] if isinstance(v, dict) and v.get("Name")),
            "simbad_2026": ";".join(f"{v.get('main_id')} ({v.get('otype')}, {v.get('nref')} refs)" for v in r["simbad"] if "main_id" in v),
            "rcb_catalogues": ";".join(r["rcb_catalogues"]),
            "n_neighbours_10arcsec": len(r.get("neighbours_10arcsec", [])),
            "brightest_neighbour_flux_ratio": max([n.get("flux_ratio_G", 0) or 0 for n in r.get("neighbours_10arcsec", [])], default=None),
            "gaia_class": (r.get("variability") or {}).get("classifier", {}).get("best_class_name") if isinstance((r.get("variability") or {}).get("classifier"), dict) else None,
            "w1_w2_median": r.get("w1_w2_median"), "w1_range": r.get("w1_range"), "w1_first": r.get("w1_first"), "w1_last": r.get("w1_last"),
        })
    pd.DataFrame(flat).to_csv(here / "vetted.csv", index=False)
    print("wrote", here / "vetted.csv")


if __name__ == "__main__":
    main()
