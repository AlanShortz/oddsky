"""Gaia DR3: who the star is, where it sits on the HR diagram, and who is standing next to it."""

from __future__ import annotations

import io

import numpy as np
import pandas as pd

from .http import request
from .provenance import Provenance

TAP = "https://gea.esac.esa.int/tap-server/tap/sync"

SOURCE_COLS = (
    "source_id, ra, dec, parallax, parallax_over_error, pmra, pmdec, ruwe, "
    "phot_g_mean_mag, phot_bp_mean_mag, phot_rp_mean_mag, bp_rp, "
    "phot_variable_flag, teff_gspphot, distance_gspphot, non_single_star"
)


def adql(query: str, timeout: float = 120) -> pd.DataFrame:
    r = request("POST", TAP, timeout=timeout, data=dict(REQUEST="doQuery", LANG="ADQL", FORMAT="csv", QUERY=query))
    text = r.text.strip()
    if not text or "\n" not in text:
        return pd.DataFrame()
    return pd.read_csv(io.StringIO(text))


def adql_async(query: str, poll_s: float = 5.0, max_wait_s: float = 1800) -> pd.DataFrame:
    """Long queries go through the async TAP endpoint: submit, poll, fetch. Sync times out on big joins."""
    import time
    import xml.etree.ElementTree as ET

    base = TAP.replace("/sync", "/async")
    r = request("POST", base, timeout=60, data=dict(REQUEST="doQuery", LANG="ADQL", FORMAT="csv", QUERY=query,
                                                     PHASE="RUN"))
    job = str(r.url)
    t0 = time.time()
    while time.time() - t0 < max_wait_s:
        phase = request("GET", job + "/phase", timeout=30).text.strip()
        if phase == "COMPLETED":
            res = request("GET", job + "/results/result", timeout=300)
            return pd.read_csv(io.StringIO(res.text))
        if phase in ("ERROR", "ABORTED"):
            err = request("GET", job, timeout=30).text
            msg = "".join(e.text or "" for e in ET.fromstring(err).iter() if e.tag.endswith("message"))
            raise RuntimeError(f"Gaia async job {phase}: {msg or err[:300]}")
        time.sleep(poll_s)
    raise TimeoutError(f"Gaia async job still running after {max_wait_s}s: {job}")


def cone(ra: float, dec: float, radius_arcsec: float = 30.0) -> tuple[pd.DataFrame, Provenance]:
    """All Gaia DR3 sources within radius, nearest first, with separation in arcsec."""
    q = (
        f"SELECT {SOURCE_COLS}, DISTANCE(POINT({ra},{dec}), POINT(ra,dec))*3600 AS sep_arcsec "
        f"FROM gaiadr3.gaia_source WHERE 1=CONTAINS(POINT(ra,dec), CIRCLE({ra},{dec},{radius_arcsec / 3600})) "
        "ORDER BY sep_arcsec"
    )
    df = adql(q)
    prov = Provenance(archive="ESA Gaia TAP gaiadr3.gaia_source", query={"adql": q}, rows_raw=len(df), rows_kept=len(df))
    if df.empty:
        prov.status = "empty"
    return df, prov


def variability(source_id: int) -> dict:
    """Gaia's own variability verdicts: summary statistics and the long-period-variable table."""
    out: dict = {}
    s = adql(
        "SELECT num_selected_g_fov, mean_mag_g_fov, std_dev_mag_g_fov, range_mag_g_fov, skewness_mag_g_fov, "
        "in_vari_long_period_variable, in_vari_eclipsing_binary, in_vari_rrlyrae, in_vari_cepheid, "
        "in_vari_short_timescale, in_vari_agn, in_vari_classification_result "
        f"FROM gaiadr3.vari_summary WHERE source_id={source_id}"
    )
    if not s.empty:
        out["summary"] = _clean(s.iloc[0].to_dict())
    lpv = adql(
        "SELECT frequency, frequency_error, amplitude, median_delta_wl_rp, is_cstar "
        f"FROM gaiadr3.vari_long_period_variable WHERE source_id={source_id}"
    )
    if not lpv.empty:
        row = _clean(lpv.iloc[0].to_dict())
        if row.get("frequency"):
            row["period_days"] = 1.0 / row["frequency"]
        out["long_period_variable"] = row
    cls = adql(
        "SELECT best_class_name, best_class_score FROM gaiadr3.vari_classifier_result "
        f"WHERE source_id={source_id}"
    )
    if not cls.empty:
        out["classifier"] = _clean(cls.iloc[0].to_dict())
    return out


def context(target: pd.Series) -> dict:
    """Derived quantities a skeptic wants before believing anything about a star."""
    g = float(target["phot_g_mean_mag"])
    plx = float(target.get("parallax", np.nan))
    poe = float(target.get("parallax_over_error", np.nan))
    ctx = {
        "G": g,
        "bp_rp": _f(target.get("bp_rp")),
        "parallax_mas": _f(plx),
        "parallax_over_error": _f(poe),
        "ruwe": _f(target.get("ruwe")),
        "teff_gspphot": _f(target.get("teff_gspphot")),
        "non_single_star": int(target.get("non_single_star", 0) or 0),
        "phot_variable_flag": str(target.get("phot_variable_flag", "")),
        "ra": _f(target.get("ra")),
        "dec": _f(target.get("dec")),
        "pmra": _f(target.get("pmra")),
        "pmdec": _f(target.get("pmdec")),
    }
    if np.isfinite(plx) and plx > 0 and np.isfinite(poe) and poe > 5:
        dist_pc = 1000.0 / plx
        ctx["distance_pc"] = dist_pc
        ctx["abs_G"] = g - 5 * np.log10(dist_pc / 10.0)
    else:
        ctx["distance_pc"] = None
        ctx["abs_G"] = None
        ctx["notes"] = ["parallax too uncertain for an absolute magnitude (parallax_over_error <= 5)"]
    return ctx


def neighbors(df: pd.DataFrame, target_id: int) -> pd.DataFrame:
    t = df[df.source_id == target_id].iloc[0]
    n = df[df.source_id != target_id].copy()
    n["dG"] = n["phot_g_mean_mag"] - t["phot_g_mean_mag"]
    n["flux_ratio_G"] = 10 ** (-0.4 * n["dG"])
    return n[["source_id", "sep_arcsec", "phot_g_mean_mag", "bp_rp", "dG", "flux_ratio_G", "parallax", "ruwe"]]


def _f(x):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return x if np.isfinite(x) else None


def _clean(d: dict) -> dict:
    out = {}
    for k, v in d.items():
        if isinstance(v, (np.bool_, bool)):
            out[k] = bool(v)
        elif isinstance(v, (np.integer,)):
            out[k] = int(v)
        elif isinstance(v, (np.floating, float)):
            out[k] = float(v) if np.isfinite(v) else None
        elif isinstance(v, str) and v.lower() in ("true", "false"):
            out[k] = v.lower() == "true"
        else:
            out[k] = v
    return out
