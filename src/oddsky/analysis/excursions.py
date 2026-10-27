"""Find dips (fainter) and flares/brightenings against a running baseline.

Works on irregular, gappy, multi-observer series: bin, estimate a running median baseline that
ignores the excursion itself, then report contiguous runs that stand clear of the noise.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .stats import daily_bins, robust_std


def excursions(df: pd.DataFrame, baseline_days: float = 300.0, k_sigma: float = 4.0, min_depth: float = 0.05,
               min_points: int = 3, max_gap_days: float = 30.0, bin_days: float = 1.0) -> dict:
    b = daily_bins(df, bin_days)
    if len(b) < 2 * min_points:
        return {"error": "too few points", "events": []}
    t, m = b["t_mjd"].to_numpy(float), b["mag"].to_numpy(float)
    # Baseline: running median in a wide window, computed from the quietest 60% of points nearby
    # so that a long dip does not drag the baseline down into itself.
    base = np.empty_like(m)
    half = baseline_days / 2
    lo_idx = np.searchsorted(t, t - half, side="left")
    hi_idx = np.searchsorted(t, t + half, side="right")
    for i in range(len(t)):
        w = m[lo_idx[i]:hi_idx[i]]
        lo, hi = np.percentile(w, [20, 80])
        core = w[(w >= lo) & (w <= hi)]
        base[i] = np.median(core) if len(core) else np.median(w)
    resid = m - base
    sigma = robust_std(resid)
    err = b["err"].to_numpy(float)
    thresh = np.maximum(k_sigma * np.hypot(sigma, np.nan_to_num(err)), min_depth)
    events = []
    for direction, sign in (("fainter", 1), ("brighter", -1)):
        hit = sign * resid > thresh
        for s, e in _runs(hit, t, max_gap_days):
            sel = slice(s, e + 1)
            if hit[sel].sum() < min_points:
                continue
            seg_t, seg_r = t[sel], sign * resid[sel]
            k = int(np.argmax(seg_r))
            ev = {
                "direction": direction,
                "start_mjd": float(seg_t[0]),
                "end_mjd": float(seg_t[-1]),
                "duration_days": float(seg_t[-1] - seg_t[0]),
                "peak_mjd": float(seg_t[k]),
                "depth_mag": float(seg_r[k]),
                "n_bins": int(hit[sel].sum()),
                "ingress_days": float(seg_t[k] - seg_t[0]),
                "egress_days": float(seg_t[-1] - seg_t[k]),
                "baseline_mag": float(base[s + k]),
            }
            dur = ev["duration_days"]
            ev["asymmetry"] = float((ev["egress_days"] - ev["ingress_days"]) / dur) if dur > 0 else 0.0
            if "observers" in b:
                ev["max_independent_observers_per_bin"] = int(b["observers"].to_numpy()[sel].max())
            if "cameras" in b:
                ev["cameras_involved"] = int(b["cameras"].to_numpy()[sel].sum())
            # Clipped edges are the sky's way of saying "I didn't see the start".
            ev["starts_after_gap"] = bool(s == 0 or t[s] - t[s - 1] > max_gap_days)
            ev["ends_before_gap"] = bool(e == len(t) - 1 or t[e + 1] - t[e] > max_gap_days)
            events.append(ev)
    events.sort(key=lambda ev: -ev["depth_mag"])
    return {
        "n_bins": int(len(t)),
        "bin_days": bin_days,
        "noise_mag": float(sigma),
        "threshold_rule": f"max({k_sigma} sigma, {min_depth} mag) beyond a {baseline_days:.0f}-day running baseline",
        "events": events[:20],
        "n_events": len(events),
    }


def _runs(hit: np.ndarray, t: np.ndarray, max_gap: float):
    """Contiguous True runs, allowing isolated False bins and bridging gaps <= max_gap days."""
    i, n = 0, len(hit)
    while i < n:
        if not hit[i]:
            i += 1
            continue
        s = e = i
        j = i + 1
        while j < n and t[j] - t[e] <= max_gap:
            if hit[j]:
                e = j
            elif j + 1 < n and hit[j + 1]:
                pass  # tolerate one non-hit between hits
            else:
                break
            j += 1
        yield s, e
        i = e + 1
