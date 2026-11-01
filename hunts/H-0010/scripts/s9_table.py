"""s9: one table, one row per source: every measurement from s1-s8 plus two context columns, then the verdicts
(work/verdicts.csv, written by hand after inspecting every light curve; see the README).
Context:
  * sun_elong_peak: the Sun's angular distance from the source at the Gaia peak. Ground surveys observe the bulge from about
    February to October; with the Sun closer than ~60 deg nobody on the ground observes, but Gaia (45 deg solar aspect) does.
  * atlas_testable: peak after 2015-08-01, dec > -45, peak G < 19, Sun > 50 deg away (ATLAS could check it; nothing queued).
  * ogle_15arcmin / kmt_15arcmin: OGLE EWS events (2014-2017) and KMTNet events (2016-2017) within 15' of the source, a proxy
    for whether the field was monitored at all.
Run from the repo root: uv run python -I hunts/H-0010/scripts/s9_table.py
Writes hunts/H-0010/work/gaia_ml_unpub.csv and hunts/H-0010/work/gaia_ml_unpub_list.csv (the bare re-derived list)."""
import os
import sys

import astropy.units as u
import numpy as np
import pandas as pd
from astropy.coordinates import SkyCoord, get_sun
from astropy.time import Time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import CASES, DATA, WORK, short_name, targets  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def main():
    T = targets()
    T[["source_id", "best_class_score", "phot_g_mean_mag", "l", "b", "ra", "dec"]].to_csv(
        os.path.join(WORK, "gaia_ml_unpub_list.csv"), index=False)
    T["name"] = [short_name(a, d) for a, d in zip(T.ra, T.dec, strict=True)]
    T["case"] = T.source_id.map(CASES).fillna("")
    out = T.copy()
    for f in ("lc_metrics", "neighbours_summary", "allwise", "neowise_events", "neowise_event", "xmatch", "tns", "ztf_repeats", "dr3_cuts", "mroz2019"):
        p = os.path.join(DATA, f"{f}.csv")
        if os.path.exists(p):
            d = pd.read_csv(p, dtype={"source_id": str, "allwise_cntr": str})
            d = d[[c for c in d.columns if c == "source_id" or c not in out.columns]]
            out = out.merge(d, on="source_id", how="left")
    # s3's other_bright_max_dG took the weakest secondary episode (sign slip); recompute the strongest from bright_eps
    def second(e):
        v = sorted(float(x.split(":")[1]) for x in str(e).split(";") if x.count(":") == 2)
        return v[1] if len(v) > 1 else 0.0
    out["other_bright_max_dG"] = out.bright_eps.map(second)
    ap = pd.read_csv(os.path.join(DATA, "ap.csv"), dtype={"source_id": str})
    ap = ap[["source_id", "mh_gspphot", "spectraltype_esphs", "evolstage_flame", "radius_gspphot"]]
    out = out.merge(ap, on="source_id", how="left")
    # Sun elongation at the Gaia peak (or the lens t0 when no episode was found)
    tp = out.t_peak.where(np.isfinite(out.t_peak), out.static_t0)
    sun = get_sun(Time(tp.values, format="mjd"))
    sun = SkyCoord(sun.ra, sun.dec, frame="icrs")  # geocentric Sun direction; parallax of the Sun irrelevant here
    src = SkyCoord(out.ra.values * u.deg, out.dec.values * u.deg)
    out["sun_elong_peak"] = np.round(src.separation(sun).deg, 0)
    # survey coverage proxy
    ref = pd.read_csv(os.path.join(REPO, "hunts/H-0008/ext/reference_lenses.csv"))
    ogle = ref[(ref.source == "OGLE") & ref.name.str.match(r"OGLE-201[4-7]")]
    kmt = ref[(ref.source == "KMTNet") & ref.name.str.match(r"KMT-201[67]")]
    for lab, cat in (("ogle_15arcmin", ogle), ("kmt_15arcmin", kmt)):
        c = SkyCoord(cat.ra.values * u.deg, cat.dec.values * u.deg)
        out[lab] = [int((src[i].separation(c).arcmin < 15).sum()) for i in range(len(out))]
    # ATLAS (no tasks queued here): could it test the event? Science operations from ~2015 Aug (MJD 57235), Hawaii units reach
    # dec ~ -45, limit ~ 19 mag, and it does not observe within ~50 deg of the Sun.
    peakmag = out.phot_g_mean_mag - 2.5 * np.log10(out.A_obs_G.fillna(1.0))
    out["atlas_testable"] = (tp > 57235) & (out.dec > -45) & (peakmag < 19.0) & (out.sun_elong_peak > 50)
    vp = os.path.join(WORK, "verdicts.csv")
    if os.path.exists(vp):
        v = pd.read_csv(vp, dtype={"source_id": str})
        out = out.merge(v, on="source_id", how="left")
    first = ["source_id", "name", "case", "verdict", "p_lens", "known_as", "what_instead", "t0_robust", "tE_range", "peak_amp",
             "achromatic", "note"]
    first = [c for c in first if c in out.columns]
    out = out[first + [c for c in out.columns if c not in first]]
    out.to_csv(os.path.join(WORK, "gaia_ml_unpub.csv"), index=False)
    cols = ["source_id", "name", "l", "b", "phot_g_mean_mag", "t_peak_date", "A_obs_G", "ep_n_dates", "sun_elong_peak",
            "ogle_15arcmin", "kmt_15arcmin"]
    print(out[[c for c in cols if c in out.columns]].to_string())


if __name__ == "__main__":
    main()
