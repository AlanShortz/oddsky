"""Shared pieces of H-0018: the sign-of-rotation statistic, its dipole fit and the dev/held-out split."""
import os

import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord

RUNS = os.path.expanduser("~/oddsky-runs/h0018")
NSS_CSV = f"{RUNS}/data/nss/nss_astrometric.csv"
WB_FITS = f"{RUNS}/data/elbadry/all_columns_catalog.fits.gz"
SHIFT_FITS = f"{RUNS}/data/elbadry/all_columns_catalog_shift.fits.gz"

NEP = SkyCoord(lon=0 * u.deg, lat=90 * u.deg, frame="barycentricmeanecliptic").galactic
NEP_GAL = np.array(NEP.cartesian.xyz.value)
NGP_GAL = np.array([0.0, 0.0, 1.0])


def is_dev(source_id):
    """30% development split: multiplicative hash of the Gaia source id, as preregistered."""
    sid = np.asarray(source_id, dtype=np.uint64)
    mixed = sid * np.uint64(11400714819323198485)
    return ((mixed >> np.uint64(40)) % np.uint64(10)) < np.uint64(3)


def gal_vectors(ra_deg, dec_deg):
    """Outward line-of-sight unit vectors in Galactic Cartesian coordinates."""
    c = SkyCoord(ra=np.asarray(ra_deg) * u.deg, dec=np.asarray(dec_deg) * u.deg, frame="icrs").galactic
    return np.asarray(c.cartesian.xyz.value).T


def fit_dipole(y, n):
    """E[y|n] = m + D.n by least squares, with heteroscedastic-robust errors. Returns a dict."""
    y = np.asarray(y, dtype=float)
    X = np.column_stack([np.ones(len(y)), n])
    XtX_inv = np.linalg.inv(X.T @ X)
    beta = XtX_inv @ (X.T @ y)
    res = y - X @ beta
    meat = (X * res[:, None]).T @ (X * res[:, None])
    cov = XtX_inv @ meat @ XtX_inv
    se = np.sqrt(np.diag(cov))
    D = beta[1:]
    out = {
        "N": int(len(y)),
        "m": beta[0], "m_se": se[0],
        "Dx": D[0], "Dy": D[1], "Dz": D[2],
        "Dx_se": se[1], "Dy_se": se[2], "Dz_se": se[3],
        "m_sig": beta[0] / se[0],
        "Dz_sig": D[2] / se[3],
        "D_amp": float(np.linalg.norm(D)),
    }
    # Component along the north ecliptic pole, with its error from the covariance matrix
    Dcov = cov[1:, 1:]
    out["Dnep"] = float(D @ NEP_GAL)
    out["Dnep_se"] = float(np.sqrt(NEP_GAL @ Dcov @ NEP_GAL))
    out["Dnep_sig"] = out["Dnep"] / out["Dnep_se"]
    out["chi2_D"] = float(D @ np.linalg.solve(Dcov, D))
    if np.linalg.norm(D) > 0:
        unit = D / np.linalg.norm(D)
        out["ang_to_ngp"] = float(np.degrees(np.arccos(np.clip(unit @ NGP_GAL, -1, 1))))
        out["ang_to_nep"] = float(np.degrees(np.arccos(np.clip(unit @ NEP_GAL, -1, 1))))
    return out


def bootstrap(y, n, draws=1000, seed=18):
    """Bootstrap errors on m and D (preregistered check on the sandwich errors)."""
    rng = np.random.default_rng(seed)
    y = np.asarray(y, dtype=float)
    X = np.column_stack([np.ones(len(y)), n])
    betas = np.empty((draws, 4))
    for i in range(draws):
        idx = rng.integers(0, len(y), len(y))
        betas[i] = np.linalg.lstsq(X[idx], y[idx], rcond=None)[0]
    return betas.std(axis=0)


def fmt(label, r):
    """One line of a results table, in percent."""
    return (
        f"{label:<34} N={r['N']:>7}  m={100 * r['m']:+6.2f}±{100 * r['m_se']:.2f}"
        f"  Dx={100 * r['Dx']:+6.2f}±{100 * r['Dx_se']:.2f}  Dy={100 * r['Dy']:+6.2f}±{100 * r['Dy_se']:.2f}"
        f"  Dz={100 * r['Dz']:+6.2f}±{100 * r['Dz_se']:.2f} ({r['Dz_sig']:+5.1f}s)"
        f"  Dnep={100 * r['Dnep']:+6.2f} ({r['Dnep_sig']:+5.1f}s)"
    )
