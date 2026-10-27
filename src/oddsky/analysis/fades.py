"""Stars that go dark: features that separate an R CrB decline from a Mira, an eclipse, or a glitch.

An R Coronae Borealis decline is a sudden fade of 1-9 mag from a flat maximum, over days to weeks,
followed by a recovery that takes months: fast down, slow up, aperiodic. A Mira is a sine of 2-8 mag
with a period of 100-1000 days. An eclipse is symmetric and recurs on a fixed period. A glitch is a
single night.

`excursions.excursions` uses a running baseline that a year-long decline drags down into itself, so
the fade features here are measured against a fixed maximum-light reference instead.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .periodogram import periodogram
from .stats import robust_std

BAND_PREFERENCE = ("ATLAS_o", "ZTF_r", "ATLAS_c", "ZTF_g", "V", "CV", "Vis.", "ZTF_i", "I", "R", "B")


def nightly(df: pd.DataFrame, band: str) -> pd.DataFrame:
    """Nightly medians of one band; upper limits are carried as censored points (mag = limit)."""
    d = df[(df.band == band) & df.flag.isin(["", "upper_limit"])].copy()
    if d.empty:
        return d
    d["night"] = np.floor(d.t_mjd + 0.5)
    d["lim"] = d.flag.eq("upper_limit")
    g = d.groupby("night")
    out = pd.DataFrame({
        "t_mjd": g.t_mjd.mean(), "mag": g.mag.median(), "err": g.err.median().fillna(0.0),
        "n": g.size(), "lim": g.lim.all(),
    }).reset_index(drop=True)
    return drop_isolated_nights(out)


def drop_isolated_nights(b: pd.DataFrame, jump: float = 0.8, agree: float = 0.4, within: float = 45.0) -> pd.DataFrame:
    """Remove a night that disagrees with both of its neighbours by more than `jump` mag while the
    neighbours agree with each other: one bad exposure set, not a star that moved and came back in a day.
    Nights more than `within` days from both neighbours are kept (nothing to compare with)."""
    if len(b) < 3:
        return b
    t, m = b.t_mjd.to_numpy(float), b.mag.to_numpy(float)
    keep = np.ones(len(b), bool)
    for i in range(1, len(b) - 1):
        if t[i] - t[i - 1] > within or t[i + 1] - t[i] > within:
            continue
        d1, d2 = m[i] - m[i - 1], m[i] - m[i + 1]
        same = np.sign(d1) == np.sign(d2)
        if same and abs(m[i - 1] - m[i + 1]) <= agree and min(abs(d1), abs(d2)) > jump:
            keep[i] = False
        elif same and min(abs(d1), abs(d2)) > 3.0:  # a 3-mag spike that is gone the next night is never a star
            keep[i] = False
    return b[keep].reset_index(drop=True)


def fold_power(t: np.ndarray, m: np.ndarray, period: float, n_bins: int = 10) -> float:
    """Fraction of the variance explained by the phase-binned mean curve at `period`: a shape-free
    periodicity test (a Mira's sawtooth scores high here even when a sinusoid fits it badly)."""
    if len(t) < 3 * n_bins or not period or period <= 0:
        return 0.0
    ph = ((t - t.min()) / period) % 1.0
    idx = np.minimum((ph * n_bins).astype(int), n_bins - 1)
    means = np.array([m[idx == k].mean() if (idx == k).any() else np.nan for k in range(n_bins)])
    model = means[idx]
    ok = np.isfinite(model)
    tot = np.var(m[ok])
    return float(1 - np.var(m[ok] - model[ok]) / tot) if tot > 0 else 0.0


def choose_band(df: pd.DataFrame, min_nights: int = 30) -> str | None:
    counts = {b: len(nightly(df, b)) for b in df.band.unique()}
    for b in BAND_PREFERENCE:
        if counts.get(b, 0) >= min_nights:
            return b
    best = max(counts, key=counts.get) if counts else None
    return best if best and counts[best] >= min_nights else None


def fade_events(t: np.ndarray, m: np.ndarray, bright: float, depth_min: float = 0.5, back_within: float = 0.3,
                max_gap: float = 120.0, lim: np.ndarray | None = None) -> list[dict]:
    """Runs of nights fainter than bright + depth_min. Ingress = start to deepest, egress = deepest to
    first night back within `back_within` of maximum (None when the series ends first)."""
    faint = m > bright + depth_min
    events = []
    i, n = 0, len(t)
    while i < n:
        if not faint[i]:
            i += 1
            continue
        s = e = i
        j = i + 1
        while j < n and t[j] - t[e] <= max_gap:
            if faint[j]:
                e = j
            elif m[j] <= bright + back_within:
                break
            j += 1
        seg = slice(s, e + 1)
        k = s + int(np.argmax(m[seg]))
        back = next((q for q in range(e + 1, n) if m[q] <= bright + back_within), None)
        pre = s - 1 if s > 0 else None
        ev = {
            "start_mjd": float(t[s]), "end_mjd": float(t[e]), "deepest_mjd": float(t[k]),
            "depth": float(m[k] - bright), "n_nights": int(faint[seg].sum()),
            "ingress_days": float(t[k] - t[pre]) if pre is not None else float(t[k] - t[s]),
            "egress_days": float(t[back] - t[k]) if back is not None else None,
            # still faint this long after the deepest night: a lower bound that survives seasonal gaps
            "egress_min_days": float(t[e] - t[k]),
            # the recovery itself fell in a gap longer than max_gap (or off the end): egress is a bound
            "egress_uncertain": bool(back is None or t[back] - t[e] > max_gap),
            "censored_depth": bool(lim[k]) if lim is not None else False,
            "last_bright_before_mjd": float(t[pre]) if pre is not None else None,
            "starts_after_gap": bool(pre is None or t[s] - t[pre] > max_gap),
            "ends_in_data": back is not None,
        }
        events.append(ev)
        i = (back if back is not None else e) + 1
    return events


def rcb_features(df: pd.DataFrame, band: str | None = None) -> dict:
    """Decline morphology in the best-covered optical band. Thresholds live in `classify_fade`."""
    band = band or choose_band(df)
    if band is None:
        return {"error": "no band with 30 nights", "n_nights": 0}
    b = nightly(df, band)
    det = b[~b.lim]
    if len(det) < 20:
        return {"error": "fewer than 20 detected nights", "band": band, "n_nights": int(len(b))}
    t, m, lim = b.t_mjd.to_numpy(float), b.mag.to_numpy(float), b.lim.to_numpy(bool)
    e = np.nan_to_num(b.err.to_numpy(float), nan=0.1)
    bright = float(np.percentile(det.mag, 5))
    near_max = np.abs(det.mag - bright) <= 0.3
    out = {
        "band": band, "n_nights": int(len(b)), "n_limits": int(lim.sum()),
        "span_days": float(t.max() - t.min()), "bright": bright,
        "max_frac": float(near_max.mean()),
        "scatter_at_max": robust_std(det.mag[near_max]) if near_max.sum() >= 5 else None,
        "faintest": float(m.max()), "amplitude": float(m.max() - bright),
    }
    # decline rate: fastest confirmed fade between nights 3-40 days apart, both ends multi-night-ish
    rate = 0.0
    for i in range(len(t)):
        for j in range(i + 1, len(t)):
            dt = t[j] - t[i]
            if dt > 40:
                break
            if dt < 3 or lim[i]:
                continue
            # a fade worth timing: at least 0.5 mag and 4 sigma (faint ZTF nights scatter by 0.3 mag on their own)
            if (m[j] - m[i]) < max(0.5, 4 * float(np.hypot(e[i], e[j]))):
                continue
            # both ends must be confirmed by a neighbouring night: the bright night by an earlier night within
            # 20 d and 0.5 mag of it, the faint night by a later night within 20 d that is at least half as faint
            earlier = (t < t[i]) & (t[i] - t <= 20)
            if not earlier.any() or not (np.abs(m[earlier] - m[i]) <= 0.5).any():
                continue
            later = (t > t[j]) & (t - t[j] <= 20)
            if not later.any() or not (m[later] >= m[i] + 0.5 * (m[j] - m[i])).any():
                continue
            rate = max(rate, (m[j] - m[i]) / dt)
    out["decline_rate_mag_per_day"] = float(rate)
    evs = fade_events(t, m, bright, lim=lim)
    deep = [e for e in evs if e["depth"] >= 1.0 and e["n_nights"] >= 2]
    out["n_events"] = len(deep)
    out["events"] = deep[:10]
    out["n_single_night_drops"] = sum(1 for e in evs if e["depth"] >= 1.0 and e["n_nights"] == 1)
    if deep:
        big = max(deep, key=lambda e: e["depth"])
        out["depth"] = big["depth"]
        out["depth_censored"] = big["censored_depth"]
        out["ingress_days"] = big["ingress_days"]
        out["egress_days"] = big["egress_days"]
        eg = big["egress_days"] if (big["egress_days"] and not big["egress_uncertain"]) else big["egress_min_days"]
        out["asymmetry"] = (eg / big["ingress_days"]) if big["ingress_days"] > 0 else None
        out["asymmetry_is_lower_bound"] = bool(big["egress_uncertain"])
        out["ongoing"] = not big["ends_in_data"]
        starts = np.array([e["start_mjd"] for e in deep])
        if len(starts) >= 3:
            gaps = np.diff(np.sort(starts))
            out["interval_cv"] = float(gaps.std() / gaps.mean()) if gaps.mean() > 0 else None
    else:
        out.update(depth=0.0, depth_censored=False, asymmetry=None, ongoing=False)
    # periodicity on detections only (limits would fake a period)
    try:
        pg = periodogram(det.rename(columns={"err": "err"})[["t_mjd", "mag", "err"]].assign(err=lambda d: d.err.clip(lower=0.02)),
                         min_period=30, max_period=1500)
        top = (pg.get("peaks") or [{}])[0]
        out["ls_power"] = top.get("power")
        out["ls_period"] = top.get("period_days")
        out["ls_alias_flags"] = top.get("alias_flags", [])
        tt, mm = det.t_mjd.to_numpy(float), det.mag.to_numpy(float)
        P = top.get("period_days") or 0
        # a fold is only evidence of periodicity when the data cover at least three cycles: with fewer,
        # one long decline "folds" perfectly at half the baseline
        span = tt.max() - tt.min()
        out["fold_power"] = max(fold_power(tt, mm, P) if span >= 3 * P else 0.0,
                                fold_power(tt, mm, 2 * P) if span >= 6 * P else 0.0) if P else 0.0
    except Exception as e:  # noqa: BLE001
        out["ls_error"] = str(e)[:80]
    return out


def disk_eclipse_features(df: pd.DataFrame, band: str | None = None) -> dict:
    """Symmetric, flat-bottomed-or-V, grey, non-recurring-on-short-periods fades."""
    f = rcb_features(df, band)
    if "error" in f or not f.get("events"):
        return {"candidate": False, **{k: f.get(k) for k in ("band", "n_nights", "depth")}}
    big = max(f["events"], key=lambda e: e["depth"])
    sym = (big["egress_days"] / big["ingress_days"]) if big["egress_days"] and big["ingress_days"] > 0 else None
    return {
        "candidate": bool(sym is not None and 0.5 <= sym <= 2.0 and big["depth"] >= 0.5 and f["max_frac"] >= 0.7
                          and not big["egress_uncertain"]),
        "depth": big["depth"], "duration_days": (big["ingress_days"] + (big["egress_days"] or 0)),
        "symmetry": sym, "max_frac": f["max_frac"], "n_events": f["n_events"],
    }


def colour_during_fade(df: pd.DataFrame, blue: str, red: str, events: list[dict], tol_days: float = 2.0) -> dict | None:
    """Median (blue - red) at maximum versus inside the deepest event; positive = redder when faint."""
    if not events:
        return None
    bb, rr = nightly(df, blue), nightly(df, red)
    if bb.empty or rr.empty:
        return None
    bb, rr = bb[~bb.lim], rr[~rr.lim]
    if bb.empty or rr.empty:
        return None
    m = pd.merge_asof(bb.sort_values("t_mjd"), rr.sort_values("t_mjd"), on="t_mjd", tolerance=tol_days,
                      direction="nearest", suffixes=("_b", "_r")).dropna(subset=["mag_r"])
    if len(m) < 10:
        return None
    big = max(events, key=lambda e: e["depth"])
    inside = (m.t_mjd >= big["start_mjd"]) & (m.t_mjd <= big["end_mjd"])
    col = m.mag_b - m.mag_r
    bright_r = np.percentile(m.mag_r, 5)
    at_max = np.abs(m.mag_r - bright_r) <= 0.3
    if inside.sum() < 3 or at_max.sum() < 3:
        return None
    faint_slope = None
    if inside.sum() >= 5:
        x, y = m.mag_r[inside] - bright_r, col[inside]
        faint_slope = float(np.polyfit(x, y, 1)[0])  # d(colour)/d(depth)
    return {"colour_at_max": float(col[at_max].median()), "colour_in_fade": float(col[inside].median()),
            "delta_colour": float(col[inside].median() - col[at_max].median()),
            "dcolour_ddepth": faint_slope, "n_pairs_in_fade": int(inside.sum()), "bands": f"{blue}-{red}"}


def classify_fade(f: dict) -> str:
    """rcb_like | mira_like | slow_variable | erratic | eclipse_like | artifact | no_event | unclassified.

    Thresholds set on synthetic curves and then checked against twenty known R CrB stars in AAVSO V since
    2015 (hunts/H-0004/aavso_cal): every star with a decline in the window is rcb_like, the four quiet ones
    (XX Cam, UV Cas, RT Nor, RS Tel) are no_event. Active R CrB stars spend most of their time faint, so
    "flat maximum" means a maximum exists, not that the star sits there; and a deep decline can dominate a
    periodogram, so periodicity alone is not a Mira: a Mira also fades slowly and on schedule.
    """
    if "error" in f:
        return "unclassified"
    power = max(f.get("ls_power") or 0.0, f.get("fold_power") or 0.0)
    depth = f.get("depth") or 0.0
    rate = f.get("decline_rate_mag_per_day") or 0.0
    regular = f.get("n_events", 0) >= 4 and (f.get("interval_cv") or 1) <= 0.2  # three events can space evenly by chance (R CrB did)
    mira = power >= 0.6 and f.get("amplitude", 0) >= 1.0 and (rate < 0.06 or regular) \
        and 80 <= (f.get("ls_period") or 0) <= 1000
    if depth < 1.0:
        if mira:
            return "mira_like"
        return "artifact" if f.get("n_single_night_drops", 0) else "no_event"
    if mira:
        return "mira_like"
    events = f.get("events") or []
    big = max(events, key=lambda e: e["depth"])
    if big["n_nights"] < 2:
        return "artifact"
    if f.get("n_events", 0) >= 12:
        # a dozen separate >= 1 mag fades in a few years is a young star or an erratic variable, not dust puffs
        # from an R CrB star (the most active known ones manage about one a year)
        return "erratic"
    if rate < 0.02:
        # deep but slow: a pulsator or a long-period variable, whatever the periodogram thinks. R CrB declines
        # are fast by definition (0.05-0.5 mag/day).
        return "mira_like" if power >= 0.4 else "slow_variable"
    asym = f.get("asymmetry")
    asym_known = asym is not None and not f.get("asymmetry_is_lower_bound")
    fast = rate >= 0.02  # real declines are 0.05-0.5 mag/day; sparse sampling waters the measured rate down
    has_max = f.get("max_frac", 0) >= 0.15
    irregular = not regular
    symmetric = asym_known and 0.5 <= asym <= 2.0
    if fast and irregular:
        # a fast, unscheduled fade. Symmetric, rare and shallow enough to be an eclipse by something on a
        # long orbit: eclipse_like. Otherwise it is the R CrB morphology, including the stars that recover
        # quickly (ASAS-RCB-19 does) and the very active ones that are hardly ever at maximum (NSV 11154).
        if symmetric and f.get("n_events", 0) <= 2 and depth <= 4.0:
            return "eclipse_like"
        return "rcb_like"
    if has_max and symmetric and power < 0.6:
        return "eclipse_like"
    return "unclassified"
