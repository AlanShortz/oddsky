"""Per-band descriptive statistics, long-term trend, and the single biggest change in level."""

from __future__ import annotations

import numpy as np
import pandas as pd

YEAR = 365.25


def robust_std(x: np.ndarray) -> float:
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) < 2:
        return float("nan")
    return float(1.4826 * np.median(np.abs(x - np.median(x))))


def daily_bins(df: pd.DataFrame, width: float = 1.0) -> pd.DataFrame:
    """Median-combine points within `width` days. Tames the 7000-point amateur series."""
    if df.empty:
        return df
    key = np.floor(df["t_mjd"].to_numpy() / width)
    g = df.assign(_k=key).groupby("_k")
    out = pd.DataFrame({
        "t_mjd": g["t_mjd"].median(),
        "mag": g["mag"].median(),
        "err": g["err"].median() / np.sqrt(g.size()),
        "n": g.size(),
    })
    if "observer" in df:
        out["observers"] = g["observer"].nunique()
    if "camera" in df:
        out["cameras"] = g["camera"].nunique()
    return out.reset_index(drop=True)


def describe(df: pd.DataFrame) -> dict:
    t, m = df["t_mjd"].to_numpy(float), df["mag"].to_numpy(float)
    if len(t) == 0:
        return {"n": 0}
    out = {
        "n": int(len(t)),
        "t_first": float(t.min()),
        "t_last": float(t.max()),
        "span_days": float(t.max() - t.min()),
        "median_mag": float(np.median(m)),
        "robust_std": robust_std(m),
        "brightest": float(np.percentile(m, 2)),
        "faintest": float(np.percentile(m, 98)),
        "amplitude_2_98": float(np.percentile(m, 98) - np.percentile(m, 2)),
        "median_err": float(np.nanmedian(df["err"])),
    }
    if len(t) >= 5 and out["span_days"] > 30:
        A = np.vstack([np.ones_like(t), (t - t.mean()) / YEAR]).T
        coef, *_ = np.linalg.lstsq(A, m, rcond=None)
        out["slope_mag_per_yr"] = float(coef[1])
        out["note"] = "positive slope = getting fainter"
    return out


def changepoint(df: pd.DataFrame, min_seg: int = 3) -> dict | None:
    """Best single step in level (two-segment median model). Returns where, how big, how significant."""
    b = daily_bins(df, 5.0) if len(df) > 400 else df[["t_mjd", "mag", "err"]].reset_index(drop=True)
    t, m = b["t_mjd"].to_numpy(float), b["mag"].to_numpy(float)
    n = len(t)
    if n < 2 * min_seg + 1:
        return None
    best = None
    total = np.sum(np.abs(m - np.median(m)))
    for i in range(min_seg, n - min_seg):
        a, c = m[:i], m[i:]
        cost = np.sum(np.abs(a - np.median(a))) + np.sum(np.abs(c - np.median(c)))
        if best is None or cost < best[0]:
            best = (cost, i)
    cost, i = best
    a, c = m[:i], m[i:]
    step = float(np.median(c) - np.median(a))
    noise = np.hypot(robust_std(a) / np.sqrt(len(a)), robust_std(c) / np.sqrt(len(c)))
    return {
        "t_change_mjd": float(0.5 * (t[i - 1] + t[i])),
        "before_median": float(np.median(a)),
        "after_median": float(np.median(c)),
        "step_mag": step,
        "direction": "fainter" if step > 0 else "brighter",
        "significance_sigma": float(abs(step) / noise) if noise > 0 else None,
        "cost_reduction": float(1 - cost / total) if total > 0 else 0.0,
        "n_before": int(len(a)),
        "n_after": int(len(c)),
    }


def window_stat(df: pd.DataFrame, start: float, end: float) -> dict:
    w = df[(df.t_mjd >= start) & (df.t_mjd <= end)]
    if w.empty:
        return {"n": 0}
    m = w["mag"].to_numpy(float)
    return {
        "n": int(len(m)),
        "median": float(np.median(m)),
        "err_of_median": float(1.2533 * max(robust_std(m), float(np.nanmedian(w["err"]))) / np.sqrt(len(m))),
        "brightest": float(m.min()),
        "faintest": float(m.max()),
    }
