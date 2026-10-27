"""Lomb-Scargle, with the spectral window alongside so survey rhythms don't pass as stellar ones."""

from __future__ import annotations

import numpy as np
import pandas as pd
from astropy.timeseries import LombScargle

# Rhythms of the instruments and the Earth, in days.
KNOWN_ALIASES = {
    "sidereal day": 0.99727,
    "solar day": 1.0,
    "TESS orbit": 13.7,
    "lunar month": 29.53,
    "half year (NEOWISE cadence)": 182.6,
    "year (seasonal gaps)": 365.25,
}


def periodogram(df: pd.DataFrame, min_period: float = 0.1, max_period: float | None = None,
                n_peaks: int = 5, samples: int = 20000) -> dict:
    t, y, dy = (df[c].to_numpy(float) for c in ("t_mjd", "mag", "err"))
    if len(t) < 10:
        return {"error": "fewer than 10 points"}
    span = t.max() - t.min()
    max_period = min(max_period or span / 2, span / 2)
    if max_period <= min_period:
        return {"error": f"baseline {span:.1f} d too short for periods >= {min_period} d"}
    # Uniform grid oversampled 5x relative to the 1/baseline resolution, so the fast (NFFT) method applies.
    n = int(min(max(samples, 5 * span * (1 / min_period - 1 / max_period)), 300_000))
    freq = np.linspace(1 / max_period, 1 / min_period, n)
    dy = np.where(np.isfinite(dy) & (dy > 0), dy, np.nanmedian(dy[dy > 0]) if (dy > 0).any() else 0.05)
    ls = LombScargle(t, y, dy)
    power = ls.power(freq, method="fast")
    win = LombScargle(t, np.ones_like(t), fit_mean=False, center_data=False).power(freq, method="fast")
    peaks = _peaks(freq, power, n_peaks)
    # Only strong window features matter (random sampling has many weak ones).
    win_peaks = [(f, p) for f, p in _peaks(freq, win, 8) if p > 0.1][:5]
    out = []
    for f, p in peaks:
        period = 1 / f
        flags = [name for name, a in KNOWN_ALIASES.items() if abs(period - a) / a < 0.03]
        for wf, _ in win_peaks:
            for k in (1, 2):
                if abs(1 / f - 1 / (wf * k)) / (1 / f) < 0.03:
                    flags.append(f"matches spectral-window peak at {1 / (wf * k):.2f} d")
            # Side lobe: a *stronger* peak sits at f +/- f_window, so this one is probably its alias.
            for s in (-1, 1):
                fa = f + s * wf
                if fa > 0 and any(abs(fa - g) / g < 0.01 and q > p for g, q in peaks if g != f):
                    flags.append(f"likely alias of a stronger peak via the {1 / wf:.1f} d window")
        out.append({"period_days": float(period), "power": float(p), "alias_flags": sorted(set(flags))})
    try:
        fap = float(ls.false_alarm_probability(peaks[0][1], minimum_frequency=freq[0], maximum_frequency=freq[-1]))
    except Exception:  # noqa: BLE001
        fap = None
    return {
        "n_points": int(len(t)),
        "baseline_days": float(span),
        "searched_days": [float(min_period), float(max_period)],
        "peaks": out,
        "false_alarm_probability_top": fap,
        "window_peaks_days": [float(1 / f) for f, _ in win_peaks],
        "caution": "FAP assumes white noise; red-noise (irregular) variability produces confident-looking false peaks.",
    }


def _peaks(freq: np.ndarray, power: np.ndarray, n: int) -> list[tuple[float, float]]:
    idx = np.where((power[1:-1] > power[:-2]) & (power[1:-1] >= power[2:]))[0] + 1
    idx = idx[np.argsort(power[idx])[::-1]]
    chosen: list[int] = []
    for i in idx:
        if all(abs(freq[i] - freq[j]) / freq[j] > 0.02 for j in chosen):
            chosen.append(i)
        if len(chosen) == n:
            break
    return [(float(freq[i]), float(power[i])) for i in chosen]
