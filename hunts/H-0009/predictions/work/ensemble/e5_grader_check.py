"""e5: end-to-end check of the grader's scoring path on synthetic "DR4" data (no network).
Run from the repo root:  uv run python -I hunts/H-0009/predictions/work/ensemble/e5_grader_check.py

Every testable source gets flat G/BP/RP photometry at the GOST transit times (catalogue magnitudes, realistic noise). Into ten
chosen events an achromatic x1.6 brightening is injected for |t - t_event| <= 30 d, and into two a chromatic one (BP up more
than RP). The grader's `fetch` is replaced by the synthetic set and `run_grade` runs unchanged, so the counting, the colour
verdicts, the falsification test and the lens-fraction posterior are all exercised. Expected: 12 passes, 10 achromatic or
undetermined, 2 chromatic or undetermined, no pass among the flat events. A last case checks that a single bright transit
listed twice still counts once (FAIL). Outputs go to work/ensemble/grade_synthetic*.
"""
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
PRED = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, PRED)
import dr4_ensemble_grade as G  # noqa: E402

rng = np.random.default_rng(5)
smp = pd.read_csv(G.SAMPLE, dtype={"source_id": str, "alt_source_id": str})
test = smp[smp.status == "testable"].reset_index(drop=True)
gs = pd.read_csv(os.path.join(HERE, "gost_sample.csv"))
inject = set(test.designation.iloc[[0, 3, 7, 10, 15, 20, 25, 30, 35, 40]])
chrom = set(test.designation.iloc[[44, 46]])


def synth(r):
    T = np.sort(gs[gs.designation == r.designation].mjd.to_numpy())
    win = np.abs(T - r.t_event_mjd) <= 30
    rows = []
    for band, m0, sig in (("G", r.G, 0.01), ("BP", r.BP, 0.03), ("RP", r.RP, 0.015)):
        if not np.isfinite(m0):
            continue
        dm = np.zeros(len(T))
        if r.designation in inject:
            dm[win] = -2.5 * np.log10(1.6)
        if r.designation in chrom:
            dm[win] = {"G": -0.5, "BP": -0.8, "RP": -0.3}[band]
        mag = m0 + dm + rng.normal(0, sig, len(T))
        rows.append(pd.DataFrame(dict(t_mjd=T + 0.001 * (band != "G"), mag=mag, err=sig, band=band, survey="GAIA", flag="",
                                      camera=[f"{r.source_id}-{i}" for i in range(len(T))])))
    return pd.concat(rows, ignore_index=True)


SYN = {r.source_id: synth(r) for r in test.itertuples()}


def fake_fetch(ids, releases):
    got = {s: SYN[s] for s in ids if s in SYN}
    return got, {"releases": [{"release": releases[0], "ok": True, "n": len(got), "error": ""}],
                 "source_release": {int(s): releases[0] for s in got}}


G.fetch = fake_fetch
summ = G.run_grade(("Gaia synthetic",))
out = pd.read_csv(os.path.join(G.WORK, "grade_synthetic.csv"))
p = set(out.designation[out.status == "pass"])
print("\ninjected passed:", len(p & inject), "/", len(inject), "; chromatic injections passed:", len(p & chrom), "/", len(chrom),
      "; flat events passed:", len(p - inject - chrom))
print(out[out.designation.isin(inject | chrom)][["designation", "status", "n_win", "n_up", "r_max", "colour", "D", "e_D"]].to_string(index=False))
ok = p == (inject | chrom) and not (out[out.designation.isin(inject)].colour == "chromatic").any() \
    and not (out[out.designation.isin(chrom)].colour == "achromatic").any()

# duplicate rows: one bright transit in the window must FAIL, also when that transit is listed twice (referee R3)
r0 = test.iloc[5]
df = SYN[r0.source_id].copy()
gw = df[(df.band == "G") & (np.abs(df.t_mjd - r0.t_event_mjd) <= 30)].index
df.loc[gw, "mag"] = r0.G
df.loc[gw[0], "mag"] = r0.G - 1.0
one = G.grade_series(df, r0.t_event_mjd)["status"]
dup = G.grade_series(pd.concat([df, df.loc[[gw[0]]]], ignore_index=True), r0.t_event_mjd)["status"]
print(f"\nduplicate-row case ({r0.designation}): one bright transit -> {one}; the same transit listed twice -> {dup}")
ok = ok and one == "fail" and dup == "fail"
print("\nsynthetic check:", "PASS" if ok else "FAIL")
