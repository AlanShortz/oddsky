"""Colours and cross-band behaviour: the fingerprints that separate dust from pulsation from geometry."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .stats import daily_bins

# Interstellar-like extinction ratios A_band / A_V (Wang & Chen 2019; approximate).
EXTINCTION_RATIO = {"B": 1.32, "V": 1.0, "g": 1.17, "R": 0.81, "I": 0.59, "TESS": 0.62, "W1": 0.039, "W2": 0.026}


def match(a: pd.DataFrame, b: pd.DataFrame, tol_days: float) -> pd.DataFrame:
    """Pair each point of b with the median of a within +/- tol_days."""
    ab = daily_bins(a, 1.0)
    ta, ma = ab["t_mjd"].to_numpy(), ab["mag"].to_numpy()
    rows = []
    for tb, mb, eb in b[["t_mjd", "mag", "err"]].itertuples(index=False):
        sel = np.abs(ta - tb) <= tol_days
        if sel.sum():
            rows.append((tb, float(np.median(ma[sel])), mb, eb, int(sel.sum())))
    return pd.DataFrame(rows, columns=["t_mjd", "mag_a", "mag_b", "err_b", "n_a"])


def cross_band(a: pd.DataFrame, b: pd.DataFrame, band_a: str, band_b: str, tol_days: float = 5.0) -> dict:
    """How band A moves when band B moves. For dust extinction dA/dB follows the extinction law."""
    pairs = match(a, b, tol_days)
    if len(pairs) < 4:
        return {"n_pairs": int(len(pairs)), "error": "fewer than 4 near-simultaneous pairs"}
    x, y = pairs["mag_b"].to_numpy(), pairs["mag_a"].to_numpy()
    r = float(np.corrcoef(x, y)[0, 1]) if np.std(x) > 0 and np.std(y) > 0 else float("nan")
    slope = float(np.polyfit(x, y, 1)[0]) if np.std(x) > 0 else float("nan")
    out = {
        "n_pairs": int(len(pairs)),
        "pearson_r": r,
        "slope_dA_dB": slope,
        "range_a": float(np.ptp(y)),
        "range_b": float(np.ptp(x)),
        "tolerance_days": tol_days,
        "pairs_sample": pairs.iloc[:: max(1, len(pairs) // 15)].round(4).to_dict(orient="records")[:15],
    }
    ra, rb = EXTINCTION_RATIO.get(_base(band_a)), EXTINCTION_RATIO.get(_base(band_b))
    if ra and rb and np.ptp(x) > 0.1:
        out["interstellar_dust_expectation_dA_dB"] = ra / rb
        out["reading"] = (
            "For grey (large-grain) dust dA/dB ~ 1; for ISM-like grains it is the ratio above; "
            "pulsation and spots give their own, often opposite-signed, slopes."
        )
    return out


def wise_color(neowise: pd.DataFrame) -> dict:
    """W1-W2 per visit and how it tracks W1 brightness (dust heating reddens as it brightens)."""
    w1 = neowise[neowise.band == "W1"].set_index(neowise[neowise.band == "W1"]["t_mjd"].round(0))
    w2 = neowise[neowise.band == "W2"].set_index(neowise[neowise.band == "W2"]["t_mjd"].round(0))
    common = w1.index.intersection(w2.index)
    if len(common) < 3:
        return {"n_visits": int(len(common)), "error": "fewer than 3 visits with both W1 and W2"}
    c = (w1.loc[common, "mag"] - w2.loc[common, "mag"]).to_numpy()
    ce = np.hypot(w1.loc[common, "err"], w2.loc[common, "err"]).to_numpy()
    t = w1.loc[common, "t_mjd"].to_numpy()
    m1 = w1.loc[common, "mag"].to_numpy()
    r = float(np.corrcoef(m1, c)[0, 1]) if np.std(c) > 0 else float("nan")
    return {
        "n_visits": int(len(c)),
        "w1_minus_w2_median": float(np.median(c)),
        "w1_minus_w2_range": float(np.ptp(c)),
        "w1_minus_w2_first_last": [float(c[0]), float(c[-1])],
        "corr_W1_vs_color": r,
        "reading": "negative corr: redder when brighter in W1 (warm dust appearing); "
                   "W1-W2 > ~0.3 suggests emission from dust warmer than the ISM but cooler than a photosphere",
        "visits": [dict(t_mjd=float(a), w1_w2=float(b), err=float(e)) for a, b, e in zip(t, c, ce, strict=True)],
    }


def _base(band: str) -> str:
    b = band.replace("ZTF_", "").replace("NEOWISE:", "")
    return {"CV": "V", "TG": "V", "SG": "g", "r": "R", "i": "I"}.get(b, b)


# WISE Vega zero points (Jarrett et al. 2011) and isophotal wavelengths.
WISE_F0_JY = {"W1": 309.540, "W2": 171.787}
WISE_LAMBDA_UM = {"W1": 3.3526, "W2": 4.6028}


def _bnu_ratio(t: float) -> float:
    """B_nu(W1)/B_nu(W2) for a blackbody at temperature t (K)."""
    h_k = 1.4388e4  # hc/k in micron K
    l1, l2 = WISE_LAMBDA_UM["W1"], WISE_LAMBDA_UM["W2"]
    return (l2 / l1) ** 3 * np.expm1(h_k / (l2 * t)) / np.expm1(h_k / (l1 * t))


def ir_excess(neowise: pd.DataFrame, base: tuple[float, float], window: tuple[float, float]) -> dict:
    """Infrared excess over a baseline (photosphere) epoch: flux fractions and a two-band dust temperature.

    The excess is what the window adds on top of the baseline in each band; its W1/W2 flux ratio
    gives a blackbody colour temperature. Assumes the baseline is pure photosphere."""
    out: dict = {"baseline_mjd": list(base), "window_mjd": list(window)}
    fx = {}
    for band in ("W1", "W2"):
        s = neowise[neowise.band == band]
        b = s[(s.t_mjd >= base[0]) & (s.t_mjd <= base[1])].mag
        w = s[(s.t_mjd >= window[0]) & (s.t_mjd <= window[1])].mag
        if len(b) < 2 or len(w) < 1:
            return {**out, "error": f"need >= 2 baseline and >= 1 window visits in {band}"}
        fb = WISE_F0_JY[band] * 10 ** (-0.4 * np.median(b))
        fw = WISE_F0_JY[band] * 10 ** (-0.4 * np.median(w))
        fx[band] = fw - fb
        out[band] = {"baseline_mag": float(np.median(b)), "window_mag": float(np.median(w)),
                     "excess_mjy": float(1e3 * (fw - fb)), "excess_fraction_of_photosphere": float((fw - fb) / fb)}
    if fx["W1"] <= 0 or fx["W2"] <= 0:
        out["reading"] = "no positive excess in both bands; no dust temperature"
        return out
    ratio = fx["W1"] / fx["W2"]
    lo, hi = 100.0, 5000.0
    if not (_bnu_ratio(lo) < ratio < _bnu_ratio(hi)):
        out["reading"] = f"excess flux ratio W1/W2 = {ratio:.2f} is outside the blackbody range 100-5000 K"
        return out
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if _bnu_ratio(mid) < ratio else (lo, mid)
    t = 0.5 * (lo + hi)
    out["excess_flux_ratio_W1_W2"] = float(ratio)
    out["blackbody_temperature_K"] = round(float(t), 0)
    out["reading"] = ("two-band colour temperature of the excess; real dust is not a blackbody and two bands cannot "
                      "separate temperature from grain emissivity. Treat as +/- a few hundred K.")
    return out
