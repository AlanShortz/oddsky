"""Rediscovery test on M33: the Miras of Yuan+2017 (ground-based I-band monitoring, periods and amplitudes published) were
not used anywhere in this pipeline. For those with two clean ACS F814W visits at least 100 d apart, does one pair show the
change their published period and amplitude predict?

Writes work/rediscovery_m33.json and work/rediscovery_m33.csv.
"""
import json, pathlib
import numpy as np, pandas as pd
from astropy.coordinates import SkyCoord
import astropy.units as u
from oddsky.analysis import twopoint

RUN = pathlib.Path.home() / "oddsky-runs/h0019"
HERE = pathlib.Path(__file__).resolve().parents[1]
det = pd.read_parquet(RUN / "hsc/MESSIER033_det.parquet"); summ = pd.read_parquet(RUN / "hsc/MESSIER033_sum.parquet")
p = twopoint.remove_zero_points(twopoint.star_pairs(det))
p = p[p.kind == "long"].merge(summ[["MatchID", "MatchRA", "MatchDec", "A_F814W"]], on="MatchID")
rows = []
for ln in (RUN / "cat/m33_yuan2017.tsv").read_text().splitlines():
    q = [x.strip() for x in ln.split("\t")]
    if ln.startswith("#") or len(q) < 7 or not q[0][:2].isdigit():
        continue
    rows.append(dict(id=q[0], ra=float(q[1]), dec=float(q[2]), per=float(q[3]), imag=float(q[4]), amp=float(q[5]), cl=q[6]))
y = pd.DataFrame(rows)
cp = SkyCoord(p.MatchRA.values * u.deg, p.MatchDec.values * u.deg)
RADIUS = 0.15   # arcsec, after the bulk offset between the two catalogues is removed


def match(ra, dec):
    idx, d2, _ = SkyCoord(ra * u.deg, dec * u.deg).match_to_catalog_sky(cp)
    return idx, d2.arcsec


# 1. bulk offset (the referee found Hubble minus Yuan = -0.45", -0.14"): median offset of the matches within 1 arcsec,
#    iterated once
cosd = np.cos(np.radians(y.dec.median())); off = np.zeros(2)
for _ in range(3):
    idx, sep = match(y.ra.values + off[0] / 3600 / cosd, y.dec.values + off[1] / 3600)
    near = sep < (1.0 if not off.any() else 0.3)
    dra = (p.MatchRA.values[idx[near]] - y.ra.values[near]) * 3600 * cosd; ddec = (p.MatchDec.values[idx[near]] - y.dec.values[near]) * 3600
    off = np.array([np.median(dra), np.median(ddec)])
idx, sep = match(y.ra.values + off[0] / 3600 / cosd, y.dec.values + off[1] / 3600)
y["sep"] = sep


def select(idx, sep):
    ok = sep < RADIUS
    m = y[ok].reset_index(drop=True); pm = p.iloc[idx[ok]].reset_index(drop=True)
    m = m.assign(d=pm.d.values, lag=pm.lag.values, mag=pm.mag.values)
    m["dI"] = m.mag - (m.imag + 0.43 + 0.25)   # HSC AB aperture magnitude minus the published mean I, same system
    return m[m.dI.abs() < 1.5]                 # the Hubble star is the Mira, not a faint neighbour


m = select(idx, sep)
# 2. chance rate: shift the Mira positions by 3, 5, 8 arcsec in 8 directions and match again
chance, chance_big = [], []
for r in (3, 5, 8):
    for k in range(8):
        dx, dy = r * np.cos(k * np.pi / 4), r * np.sin(k * np.pi / 4)
        i2, s2 = match(y.ra.values + (off[0] + dx) / 3600 / cosd, y.dec.values + (off[1] + dy) / 3600)
        c = select(i2, s2); chance.append(len(c)); chance_big.append(int((c.d.abs() > 0.3).sum()))
# expectation: sinusoid of the published peak-to-peak amplitude at random phase, 0.05 mag noise
rng = np.random.default_rng(33)
ph = rng.uniform(0, 2 * np.pi, (4000, len(m)))
sim = m.amp.values / 2 * (np.sin(ph + 2 * np.pi * m.lag.values / m.per.values) - np.sin(ph)) + rng.normal(0, 0.05, ph.shape)
# control: stars of the same magnitudes that are not in the Mira list
far = np.ones(len(p), bool); far[idx[y.sep < 1.0]] = False
ctrl = p[far & p.mag.between(m.mag.quantile(0.05), m.mag.quantile(0.95))]
out = dict(n_miras_published=len(y), offset_arcsec=[round(float(off[0]), 3), round(float(off[1]), 3)], match_radius_arcsec=RADIUS,
           chance_matches_per_trial=round(float(np.mean(chance)), 1), chance_big_per_trial=round(float(np.mean(chance_big)), 2), n_used=len(m), median_lag=float(m.lag.median()),
           median_amp=float(m.amp.median()), n_control=len(ctrl))
for x in (0.3, 0.5, 1.0):
    k = int((m.d.abs() > x).sum()); exp = (np.abs(sim) > x).mean(axis=1)
    out[f"x{x}"] = dict(observed=k, frac=round(k / len(m), 3), expected_frac=round(float(exp.mean()), 3),
                        expected_sd=round(float(exp.std()), 3), control_frac=round(float((ctrl.d.abs() > x).mean()), 4))
out["rms_observed"], out["rms_expected"] = round(float(np.sqrt((m.d ** 2).mean())), 3), round(float(np.sqrt((sim ** 2).mean())), 3)
out["dimmed_vs_brightened"] = [int((m.d > 0).sum()), int((m.d < 0).sum())]
m.round(4).to_csv(HERE / "work/rediscovery_m33.csv", index=False)
(HERE / "work/rediscovery_m33.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
