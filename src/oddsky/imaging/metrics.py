"""Variability metrics for six-monthly difference light curves, and a DS1-like vs LPV classifier.

The core distinction (H-0012 README): a failed supernova / dust-formation event is ONE long, smooth
excursion (years), while an AGB/Mira or OH/IR star at a 182.6-day cadence shows repeated swings.
Three numbers carry most of it:

- eta, the von Neumann ratio (mean squared successive difference / variance): ~2 for a light curve
  that is uncorrelated from visit to visit (a Mira with P = 200-800 d sampled every 183 d looks
  like that), << 1 for a smooth trend.
- n_turns: significant reversals of direction (zig-zag with a 3-sigma hysteresis). A 14-year
  baseline (2010-2024) gives a P ~ 1500 d OH/IR star 5+ turns; DS1 has one (up, then down).
- early_quiet / delta_late: the WISE 2010-2011 epochs vs the last epochs; a star that vanished
  or appeared has a large, one-way change between them.
"""

from __future__ import annotations

import numpy as np
from scipy.stats import spearmanr

EARLY_MJD = 55700.0  # WISE 4-band + 3-band cryo + post-cryo: 2010 Jan - 2011 Feb (e000-e002)


def _good(f, e):
    return np.isfinite(f) & np.isfinite(e) & (e > 0)


def von_neumann(f: np.ndarray) -> float:
    if f.size < 4:
        return np.nan
    v = np.var(f, ddof=1)
    return float(np.sum(np.diff(f) ** 2) / (f.size - 1) / v) if v > 0 else np.nan


def zigzag_turns(f: np.ndarray, thresh: float) -> int:
    """Number of direction reversals; a reversal needs a retreat of > thresh from the running extreme."""
    if f.size < 3:
        return 0
    turns, direction = 0, 0
    hi = lo = ext = f[0]
    for v in f[1:]:
        if direction == 0:
            hi, lo = max(hi, v), min(lo, v)
            if v - lo > thresh:
                direction, ext = 1, v
            elif hi - v > thresh:
                direction, ext = -1, v
        elif direction == 1:
            ext = max(ext, v)
            if ext - v > thresh:
                turns, direction, ext = turns + 1, -1, v
        else:
            ext = min(ext, v)
            if v - ext > thresh:
                turns, direction, ext = turns + 1, 1, v
    return turns


def running_median(f: np.ndarray, k: int = 3) -> np.ndarray:
    if f.size < k:
        return f.copy()
    h = k // 2
    pad = np.r_[np.repeat(f[0], h), f, np.repeat(f[-1], h)]
    return np.array([np.median(pad[i : i + k]) for i in range(f.size)])


def align_seasons(f: np.ndarray, season: np.ndarray, ref_flux: dict) -> np.ndarray:
    """Difference fluxes against per-season references sit on different zero points (each season's
    median). Put them on one: add (ref_flux[s] - mean of ref_flux) per season. ref_flux is the
    PSF flux of the source in each season's reference image; blends cancel in the difference."""
    vals = [v for v in ref_flux.values() if np.isfinite(v)]
    if len(vals) < 2:
        return np.asarray(f, float)
    mu = np.mean(vals)
    off = np.array([ref_flux.get(int(s), mu) - mu if np.isfinite(ref_flux.get(int(s), np.nan)) else 0.0 for s in season])
    return np.asarray(f, float) + off


def band_metrics(mjd, f, e, season=None) -> dict:
    """Metrics for one band. f, e: difference fluxes (season-aligned, see align_seasons) and errors."""
    mjd, f, e = map(np.asarray, (mjd, f, e))
    g = _good(f, e)
    out = dict(n=int(g.sum()))
    if g.sum() < 5:
        return out
    t, y, s = mjd[g], f[g], e[g]
    o = np.argsort(t)
    t, y, s = t[o], y[o], s[o]
    w = 1 / s**2
    mu = np.sum(w * y) / np.sum(w)
    chi = (y - mu) / s
    sm = running_median(y, 3)
    med_e = float(np.median(s))
    early = t < EARLY_MJD
    late = np.arange(y.size) >= y.size - 3
    e_mu = np.sum(w[early] * y[early]) / np.sum(w[early]) if early.any() else np.nan
    e_err = 1 / np.sqrt(np.sum(w[early])) if early.any() else np.nan
    l_mu = np.sum(w[late] * y[late]) / np.sum(w[late])
    l_err = 1 / np.sqrt(np.sum(w[late]))
    neo = t > 56600  # NEOWISE-R, 2013 Dec onward
    n_mu = np.sum(w[neo] * y[neo]) / np.sum(w[neo]) if neo.any() else np.nan
    n_err = 1 / np.sqrt(np.sum(w[neo])) if neo.any() else np.nan
    ipk = int(np.argmax(sm))
    ilo = int(np.argmin(sm))
    after = sm[ipk:]
    out.update(
        chi2r=float(np.sum(chi**2) / (y.size - 1)),
        n_sig3=int(np.sum(np.abs(chi) > 3)),
        amp=float(np.max(sm) - np.min(sm)),
        amp_sig=float((np.max(sm) - np.min(sm)) / med_e),
        eta=von_neumann(y),
        n_turns=zigzag_turns(sm, max(3 * med_e, 0.15 * (np.max(sm) - np.min(sm)))),
        rho=float(spearmanr(t, y).statistic),
        early_mean=float(e_mu),
        early_chi2r=float(np.sum(((y[early] - e_mu) / s[early]) ** 2) / max(early.sum() - 1, 1)) if early.sum() > 1 else np.nan,
        late_mean=float(l_mu),
        delta_late=float(l_mu - e_mu),
        delta_late_sig=float((l_mu - e_mu) / np.hypot(l_err, e_err)) if early.any() else np.nan,
        # all NEOWISE epochs vs WISE 2010-11: a star that changed in the 2011-2013 gap
        delta_neo=float(n_mu - e_mu),
        delta_neo_sig=float((n_mu - e_mu) / np.hypot(n_err, e_err)) if early.any() and neo.any() else np.nan,
        t_peak=float(t[ipk]),
        t_min=float(t[ilo]),
        rise_sig=float((sm[ipk] - e_mu) / np.hypot(med_e, e_err)) if early.any() else np.nan,
        fade_sig=float((e_mu - after.min()) / np.hypot(med_e, e_err)) if early.any() else np.nan,
        med_err=med_e,
    )
    # share of the total chi^2 (about the median) carried by the best 3 consecutive epochs
    c2 = ((y - np.median(y)) / s) ** 2
    if y.size >= 3:
        win = np.convolve(c2, np.ones(3), mode="valid")
        out["burst_frac"] = float(win.max() / max(c2.sum(), 1e-12))
    if season is not None:
        ss = np.asarray(season)[g][o]
        if (ss == 0).sum() >= 2 and (ss == 1).sum() >= 2:
            a, b = y[ss == 0], y[ss == 1]
            within = np.sqrt((np.var(a - running_median(a)) + np.var(b - running_median(b))) / 2 + med_e**2)
            out["season_split"] = float(abs(a.mean() - b.mean()) / within)
    return out


def classify_band(m: dict, n_sig_min: int = 3, chi2_min: float = 5.0) -> tuple[str, float]:
    """(class, ds1_score) from ONE band's metrics.

    Classes: 'not-variable', 'step-down' / 'step-up' (quiet epoch to epoch but changed between the
    2010-11 WISE epochs and NEOWISE as a whole at >= 5 sigma), 'season-locked' (a PSF-orientation
    artefact or a P ~ 1 yr variable),
    'transient' (one burst), 'lpv-like' (repeated swings), the long-term one-way classes
    'rise-then-fade', 'fading', 'brightening', and 'irregular'. ds1_score ranks how DS1-like the
    band's light curve is: significance of the one-way change x smoothness, penalised for extra
    turns."""
    if m.get("n", 0) < 5 or "chi2r" not in m:
        return "no-data", 0.0
    eta, turns = m["eta"], m["n_turns"]
    if m["n_sig3"] < n_sig_min or m["chi2r"] < chi2_min:
        # too quiet epoch by epoch, but did it change between WISE 2010-11 and NEOWISE as a whole?
        # (the stacked channel's statistic; N6946-BH1 is the example)
        dn = np.nan_to_num(m.get("delta_neo_sig", 0.0))
        if abs(dn) >= 5:
            return ("step-down" if dn < 0 else "step-up"), float(abs(dn) * float(np.clip((2.0 - eta) / 2.0, 0, 1)))
        return "not-variable", 0.0
    dls = abs(np.nan_to_num(m.get("delta_late_sig", 0.0)))
    rise = np.nan_to_num(m.get("rise_sig", 0.0))
    fade = np.nan_to_num(m.get("fade_sig", 0.0))
    smooth = float(np.clip((2.0 - eta) / 2.0, 0, 1)) if np.isfinite(eta) else 0.0
    score = float(max(dls, min(rise, fade)) * smooth / (1 + max(0, turns - 2)))
    if np.nan_to_num(m.get("season_split", 0)) > 4 and eta > 2.5:
        return "season-locked", score * 0.1
    if m.get("burst_frac", 0) > 0.8:
        return "transient", score
    if eta > 1.2 and turns >= 4:
        return "lpv-like", score
    if eta < 1.2 and turns <= 3:
        if rise > 5 and fade > 3:
            return "rise-then-fade", score
        if dls > 5:
            return ("fading" if m["delta_late"] < 0 else "brightening"), score
        if rise > 5 or fade > 5:
            return "transient", score
    return "irregular", score


def classify_bands(m1: dict, m2: dict) -> dict:
    """Per-band classes, and the verdict of the GATE band (the one with the larger chi^2: the band
    that made the source variable). The class and score are never assembled from different bands.
    `band_agree` says whether the other band, if variable, gives the same class."""
    c1, s1 = classify_band(m1)
    c2, s2 = classify_band(m2)
    x1 = m1.get("chi2r", -1) if c1 != "no-data" else -1
    x2 = m2.get("chi2r", -1) if c2 != "no-data" else -1
    gate = 1 if x1 >= x2 else 2
    cls, score = (c1, s1) if gate == 1 else (c2, s2)
    other = c2 if gate == 1 else c1
    if cls in ("not-variable", "no-data") and other.startswith("step"):  # gate on the step if only it exists
        gate = 2 if gate == 1 else 1
        cls, score, other = (c2, s2, c1) if gate == 2 else (c1, s1, c2)
    agree = other in ("no-data", "not-variable") or other == cls
    return dict(cls=cls, ds1_score=score, cls_w1=c1, cls_w2=c2, gate_band=gate, band_agree=bool(agree),
                ds1_score_w1=s1, ds1_score_w2=s2)


def classify(m1: dict, m2: dict) -> tuple[str, float]:
    """(class, ds1_score) of the gate band; see classify_bands."""
    r = classify_bands(m1, m2)
    return r["cls"], r["ds1_score"]
