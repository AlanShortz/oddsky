"""Hunt H-0004, step 3: score every fetched light curve for an R CrB-like decline, an eclipse, or nothing.

Reads hunts/H-0004/lc/<id>.parquet (ZTF + ATLAS), writes hunts/H-0004/scored.csv with the features
from oddsky.analysis.fades plus Gaia context from candidates.csv, and a verdict per star. Run on the
calibration set too (--file calibration.csv --out scored_calibration.csv) to measure recall on the
known R CrB stars before believing any threshold.

  .venv/bin/python scripts/hunt_h0004_score.py [--file candidates.csv] [--out scored.csv]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from hunt_h0004_fetch import load_star  # noqa: E402

from oddsky.analysis import fades

sys.path.insert(0, str(Path(__file__).parent))
here = Path("hunts/H-0004")
lc_dir = here / "lc"

FEATURES = ["band", "n_nights", "n_limits", "span_days", "bright", "max_frac", "scatter_at_max", "faintest", "amplitude",
            "decline_rate_mag_per_day", "n_events", "depth", "depth_censored", "ingress_days", "egress_days", "asymmetry",
            "asymmetry_is_lower_bound", "ongoing", "interval_cv", "ls_power", "ls_period", "fold_power", "n_single_night_drops"]


def score_one(cid: str) -> dict:
    rec = {"id": cid}
    df, provs = load_star(cid)
    if not provs:
        rec["verdict"] = "not_fetched"
        return rec
    rec["surveys"] = ",".join(sorted(df.survey.unique())) if not df.empty else ""
    rec["n_ztf"] = int(((df.survey == "ZTF") & (df.flag == "")).sum()) if not df.empty else 0
    rec["n_atlas"] = int(((df.survey == "ATLAS") & (df.flag == "")).sum()) if not df.empty else 0
    rec["fetch_status"] = ";".join(f"{k}:{v.get('status')}" for k, v in provs.items())
    if df.empty or rec["n_ztf"] + rec["n_atlas"] < 30:
        rec["verdict"] = "too_few_points"
        return rec
    f = fades.rcb_features(df)
    for k in FEATURES:
        rec[k] = f.get(k)
    rec["verdict"] = fades.classify_fade(f)
    rec["events_json"] = json.dumps(f.get("events", [])[:3])
    # second opinion from the other survey, when both cover the deepest event
    if rec["n_ztf"] >= 30 and rec["n_atlas"] >= 30 and f.get("events"):
        other = "ZTF_r" if f["band"].startswith("ATLAS") else "ATLAS_o"
        g = fades.rcb_features(df, band=other)
        rec["other_band"] = other
        rec["other_depth"] = g.get("depth")
        rec["other_verdict"] = fades.classify_fade(g) if "error" not in g else "no_data"
        if g.get("depth") is not None and f.get("depth"):
            rec["cross_confirmed"] = bool(abs(g["depth"] - f["depth"]) < max(0.6, 0.3 * f["depth"]))
    # colour inside the deepest fade
    pairs = [("ZTF_g", "ZTF_r"), ("ATLAS_c", "ATLAS_o")]
    for blue, red in pairs:
        col = fades.colour_during_fade(df, blue, red, f.get("events", []))
        if col:
            rec["colour_bands"] = col["bands"]
            rec["delta_colour"] = col["delta_colour"]
            rec["dcolour_ddepth"] = col["dcolour_ddepth"]
            break
    if rec["verdict"] == "eclipse_like":
        rec["disk_candidate"] = fades.disk_eclipse_features(df).get("candidate")
    return rec


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default="candidates.csv")
    ap.add_argument("--out", default="scored.csv")
    a = ap.parse_args()
    cand = pd.read_csv(here / a.file)
    recs = [score_one(cid) for cid in cand.id]
    sc = pd.DataFrame(recs)
    keep = [c for c in ("id", "pool", "ra", "dec", "glon", "glat", "name", "cls", "w1", "w2", "w3", "w4", "j", "k", "k24_lc_pri", "k24_col_pri",
                        "k24_class", "simbad_main_id", "simbad_otype", "source_id", "gaia_g", "bp_rp", "parallax", "poe", "ruwe", "abs_g",
                        "n_gaia_3arcsec", "ztf_footprint") if c in cand]
    sc = cand[keep].merge(sc, on="id", how="left")
    # luminosity sanity: an R CrB star is a supergiant (M_G brighter than about -1). A good parallax that says
    # dwarf rules the class out; no parallax is neutral.
    sc["abs_g_ok"] = ~((sc.get("poe", pd.Series(np.nan, index=sc.index)) > 5) & (sc.get("abs_g", pd.Series(np.nan, index=sc.index)) > -1))
    sc["rcb_pick"] = sc.verdict.eq("rcb_like") & sc.abs_g_ok
    sc["eclipse_pick"] = sc.verdict.eq("eclipse_like")
    order = {"rcb_like": 0, "eclipse_like": 1, "unclassified": 2, "mira_like": 3, "slow_variable": 4, "erratic": 5, "artifact": 6, "no_event": 7, "too_few_points": 8, "not_fetched": 9}
    sc = sc.sort_values(["verdict", "depth"], key=lambda s: s.map(order) if s.name == "verdict" else -s.fillna(0)).reset_index(drop=True)
    sc.to_csv(here / a.out, index=False)
    print(sc.verdict.value_counts().to_string())
    print("rcb picks:", int(sc.rcb_pick.sum()), "eclipse picks:", int(sc.eclipse_pick.sum()))
    cols = ["id", "simbad_main_id", "verdict", "band", "depth", "decline_rate_mag_per_day", "asymmetry", "max_frac", "ls_power", "ongoing", "cross_confirmed"]
    print(sc[sc.rcb_pick | sc.eclipse_pick][[c for c in cols if c in sc]].head(40).to_string())


if __name__ == "__main__":
    main()
