"""Grade the pre-registered forecasts for the Gaia DR4-day searches (hunts/H-0014/predictions/dr4_search_forecast.md).

Run from the repo root, after the DR4-day pipeline (scripts/dr4_day.py --release dr4) has written its outputs:
    uv run python -I hunts/H-0014/predictions/dr4_search_grade.py                 # grade against Gaia DR4
    uv run python -I hunts/H-0014/predictions/dr4_search_grade.py --self-test     # Gaia DR3 as the stand-in (dry run)

It reads only the pipeline's outputs and the sealed sample, and writes only to <run>/forecast_grade/ (default run directory:
~/oddsky-runs/h0014/<release>, else hunts/H-0014/<release dir>). It never writes into hunts/H-0014/predictions/.

Inputs (all written by src/oddsky/dr4day/pipeline.py):
  <run>/catalogue/lens_catalogue.csv   the release's microlensing catalogue (gaiadr4.vari_microlensing; section 1 of the text)
  <run>/catalogue/target_flags.csv     which of our (mapped) ids the release knows (identity check)
  <run>/idmap.csv                      DR3 -> release ids (nearest within 0.5" and 0.3 mag; not applied for the stand-in)
  <run>/epoch_status.csv               per source: ok / absent / error / missing (archive says it has epoch photometry)
  <run>/search/metrics.csv             per-source light-curve analysis (bright_eps = "t_peak:dG_peak:n;...")
  <run>/epoch/<release id>.csv         epoch photometry cache (gaia_epoch.to_series format)

The forecasts (sample: dr4_search_sample.csv, one row per item; the column `forecast` says which):
  F1  How many of H-0010's 67 classifier-only MICROLENSING sources are in the release's microlensing catalogue (13-36).
  F2  Among the 39 of them no survey catalogued, does Oddsky's sealed P(lens) rank catalogue membership the way the catalogue's
      selection does (AUC > 0.60)?
  F3  Of H-0010's 21 first-pass lens candidates, how many fail DR4's single-event test (2-6)?
  F4  Of the 61 strong NEOWISE events in DR4's span not already Gaia-confirmed, how many does the catalogue list at the NEOWISE
      time (2-6)?
  F5  Unclassified NEOWISE brightenings (blind sample): does Gaia DR4 brighten at the NEOWISE time more often than at control
      times one and two years away (sealed ensemble rule)? Excess > 0 with p < 0.05 (signs flipped per Gaia star).

Every graded bound is fixed in GRADED. `model_*` are the forecasts' Monte Carlos; work/forecast.py calls them to make the sealed
numbers, and this grader calls them (same seeds) only to report the model's probability of the fixed bounds when some F3 items
cannot be tested.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SAMPLE = HERE / "dr4_search_sample.csv"
FORECAST = HERE / "work" / "forecast.json"
ENSEMBLE_GRADER = ROOT / "hunts/H-0009/predictions/dr4_ensemble_grade.py"

# Release facts the rules need. "f3_new_after" is where the light curve's new information starts: 30 d after Gaia DR3's last
# transit for DR4. For the DR3 stand-in (self-test only) the DR3 span is split at its middle so the code path runs.
RELEASES = {
    "dr4": dict(name="Gaia DR4", span=(56863.44, 58868.92), f3_new_after=57931.0, stand_in=False, run_subdir="dr4"),
    "dr3": dict(name="Gaia DR3", span=(56863.0, 57901.0), f3_new_after=57382.0, stand_in=True, run_subdir="dryrun_dr3"),
}

# The graded statements (fixed; never recomputed).
GRADED = dict(F1=(13, 36), F2=0.60, F3=(2, 6), F4=(2, 6), F5_alpha=0.05)

RULES = dict(
    id_pos_arcsec=0.5,          # F1: positional fallback to the release catalogue (same radius as the id map)
    f1_min_identity=60,         # F1/F2: not yet resolvable if fewer than 60 of the 67 have a DR4 identity
    f4_pos_arcsec=3.0,          # F4: catalogue lens within 3" of the AllWISE position ...
    f4_min_dt=60.0,             # ... and |tmax - t_NEOWISE| <= max(60 d, min(2 tE, 365 d))
    f4_max_dt=365.0,
    f4_tmax_median=(56000.0, 59500.0),   # F4: the catalogue's median peak time (MJD) must lie here, else not yet resolvable
    f3_repro_dt=45.0,           # F3: a DR4 brightening episode peaking within 45 d of the DR3 Gaia peak ...
    f3_repro_dg=-0.15,          # ... with its peak transit at least 0.15 mag brighter than baseline
    f3_rep_dg=-0.30,            # F3: a new episode whose peak transit is at least 0.30 mag brighter ...
    f3_rep_n=3,                 # ... made of at least 3 transits beyond the episode threshold max(4 sigma, 0.08 mag) ...
    f3_rep_sep=200.0,           # ... peaking at least 200 d from the DR3 peak and after f3_new_after
    f3_min_new_transits=10,     # F3: at least 10 valid G transits after f3_new_after to test for a repeat
    f3_min_testable=15,         # F3 is void if fewer than 15 of the 21 are testable
    f5_offsets=(-730.5, -365.25, 365.25, 730.5),   # F5 control times (d from the NEOWISE time), used when inside the span
    f5_min_pairs=150,           # F5 is void with fewer than 150 events testable at the NEOWISE time and >= 1 control time
    f5_perm=20000, f5_seed=20261202,
)

# Column look-up lists for the catalogue (dr4_search_forecast.md section 6 item 1: names may be appended, nothing else).
COLUMNS = dict(
    source_id=["source_id"],
    ra=["ra"],
    dec=["dec"],
    tmax=["paczynski0_tmax", "paczynski1_tmax"],     # always converted with to_mjd (never the pipeline's derived tmax_mjd)
    tE=["paczynski0_te", "paczynski1_te"],
)
INCOMPLETE_EPOCH = ("error", "missing")   # epoch_status values that make F3/F5 not yet resolvable

MC_N = 20000
MC_SEED = 20261102

# The forecasts' parameters (dr4_search_forecast.md section 3). Shared by F1, F2 and F4: one catalogue, one selection.
PARAMS = dict(
    c0=(3.0, 3.5),        # Beta: catalogue completeness for a real single-lens event the DR3 classifier labelled microlensing ...
    c0_low=(1.0, 8.0),    # ... mixed with a low-completeness scenario (DR4 repeats DR3's cuts), Beta(1, 8) ...
    c0_low_w=0.25,        # ... with weight 0.25
    f0=(1.5, 13.5),       # Beta: inclusion probability for a non-lens with a lens-like DR3 light curve
    c_cap=0.95,
    f3_r0=(0.10, 0.35),   # uniform: P(a non-lens one-off brightener shows another >= 0.3 mag episode in 2017.5-2020.0)
    f3_mrepro=(0.5, 2.0),  # uniform: shared multiplier on the per-source "not reproduced" probabilities
    f5_q_on=(2.0, 18.0),  # Beta: fraction of events with a real optical brightening of the Gaia star at the NEOWISE time
    f5_s=(0.35, 0.70),    # uniform: P(pass | real brightening, resolved)
    f5_n0=(0.005, 0.03),  # uniform: P(pass) of a flat star at any time (noise, crowding)
    f5_v=(1.5, 48.5),     # Beta: fraction of strongly variable Gaia stars (pass at random times)
    f5_pv=(0.10, 0.40),   # uniform: P(pass) of such a variable at a random time
    f5_res=0.85,          # P(an epoch is testable: >= 2 transits within +-30 d and >= 10 baseline)
)


# ----------------------------------------------------------------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------------------------------------------------------------
def load_sample(path: Path = SAMPLE) -> pd.DataFrame:
    s = pd.read_csv(path, dtype={"source_id": str, "alt_source_id": str})
    for c in ("source_id", "alt_source_id"):
        s[c] = s[c].fillna("")
    return s


def sid(x) -> str:
    """A Gaia source id as a string ("" for missing). Never through float: 19-digit ids lose precision."""
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return ""
    s = str(x).strip()
    if s.endswith(".0") and s[:-2].isdigit():
        s = s[:-2]
    return s if s.isdigit() else ""


def to_mjd(v: pd.Series) -> pd.Series:
    """Peak times to MJD whatever the zero point: Gaia's BJD(TCB) - 2455197.5 (DR3), MJD, or JD."""
    x = pd.to_numeric(v, errors="coerce").astype(float)
    out = x.copy()
    gaia = (x > 0) & (x < 20000)
    jd = x > 2.0e6
    out[gaia] = x[gaia] + 55197.0
    out[jd] = x[jd] - 2400000.5
    return out


def first_col(df: pd.DataFrame, names: list[str]) -> str | None:
    return next((n for n in names if n in df.columns), None)


def catalogue_frame(path: Path) -> pd.DataFrame:
    """The release's microlensing catalogue, normalised to source_id (str), ra, dec, tmax_mjd, tE. Columns are found through
    the COLUMNS look-up lists only. The peak time always comes from the raw catalogue column through to_mjd."""
    raw = pd.read_csv(path, dtype=str)
    scol = first_col(raw, COLUMNS["source_id"])
    if scol is None:
        raise KeyError(f"{path}: no source-id column among {COLUMNS['source_id']}")
    d = pd.DataFrame({"source_id": raw[scol].map(sid)})
    for k in ("ra", "dec"):
        c = first_col(raw, COLUMNS[k])
        d[k] = pd.to_numeric(raw[c], errors="coerce") if c else np.nan
    tcol, ecol = first_col(raw, COLUMNS["tmax"]), first_col(raw, COLUMNS["tE"])
    d["tmax_mjd"] = to_mjd(raw[tcol]) if tcol else np.nan
    d["tE"] = pd.to_numeric(raw[ecol], errors="coerce") if ecol else np.nan
    d = d[d.source_id != ""].reset_index(drop=True)
    d.attrs["time_column"] = tcol
    return d


def idmap_dict(run: Path, rel: dict) -> dict:
    """DR3 id -> release id. The stand-in's map is not a valid map (pipeline.Run.idm), so DR3 ids are used as they are."""
    p = run / "idmap.csv"
    if rel["stand_in"] or not p.exists():
        return {}
    m = pd.read_csv(p, dtype={"dr3_source_id": str, "new_source_id": str})
    return {sid(a): sid(b) for a, b in zip(m.dr3_source_id, m.new_source_id, strict=True) if sid(a) and sid(b)}


def known_ids(run: Path) -> set:
    """Release ids the archive answered for (target_flags.csv); empty if the file is missing."""
    p = run / "catalogue" / "target_flags.csv"
    if not p.exists() or p.stat().st_size <= 1:
        return set()
    f = pd.read_csv(p, dtype={"source_id": str})
    return {sid(x) for x in f.get("source_id", pd.Series(dtype=str))}


def epoch_status(run: Path) -> dict | None:
    """release id -> epoch status (pipeline epoch_status.csv); None if the file is missing."""
    p = run / "epoch_status.csv"
    if not p.exists():
        return None
    st = pd.read_csv(p, dtype={"release_source_id": str})
    return {sid(a): str(b) for a, b in zip(st.release_source_id, st.status, strict=True)}


def epoch_completeness(status: dict | None, ids: list[str]) -> list[str]:
    """Problems that make a light-curve forecast not yet resolvable: no epoch_status.csv, a sample source the epochs stage never
    reached, or a source whose request failed ('error') or came back empty although the archive says it has epoch photometry
    ('missing ...'). An empty list means the run is complete for these sources."""
    if status is None:
        return ["no epoch_status.csv"]
    out = []
    for i in ids:
        s = status.get(i)
        if s is None:
            out.append(f"{i}: not in epoch_status.csv")
        elif s.startswith(INCOMPLETE_EPOCH):
            out.append(f"{i}: {s}")
    return out


def sep_arcsec(ra1, dec1, ra2, dec2) -> np.ndarray:
    ra1, dec1, ra2, dec2 = (np.radians(np.asarray(x, float)) for x in (ra1, dec1, ra2, dec2))
    c = np.sin(dec1) * np.sin(dec2) + np.cos(dec1) * np.cos(dec2) * np.cos(ra2 - ra1)
    return np.degrees(np.arccos(np.clip(c, -1, 1))) * 3600


def parse_eps(s) -> list[tuple[float, float, int]]:
    """metrics.csv bright_eps: 't_peak:dG_peak:n;...' -> [(t_peak, dG_peak, n), ...]."""
    if not isinstance(s, str) or not s.strip():
        return []
    out = []
    for part in s.split(";"):
        bits = part.split(":")
        if len(bits) >= 3:
            try:
                out.append((float(bits[0]), float(bits[1]), int(float(bits[2]))))
            except ValueError:
                continue
    return out


def valid_g(df: pd.DataFrame) -> pd.DataFrame:
    """Valid G transits (not flagged rejected_by_photometry, finite time and magnitude), one per transit id."""
    ok = ((df.flag.astype(str) != "rejected_by_photometry") & np.isfinite(df.mag.astype(float))
          & np.isfinite(df.t_mjd.astype(float)) & (df.band == "G"))
    return df[ok].groupby("camera", as_index=False).agg(t_mjd=("t_mjd", "first"), mag=("mag", "median"))


def read_epoch(run: Path, release_id: str) -> pd.DataFrame | None:
    p = run / "epoch" / f"{release_id}.csv"
    if not p.exists():
        return None
    return pd.read_csv(p, dtype={"camera": str})


def auc_mw(score, y) -> tuple[float, float]:
    """AUC of `score` for binary outcome `y` (ties count one half) and the one-sided Mann-Whitney p-value (normal
    approximation with tie correction and continuity correction). (nan, nan) if y is all 0 or all 1."""
    from scipy.stats import mannwhitneyu
    score, y = np.asarray(score, float), np.asarray(y, bool)
    pos, neg = score[y], score[~y]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan"), float("nan")
    r = mannwhitneyu(pos, neg, alternative="greater", method="asymptotic", use_continuity=True)
    return float(r.statistic / (len(pos) * len(neg))), float(r.pvalue)


def auc_fast(score: np.ndarray, y: np.ndarray) -> float:
    pos, neg = score[y], score[~y]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    gt = (pos[:, None] > neg[None, :]).sum() + 0.5 * (pos[:, None] == neg[None, :]).sum()
    return float(gt / (len(pos) * len(neg)))


def summary(x: np.ndarray, bounds: tuple[int, int] | None = None) -> dict:
    x = np.asarray(x, float)
    out = dict(mean=round(float(x.mean()), 3), median=float(np.percentile(x, 50, method="lower")),
               p10=float(np.percentile(x, 10, method="lower")), p90=float(np.percentile(x, 90, method="higher")))
    if bounds is not None:
        out["bounds"] = list(bounds)
        out["p_hit"] = round(float(np.mean((x >= bounds[0]) & (x <= bounds[1]))), 3)
        out["p_below"] = round(float(np.mean(x < bounds[0])), 3)
        out["p_above"] = round(float(np.mean(x > bounds[1])), 3)
    return out


def ensemble_rule():
    """The sealed H-0009 ensemble grader as a module, for its grade_series (read-only)."""
    spec = importlib.util.spec_from_file_location("dr4_ensemble_grade_ro", ENSEMBLE_GRADER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ----------------------------------------------------------------------------------------------------------------------------
# The forecasts' Monte Carlos
# ----------------------------------------------------------------------------------------------------------------------------
def _cat_draws(rng, n):
    hi = rng.beta(*PARAMS["c0"], n)
    lo = rng.beta(*PARAMS["c0_low"], n)
    c0 = np.where(rng.random(n) < PARAMS["c0_low_w"], lo, hi)
    return c0, rng.beta(*PARAMS["f0"], n)


def model_f1(s: pd.DataFrame, n: int = MC_N, seed: int = MC_SEED, use: np.ndarray | None = None) -> dict:
    """F1 count and F2 AUC over the 67 (rows of forecast F1). Each source is a lens with P = p_lens; a lens is catalogued with
    c = min(cap, c0 * cat_mult), a non-lens with f0 * f_mult; c0 and f0 are shared (one catalogue)."""
    s = s.reset_index(drop=True)
    use = np.ones(len(s), bool) if use is None else np.asarray(use, bool)
    rng = np.random.default_rng(seed)
    c0, f0 = _cat_draws(rng, n)
    pl = s.p_lens.to_numpy(float)
    cm, fm = s.cat_mult.to_numpy(float), s.f_mult.to_numpy(float)
    lens = rng.random((n, len(s))) < pl
    c = np.minimum(PARAMS["c_cap"], c0[:, None] * cm)
    f = np.minimum(PARAMS["c_cap"], f0[:, None] * fm)
    inc = rng.random((n, len(s))) < np.where(lens, c, f)
    inc &= use
    f2 = (s.f2_member.to_numpy(bool)) & use
    score = pl[f2]
    aucs = np.array([auc_fast(score, inc[i, f2]) for i in range(n)])
    p_in = np.where(use, (pl * c + (1 - pl) * f).mean(0), np.nan)
    return dict(count=inc.sum(1), auc=aucs, p_in=p_in, inc=inc, f2=f2, c0=c0)


def model_f3(s: pd.DataFrame, n: int = MC_N, seed: int = MC_SEED + 3, use: np.ndarray | None = None) -> dict:
    """F3 failures among the 21: not reproduced (p_norepro * shared multiplier) or a new repeat (lens: r_lens; non-lens:
    r0 * r_nonlens_mult, r0 shared)."""
    s = s.reset_index(drop=True)
    use = np.ones(len(s), bool) if use is None else np.asarray(use, bool)
    rng = np.random.default_rng(seed)
    r0 = rng.uniform(*PARAMS["f3_r0"], n)
    mr = rng.uniform(*PARAMS["f3_mrepro"], n)
    pl = s.p_lens.to_numpy(float)
    lens = rng.random((n, len(s))) < pl
    prep = np.where(lens, s.r_lens.to_numpy(float), np.minimum(1, r0[:, None] * s.r_nonlens_mult.to_numpy(float)))
    pnr = np.minimum(1, mr[:, None] * s.p_norepro.to_numpy(float))
    fail = (rng.random((n, len(s))) < pnr) | (rng.random((n, len(s))) < prep)
    fail &= use
    p_fail = np.where(use, 1 - (1 - pnr.mean(0)) * (1 - prep.mean(0)), np.nan)
    return dict(count=fail.sum(1), p_fail=p_fail)


def model_f4(s: pd.DataFrame, n: int = MC_N, seed: int = MC_SEED) -> dict:
    """F4 count over the 61 events. Same seed as F1, so c0 and f0 are the same draws (one catalogue). A lens on the tested
    (or neighbour) star, P = p_lens, is catalogued at the NEOWISE time with p_sampled * min(cap, c0 * cat_mult); a non-lens
    brightening of the star (p_nonlens_real) with f0."""
    s = s.reset_index(drop=True)
    rng = np.random.default_rng(seed)
    c0, f0 = _cat_draws(rng, n)
    pl, ps = s.p_lens.to_numpy(float), s.p_sampled.to_numpy(float)
    pr = s.p_nonlens_real.to_numpy(float)
    c = ps * np.minimum(PARAMS["c_cap"], c0[:, None] * s.cat_mult.to_numpy(float))
    u = rng.random((n, len(s)))
    lens = u < pl
    real = (u >= pl) & (u < pl + pr)
    inc = rng.random((n, len(s))) < np.where(lens, c, np.where(real, ps * f0[:, None], 0.0))
    p_in = (pl * c + pr * ps * f0[:, None]).mean(0)
    return dict(count=inc.sum(1), p_in=p_in)


def model_f5(k_controls: np.ndarray, n: int = 4000, seed: int = MC_SEED + 5) -> dict:
    """F5 excess pass fraction (NEOWISE time minus mean of control times, per event) and its significance (one-sided t,
    the Monte Carlo's stand-in for the grader's sign-flip permutation)."""
    rng = np.random.default_rng(seed)
    k_controls = np.asarray(k_controls, int)
    m = len(k_controls)
    kmax = max(int(k_controls.max()), 1) if m else 1
    ex, sig = np.empty(n), np.empty(n, bool)
    for i in range(n):
        q = rng.beta(*PARAMS["f5_q_on"])
        s_ = rng.uniform(*PARAMS["f5_s"])
        n0 = rng.uniform(*PARAMS["f5_n0"])
        v = rng.beta(*PARAMS["f5_v"])
        pv = rng.uniform(*PARAMS["f5_pv"])
        u = rng.random(m)
        real, var = u < q, (u >= q) & (u < q + v)
        p_true = np.where(real, s_, np.where(var, pv, n0))
        p_ctrl = np.where(var, pv, n0)
        res_t = rng.random(m) < PARAMS["f5_res"]
        res_c = (rng.random((m, kmax)) < PARAMS["f5_res"]) & (np.arange(kmax)[None, :] < k_controls[:, None])
        pt = rng.random(m) < p_true
        pc = rng.random((m, kmax)) < p_ctrl[:, None]
        nc = res_c.sum(1)
        ok = res_t & (nc > 0)
        d = pt[ok].astype(float) - (pc & res_c)[ok].sum(1) / nc[ok]
        ex[i] = d.mean() if ok.any() else np.nan
        sd = d.std(ddof=1) if ok.sum() > 1 else np.nan
        sig[i] = bool(ok.sum() > 1 and sd > 0 and ex[i] / (sd / np.sqrt(ok.sum())) > 1.645)
    return dict(excess=ex, significant=sig, n_pairs_expected=float(m * PARAMS["f5_res"] * (1 - (1 - PARAMS["f5_res"]) ** 2)))


# ----------------------------------------------------------------------------------------------------------------------------
# Grading
# ----------------------------------------------------------------------------------------------------------------------------
def grade_f1_f2(s: pd.DataFrame, cat: pd.DataFrame, idm: dict, kn: set) -> tuple[pd.DataFrame, dict]:
    s = s.reset_index(drop=True)
    cat_ids = set(cat.source_id)
    has_pos = (cat.ra.notna() & cat.dec.notna()).to_numpy()
    rows = []
    for r in s.itertuples():
        rid = idm.get(r.source_id, r.source_id)
        by_id = rid in cat_ids or r.source_id in cat_ids
        by_pos = False
        if has_pos.any() and np.isfinite(r.ra):
            by_pos = bool((sep_arcsec(r.ra, r.dec, cat.ra[has_pos], cat.dec[has_pos]) <= RULES["id_pos_arcsec"]).any())
        identity = (rid in kn) or by_id or by_pos
        row = cat[cat.source_id.isin([rid, r.source_id])]
        rows.append(dict(name=r.key, source_id=r.source_id, release_source_id=rid, group=r.group, p_lens=r.p_lens,
                         p_in=r.p_in, in_catalogue=bool(by_id or by_pos), by_id=by_id, by_pos=by_pos, identity=identity,
                         cat_tmax_mjd=float(row.tmax_mjd.iloc[0]) if len(row) else np.nan, t_peak_dr3=r.t_peak_dr3))
    g = pd.DataFrame(rows)
    n_id = int(g.identity.sum())
    if n_id < RULES["f1_min_identity"]:
        why = (f"not yet resolvable: only {n_id} of {len(g)} sources have a DR4 identity (< {RULES['f1_min_identity']}); "
               "rerun the catalogue stage")
        return g, dict(F1=dict(statistic=None, verdict=why, n_with_identity=n_id), F2=dict(statistic=None, verdict=why))
    lo, hi = GRADED["F1"]
    k = int(g.in_catalogue.sum())
    y = g.in_catalogue.to_numpy(bool)
    use = g.identity.to_numpy(bool)
    f1 = dict(statistic=k, n_sample=len(g), n_with_identity=n_id, bounds=[lo, hi], hit=bool(lo <= k <= hi),
              stated_probability=FC.get("F1", {}).get("p_hit"),
              by_group=g.groupby("group").in_catalogue.agg(["sum", "count"]).to_dict("index"),
              brier=round(float(np.mean((g.p_in - y) ** 2)), 4), n_by_position_only=int((g.by_pos & ~g.by_id).sum()))
    m2 = s.f2_member.to_numpy(bool) & use
    auc, p = auc_mw(s.p_lens.to_numpy(float)[m2], y[m2])
    if not np.isfinite(auc):
        f2 = dict(statistic=None, verdict="not graded (no source, or every source, is in the catalogue)", n=int(m2.sum()))
    else:
        f2 = dict(statistic=round(auc, 4), n=int(m2.sum()), n_in_catalogue=int(y[m2].sum()), threshold=GRADED["F2"],
                  hit=bool(auc > GRADED["F2"]), stated_probability=FC.get("F2", {}).get("p_hit"),
                  reported_auc_gt_half=bool(auc > 0.5), reported_mann_whitney_p_one_sided=round(p, 4))
    return g, dict(F1=f1, F2=f2)


def f3_untestable_label(label) -> str | None:
    """A metrics row that cannot be read as a DR4 light-curve verdict: missing/empty label, too few transits, analysis error."""
    if label is None or (isinstance(label, float) and not np.isfinite(label)) or not str(label).strip():
        return "no analysis label"
    lab = str(label)
    if lab.startswith("too few"):
        return "fewer than 10 G transits"
    if lab.startswith("analysis error"):
        return "analysis error"
    return None


def grade_f3(s: pd.DataFrame, run: Path, rel: dict, metrics: pd.DataFrame | None,
             status: dict | None = None, check_complete: bool = True) -> tuple[pd.DataFrame, dict]:
    s = s.reset_index(drop=True)
    new_after = rel["f3_new_after"]
    mm = {} if metrics is None else {sid(a): r for a, r in zip(metrics.source_id, metrics.to_dict("records"), strict=True)
                                     if r.get("set") == "h0010"}
    idm = idmap_dict(run, rel)
    rids = [idm.get(x, x) for x in s.source_id]
    if check_complete:
        probs = epoch_completeness(status, rids)
        if metrics is None:
            probs.append("no search/metrics.csv")
        if probs:
            return pd.DataFrame(), dict(F3=dict(statistic=None, verdict="not yet resolvable: incomplete run",
                                                problems=probs[:20], n_problems=len(probs)))
    rows, incomplete = [], []
    for r, rid in zip(s.itertuples(), rids, strict=True):
        rec = dict(name=r.key, source_id=r.source_id, p_fail=r.p_fail, t_peak_dr3=r.t_peak_dr3, testable=False,
                   reproduced=None, repeat=None, fail=None, note="")
        st = (status or {}).get(rid, "ok")
        if st == "absent":
            rec["note"] = "the archive has no DR4 epoch photometry for it (untestable)"
            rows.append(rec)
            continue
        m = mm.get(r.source_id)
        why = f3_untestable_label(None if m is None else m.get("label"))
        if m is None or why:
            rec["note"] = f"{why or 'no metrics row'} (untestable)"
            if m is None and check_complete:
                incomplete.append(f"{rid}: epoch status ok but no metrics row")
            rows.append(rec)
            continue
        df = read_epoch(run, sid(m.get("release_source_id")) or rid)
        if df is None:
            rec["note"] = "epoch cache missing"
            if check_complete:
                incomplete.append(f"{rid}: epoch status ok but no cached light curve")
            rows.append(rec)
            continue
        t = valid_g(df).t_mjd.to_numpy(float)
        near_peak = int((np.abs(t - r.t_peak_dr3) <= RULES["f3_repro_dt"]).sum())
        n_new = int((t >= new_after).sum())
        rec.update(n_near_dr3_peak=near_peak, n_new=n_new)
        if near_peak == 0:
            rec["note"] = "no valid G transit within 45 d of the DR3 peak (untestable)"
            rows.append(rec)
            continue
        if n_new < RULES["f3_min_new_transits"]:
            rec["note"] = f"only {n_new} G transits after MJD {new_after:g} (untestable)"
            rows.append(rec)
            continue
        eps = parse_eps(m.get("bright_eps"))
        repro = any(abs(tp - r.t_peak_dr3) <= RULES["f3_repro_dt"] and dg <= RULES["f3_repro_dg"] for tp, dg, _ in eps)
        rep = [e for e in eps if e[1] <= RULES["f3_rep_dg"] and e[2] >= RULES["f3_rep_n"] and e[0] >= new_after
               and abs(e[0] - r.t_peak_dr3) >= RULES["f3_rep_sep"]]
        rec.update(testable=True, reproduced=bool(repro), repeat=bool(rep), fail=bool((not repro) or rep),
                   repeat_eps=";".join(f"{a:.0f}:{b:+.2f}:{c}" for a, b, c in rep), label=m.get("label"))
        rows.append(rec)
    g = pd.DataFrame(rows)
    if incomplete:
        return g, dict(F3=dict(statistic=None, verdict="not yet resolvable: incomplete run", problems=incomplete[:20],
                               n_problems=len(incomplete)))
    use = g.testable.to_numpy(bool)
    if use.sum() < RULES["f3_min_testable"]:
        return g, dict(F3=dict(statistic=None, verdict=f"void: {int(use.sum())} of {len(g)} testable "
                                                         f"(< {RULES['f3_min_testable']})", n_testable=int(use.sum())))
    lo, hi = GRADED["F3"]
    k = int(g.fail[use].sum())
    p_model = (summary(model_f3(s, use=use)["count"], (lo, hi))["p_hit"] if not use.all()
               else FC.get("F3", {}).get("p_hit"))
    return g, dict(F3=dict(statistic=k, n_testable=int(use.sum()), bounds=[lo, hi], hit=bool(lo <= k <= hi),
                           stated_probability=FC.get("F3", {}).get("p_hit"), model_probability_for_testable=p_model,
                           n_not_reproduced=int((g.reproduced[use] == False).sum()),  # noqa: E712
                           n_repeat=int((g.repeat[use] == True).sum()),  # noqa: E712
                           brier=round(float(np.mean((g.p_fail[use] - g.fail[use].astype(float)) ** 2)), 4)))


def catalogue_time_problem(cat: pd.DataFrame) -> str | None:
    if cat.attrs.get("time_column") is None or not cat.tmax_mjd.notna().any():
        return f"no peak-time column among {COLUMNS['tmax']}"
    med = float(cat.tmax_mjd.median())
    lo, hi = RULES["f4_tmax_median"]
    if not lo <= med <= hi:
        return f"median catalogue peak time MJD {med:.1f} outside [{lo:g}, {hi:g}] (time zero point)"
    return None


def grade_f4(s: pd.DataFrame, cat: pd.DataFrame, idm: dict) -> tuple[pd.DataFrame, dict]:
    s = s.reset_index(drop=True)
    tp = catalogue_time_problem(cat)
    if tp:
        return pd.DataFrame(), dict(F4=dict(statistic=None, verdict=f"not yet resolvable: {tp}"))
    has_pos = (cat.ra.notna() & cat.dec.notna()).to_numpy()
    rows = []
    for r in s.itertuples():
        ids = {idm.get(x, x) for x in (r.source_id, r.alt_source_id) if x} | {x for x in (r.source_id, r.alt_source_id) if x}
        cand = cat.source_id.isin(ids).to_numpy()
        if has_pos.any():
            near = np.zeros(len(cat), bool)
            near[has_pos] = sep_arcsec(r.ra, r.dec, cat.ra[has_pos], cat.dec[has_pos]) <= RULES["f4_pos_arcsec"]
            cand |= near
        hits = cat[cand]
        te = hits.tE.fillna(0.0).clip(lower=0)
        win = np.maximum(RULES["f4_min_dt"], np.minimum(2 * te, RULES["f4_max_dt"]))
        ok = ((hits.tmax_mjd - r.t_event).abs() <= win).fillna(False).to_numpy(bool)   # a missing peak time never matches
        hits = hits[ok]
        rows.append(dict(name=r.key, source_id=r.source_id, t_event=r.t_event, p_in=r.p_in, case=r.case,
                         catalogued=bool(len(hits)), n_same_object_any_time=int(cand.sum()),
                         cat_source_id=";".join(hits.source_id), cat_tmax_mjd=";".join(f"{x:.1f}" for x in hits.tmax_mjd)))
    g = pd.DataFrame(rows)
    lo, hi = GRADED["F4"]
    k = int(g.catalogued.sum())
    return g, dict(F4=dict(statistic=k, n=len(g), bounds=[lo, hi], hit=bool(lo <= k <= hi),
                           stated_probability=FC.get("F4", {}).get("p_hit"),
                           time_column=cat.attrs.get("time_column"), catalogue_median_tmax_mjd=round(float(cat.tmax_mjd.median()), 1),
                           catalogue_rows_without_peak_time=int(cat.tmax_mjd.isna().sum()),
                           catalogue_rows_without_position=int((~has_pos).sum()),
                           brier=round(float(np.mean((g.p_in - g.catalogued) ** 2)), 4),
                           named={r.case: bool(r.catalogued) for r in g.itertuples() if isinstance(r.case, str) and r.case}))


def f5_events(events: pd.DataFrame, run: Path, rel: dict, idm: dict, rule_mod=None) -> pd.DataFrame:
    """The sealed ensemble rule at the NEOWISE time and at each control time inside the span, per event."""
    rule_mod = rule_mod or ensemble_rule()
    lo, hi = rel["span"]
    rows, cache = [], {}
    for r in events.itertuples():
        rid = idm.get(r.source_id, r.source_id)
        if rid not in cache:
            cache[rid] = read_epoch(run, rid)
        df = cache[rid]
        rec = dict(name=r.key, source_id=r.source_id, release_source_id=rid, t_event=r.t_event)
        if df is None:
            rec.update(true_status="no light curve", n_ctrl=0, n_ctrl_testable=0, n_ctrl_pass=0)
            rows.append(rec)
            continue
        st = rule_mod.grade_series(df, float(r.t_event))["status"].split(":")[0]
        cs = [rule_mod.grade_series(df, float(r.t_event + o))["status"].split(":")[0]
              for o in RULES["f5_offsets"] if lo <= r.t_event + o <= hi]
        rec.update(true_status=st, n_ctrl=len(cs), n_ctrl_testable=sum(c in ("pass", "fail") for c in cs),
                   n_ctrl_pass=sum(c == "pass" for c in cs))
        rows.append(rec)
    return pd.DataFrame(rows)


def f5_statistic(ev: pd.DataFrame) -> dict:
    """Excess = mean over paired events of pass(t) - control pass fraction. One-sided sign-flip permutation p-value, with one
    random sign per Gaia star (all events on a star share it), seeded."""
    ok = (ev.true_status.isin(["pass", "fail"]) & (ev.n_ctrl_testable > 0)).to_numpy()
    if not ok.any():
        return dict(n_pairs=0)
    e = ev[ok]
    d = ((e.true_status == "pass").astype(float) - e.n_ctrl_pass / e.n_ctrl_testable).to_numpy(float)
    star = pd.factorize(e.source_id)[0]
    obs = float(d.mean())
    rng = np.random.default_rng(RULES["f5_seed"])
    signs = rng.choice([-1.0, 1.0], size=(RULES["f5_perm"], star.max() + 1))[:, star]
    perm = (signs * d).mean(1)
    p = float((1 + (perm >= obs - 1e-12).sum()) / (1 + RULES["f5_perm"]))
    return dict(n_pairs=int(len(d)), n_stars=int(star.max() + 1), excess=round(obs, 4), p_one_sided=round(p, 5),
                pass_rate_true=round(float((e.true_status == "pass").mean()), 4),
                pass_rate_control=round(float(e.n_ctrl_pass.sum() / e.n_ctrl_testable.sum()), 4),
                n_true_pass=int((e.true_status == "pass").sum()))


def grade_f5(s: pd.DataFrame, run: Path, rel: dict, idm: dict, status: dict | None) -> tuple[pd.DataFrame, dict]:
    rids = sorted({idm.get(x, x) for x in s.source_id})
    probs = epoch_completeness(status, rids)
    if not probs:
        missing = [i for i in rids if status.get(i) == "ok" and not (run / "epoch" / f"{i}.csv").exists()]
        probs = [f"{i}: epoch status ok but no cached light curve" for i in missing]
    if probs:
        return pd.DataFrame(), dict(F5=dict(statistic=None, verdict="not yet resolvable: incomplete run",
                                            problems=probs[:20], n_problems=len(probs)))
    ev = f5_events(s, run, rel, idm)
    st = f5_statistic(ev)
    if st["n_pairs"] < RULES["f5_min_pairs"]:
        return ev, dict(F5=dict(st, statistic=None, verdict=f"void: {st['n_pairs']} paired events (< {RULES['f5_min_pairs']})"))
    fc = FC.get("F5", {})
    hit = bool(st["excess"] > 0 and st["p_one_sided"] < GRADED["F5_alpha"])
    iv = (fc.get("p10"), fc.get("p90"))
    return ev, dict(F5=dict(st, statistic=st["excess"], hit=hit, stated_probability=fc.get("p_significant"),
                            reported_interval=list(iv),
                            reported_interval_hit=bool(iv[0] is not None and iv[0] <= st["excess"] <= iv[1])))


# ----------------------------------------------------------------------------------------------------------------------------
# Driver
# ----------------------------------------------------------------------------------------------------------------------------
def load_forecast() -> dict:
    return json.loads(FORECAST.read_text()) if FORECAST.exists() else {}


FC = load_forecast()


def default_run(rel: dict) -> Path:
    home = Path(os.environ.get("ODDSKY_H0014_RUNS", Path.home() / "oddsky-runs" / "h0014")) / ("dr4" if rel["name"] == "Gaia DR4" else "dr3")
    return home if home.exists() else ROOT / "hunts/H-0014" / rel["run_subdir"]


def grade(run: Path, release: str = "dr4", out: Path | None = None, sample: pd.DataFrame | None = None,
          only: tuple[str, ...] = ("F1", "F2", "F3", "F4", "F5"), quiet: bool = False) -> dict:
    rel = RELEASES[release]
    s = load_sample() if sample is None else sample
    out = out or (run / "forecast_grade")
    if out.resolve() == HERE or HERE in out.resolve().parents:
        raise SystemExit("refusing to write into the sealed predictions directory")
    out.mkdir(parents=True, exist_ok=True)
    idm, kn, status = idmap_dict(run, rel), known_ids(run), epoch_status(run)
    res: dict = dict(release=rel["name"], run=str(run), numpy=np.__version__, pandas=pd.__version__,
                     python=sys.version.split()[0])
    catp = run / "catalogue" / "lens_catalogue.csv"
    cat = None
    if catp.exists() and catp.stat().st_size > 1:
        try:
            cat = catalogue_frame(catp)
            res["catalogue_rows"] = len(cat)
            res["catalogue_unique_sources"] = int(cat.source_id.nunique())
        except Exception as e:  # noqa: BLE001
            res["catalogue_error"] = f"{type(e).__name__}: {e}"
    if {"F1", "F2"} & set(only):
        if cat is None:
            res.update(F1=dict(statistic=None, verdict="not yet resolvable: no release lens catalogue"),
                       F2=dict(statistic=None, verdict="not yet resolvable: no release lens catalogue"))
        else:
            g, r = grade_f1_f2(s[s.forecast == "F1"], cat, idm, kn)
            g.to_csv(out / "f1_f2.csv", index=False)
            res.update(r)
    if "F3" in only:
        mp = run / "search" / "metrics.csv"
        metrics = pd.read_csv(mp, dtype={"source_id": str, "release_source_id": str}) if mp.exists() else None
        g, r = grade_f3(s[s.forecast == "F3"], run, rel, metrics, status)
        g.to_csv(out / "f3.csv", index=False)
        res.update(r)
    if "F4" in only:
        if cat is None:
            res["F4"] = dict(statistic=None, verdict="not yet resolvable: no release lens catalogue")
        else:
            g, r = grade_f4(s[s.forecast == "F4"], cat, idm)
            g.to_csv(out / "f4.csv", index=False)
            res.update(r)
    if "F5" in only:
        g, r = grade_f5(s[s.forecast == "F5"], run, rel, idm, status)
        g.to_csv(out / "f5.csv", index=False)
        res.update(r)
    (out / "summary.json").write_text(json.dumps(res, indent=1, default=str))
    if not quiet:
        print(json.dumps(res, indent=1, default=str))
    return res


def self_test(run: Path | None = None) -> bool:
    """Gaia DR3 as the stand-in. Known answers: the 67 are by definition absent from DR3's catalogue (F1 = 0, F2 not graded);
    the strong events are by definition unmatched to it (F4 = 0); the id matcher must recover the 187 classifier sources that
    ARE in DR3's catalogue (an independent number, from H-0010). Regression values (taken from this matcher's first run, checked
    by hand by the referee): 25 of 40 H-0008/H-0009 known-lens NEOWISE events in DR3's span match DR3's catalogue by position and
    time. The F3 rule must reproduce every DR3 event it is shown and find no repeat in catalogued lenses; the F5 machinery must
    find a large excess for the non-blind DR3-confirmed events. Writes only to <run>/forecast_grade_selftest/."""
    rel = RELEASES["dr3"]
    run = run or default_run(rel)
    out = run / "forecast_grade_selftest"
    print(f"self-test against {rel['name']} outputs in {run}")
    res = grade(run, "dr3", out=out, only=("F1", "F2", "F3", "F4"), quiet=True)
    s = load_sample()
    ok = True

    def check(name, cond, detail):
        nonlocal ok
        ok &= bool(cond)
        print(f"  [{'ok' if cond else 'FAIL'}] {name}: {detail}")

    check("F1 on DR3 (the 67 are classifier-only by definition)", res.get("F1", {}).get("statistic") == 0,
          f"{res.get('F1', {}).get('statistic')} of 67 in DR3 vari_microlensing (expect 0); "
          f"{res.get('F1', {}).get('n_with_identity')} with identity")
    check("F2 on DR3", res.get("F2", {}).get("statistic") is None, res.get("F2", {}).get("verdict"))
    check("F4 on DR3 (strong events are unmatched to DR3's catalogue by definition)", res.get("F4", {}).get("statistic") == 0,
          f"{res.get('F4', {}).get('statistic')} of 61 (expect 0); median peak MJD {res.get('F4', {}).get('catalogue_median_tmax_mjd')}")
    cat = catalogue_frame(run / "catalogue" / "lens_catalogue.csv")
    co = run / "catalogue" / "classifier_only.csv"
    if co.exists():
        c = pd.read_csv(co, dtype={"source_id": str})
        pos = pd.DataFrame(dict(forecast="F1", key=c.source_id, source_id=c.source_id.map(sid), ra=np.nan, dec=np.nan,
                                group="x", p_lens=0.5, p_in=0.5, t_peak_dr3=np.nan, f2_member=False))
        g, _ = grade_f1_f2(pos, cat, {}, set(pos.source_id))
        n_in = int(g.in_catalogue.sum())
        check("id matcher, positive control (independent: H-0010's 187)", n_in == 187,
              f"{n_in} of {len(c)} classifier MICROLENSING sources found in DR3's catalogue")
    nw = []
    for f in ("hunts/H-0009/work/sky4_classified.csv", "hunts/H-0008/work/sky3_classified.csv"):
        x = pd.read_csv(ROOT / f, usecols=["designation", "ra", "dec", "t", "class"])
        nw.append(x[x["class"].astype(str).str.startswith("microlensing (known)")])
    nw = pd.concat(nw).drop_duplicates("designation")
    nw = nw[(nw.t >= rel["span"][0]) & (nw.t <= rel["span"][1])]
    ctrl = pd.DataFrame(dict(forecast="F4", key=nw.designation, source_id="", alt_source_id="", ra=nw.ra, dec=nw.dec,
                             t_event=nw.t, p_in=0.5, case=""))
    g, _ = grade_f4(ctrl, cat, {})
    check("position+time matcher (regression value 25)", int(g.catalogued.sum()) == 25,
          f"{int(g.catalogued.sum())} of {len(g)} known-lens NEOWISE events in DR3's span matched to DR3's catalogue")
    g2, _ = grade_f4(ctrl.assign(t_event=ctrl.t_event + 400), cat, {})
    check("position+time matcher, negative control (+400 d)", int(g2.catalogued.sum()) <= 1,
          f"{int(g2.catalogued.sum())} matched with the NEOWISE time moved by +400 d (expect <= 1)")
    f3 = res.get("F3", {})
    g3 = pd.read_csv(out / "f3.csv") if (out / "f3.csv").exists() and (out / "f3.csv").stat().st_size > 1 else pd.DataFrame()
    tested = g3[g3.testable == True] if len(g3) else g3  # noqa: E712
    check("F3 reproduction on DR3 (the events were found in DR3)", len(tested) > 0 and bool(tested.reproduced.all()),
          f"{int(tested.reproduced.sum()) if len(tested) else 0} of {len(tested)} testable reproduced; F3 = {f3}")
    sp = s[s.forecast == "F1"]
    mp = run / "search" / "metrics.csv"
    if mp.exists():
        known = sp[sp.group.isin(["known lens", "Oddsky case"]) & sp.t_peak_dr3.notna()].assign(forecast="F3", p_fail=0.0)
        gk, _ = grade_f3(known, run, rel, pd.read_csv(mp, dtype={"source_id": str, "release_source_id": str}),
                         epoch_status(run))
        tk = gk[gk.testable == True] if len(gk) else gk  # noqa: E712
        check("F3 rule on the catalogued lenses (control: lenses do not repeat)",
              len(tk) > 0 and int(tk.repeat.sum()) == 0 and bool(tk.reproduced.all()),
              f"{len(tk)} testable, {int(tk.reproduced.sum()) if len(tk) else 0} reproduced, "
              f"{int(tk.repeat.sum()) if len(tk) else 0} repeats (expect all reproduced, 0 repeats)")
    pos_events = sp[sp.group == "Oddsky case"]
    tgt = pd.read_csv(ROOT / "hunts/H-0014/data/targets.csv", dtype={"source_id": str})
    strong = tgt[(tgt.set == "strong") & tgt.source_id.isin(pos_events.source_id)].drop_duplicates("source_id")
    ev = pd.DataFrame(dict(key=strong.name, source_id=strong.source_id, t_event=strong.t_event.astype(float)))
    st = f5_statistic(f5_events(ev, run, rel, {}))
    check("F5 machinery, positive control (OS-0026/27/29 at their NEOWISE times)",
          st.get("n_true_pass", 0) == 3 and st.get("pass_rate_control", 1) == 0, f"{st}")
    print("self-test:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--release", default="dr4", choices=sorted(RELEASES))
    ap.add_argument("--run", type=Path, default=None, help="pipeline output directory (default ~/oddsky-runs/h0014/<release>)")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--self-test", action="store_true", help="run on the Gaia DR3 dry-run outputs (stand-in release)")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(0 if self_test(a.run) else 1)
    grade(a.run or default_run(RELEASES[a.release]), a.release, out=a.out)
