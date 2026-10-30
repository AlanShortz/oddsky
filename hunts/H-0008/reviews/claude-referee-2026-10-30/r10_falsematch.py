"""r10: claim 1 (60 known lenses recovered blind). (a) Re-implement the investigators' match (6", |t - t0| <= max(2 tE, 30 d),
100 d for alerts without tE, 2018.2-2021.5 for position-only ZTF lists) and reproduce the count; (b) chance-coincidence rate by
moving every one of the 661 events 1-3' in a random direction (200 draws; keeps the local reference density) and by shifting
the event times by +-1, 2, 3 yr (keeps the NEOWISE season); (c) for matches with a reference point-lens fit, the predicted
magnification at the NEOWISE visit vs the observed W1 brightening (a NEOWISE amplitude far above prediction is suspect; below is blending).
Also matches against the full Zhai+2024 list (r5_zhai_full.csv), which the investigators did not have."""
import os, sys
import numpy as np, pandas as pd
import astropy.units as u
from astropy.coordinates import SkyCoord
HERE = os.path.dirname(os.path.abspath(__file__))
from oddsky.analysis.lensing import magnification
ref = pd.read_csv(f"{HERE}/../../ext/reference_lenses.csv")
z = pd.read_csv(f"{HERE}/r5_zhai_full.csv")
z = pd.DataFrame({"name": z.id, "ra": z.ra, "dec": z.dec, "t0_mjd": z.t0_mjd, "tE": z.tE, "u0": z.u0, "mag": np.nan, "source": "ZTF (Zhai+2024 full)"})
ref2 = pd.concat([ref[ref.source != "ZTF (Zhai+2024)"], z], ignore_index=True)
c = pd.read_csv(f"{HERE}/../../work/sky3_classified.csv", dtype={"g_source_id": str})
rng = np.random.default_rng(42)


def match(ra, dec, t, R):
    rc = SkyCoord(R.ra.values * u.deg, R.dec.values * u.deg)
    cc = SkyCoord(ra * u.deg, dec * u.deg)
    win = np.where(R.tE.notna(), np.maximum(2 * R.tE.fillna(0), 30), 100)
    not0 = R.t0_mjd.isna().values
    i1, i2, sep, _ = cc.search_around_sky(rc, 6 * u.arcsec)  # i1 -> event index, i2 -> ref index
    i1, i2 = i2, i1
    dt = np.abs(R.t0_mjd.values[i2] - t[i1])
    ok = (dt <= win[i2]) | (not0[i2] & (t[i1] >= 58180) & (t[i1] <= 59380))
    return i1[ok], i2[ok], sep.arcsec[ok]


ra, dec, t = c.ra.values, c.dec.values, c.t.values
for name, R in (("investigators' reference", ref), ("with full Zhai+2024", ref2)):
    i1, i2, s = match(ra, dec, t, R)
    print(f"{name}: events matched {len(set(i1))}")
i1, i2, s = match(ra, dec, t, ref)
base = len(set(i1))
# (b) position shifts
counts = []
for _ in range(200):
    r_ = np.radians(rng.uniform(1, 3, len(c)) / 60); th = rng.uniform(0, 2 * np.pi, len(c))
    d2 = dec + np.degrees(r_ * np.cos(th)); r2 = ra + np.degrees(r_ * np.sin(th)) / np.cos(np.radians(dec))
    counts.append(len(set(match(r2, d2, t, ref)[0])))
counts = np.array(counts)
print(f"position shifts 1-3': mean {counts.mean():.3f} chance matches per 661 (max {counts.max()}, P(>=1) {np.mean(counts >= 1):.2f})")
for dy in (-3, -2, -1, 1, 2, 3):
    n = len(set(match(ra, dec, t + dy * 365.25, ref)[0]))
    print(f"time shift {dy:+d} yr: {n} matches")
# (c) predicted magnification at the NEOWISE visit
rows = []
for a, b, sp in zip(i1, i2, s):
    r = ref.iloc[b]
    ap = float(magnification(np.hypot((t[a] - r.t0_mjd) / r.tE, r.u0))) if (r.tE == r.tE and r.u0 == r.u0) else np.nan
    rows.append({"designation": c.designation.iloc[a], "ref": r["name"], "source": r.source, "sep": round(sp, 2),
                 "dt": round(t[a] - r.t0_mjd, 1) if r.t0_mjd == r.t0_mjd else np.nan, "tE": r.tE, "u0": r.u0,
                 "A_pred": round(ap, 2), "A_obs_W1": round(10 ** (-0.4 * c.dw1.iloc[a]), 2), "b": round(c.b.iloc[a], 2)})
m = pd.DataFrame(rows).sort_values("sep")
m.to_csv(f"{HERE}/r10_matches.csv", index=False)
pd.set_option("display.width", 220)
print(m.to_string(index=False))
f = m.dropna(subset=["A_pred"])
print("with a reference fit:", f.designation.nunique(), "| A_obs > 1.5 A_pred (suspect):", f[f.A_obs_W1 > 1.5 * f.A_pred].designation.nunique(),
      "| A_obs < 0.5 (A_pred-1)+1 (diluted):", f[(f.A_obs_W1 - 1) < 0.5 * (f.A_pred - 1)].designation.nunique())
print("sep > 2\":", m[m.sep > 2].designation.nunique())
