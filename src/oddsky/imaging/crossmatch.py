"""Triage cross-matches for difference-imaging candidates: Gaia DR3 (foreground stars, quasars) and
mid-IR colour (AGN).

Gaia source_id is a 19-digit integer; a float64 column silently corrupts it (3.807544900839501e+17).
Everything here keeps it as a STRING, from the TAP CSV onwards.
"""

from __future__ import annotations

import io
import time

import numpy as np
import pandas as pd

from ..data.http import request

TAP_ASYNC = "https://gea.esac.esa.int/tap-server/tap/async"
ID_COLS = ("source_id",)
GAIA_COLS = (
    "s.source_id, s.ra, s.dec, s.phot_g_mean_mag AS g, s.bp_rp, s.parallax, s.parallax_over_error, "
    "s.pmra, s.pmra_error, s.pmdec, s.pmdec_error, s.phot_variable_flag, s.ruwe, "
    "a.classprob_dsc_combmod_quasar AS p_quasar, a.classprob_dsc_combmod_galaxy AS p_galaxy"
)
AGN_W1W2 = 0.8  # Stern et al. 2012: W1 - W2 >= 0.8 (Vega) selects AGN


def read_gaia_csv(text: str) -> pd.DataFrame:
    """Parse a Gaia TAP CSV keeping every *source_id column as str (never float)."""
    head = text.splitlines()[0].split(",") if text.strip() else []
    dtype = {c: str for c in head if c.strip().strip('"').endswith("source_id")}
    return pd.read_csv(io.StringIO(text), dtype=dtype)


def _async(query: str, poll_s: float = 5.0, max_wait_s: float = 1800) -> str:
    r = request("POST", TAP_ASYNC, timeout=60,
                data=dict(REQUEST="doQuery", LANG="ADQL", FORMAT="csv", QUERY=query, PHASE="RUN"))
    job = str(r.url)
    t0 = time.time()
    while time.time() - t0 < max_wait_s:
        phase = request("GET", job + "/phase", timeout=30).text.strip()
        if phase == "COMPLETED":
            return request("GET", job + "/results/result", timeout=300).text
        if phase in ("ERROR", "ABORTED"):
            raise RuntimeError(f"Gaia async job {phase}: {request('GET', job, timeout=30).text[:300]}")
        time.sleep(poll_s)
    raise TimeoutError(job)


def gaia_batch(ras, decs, r_arcsec: float = 3.0) -> pd.DataFrame:
    """All Gaia DR3 sources within r_arcsec of any position (one async job), with the DSC class
    probabilities from astrophysical_parameters."""
    circles = " OR ".join(
        f"1 = CONTAINS(POINT('ICRS', s.ra, s.dec), CIRCLE('ICRS', {a:.6f}, {d:.6f}, {r_arcsec / 3600:.6f}))"
        for a, d in zip(ras, decs, strict=True))
    q = (f"SELECT {GAIA_COLS} FROM gaiadr3.gaia_source AS s "
         f"LEFT JOIN gaiadr3.astrophysical_parameters AS a ON a.source_id = s.source_id WHERE {circles}")
    return read_gaia_csv(_async(q))


def nearest(cands: pd.DataFrame, gaia: pd.DataFrame, r_arcsec: float = 3.0) -> pd.DataFrame:
    """Per candidate: the brightest Gaia source within r_arcsec, with foreground and quasar flags."""
    rows = []
    for _, c in cands.iterrows():
        rec = dict(group=c.group)
        if len(gaia):
            sep = np.hypot((gaia.ra - c.ra) * np.cos(np.radians(c.dec)), gaia.dec - c.dec) * 3600
            g = gaia[sep < r_arcsec].assign(sep=sep[sep < r_arcsec]).sort_values("g")
        else:
            g = gaia
        rec["n_gaia"] = len(g)
        if len(g):
            b = g.iloc[0]
            pm_snr = float(np.hypot(b.pmra / b.pmra_error, b.pmdec / b.pmdec_error)) if np.isfinite(b.pmra) else np.nan
            rec.update(gaia_id=str(b.source_id), gaia_sep=float(b.sep), G=float(b.g), bp_rp=float(b.bp_rp),
                       plx_snr=float(b.parallax_over_error), pm_snr=pm_snr, var_flag=str(b.phot_variable_flag),
                       p_quasar=float(b.p_quasar) if pd.notna(b.p_quasar) else np.nan)
            rec["foreground"] = bool(np.nan_to_num(rec["plx_snr"]) > 5 or np.nan_to_num(pm_snr) > 5)
            rec["quasar"] = bool(np.nan_to_num(rec["p_quasar"]) > 0.5)
        rows.append(rec)
    out = pd.DataFrame(rows)
    if "gaia_id" in out:
        out["gaia_id"] = out["gaia_id"].astype("string")
    return out


def agn_colour_flag(w1_flux, w2_flux, r_ell) -> np.ndarray:
    """W1 - W2 >= 0.8 (Vega, from the reference PSF fluxes in Vega nanomaggies) for a source
    OUTSIDE the D25 ellipse (r_ell > 1): probably a background AGN, not a star in the galaxy."""
    with np.errstate(all="ignore"):
        w1w2 = -2.5 * np.log10(np.asarray(w1_flux, float) / np.asarray(w2_flux, float))
    return (w1w2 >= AGN_W1W2) & (np.asarray(r_ell, float) > 1.0)


def w1_minus_w2(w1_flux, w2_flux) -> np.ndarray:
    with np.errstate(all="ignore"):
        return -2.5 * np.log10(np.asarray(w1_flux, float) / np.asarray(w2_flux, float))
