"""Recurrent dust-formation outbursts in sparse two-band light curves (hunt H-0013).

The target class is the episodic dust maker: a colliding-wind WC binary (WR 140-like) or an LBV
binary that makes dust at every periastron. In the mid-infrared it shows **repeated outbursts**: a
fast rise (months), a slower decline (one to a few years), and a return to a flat minimum, again
every P years. The light curves are the H-0012 forced PSF light curves on unWISE difference images:
W1 and W2, two visits a year (one per visit season), 2010-2011 and 2013.9-2024.5 (about 23-25 epochs
per band).

Model. Per band b and visit season s, y = c[b, s] + A[b] * h(t; P, t0, tau_r, tau_d) + noise, where
h is a periodic train of outburst profiles (a linear rise of length tau_r to a peak at t0 + kP, then
an exponential decline with e-folding time tau_d) and A[b] >= 0. The four season offsets c[b, s]
absorb the per-season reference zero points (each season has its own reference image) and any
season-locked systematic. For each template on a grid of (P, t0, tau_r, tau_d) the amplitudes and
offsets are linear, so the fit is a projection; the improvement over the offsets-only model is

    dchi2 = sum_b max(0, <h~, y~>_w)^2 / <h~, h~>_w      (h~, y~: season means removed, weights 1/e^2)

The ranking statistic is scale-free (it does not trust the forced-photometry errors' absolute scale):

    F = dchi2 / max(1, chi2_fit / dof)

so a long-period variable (a Mira, OH/IR star or AGN), whose residuals about any outburst train
stay large, gets a small F even when its dchi2 is large.

Significance and the false-positive classes:

- **Shuffle null** (`shuffle_null`): epochs are permuted within each visit season, with the same
  permutation for W1 and W2 (cross-band correlation and season zero points kept; time order
  destroyed). p_shuffle is the fraction of shuffles whose best F reaches the observed one, over the
  same template grid (the look-elsewhere effect is included).
- **Red-noise null** (`phase_null`): Fourier phase randomisation of the evenly sampled NEOWISE
  segment (same random phases in both bands). The surrogates keep the power spectrum, so they mimic
  quasi-periodic stochastic variability (AGN, irregular red variables); a small p_phase means the
  light curve is more outburst-like (flat minima, sharp peaks) than a Gaussian process with the same
  spectrum.
- **Recurrence** (`cycle_fit`): at the best template every cycle gets its own scale alpha_k
  (colour fixed); a cycle is detected at alpha_k / sigma_k >= 3. Two or more detected cycles are
  required. A cycle whose data could have shown it (sigma_k <= 1/3) but did not is "missing": the
  source then recurs but is not strictly periodic.
- **Single outburst** (`single_scan`): the best single fast-rise / slow-decline event (any time,
  tau_d up to 4 yr). R = (dchi2_periodic - dchi2_single) / max(1, chi2_fit/dof) measures what the
  second (and later) outbursts add.
- **Sinusoid** (`sine_scan`): the best sinusoid, periods 100 d - 16 yr, independent phase per band.
  S = (dchi2_outburst - dchi2_sine) / max(1, chi2_fit/dof). Mira/LPV pulsation (P < ~1000 d at a
  182.6-d cadence) is sinusoid-like and is vetoed when S is small and P_sine < 1000 d.
- **Seasons**: the hump light must be present in both visit seasons (each season's own reference),
  otherwise it is a PSF-orientation artefact.

Vetoes that need the image or catalogue context (moving stars, saturated cores, neighbours, AGN) are
applied by the hunt script from the H-0012 merged table; `verdict` combines everything.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

YEAR_D = 365.25
MJD_J2000 = 51544.5

# template grid (years)
P_MIN, P_MAX = 1.5, 16.0
SHAPES = ((0.15, 0.35), (0.15, 0.7), (0.15, 1.2), (0.15, 2.0), (0.4, 0.7), (0.4, 1.2), (0.4, 2.0))
SINGLE_SHAPES = SHAPES + ((0.15, 3.0), (0.4, 3.0), (0.4, 4.0), (1.0, 2.0))
# decline must have mostly finished before the next rise: tau_d <= P / TAU_D_MAX_FRAC, tau_r <= P / 3
TAU_D_MAX_FRAC = 2.5
T0_STEP = 0.1
SINE_PMIN_D = 100.0
LPV_P_D = 1000.0
# 2/yr alias family: an apparent period P is also fitted by a pulsator at 365.25 / (2 +- 1/P) d. Below
# P_ALIAS_MIN that alias is >= 230 d, an ordinary Mira period, so the long period means nothing.
P_ALIAS_MIN = 2.3
# beyond this an AGB/OH-IR pulsation period is not expected (the longest SPIRITS LPV: 2538 d)
P_AGB_MAX = 7.0
SHARP_DUTY = 0.25  # FWHM / P of the 'flat-minimum' outburst family in the shape test
Z_SHARP = 4.0  # shape test: flat-minimum outbursts preferred over a sinusoid at the same period

# decision thresholds (calibrated in hunts/H-0013 on shuffled real light curves and injections)
F_MIN = 25.0
P_SHUFFLE_MAX = 0.01
CYCLE_SIG = 3.0
S_MIN = 9.0
R_MIN = 9.0


def mjd_to_year(mjd):
    return 2000.0 + (np.asarray(mjd, float) - MJD_J2000) / YEAR_D


# ----------------------------------------------------------------------------------------------
# templates


def outburst_profile(x, tau_r: float, tau_d: float) -> np.ndarray:
    """One outburst with its peak at x = 0 (years): 0 before -tau_r, a linear rise to 1 at 0, then
    exp(-x / tau_d)."""
    x = np.asarray(x, float)
    out = np.zeros_like(x)
    r = (x > -tau_r) & (x <= 0)
    out[r] = (x[r] + tau_r) / tau_r
    d = x > 0
    out[d] = np.exp(-x[d] / tau_d)
    return out


def train_profile(t, P: float, t0, tau_r: float, tau_d: float, reverse: bool = False) -> np.ndarray:
    """An infinite train of outbursts peaking at t0 + k P, in closed form (t in years; t0 scalar or
    a column vector for many phases at once). With x = (t - t0) mod P the decline of every earlier
    cycle sums to exp(-x / tau_d) / (1 - exp(-P / tau_d)), and the rise (tau_r <= P / 3) belongs to
    the next cycle only. `reverse` mirrors the profile in time (slow rise, fast decline)."""
    t = np.asarray(t, float)
    d = (np.asarray(t0, float) - t) if reverse else (t - np.asarray(t0, float))
    x = np.mod(d, P)
    h = np.exp(-x / tau_d) / (1.0 - np.exp(-P / tau_d))
    return h + np.clip((x - (P - tau_r)) / tau_r, 0.0, None)


def periodic_template(t, P: float, t0: float, tau_r: float, tau_d: float, reverse: bool = False) -> np.ndarray:
    """A train of outbursts peaking at t0 + k P (t in years); see train_profile."""
    return train_profile(t, P, t0, tau_r, tau_d, reverse)


def period_grid(baseline_yr: float, p_min: float = P_MIN, p_max: float = P_MAX, phase_tol_yr: float = 0.2) -> np.ndarray:
    """Log-spaced periods: a period error dP shifts the last cycle by dP * baseline / P, kept below
    phase_tol_yr."""
    dlnp = phase_tol_yr / max(baseline_yr, 1.0)
    return np.exp(np.arange(np.log(p_min), np.log(p_max) + dlnp, dlnp))


@dataclass
class Bank:
    """Templates evaluated at one set of epoch times. params rows: (P, t0, tau_r, tau_d)."""

    t: np.ndarray
    params: np.ndarray
    H: np.ndarray  # (n_templates, n_t) float32
    kind: str = "periodic"


_BANKS: dict = {}


def periodic_bank(t, reverse: bool = False, shapes=SHAPES) -> Bank:
    """All periodic templates for epoch times t (years). Cached per time set."""
    t = np.asarray(t, float)
    key = ("p", reverse, shapes, tuple(np.round(t, 3)))
    if key in _BANKS:
        return _BANKS[key]
    base = t.max() - t.min()
    rows, H = [], []
    for P in period_grid(base):
        for tr, td in shapes:
            if td > P / TAU_D_MAX_FRAC or tr > P / 3:
                continue
            t0 = t.min() + np.arange(0, P, T0_STEP)
            rows.append(np.c_[np.full(t0.size, P), t0, np.full(t0.size, tr), np.full(t0.size, td)])
            H.append(train_profile(t[None, :], P, t0[:, None], tr, td, reverse).astype(np.float32))
    b = Bank(t, np.vstack(rows), np.vstack(H), "periodic-rev" if reverse else "periodic")
    _BANKS[key] = b
    return b


def short_bank(t, p_min_d: float = SINE_PMIN_D, p_max_d: float = LPV_P_D) -> Bank:
    """Mira-like periodic templates, P = 100-1000 d: asymmetric (rise 0.3-0.45 P, exponential decline
    0.25-0.4 P), the shape of a pulsating AGB star. At the 182.6-d WISE cadence these alias to long
    apparent periods (P = 243 d or 146 d looks like 2 yr), so a long-period outburst fit has to beat
    them before its period means anything."""
    t = np.asarray(t, float)
    key = ("short", p_min_d, p_max_d, tuple(np.round(t, 3)))
    if key in _BANKS:
        return _BANKS[key]
    base = max(t.max() - t.min(), 1.0)
    rows, H = [], []
    P = p_min_d / YEAR_D
    while P <= p_max_d / YEAR_D:
        for fr, fd in ((0.3, 0.25), (0.45, 0.25), (0.3, 0.4), (0.45, 0.4)):
            tr, td = fr * P, fd * P
            t0 = t.min() + np.arange(0, P, min(T0_STEP, P / 12))
            rows.append(np.c_[np.full(t0.size, P), t0, np.full(t0.size, tr), np.full(t0.size, td)])
            H.append(train_profile(t[None, :], P, t0[:, None], tr, td).astype(np.float32))
        P *= 1 + 0.15 * P / base  # the last cycle moves by < 0.15 P
    b = Bank(t, np.vstack(rows), np.vstack(H), "short")
    _BANKS[key] = b
    return b


def single_bank(t, shapes=SINGLE_SHAPES) -> Bank:
    """One outburst anywhere from 4 yr before the first epoch to just after the last."""
    t = np.asarray(t, float)
    key = ("s", shapes, tuple(np.round(t, 3)))
    if key in _BANKS:
        return _BANKS[key]
    rows, H = [], []
    tp = np.arange(t.min() - 4.0, t.max() + 0.3, T0_STEP)
    for tr, td in shapes:
        rows.append(np.c_[np.full(tp.size, np.inf), tp, np.full(tp.size, tr), np.full(tp.size, td)])
        H.append(outburst_profile(t[None, :] - tp[:, None], tr, td).astype(np.float32))
    b = Bank(t, np.vstack(rows), np.vstack(H), "single")
    _BANKS[key] = b
    return b


# ----------------------------------------------------------------------------------------------
# light curve container


@dataclass
class LightCurve:
    """Both bands on a common epoch axis. y, e: (2, n_epochs) arrays (NaN where missing);
    t: (n_epochs,) years; season: (n_epochs,) 0/1."""

    t: np.ndarray
    season: np.ndarray
    y: np.ndarray
    e: np.ndarray
    epoch: np.ndarray = field(default_factory=lambda: np.zeros(0, int))

    @property
    def ok(self) -> np.ndarray:
        return np.isfinite(self.y) & np.isfinite(self.e) & (self.e > 0)

    def n_good(self) -> int:
        return int(self.ok.sum())


def from_long(lc, align=None) -> LightCurve | None:
    """H-0012 long-format light curve (columns band, epoch, mjd, season, flux, err, ref_flux) ->
    LightCurve. `align(flux, season, ref_flux_by_season)` puts the two seasons on one zero point
    (oddsky.imaging.metrics.align_seasons); the season offsets of the model make this cosmetic."""
    import pandas as pd  # noqa: F401  (lc is a DataFrame)

    ep = np.sort(lc.epoch.unique())
    n = ep.size
    if n < 6:
        return None
    t = np.full(n, np.nan)
    season = np.zeros(n, int)
    y = np.full((2, n), np.nan)
    e = np.full((2, n), np.nan)
    idx = {v: i for i, v in enumerate(ep)}
    for bi, b in enumerate((1, 2)):
        lb = lc[lc.band == b]
        if lb.empty:
            continue
        f = lb.flux.to_numpy(float)
        if align is not None:
            rf = lb.groupby("season").ref_flux.first().to_dict()
            f = align(f, lb.season.to_numpy(), rf)
        ii = np.array([idx[v] for v in lb.epoch.to_numpy()])
        y[bi, ii] = f
        e[bi, ii] = lb.err.to_numpy(float)
        t[ii] = mjd_to_year(lb.mjd.to_numpy(float))
        season[ii] = lb.season.to_numpy(int)
    good = np.isfinite(t)
    return LightCurve(t[good], season[good], y[:, good], e[:, good], ep[good])


# ----------------------------------------------------------------------------------------------
# the matched-filter scan


def _project(lc: LightCurve):
    """Per band: index of good epochs, weights, season-mean-removed data, and the group labels."""
    out = []
    ok = lc.ok
    for b in range(2):
        g = np.nonzero(ok[b])[0]
        if g.size < 5:
            out.append(None)
            continue
        w = 1.0 / lc.e[b, g] ** 2
        s = lc.season[g]
        yc = lc.y[b, g].copy()
        for ss in (0, 1):
            m = s == ss
            if m.any():
                yc[m] -= np.sum(w[m] * yc[m]) / np.sum(w[m])
        out.append((g, w, s, yc))
    return out


def _center_rows(H: np.ndarray, w: np.ndarray, s: np.ndarray) -> np.ndarray:
    """Remove the weighted mean of each season from every template row."""
    Hc = H.astype(np.float64, copy=True)
    for ss in (0, 1):
        m = s == ss
        if m.any():
            wm = w[m] / w[m].sum()
            Hc[:, m] -= (Hc[:, m] @ wm)[:, None]
    return Hc


def scan(lc: LightCurve, bank: Bank, return_all: bool = False) -> dict:
    """Best template of `bank` for `lc`: dchi2, amplitudes, chi2 of the fit, dof, F."""
    proj = _project(lc)
    dchi = np.zeros(bank.H.shape[0])
    amps = np.zeros((2, bank.H.shape[0]))
    chi2_null, n, n_groups = 0.0, 0, 0
    for b, p in enumerate(proj):
        if p is None:
            continue
        g, w, s, yc = p
        Hc = _center_rows(bank.H[:, g], w, s)
        num = Hc @ (w * yc)
        den = (Hc**2) @ w
        with np.errstate(divide="ignore", invalid="ignore"):
            a = np.where(den > 0, num / den, 0.0)
        a = np.where(a > 0, a, 0.0)
        dchi += a * num
        amps[b] = a
        chi2_null += float(np.sum(w * yc**2))
        n += g.size
        n_groups += np.unique(s).size
    k = int(np.argmax(dchi))
    dof = max(n - n_groups - 2 - 4, 1)
    chi2_fit = chi2_null - dchi[k]
    out = dict(dchi2=float(dchi[k]), chi2_null=chi2_null, chi2_fit=float(chi2_fit), dof=dof, n=n,
               F=float(dchi[k] / max(1.0, chi2_fit / dof)), i_best=k, params=bank.params[k].tolist(),
               amp_w1=float(amps[0, k]), amp_w2=float(amps[1, k]))
    if return_all:
        out["dchi2_all"] = dchi
        out["amps_all"] = amps
    return out


def sine_scan(lc: LightCurve, p_min_d: float = SINE_PMIN_D, p_max_yr: float = P_MAX) -> dict:
    """Best sinusoid (independent amplitude and phase per band, season offsets)."""
    t = lc.t
    base = max(t.max() - t.min(), 1.0)
    freqs = np.arange(1 / p_max_yr, YEAR_D / p_min_d, 1 / (5 * base))
    proj = _project(lc)
    dchi = np.zeros(freqs.size)
    for p in proj:
        if p is None:
            continue
        g, w, s, yc = p
        ph = 2 * np.pi * np.outer(freqs, t[g])
        C = _center_rows(np.cos(ph), w, s)
        S = _center_rows(np.sin(ph), w, s)
        a, bb, c = (C**2) @ w, (C * S) @ w, (S**2) @ w
        u, v = C @ (w * yc), S @ (w * yc)
        det = a * c - bb**2
        with np.errstate(divide="ignore", invalid="ignore"):
            q = np.where(det > 1e-12 * a * c, (c * u**2 - 2 * bb * u * v + a * v**2) / det, 0.0)
        dchi += q
    k = int(np.argmax(dchi))
    return dict(dchi2_sine=float(dchi[k]), P_sine_d=float(YEAR_D / freqs[k]))


def single_scan(lc: LightCurve) -> dict:
    r = scan(lc, single_bank(lc.t))
    return dict(dchi2_single=r["dchi2"], t_single=r["params"][1], taud_single=r["params"][3])


def design_cycles(lc: LightCurve, P, t0, tau_r, tau_d):
    """Cycle peak times that touch the data, and one profile per cycle evaluated at lc.t."""
    t = lc.t
    k0 = int(np.floor((t.min() - t0) / P)) - int(np.ceil(6 * tau_d / P)) - 1
    k1 = int(np.ceil((t.max() - t0) / P)) + 1
    cyc, cols = [], []
    for k in range(k0, k1 + 1):
        tp = t0 + k * P
        h = outburst_profile(t - tp, tau_r, tau_d)
        if h.max() > 0.05:
            cyc.append(tp)
            cols.append(h)
    return np.array(cyc), np.array(cols)


def cycle_fit(lc: LightCurve, P, t0, tau_r, tau_d, amp_w1, amp_w2, chi2_scale: float = 1.0) -> list[dict]:
    """Per-cycle scale alpha_k (1 = the global fit) with the colour fixed; season offsets free.
    sigma_k is scaled by sqrt(chi2_scale) (= max(1, chi2_fit/dof))."""
    cyc, cols = design_cycles(lc, P, t0, tau_r, tau_d)
    if cyc.size == 0:
        return []
    ok = lc.ok
    X, Y, W = [], [], []
    amps = (amp_w1, amp_w2)
    for b in range(2):
        g = np.nonzero(ok[b])[0]
        for i in g:
            row = np.zeros(cyc.size + 4)
            row[: cyc.size] = amps[b] * cols[:, i]
            row[cyc.size + 2 * b + lc.season[i]] = 1.0
            X.append(row)
            Y.append(lc.y[b, i])
            W.append(1 / lc.e[b, i] ** 2)
    X, Y, W = np.array(X), np.array(Y), np.array(W)
    keep = np.abs(X).sum(0) > 0
    Xk = X[:, keep]
    A = Xk.T @ (Xk * W[:, None])
    try:
        cov = np.linalg.pinv(A)
    except np.linalg.LinAlgError:
        return []
    p = cov @ (Xk.T @ (W * Y))
    full = np.full(X.shape[1], np.nan)
    sig = np.full(X.shape[1], np.nan)
    full[keep] = p
    sig[keep] = np.sqrt(np.clip(np.diag(cov), 0, None)) * np.sqrt(max(chi2_scale, 1.0))
    out = []
    for k, tp in enumerate(cyc):
        a, s = full[k], sig[k]
        covered = bool(np.isfinite(s) and s <= 1 / 3)
        det = bool(np.isfinite(s) and s > 0 and a / s >= CYCLE_SIG)
        out.append(dict(t_peak=float(tp), alpha=float(a), sigma=float(s), snr=float(a / s) if s > 0 else np.nan,
                        covered=covered, detected=det, missing=bool(covered and a + 2 * s < 0.5),
                        n_epochs=int(np.sum(cols[k] > 0.3))))
    return out


def season_check(lc: LightCurve, h: np.ndarray, amp_w1: float, amp_w2: float) -> dict:
    """Template amplitude fitted separately in each visit season (both bands, colour fixed):
    the outburst must be there in both seasons' difference images."""
    out = {}
    ok = lc.ok
    amps = (amp_w1, amp_w2)
    for ss in (0, 1):
        num = den = 0.0
        for b in range(2):
            g = np.nonzero(ok[b] & (lc.season == ss))[0]
            if g.size < 3 or amps[b] <= 0:
                continue
            w = 1 / lc.e[b, g] ** 2
            x = amps[b] * h[g]
            x = x - np.sum(w * x) / w.sum()
            yy = lc.y[b, g] - np.sum(w * lc.y[b, g]) / w.sum()
            num += np.sum(w * x * yy)
            den += np.sum(w * x * x)
        out[f"alpha_s{ss}"] = float(num / den) if den > 0 else np.nan
        out[f"snr_s{ss}"] = float(num / np.sqrt(den)) if den > 0 else np.nan
    return out


def analyse(lc: LightCurve, extended: bool = True) -> dict:
    """Everything except the nulls: best periodic template, F, amplitudes, cycles, seasons, single
    outburst, sinusoid, time-reversed asymmetry."""
    bank = periodic_bank(lc.t)
    r = scan(lc, bank)
    P, t0, tr, td = r["params"]
    out = dict(P_yr=P, t0=t0, tau_r=tr, tau_d=td, F=r["F"], dchi2=r["dchi2"], chi2_fit=r["chi2_fit"], dof=r["dof"],
               chi2r_fit=r["chi2_fit"] / r["dof"], chi2r_null=r["chi2_null"] / max(r["n"] - 4, 1), n=r["n"],
               amp_w1=r["amp_w1"], amp_w2=r["amp_w2"])
    if not extended:
        return out
    scale = max(1.0, r["chi2_fit"] / r["dof"])
    cyc = cycle_fit(lc, P, t0, tr, td, r["amp_w1"], r["amp_w2"], scale)
    det = [c for c in cyc if c["detected"]]
    out.update(cycles=cyc, n_cycles_det=len(det), n_cycles_covered=sum(c["covered"] for c in cyc),
               n_cycles_missing=sum(c["missing"] for c in cyc),
               peaks_det=[round(c["t_peak"], 2) for c in det],
               cycle_snr2=float(sorted([c["snr"] for c in cyc if np.isfinite(c["snr"])] + [0, 0])[-2]))
    h = periodic_template(lc.t, P, t0, tr, td)
    out.update(season_check(lc, h, r["amp_w1"], r["amp_w2"]))
    out.update(single_scan(lc))
    out.update(sine_scan(lc))
    rr = scan(lc, periodic_bank(lc.t, reverse=True))
    sh = scan(lc, short_bank(lc.t))
    out["dchi2_short"], out["P_short_d"] = sh["dchi2"], sh["params"][0] * YEAR_D
    # > 0: the long-period outburst train beats every Mira-like short-period train (aliases included)
    out["A"] = (out["dchi2"] - sh["dchi2"]) / scale
    out["Z"] = shape_test(lc, P)["Z"]
    out["R"] = (out["dchi2"] - out["dchi2_single"]) / scale
    out["S"] = (out["dchi2"] - out["dchi2_sine"]) / scale
    out["asym"] = (out["dchi2"] - rr["dchi2"]) / scale
    # FWHM duty cycle of the profile
    out["duty"] = float(min(1.0, (tr / 2 + td * np.log(2)) / P))
    # colour of the outburst light (Vega W1-W2) if both amplitudes are positive (nanomaggies)
    out["colour"] = float(-2.5 * np.log10(r["amp_w1"] / r["amp_w2"])) if r["amp_w1"] > 0 and r["amp_w2"] > 0 else np.nan
    return out


# ----------------------------------------------------------------------------------------------
# shape at a fixed period: flat-minimum outbursts or continuous (sinusoidal) pulsation?


def fixed_period_banks(t, P: float) -> tuple[Bank, Bank]:
    """At period P: (sharp outburst trains with FWHM/P <= SHARP_DUTY, sinusoids 0.5(1 + cos)), phase on a
    0.02 P grid. Both families share one phase across all bands, so they have the same freedom."""
    t = np.asarray(t, float)
    t0 = t.min() + np.arange(0, P, 0.02 * P)
    rows, H = [], []
    for tr in (0.05, 0.1, 0.2):
        for td in (0.05, 0.1, 0.15, 0.25):
            tau_r, tau_d = tr * P, td * P
            if (tau_r / 2 + tau_d * np.log(2)) / P > SHARP_DUTY:
                continue
            rows.append(np.c_[np.full(t0.size, P), t0, np.full(t0.size, tau_r), np.full(t0.size, tau_d)])
            H.append(train_profile(t[None, :], P, t0[:, None], tau_r, tau_d))
    sharp = Bank(t, np.vstack(rows), np.vstack(H).astype(np.float32), "sharp")
    sine = Bank(t, np.c_[np.full(t0.size, P), t0, np.zeros(t0.size), np.zeros(t0.size)],
                (0.5 * (1 + np.cos(2 * np.pi * (t[None, :] - t0[:, None]) / P))).astype(np.float32), "sine")
    return sharp, sine


def shape_test(lc_or_series, P: float) -> dict:
    """Z = (dchi2_sharp - dchi2_sine) / max(1, chi2_fit/dof) at period P. Z > 0: the data prefer
    outbursts with a flat minimum; Z < 0: a continuous, sinusoid-like variation (pulsation). Works on a
    LightCurve (WISE) or a list of Series (WISE + Spitzer)."""
    if isinstance(lc_or_series, LightCurve):
        sharp, sine = fixed_period_banks(lc_or_series.t, P)
        a, b = scan(lc_or_series, sharp), scan(lc_or_series, sine)
    else:
        t = np.concatenate([s.t for s in lc_or_series])
        sharp, sine = fixed_period_banks(t, P)
        a, b = fit_series(lc_or_series, sharp), fit_series(lc_or_series, sine)
    scale = max(1.0, min(a["chi2_fit"], b["chi2_fit"]) / a["dof"])
    return dict(Z=(a["dchi2"] - b["dchi2"]) / scale, dchi2_sharp=a["dchi2"], dchi2_sinefix=b["dchi2"])


# ----------------------------------------------------------------------------------------------
# nulls


def _best_F(lc: LightCurve, bank: Bank) -> float:
    return scan(lc, bank)["F"]


def shuffle_null(lc: LightCurve, n: int = 200, seed: int = 0, bank: Bank | None = None) -> np.ndarray:
    """Best F of n within-season epoch permutations (same permutation in both bands)."""
    rng = np.random.default_rng(seed)
    bank = bank or periodic_bank(lc.t)
    out = np.empty(n)
    for i in range(n):
        perm = np.arange(lc.t.size)
        for ss in (0, 1):
            m = np.nonzero(lc.season == ss)[0]
            perm[m] = rng.permutation(m)
        sh = LightCurve(lc.t, lc.season, lc.y[:, perm], lc.e[:, perm], lc.epoch)
        out[i] = _best_F(sh, bank)
    return out


def _season_offsets_removed(lc: LightCurve) -> np.ndarray:
    y = lc.y.copy()
    for b in range(2):
        for ss in (0, 1):
            m = (lc.season == ss) & lc.ok[b]
            if m.any():
                w = 1 / lc.e[b, m] ** 2
                y[b, m] -= np.sum(w * y[b, m]) / w.sum()
    return y


def phase_null(lc: LightCurve, n: int = 200, seed: int = 0, bank: Bank | None = None, t_split: float = 2013.0) -> np.ndarray:
    """Best F of n Fourier phase-randomised surrogates. The NEOWISE epochs (after t_split; evenly
    spaced at half a year) are randomised as one series per band with shared random phases; the few
    2010-11 epochs are permuted among themselves. Missing points are filled by linear interpolation
    for the transform and blanked again afterwards."""
    rng = np.random.default_rng(seed)
    bank = bank or periodic_bank(lc.t)
    y0 = _season_offsets_removed(lc)
    late = np.nonzero(lc.t > t_split)[0]
    early = np.nonzero(lc.t <= t_split)[0]
    ok = lc.ok
    filled = np.zeros((2, late.size))
    for b in range(2):
        m = ok[b, late]
        if m.sum() < 4:
            filled[b] = 0.0
        else:
            filled[b] = np.interp(lc.t[late], lc.t[late][m], y0[b, late][m])
    mean = filled.mean(1, keepdims=True)
    Fz = np.fft.rfft(filled - mean, axis=1)
    out = np.empty(n)
    for i in range(n):
        ph = rng.uniform(0, 2 * np.pi, Fz.shape[1])
        ph[0] = 0.0
        if late.size % 2 == 0:
            ph[-1] = 0.0
        sur = np.fft.irfft(Fz * np.exp(1j * ph)[None, :], n=late.size, axis=1) + mean
        y = y0.copy()
        y[:, late] = np.where(ok[:, late], sur, np.nan)
        if early.size > 1:
            pe = rng.permutation(early)
            y[:, early] = y0[:, pe]
            e = lc.e.copy()
            e[:, early] = lc.e[:, pe]
        else:
            e = lc.e
        out[i] = _best_F(LightCurve(lc.t, lc.season, y, e, lc.epoch), bank)
    return out


def p_value(null: np.ndarray, obs: float) -> float:
    """(1 + #null >= obs) / (1 + n): never zero."""
    return float((1 + np.sum(np.asarray(null) >= obs)) / (1 + len(null)))


# ----------------------------------------------------------------------------------------------
# injection


def inject(lc: LightCurve, P: float, t0: float, tau_r: float, tau_d: float, amp_w1: float, amp_w2: float) -> LightCurve:
    """Add a periodic outburst train (amplitudes in the light curve's flux units) to a real light curve."""
    h = periodic_template(lc.t, P, t0, tau_r, tau_d)
    y = lc.y + np.array([amp_w1, amp_w2])[:, None] * h[None, :]
    return LightCurve(lc.t, lc.season, y, lc.e, lc.epoch)


# ----------------------------------------------------------------------------------------------
# several instruments at once (WISE W1/W2 + Spitzer IRAC [3.6]/[4.5], 2004-2024)


@dataclass
class Series:
    """One band of one instrument: times (yr), values, errors, and an integer offset group per point
    (visit season for WISE; cryogenic/warm mission for IRAC). Each series has its own amplitude >= 0."""

    name: str
    t: np.ndarray
    y: np.ndarray
    e: np.ndarray
    group: np.ndarray

    def clean(self) -> Series:
        ok = np.isfinite(self.t) & np.isfinite(self.y) & np.isfinite(self.e) & (self.e > 0)
        return Series(self.name, self.t[ok], self.y[ok], self.e[ok], np.asarray(self.group)[ok])


def series_from_lc(lc: LightCurve) -> list[Series]:
    return [Series(f"W{b + 1}", lc.t, lc.y[b], lc.e[b], lc.season).clean() for b in range(2)]


def _center_groups(H: np.ndarray, w: np.ndarray, grp: np.ndarray) -> np.ndarray:
    Hc = H.astype(np.float64, copy=True)
    for gg in np.unique(grp):
        m = grp == gg
        wm = w[m] / w[m].sum()
        Hc[..., m] -= (Hc[..., m] @ wm)[..., None]
    return Hc


def series_bank(series: list[Series], reverse: bool = False, p_max: float = P_MAX) -> Bank:
    """Periodic templates evaluated at the concatenated times of `series` (in order)."""
    t = np.concatenate([s.t for s in series])
    key = ("ser", reverse, p_max, tuple(np.round(t, 4)))
    if key in _BANKS:
        return _BANKS[key]
    base = t.max() - t.min()
    rows, H = [], []
    for P in period_grid(base, p_max=p_max):
        for tr, td in SHAPES:
            if td > P / TAU_D_MAX_FRAC or tr > P / 3:
                continue
            t0 = t.min() + np.arange(0, P, T0_STEP)
            rows.append(np.c_[np.full(t0.size, P), t0, np.full(t0.size, tr), np.full(t0.size, td)])
            H.append(train_profile(t[None, :], P, t0[:, None], tr, td, reverse).astype(np.float32))
    b = Bank(t, np.vstack(rows), np.vstack(H), "series")
    _BANKS[key] = b
    return b


def fit_series(series: list[Series], bank: Bank | None = None, return_all: bool = False) -> dict:
    """Best periodic outburst train for several series at once (amplitude >= 0 and offsets per
    group in each series). Same statistic as `scan`."""
    bank = bank or series_bank(series)
    dchi = np.zeros(bank.H.shape[0])
    amps = np.zeros((len(series), bank.H.shape[0]))
    chi2_null, n, n_groups, j = 0.0, 0, 0, 0
    for i, s in enumerate(series):
        cols = slice(j, j + s.t.size)
        j += s.t.size
        if s.t.size < 3:
            continue
        w = 1 / s.e**2
        yc = _center_groups(s.y[None, :], w, s.group)[0]
        Hc = _center_groups(bank.H[:, cols], w, s.group)
        num = Hc @ (w * yc)
        den = (Hc**2) @ w
        with np.errstate(divide="ignore", invalid="ignore"):
            a = np.where(den > 0, num / den, 0.0)
        a = np.where(a > 0, a, 0.0)
        dchi += a * num
        amps[i] = a
        chi2_null += float(np.sum(w * yc**2))
        n += s.t.size
        n_groups += np.unique(s.group).size
    k = int(np.argmax(dchi))
    dof = max(n - n_groups - len(series) - 4, 1)
    chi2_fit = chi2_null - dchi[k]
    out = dict(dchi2=float(dchi[k]), chi2_null=chi2_null, chi2_fit=float(chi2_fit), dof=dof, n=n,
               F=float(dchi[k] / max(1.0, chi2_fit / dof)), params=bank.params[k].tolist(),
               amps={s.name: float(amps[i, k]) for i, s in enumerate(series)})
    if return_all:
        out["dchi2_all"] = dchi
        out["params_all"] = bank.params
    return out


def period_profile(fit_all: dict, scale: float) -> dict:
    """Best dchi2 per trial period, and the 1-sigma period range (dchi2 within `scale` of the best,
    scale = max(1, chi2_fit/dof))."""
    P = fit_all["params_all"][:, 0]
    d = fit_all["dchi2_all"]
    up = np.unique(P)
    best = np.array([d[P == p].max() for p in up])
    ok = best >= best.max() - scale
    return dict(P=up, best=best, P_lo=float(up[ok].min()), P_hi=float(up[ok].max()))


def cycles_series(series: list[Series], P, t0, tau_r, tau_d, amps: dict, chi2_scale: float = 1.0) -> list[dict]:
    """Per-cycle scales alpha_k over all series (each series' amplitude fixed at the global fit)."""
    t = np.concatenate([s.t for s in series])
    k0 = int(np.floor((t.min() - t0) / P)) - int(np.ceil(6 * tau_d / P)) - 1
    k1 = int(np.ceil((t.max() - t0) / P)) + 1
    tps = [t0 + k * P for k in range(k0, k1 + 1)]
    tps = [tp for tp in tps if outburst_profile(t - tp, tau_r, tau_d).max() > 0.05]
    if not tps:
        return []
    ng = [np.unique(s.group) for s in series]
    n_off = sum(g.size for g in ng)
    X, Y, W = [], [], []
    off0 = 0
    for s, gs in zip(series, ng, strict=False):
        A = amps.get(s.name, 0.0)
        for i in range(s.t.size):
            row = np.zeros(len(tps) + n_off)
            row[: len(tps)] = [A * outburst_profile(np.r_[s.t[i] - tp], tau_r, tau_d)[0] for tp in tps]
            row[len(tps) + off0 + int(np.searchsorted(gs, s.group[i]))] = 1.0
            X.append(row)
            Y.append(s.y[i])
            W.append(1 / s.e[i] ** 2)
        off0 += gs.size
    X, Y, W = np.array(X), np.array(Y), np.array(W)
    keep = np.abs(X).sum(0) > 0
    cov = np.linalg.pinv(X[:, keep].T @ (X[:, keep] * W[:, None]))
    p = cov @ (X[:, keep].T @ (W * Y))
    full = np.full(X.shape[1], np.nan)
    sig = np.full(X.shape[1], np.nan)
    full[keep] = p
    sig[keep] = np.sqrt(np.clip(np.diag(cov), 0, None)) * np.sqrt(max(chi2_scale, 1.0))
    out = []
    for k, tp in enumerate(tps):
        a, s_ = full[k], sig[k]
        covered = bool(np.isfinite(s_) and s_ <= 1 / 3)
        out.append(dict(t_peak=float(tp), alpha=float(a), sigma=float(s_), snr=float(a / s_) if s_ > 0 else np.nan,
                        covered=covered, detected=bool(np.isfinite(s_) and s_ > 0 and a / s_ >= CYCLE_SIG),
                        missing=bool(covered and a + 2 * s_ < 0.5),
                        instruments=sorted({s.name for s in series
                                            if (outburst_profile(s.t - tp, tau_r, tau_d) > 0.3).any()})))
    return out


def shuffle_series_null(series: list[Series], n: int = 200, seed: int = 0, bank: Bank | None = None) -> np.ndarray:
    """Best F of n surrogates with the points of each series permuted within their offset groups."""
    rng = np.random.default_rng(seed)
    bank = bank or series_bank(series)
    out = np.empty(n)
    for i in range(n):
        sh = []
        for s in series:
            perm = np.arange(s.t.size)
            for gg in np.unique(s.group):
                m = np.nonzero(s.group == gg)[0]
                perm[m] = rng.permutation(m)
            sh.append(Series(s.name, s.t, s.y[perm], s.e[perm], s.group))
        out[i] = fit_series(sh, bank)["F"]
    return out


# ----------------------------------------------------------------------------------------------
# decision


def light_verdict(a: dict, f_min: float = F_MIN, s_min: float = S_MIN) -> tuple[str, list[str]]:
    """Light-curve-only verdict: ('recurrent', []) or ('rejected', reasons) / ('weak', reasons).
    Nulls and context vetoes are added by `verdict`."""
    why = []
    if a.get("F", 0) < f_min:
        why.append("weak")
    if a.get("n_cycles_det", 0) < 2:
        why.append("single-outburst" if a.get("n_cycles_det", 0) == 1 else "no-cycle")
    s = a.get("S", 0)
    if s < s_min and a.get("P_sine_d", np.inf) < LPV_P_D:
        why.append("lpv-sinusoid")
    if a.get("P_yr", np.inf) < P_ALIAS_MIN:
        why.append("mira-alias")
    for ss in (0, 1):
        if np.nan_to_num(a.get(f"snr_s{ss}", 0.0)) < 2.0:
            why.append("one-season")
            break
    if a.get("amp_w2", 0) <= 0 and a.get("amp_w1", 0) <= 0:
        why.append("no-amplitude")
    return ("recurrent" if not why else ("weak" if why == ["weak"] else "rejected")), why


def verdict(a: dict, p_shuffle: float | None = None, context_flags: list[str] | None = None,
            f_min: float = F_MIN, p_max: float = P_SHUFFLE_MAX) -> tuple[str, list[str]]:
    """Final verdict: 'candidate' (recurrent, significant, no veto), 'flagged' (recurrent and
    significant with a soft flag), or 'rejected', with reasons."""
    v, why = light_verdict(a, f_min)
    if p_shuffle is not None and p_shuffle > p_max:
        why.append("shuffle-null")
    hard = {"moving", "core", "saturated", "neighbour", "foreground-star", "empty-sky", "tile-systematic"}
    soft = []
    for f in context_flags or []:
        (why if f in hard else soft).append(f)
    # a period an AGB/OH-IR star can have, and no preference for flat-minimum outbursts over a sinusoid:
    # the WISE light curve alone cannot tell this from a long-period dusty pulsator (the Spitzer test can)
    if a.get("P_yr", np.inf) < P_AGB_MAX and a.get("Z", np.inf) < Z_SHARP:
        soft.append("agb-compatible")
    if a.get("n_cycles_missing", 0) > 0:
        soft.append("missing-cycle")
    if why:
        return "rejected", why + soft
    return ("flagged" if soft else "candidate"), soft
