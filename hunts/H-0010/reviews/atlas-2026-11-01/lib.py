"""Shared loaders for the H-0010 ATLAS second-instrument check (8 candidates). Own code; follows the ATLAS lessons of
hunts/H-0008/reviews/claude-referee-atlas10-2026-10-30.md and hunts/H-0009/reviews/claude-referee-atlas-2026-10-31.md:
  * c/o only; err == 0, dujy > 0, mag5sig > 17.5; NO chi/N cut (chi/N grows with flux and a cut removes event frames);
  * nightly weighted means per (band, unit, local night) with a 4-sigma clip on >= 3 frames;
  * baselines per unit/band from nights > 400 d from the Gaia event, and at a PSF width matched to the event nights
    (pre-2018 ATLAS forced fluxes depend on PSF width in crowded fields);
  * series whose baseline is not clearly detected (median / robust scatter < 3, or median <= 0) are not turned into ratios;
  * fit/compare in excess flux, take blending from Gaia neighbours (ATLAS PSF ~ 4-7" FWHM; neighbours within 8").
Run from the repo root:  uv run python -I hunts/H-0010/reviews/atlas-2026-11-01/aN_*.py
"""
import os

import numpy as np
import pandas as pd

from oddsky.data import atlas

HERE = os.path.dirname(os.path.abspath(__file__))
H10 = os.path.abspath(os.path.join(HERE, "..", ".."))
ATL = os.path.join(H10, "work", "atlas")
DATA = os.path.join(HERE, "data")
os.makedirs(DATA, exist_ok=True)
SOUTH = ("03a", "04a", "05r", "06r")  # southern units: local night straddles 0h UT
KEYS = ("J182124", "J200958", "J184837", "J174036", "J180313", "J184922", "J182811", "J174029")
PIX = 1.86  # ATLAS arcsec / pixel

# Gaia DR3 zero points (EDR3/DR3 passbands): AB - Vega
AB_MINUS_VEGA = {"G": 25.8010 - 25.6874, "BP": 25.3540 - 25.3385, "RP": 25.1040 - 24.7479}


def targets():
    q = pd.read_csv(os.path.join(ATL, "queue.csv"), dtype={"source_id": str})
    u = pd.read_csv(os.path.join(H10, "work", "gaia_ml_unpub.csv"), dtype={"source_id": str})
    out = {}
    for _, r in q.iterrows():
        k = r["name"].split(".")[0][:7]
        row = u[u.source_id == r.source_id].iloc[0]
        out[k] = dict(name=r["name"], sid=r.source_id, ra=float(r.ra), dec=float(r.dec), t0=float(row.static_t0),
                      tpk=float(row.t_peak), ep_first=float(row.ep_first), ep_last=float(row.ep_last),
                      G=float(row.phot_g_mean_mag), BP=float(row.phot_bp_mean_mag), RP=float(row.phot_rp_mean_mag),
                      bprp=float(row.bp_rp), Apk=float(row.A_obs_G), row=row)
    return out


def atlas_raw(k):
    r = atlas.parse(open(os.path.join(ATL, f"atlas_{k}.txt")).read())
    r = r[r.F.isin(["c", "o"])].copy()
    r["cam"] = r.obs.str[:3]
    r["night"] = np.where(r.cam.isin(SOUTH), np.floor(r.mjd - 0.5), np.floor(r.mjd)).astype(int)
    r["year"] = 2000 + (r.mjd - 51544.5) / 365.25
    return r


def clean(r, m5min=17.5):
    return r[(r.err == 0) & (r.dujy > 0) & (r.mag5sig > m5min) & (r.ujy.abs() < 1e7)].copy()


def nightly(r, clip=4.0):
    rows = []
    for (F, cam, night), d in r.groupby(["F", "cam", "night"]):
        f, e, t = d.ujy.values, d.dujy.values, d.mjd.values
        if len(f) >= 3:
            med = np.median(f)
            s = np.maximum(1.4826 * np.median(np.abs(f - med)), np.median(e))
            ok = np.abs(f - med) < clip * s
            f, e, t = f[ok], e[ok], t[ok]
        if len(f) == 0:
            continue
        w = 1 / e**2
        m = np.sum(w * f) / np.sum(w)
        fe = 1 / np.sqrt(np.sum(w))
        if len(f) > 1:
            fe = max(fe, np.std(f, ddof=1) / np.sqrt(len(f)))
        rows.append((F, cam, night, float(np.mean(t)), m, fe, len(f), len(d), float(d.maj.median()), float(d["min"].median()),
                     float(d.mag5sig.median()), float(d.chi_n.median()), float(d.sky.median())))
    return pd.DataFrame(rows, columns=["F", "cam", "night", "t", "ujy", "ujy_err", "n", "nraw", "maj", "mnr", "m5", "chi", "sky"])


def gaia_ab(G, BP, RP):
    """AB magnitudes of the Gaia bands."""
    return G + AB_MINUS_VEGA["G"], BP + AB_MINUS_VEGA["BP"], RP + AB_MINUS_VEGA["RP"]


def gaia_to_atlas_ujy(G, BP, RP):
    """Approximate ATLAS c and o fluxes (uJy) of a star from Gaia G/BP/RP: interpolate the AB spectrum in log(lambda)
    between BP (511 nm), G (~640 nm for these red stars) and RP (777 nm); c at 533 nm, o at 679 nm. ~0.2 mag uncertain.
    Neighbours without BP/RP get the G flux in both bands."""
    g, b, r = gaia_ab(G, BP, RP)
    if not (np.isfinite(b) and np.isfinite(r)):
        f = 10 ** (-0.4 * (g - 23.9))
        return f, f
    lam = np.log10([511.0, 640.0, 777.0])
    m = np.array([b, g, r])
    mc = np.interp(np.log10(533.0), lam, m)
    mo = np.interp(np.log10(679.0), lam, m)
    return 10 ** (-0.4 * (mc - 23.9)), 10 ** (-0.4 * (mo - 23.9))


def psf_weight(sep_arcsec, maj_px):
    """Forced-PSF response of a Gaussian PSF (FWHM = maj px) to a point source at sep: the normalised cross-correlation
    of two Gaussians, exp(-r^2 / (4 sigma^2))."""
    s = maj_px * PIX / 2.3548
    return np.exp(-np.asarray(sep_arcsec) ** 2 / (4 * s**2))


def mjd2date(m):
    from astropy.time import Time
    return Time(m, format="mjd").iso[:10]


def ujy2ab(f):
    return 23.9 - 2.5 * np.log10(f)
