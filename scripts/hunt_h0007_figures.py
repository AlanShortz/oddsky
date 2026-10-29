"""H-0007 figures for J040025.77+323527.4: NEOWISE 2014-2024 (J040025.png) and the 2017 event with ATLAS (J040025_atlas.png).
The model curves come from work/lensfit_J040025.json (scripts/hunt_h0007_lensfit.py)."""
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from oddsky.data import atlas

ra, dec = 60.1073758, 32.5909576
ex = pd.read_parquet("hunts/H-0007/work/exp_J040025.parquet")
ex["sep"] = 3600 * np.hypot((ex.ra - ra) * np.cos(np.radians(dec)), ex.dec - dec)
ok = (ex.qual_frame > 0) & (ex.nb == 1)
t = ex[(ex.sep < 2.5) & ok].copy(); t["yr"] = 1858.88 + t.mjd / 365.25
c = ex[ok & (ex.allwise_cntr == 593133301351000350)].copy(); c["yr"] = 1858.88 + c.mjd / 365.25
z = pd.read_csv("hunts/H-0007/work/ztf_J040025.csv"); z = z[z.catflags == 0]; z["yr"] = 1858.88 + z.mjd / 365.25
fig, ax = plt.subplots(1, 2, figsize=(15, 5), gridspec_kw={"width_ratios": [3, 1]})
ax[0].plot(t.yr, t.w1mpro, ".", ms=3, label="target W1 (single exposures)"); ax[0].plot(t.yr, t.w2mpro + 0.6, ".", ms=3, label="target W2 + 0.6")
ax[0].plot(c.yr, c.w1mpro - 2.0, ".", ms=3, color="gray", label="control star 15\" away, W1 − 2.0")
for b, col, off in [("zr", "r", 3.0), ("zg", "g", 2.1)]:
    g = z[z.filtercode == b]; ax[0].plot(g.yr, g.mag - off, ".", ms=2, color=col, alpha=.5, label=f"ZTF {b[1]} − {off}")
ax[0].invert_yaxis(); ax[0].legend(fontsize=8, loc="lower left"); ax[0].set_xlabel("year"); ax[0].set_ylabel("mag")
ax[0].set_title("J040025.77+323527.4 (Gaia DR3 170329679884731008): NEOWISE 2014-2024")
e = t[(t.mjd > 57990) & (t.mjd < 57996)]; bl = t[(t.mjd < 57900) | (t.mjd > 58100)]
ax[1].errorbar(e.mjd - 57992, e.w1mpro, e.w1sigmpro, fmt="o", label="W1"); ax[1].errorbar(e.mjd - 57992, e.w2mpro, e.w2sigmpro, fmt="s", label="W2")
ax[1].axhline(bl.w1mpro.median(), ls=":", color="C0"); ax[1].axhline(bl.w2mpro.median(), ls=":", color="C1")
ax[1].invert_yaxis(); ax[1].set_xlabel("MJD − 57992 (days from 2017 Aug 27 0h UT)"); ax[1].legend(fontsize=8); ax[1].set_title("the event visit (dotted: baseline)")
plt.tight_layout(); plt.savefig("hunts/H-0007/figures/J040025.png", dpi=90)

r = atlas.parse(open("hunts/H-0007/work/atlas_J040025.txt").read()); r = r[(r.dujy > 0) & (r.dujy < 1000) & r.F.isin(["c", "o"])].copy()
base = {F: g[(g.mjd < 57850) | (g.mjd > 58200)].ujy.median() for F, g in r.groupby("F")}; r["A"] = r.ujy / r.F.map(base)
import json
from astropy.coordinates import SkyCoord, get_body_barycentric
from astropy.time import Time
import astropy.units as u
fit = json.load(open("hunts/H-0007/work/lensfit_J040025.json"))["fits"]
sc = SkyCoord(ra * u.deg, dec * u.deg)
east = np.array([-np.sin(sc.ra.rad), np.cos(sc.ra.rad), 0.0])
north = np.array([-np.sin(sc.dec.rad) * np.cos(sc.ra.rad), -np.sin(sc.dec.rad) * np.sin(sc.ra.rad), np.cos(sc.dec.rad)])
def sun(m):
    xyz = -get_body_barycentric("earth", Time(m, format="mjd")).xyz.to(u.au).value.T
    return xyz @ north, xyz @ east
def A(tt, p, par):
    t0, tE, u0 = p[:3]; tau = (tt - t0) / tE; beta = np.full_like(tt, u0)
    if par:
        n0, e0 = sun(np.array([58010.0, 58011.0, 58012.0]))
        sn, se = sun(tt); dN = sn - n0[1] - (n0[2] - n0[0]) / 2 * (tt - 58011.0); dE = se - e0[1] - (e0[2] - e0[0]) / 2 * (tt - 58011.0)
        tau = tau + p[3] * dN + p[4] * dE; beta = beta + (-p[3] * dE + p[4] * dN)
    uu = np.sqrt(tau**2 + beta**2); return (uu**2 + 2) / (uu * np.sqrt(uu**2 + 4))
fig, ax = plt.subplots(1, 2, figsize=(15, 5), gridspec_kw={"width_ratios": [2, 3]})
for F, col in [("o", "darkorange"), ("c", "teal")]:
    g = r[r.F == F]; ax[0].plot(g.mjd, g.A, ".", ms=2, color=col, label=f"ATLAS {F}")
    w = g[(g.mjd > 57900) & (g.mjd < 58150)]; ax[1].plot(w.mjd, w.A, "o", ms=3, color=col, label=f"ATLAS {F}")
sat = r[(r.F == "o") & (r.m < 12.2) & (r.mjd > 57900) & (r.mjd < 58150)]
ax[1].plot(sat.mjd, sat.A, "o", mfc="none", mec="k", ms=7, label="ATLAS o, m < 12.2 (near saturation; not fitted)")
ax[1].errorbar([57993.08], [2.731], [0.04], fmt="*", ms=16, color="crimson", label="NEOWISE W1 (2017 Aug 27-28)")
ax[1].plot([57993.08], [2.716], "P", ms=10, color="purple", label="NEOWISE W2")
tt = np.linspace(57900, 58150, 800)
ax[1].plot(tt, A(tt, fit["a"]["p"], False), "--", color="gray", lw=1, label=f"symmetric point lens (χ² {fit['a']['chi2']:.0f}/{fit['a']['dof']})")
ax[1].plot(tt, A(tt, fit["c"]["p"], True), "k-", lw=1, label=f"with annual parallax (χ² {fit['c']['chi2']:.0f}/{fit['c']['dof']}); acceleration/xallarap fit equally")
for d, lab in [(57961.7, "Gaia Jul 27"), (57987.2, "Gaia Aug 22"), (58014.7, "Gaia Sep 18 (one FoV)")]:
    ax[1].axvline(d, ls=":", color="gray"); ax[1].text(d + 1, 6.5, lab, rotation=90, fontsize=7, color="gray")
ax[1].set_ylim(0.8, 10); ax[1].set_xlabel("MJD"); ax[1].set_ylabel("flux / baseline"); ax[1].legend(fontsize=7, loc="upper right")
ax[0].set_ylim(0.5, 9); ax[0].set_xlabel("MJD"); ax[0].set_ylabel("flux / baseline"); ax[0].set_title("ATLAS 2015-2026: one event"); ax[0].legend(fontsize=8)
ax[1].set_title("J040025.77+323527.4: 2017 July - November")
plt.tight_layout(); plt.savefig("hunts/H-0007/figures/J040025_atlas.png", dpi=90)
