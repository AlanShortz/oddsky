"""H-0008 step 2: the sky3lens event catalogue -> vetted microlensing candidates, matched against KMTNet.

1. Read every pixel's events (runs/sky3lens/events) and keep isolated, achromatic brightenings that are not artifacts:
   not at the first or last visit; artifact-flagged share of the event visit <= 0.2 above the star's own typical share;
   chi-square ratio < 3; stellar colour (median W1 - W2 < 0.5, which drops most quasar flares).
2. Positions from AllWISE (IRSA TAP by cntr), Galactic coordinates, then known lenses (KMTNet, OGLE, Gaia DR3, Gaia alerts;
   hunt_h0008_reference.py): within 6" (WISE positions shift in crowded fields) and t0 within max(2 tE, 30 d) of the visit
   (100 d for alerts without tE).
Also reads the sky4long pass (H-0009, neowise_lens.py --mode long): every event there is a brightening, and a block of visits
t_first..t_last matches a known lens whose t0 falls within the window of any of them.
usage: hunt_h0008_events.py EVENTS_DIR REFERENCE_CSV OUT_PREFIX
"""

import glob
import io
import sys

import astropy.units as u
import numpy as np
import pandas as pd
import requests
from astropy.coordinates import SkyCoord

# skip empty per-pixel tables: concatenating them turns the int64 cntr into float64 (19-digit ids lose precision)
frames = [pd.read_parquet(f) for f in glob.glob(f"{sys.argv[1]}/*.parquet")]
ev = pd.concat([d for d in frames if len(d)], ignore_index=True)
ev["edge"] = ev["edge"].astype(bool)
if "kind" not in ev:  # sky4long
    ev["kind"] = "brighten"
if "t_first" not in ev:
    ev["t_first"] = ev["t_last"] = ev["t"]
print("events (all kinds):", len(ev), ev.groupby(["kind", "edge"]).size().to_dict())
b = ev[(ev.kind == "brighten") & ~ev.edge].copy()
b["w1w2"] = b.w1_med - b.w2_med
b["clean"] = (b.ccfrac_event <= b.ccfrac_other + 0.2) & (b.rchi_ratio < 3) & (b.w1w2 < 0.5)
print("isolated brightenings:", len(b), "clean:", int(b.clean.sum()))
c = b[b.clean].copy()
pos = []
for i in range(0, len(c), 400):
    ids = ",".join(str(int(x)) for x in c.allwise_cntr.iloc[i:i + 400])
    q = f"SELECT cntr, designation, ra, dec, w1mpro, w2mpro, w3mpro, w4mpro, j_m_2mass, k_m_2mass, ext_flg FROM allwise_p3as_psd WHERE cntr IN ({ids})"
    r = requests.post("https://irsa.ipac.caltech.edu/TAP/sync", data={"QUERY": q, "FORMAT": "csv"}, timeout=600)
    pos.append(pd.read_csv(io.StringIO(r.text)))
c = c.merge(pd.concat(pos), left_on="allwise_cntr", right_on="cntr", how="left")
missing = c.ra.isna()
if missing.any():
    print("no AllWISE position for", int(missing.sum()), "events:", c.allwise_cntr[missing].tolist()[:10])
c = c[~missing].reset_index(drop=True)
g = SkyCoord(c.ra.to_numpy() * u.deg, c.dec.to_numpy() * u.deg).galactic
c["l"], c["b"] = g.l.deg, g.b.deg
k = pd.read_csv(sys.argv[2])  # reference_lenses.csv (hunt_h0008_reference.py)
kc = SkyCoord(k.ra.to_numpy() * u.deg, k.dec.to_numpy() * u.deg)
win = np.where(k.tE.notna(), np.maximum(2 * k.tE.fillna(0), 30), 100)
not0 = k.t0_mjd.isna().to_numpy()  # ZTF DR5 catalogues give positions only: match if the visit falls in 2018 Mar - 2021 Jun
c["known_lens"] = ""
for j in range(len(c)):
    sep = kc.separation(SkyCoord(c.ra.iloc[j] * u.deg, c.dec.iloc[j] * u.deg)).arcsec
    t0k = k.t0_mjd.to_numpy()
    intime = (t0k >= c.t_first.iloc[j] - win) & (t0k <= c.t_last.iloc[j] + win)
    ok = (sep < 6) & (intime | (not0 & (58180 <= c.t.iloc[j] <= 59380)))
    if ok.any():
        kk = k[ok].assign(sep=sep[ok]).sort_values("sep")
        c.iloc[j, c.columns.get_loc("known_lens")] = "; ".join(
            f"{r.name} ({r.source}, {r.sep:.1f}\"" + (f", t0 {r.t0_mjd:.0f})" if r.t0_mjd == r.t0_mjd else ")") for r in kk.itertuples())
c.to_csv(f"{sys.argv[3]}_clean.csv", index=False)
b.to_csv(f"{sys.argv[3]}_brighten.csv", index=False)
print("clean candidates:", len(c), "| matched to a known lens:", int((c.known_lens != "").sum()), "| |b| < 10:", int((c.b.abs() < 10).sum()))
