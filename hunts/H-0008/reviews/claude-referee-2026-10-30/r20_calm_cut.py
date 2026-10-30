"""r20: the 'every other visit calm' cut vs long events. For each Zhai+2024 / KMT / OGLE event with a fit, predicted (unblended)
magnification at every real NEOWISE visit (r12's template method). Classify what the sky3lens detector would do with an
unblended, noise-free source: 'pass' (1-3 consecutive visits >= 0.2 mag, all others <= 0.15), 'fail_calm' (some other visit
in 0.15-0.2 mag, or > 3 / non-consecutive hits), 'below' (no visit >= 0.2 mag). Then the failure share vs tE."""
import os, sys
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
sys.argv = [sys.argv[0]]
import importlib.util
spec = importlib.util.spec_from_file_location("r12", f"{HERE}/r12_efficiency.py")
# reuse the template predictor without re-running r12's report: copy the minimal pieces
import astropy.units as u
from astropy.coordinates import GeocentricTrueEcliptic, SkyCoord
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
e = pd.read_csv(f"{HERE}/r12_eff.csv")
e = e[e.source.isin(["KMTNet", "OGLE", "ZTF (Zhai+2024 full)", "Gaia DR3", "OGLE GVS (Mroz+2020)"])]
ec = SkyCoord(e.ra.values * u.deg, e.dec.values * u.deg)
idx, _, _ = ec.match_to_catalog_sky(tc)
el = ec.transform_to(GeocentricTrueEcliptic()).lon.deg
out = []
for i, r in enumerate(e.itertuples()):
    j = idx[i]
    pv = vis[int(c.allwise_cntr.iloc[j])] + (((el[i] - tl[j] + 180) % 360) - 180) / 0.9856
    dm = 2.5 * np.log10(magnification(np.hypot((pv - r.t0) / r.tE, r.u0)))
    hit = dm >= 0.2
    calm = dm <= 0.15
    k = np.where(hit)[0]
    if not hit.any():
        st = "below"
    elif hit.sum() <= 3 and (k[-1] - k[0] + 1 == len(k)) and (hit | calm).all() and k[0] > 0 and k[-1] < len(pv) - 1:
        st = "pass"
    else:
        st = "fail_calm_or_edge"
    out.append(st)
e["detector"] = out
e["tE_bin"] = pd.cut(e.tE, [0, 20, 40, 70, 100, 150, 2000])
t = e[e.detector != "below"].groupby("tE_bin", observed=True).detector.apply(lambda s: (s == "fail_calm_or_edge").mean()).round(3)
n = e[e.detector != "below"].groupby("tE_bin", observed=True).size()
print("share of events with a >= 0.2 mag NEOWISE visit that the 'others calm' / edge rule would reject (unblended, noise-free):")
print(pd.DataFrame({"n": n, "rejected": t}).to_string())
z = e[e.source.str.startswith("ZTF")]
print(z[z.name.isin(["ZTF19abagvae", "ZTF21abmnkml", "ZTF21abrgqfr", "ZTF21aawqeqn", "ZTF21acqomnw", "ZTF18absrimp"])][["name", "tE", "A_real_visits", "detector"]].to_string(index=False))
e.to_csv(f"{HERE}/r20_calm_cut.csv", index=False)
