"""r12: claim 3 redone with the REAL NEOWISE visit dates. hunt_h0008_efficiency.py assumes a target is seen when the Sun's
ecliptic longitude is 90 +- 1 deg from it; r11 shows that from 2015 on one of the two yearly visits drifts to |dl| = 105-113
(about three weeks later/earlier), so half of all predicted epochs are wrong. Here each reference event takes the visit
dates of the nearest of the 661 clean event stars (their full sky3lens light curves), shifted by the ecliptic-longitude
difference / 0.9856 deg per day; the shift is validated leave-one-out. Then: A at each real visit (first and last visits
excluded, as in the pipeline: 'edge' events are dropped), catchable = A >= 1.6 and mag <= 16 (the investigators' cut), and
recovered = a clean event within 3" and max(2 tE, 30 d). Output: per-catalogue and per-region efficiencies, r12_eff.csv."""
import glob, os
import numpy as np, pandas as pd
import astropy.units as u
from astropy.coordinates import GeocentricTrueEcliptic, SkyCoord
HERE = os.path.dirname(os.path.abspath(__file__))
from oddsky.analysis.lensing import magnification
c = pd.read_csv(f"{HERE}/../../work/sky3_classified.csv", dtype={"g_source_id": str})
LC = os.path.expanduser("~/oddsky-runs/h0008/lightcurves")
vis = {}
for pix, grp in c.groupby("pixel"):
    lc = pd.read_parquet(f"{LC}/pixel={pix}.parquet")
    for cn in grp.allwise_cntr:
        vis[int(cn)] = np.sort(lc[lc.allwise_cntr == cn].t.to_numpy())
c = c[c.allwise_cntr.map(lambda x: len(vis.get(int(x), [])) >= 10)].reset_index(drop=True)
tc = SkyCoord(c.ra.values * u.deg, c.dec.values * u.deg)
tl = tc.transform_to(GeocentricTrueEcliptic()).lon.deg


def predict(ra, dec, exclude=None):
    """Visit dates at (ra, dec) from the nearest template star, shifted by the ecliptic-longitude difference."""
    p = SkyCoord(ra * u.deg, dec * u.deg)
    s = tc.separation(p).deg
    if exclude is not None:
        s[exclude] = 999
    j = int(np.argmin(s))
    dlam = ((p.transform_to(GeocentricTrueEcliptic()).lon.deg - tl[j] + 180) % 360) - 180
    return vis[int(c.allwise_cntr.iloc[j])] + dlam / 0.9856, s[j]


# leave-one-out validation: predicted vs real visit dates for each template
err = []
for i in range(len(c)):
    pv, sep = predict(c.ra.iloc[i], c.dec.iloc[i], exclude=i)
    real = vis[int(c.allwise_cntr.iloc[i])]
    d = np.array([np.min(np.abs(pv - r)) for r in real])
    err.append((sep, np.median(d), np.mean(d < 3)))
err = np.array(err)
near = err[:, 0] < 5
print(f"LOO (template < 5 deg away, n={near.sum()}): median |dt| {np.median(err[near, 1]):.2f} d; share of real visits matched within 3 d: {np.mean(err[near, 2]):.3f}")

ref = pd.read_csv(f"{HERE}/../../ext/reference_lenses.csv")
z = pd.read_csv(f"{HERE}/r5_zhai_full.csv")
z = pd.DataFrame({"name": z.id, "ra": z.ra, "dec": z.dec, "t0_mjd": z.t0_mjd, "tE": z.tE, "u0": z.u0, "mag": np.nan, "source": "ZTF (Zhai+2024 full)"})
R = pd.concat([ref[ref.source.isin(["KMTNet", "OGLE", "Gaia DR3", "OGLE GVS (Mroz+2020)"])], z], ignore_index=True)
R = R[R.t0_mjd.between(56600, 60531) & (R.tE > 0) & R.u0.notna()].drop_duplicates(["name", "source"]).reset_index(drop=True)
rc = SkyCoord(R.ra.values * u.deg, R.dec.values * u.deg)
rows = []
for i, r in R.iterrows():
    pv, sep = predict(r.ra, r.dec)
    inner = pv[1:-1]
    amax = float(magnification(np.hypot((inner - r.t0_mjd) / r.tE, r.u0)).max()) if len(inner) else 1.0
    s3 = tc.separation(rc[i]).arcsec
    hit = (s3 < 3) & (np.abs(c.t.values - r.t0_mjd) <= max(2 * r.tE, 30))
    rows.append({"name": r["name"], "source": r.source, "ra": r.ra, "dec": r.dec, "t0": r.t0_mjd, "tE": r.tE, "u0": r.u0, "mag": r.mag,
                 "template_sep_deg": round(sep, 2), "A_real_visits": round(amax, 3), "recovered": bool(hit.any())})
e = pd.DataFrame(rows)
g = SkyCoord(e.ra.values * u.deg, e.dec.values * u.deg).galactic
e["l"], e["b"] = ((g.l.deg + 180) % 360) - 180, g.b.deg
e["inner_bulge"] = (e.l.abs() < 10) & (e.b.abs() < 5)
e["catchable_v2"] = (e.A_real_visits >= 1.6) & ((e.mag <= 16) | e.mag.isna())
# the investigators' own catchable flags, for comparison
old = pd.concat([pd.read_csv(f"{HERE}/../../work/eff_{k}.csv", dtype={"name": str}).assign(cat=k) for k in ("kmt", "ogle", "gaia")])
old["name"] = np.where(old.cat == "gaia", "Gaia DR3 " + old.name.astype(str), old.name)
e = e.merge(old[["name", "catchable", "A_at_neowise"]], on="name", how="left")
e.to_csv(f"{HERE}/r12_eff.csv", index=False)
pd.set_option("display.width", 200)
for src, d in e.groupby("source"):
    cv = d[d.catchable_v2]
    co = d[d.catchable == True]  # noqa: E712
    print(f"{src}: n {len(d)} | old catchable {len(co)} rec {int(co.recovered.sum())} | NEW catchable {len(cv)} rec {int(cv.recovered.sum())}"
          f" | recovered total {int(d.recovered.sum())}, of which NEW-catchable {int((d.recovered & d.catchable_v2).sum())}")
for lab, d in (("inner bulge |l|<10,|b|<5", e[e.inner_bulge]), ("elsewhere", e[~e.inner_bulge])):
    cv = d[d.catchable_v2 & d.mag.notna()]
    print(f"{lab} (KMT/OGLE/GVS/GaiaDR3 with mag <= 16): catchable {len(cv)} recovered {int(cv.recovered.sum())} ({cv.recovered.mean():.3f})")
zz = e[e.source.str.startswith("ZTF")]
print("Zhai full list: A>=1.6 at a real visit:", int((zz.A_real_visits >= 1.6).sum()), "| recovered:", int(zz.recovered.sum()),
      "| recovered among A>=1.6:", int((zz.recovered & (zz.A_real_visits >= 1.6)).sum()))
print(e[e.recovered][["name", "source", "mag", "A_real_visits", "A_at_neowise", "catchable", "catchable_v2", "b"]].to_string(index=False))
