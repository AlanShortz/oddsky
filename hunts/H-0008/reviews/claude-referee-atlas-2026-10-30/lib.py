"""Shared loaders for the ATLAS referee pass (written from scratch; does not import the investigators' scripts).

Run everything from the repo root:  uv run python hunts/H-0008/reviews/claude-referee-atlas-2026-10-30/rN_*.py
"""
import os

import numpy as np
import pandas as pd

from oddsky.data import atlas

HERE = os.path.dirname(os.path.abspath(__file__))
H8 = os.path.abspath(os.path.join(HERE, "..", ".."))
REF = os.path.join(H8, "reviews", "claude-referee-2026-10-30", "data")
ATL = os.path.join(H8, "work", "atlas")

# AllWISE position, Gaia DR3 id, NEOWISE event visit, provisional peak (from the ATLAS data, not the investigators' fit)
TARGETS = {
    "J180624": dict(name="J180624.78-090411.4", ra=271.603281, dec=-9.069857, gaia=4158424169627436800, tvis=59823.29, tpk=59842.0),
    "J183040": dict(name="J183040.98-220950.3", ra=277.670788, dec=-22.163984, gaia=4090003970570642816, tvis=59831.31, tpk=59825.0),
}
SOUTH = ("03a", "04a")  # southern units (Chile / South Africa): their nights straddle 0h UT


def atlas_raw(k):
    r = atlas.parse(open(os.path.join(ATL, f"atlas_{k}.txt")).read())
    r = r[r.F.isin(["c", "o"]) & (r.err == 0) & (r.dujy > 0) & (r.ujy.abs() < 1e6)].copy()
    r["cam"] = r.obs.str[:3]
    r["night"] = np.where(r.cam.isin(SOUTH), np.floor(r.mjd - 0.5), np.floor(r.mjd)).astype(int)
    r["year"] = 2000 + (r.mjd - 51544.5) / 365.25
    return r


def clean(r, m5min=17.5, chi="rel", chi_abs=10.0, maj_max=None):
    """chi: 'abs' = chi/N < chi_abs (the investigators' cut, which removes bright event points); 'rel' = chi/N below
    4x the series' baseline median *scaled with flux* (chi/N of a slightly mis-modelled PSF grows ~linearly with flux);
    'none' = no chi cut."""
    r = r[r.mag5sig > m5min].copy()
    if maj_max is not None:
        r = r[r.maj < maj_max]
    if chi == "abs":
        r = r[r.chi_n < chi_abs]
    elif chi == "rel":
        keep = np.ones(len(r), bool)
        for (_F, _c), d in r.groupby(["F", "cam"]):
            fmed = np.median(d.ujy)
            cmed = np.median(d.chi_n)
            lim = 4 * cmed * np.maximum(d.ujy / fmed, 1.0)
            keep[r.index.get_indexer(d.index)] = d.chi_n.values < np.maximum(lim, 10)
        r = r[keep]
    return r


def nightly(r, clip=4.0, nmin=2):
    """Per (band, unit, night): drop exposures > clip robust-sigma from the night median, weighted mean of the rest.
    Error = max(formal, std/sqrt(n))."""
    rows = []
    for (F, cam, night), d in r.groupby(["F", "cam", "night"]):
        f, e = d.ujy.values, d.dujy.values
        if len(f) >= 3:
            med = np.median(f)
            s = np.maximum(1.4826 * np.median(np.abs(f - med)), np.median(e))
            ok = np.abs(f - med) < clip * s
            f, e, t = f[ok], e[ok], d.mjd.values[ok]
        else:
            t = d.mjd.values
        if len(f) < nmin:
            continue
        w = 1 / e**2
        m = np.sum(w * f) / np.sum(w)
        fe = 1 / np.sqrt(np.sum(w))
        if len(f) > 1:
            fe = max(fe, np.std(f, ddof=1) / np.sqrt(len(f)))
        rows.append((F, cam, night, float(np.mean(t)), m, fe, len(f), float(d.maj.median()), float(d.apfit.median()),
                     float(d.mag5sig.median()), float(d.chi_n.median())))
    return pd.DataFrame(rows, columns=["F", "cam", "night", "t", "ujy", "ujy_err", "n", "maj", "apfit", "m5", "chi"])


def ztf(k, flags=(0,)):
    z = pd.read_csv(os.path.join(REF, f"ztf_{k}.csv"))
    z = z[z.catflags.isin(flags) & z.mag.notna()].copy()
    z["band"] = z.filtercode.str[-1]
    z["night"] = np.floor(z.mjd - 0.3).astype(int)  # Palomar: nights straddle 0h UT? no (UT-8): floor is fine; -0.3 is safe
    z["fl"] = 10 ** (-0.4 * z.mag)
    rows = []
    for (b, fld, n), d in z.groupby(["band", "field", "night"]):
        e = d.fl * d.magerr / 1.0857
        w = 1 / e**2
        rows.append((b, fld, n, d.mjd.mean(), np.sum(w * d.fl) / np.sum(w), 1 / np.sqrt(np.sum(w)), len(d)))
    return pd.DataFrame(rows, columns=["band", "field", "night", "t", "fl", "fl_err", "n"])


def neowise(k):
    n = pd.read_csv(os.path.join(REF, f"neowise_{k}.csv"))
    out = []
    for b in ("w1", "w2"):
        fl = 10 ** (-0.4 * n[b].values)
        out.append(pd.DataFrame({"t": n.t.values, "fl": fl, "fl_err": fl * n[f"{b}_err"].values / 1.0857, "band": b.upper()}))
    return pd.concat(out, ignore_index=True)


def to_ratio(t, fl, fe, label, base, floor="mad"):
    """Flux / baseline median. floor: 'mad' adds the baseline's robust scatter in quadrature (beyond the formal errors);
    'scale' multiplies errors so the baseline chi2/dof = 1 (never shrinks); 'none' formal only."""
    t, fl, fe = map(np.asarray, (t, fl, fe))
    med = np.median(fl[base])
    f, e = fl / med, fe / med
    if floor == "mad":
        resid = f[base] - 1
        rob = 1.4826 * np.median(np.abs(resid - np.median(resid)))
        extra = np.sqrt(max(rob**2 - np.median(e[base]) ** 2, 0))
        e = np.hypot(e, extra)
    elif floor == "scale":
        chi = np.sum(((f[base] - 1) / e[base]) ** 2) / max(base.sum() - 1, 1)
        rob = 1.4826 * np.median(np.abs((f[base] - 1) / e[base]))
        e = e * max(1.0, rob)
    elif floor == "mad_inv":  # the investigators' choice: the full baseline MAD in quadrature (double-counts formal error)
        rob = 1.4826 * np.median(np.abs(f[base] - 1))
        e = np.hypot(e, rob)
    return pd.DataFrame({"t": t, "f": f, "e": e, "g": label})
