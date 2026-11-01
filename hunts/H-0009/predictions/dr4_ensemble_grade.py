"""Grade the pre-registered Gaia DR4 ensemble forecast (hunts/H-0009/predictions/dr4_ensemble.md).

Run from the repo root:
    uv run python -I hunts/H-0009/predictions/dr4_ensemble_grade.py            # grade against Gaia DR4 (after 2026-12-02)
    uv run python -I hunts/H-0009/predictions/dr4_ensemble_grade.py --test-dr3 # self-test: the three DR3-confirmed events, DR3 data

The rule (fixed before DR4; `RULE` below is the machine form of dr4_ensemble.md section 2):
  For each event in dr4_ensemble_sample.csv with status "testable" (GOST predicts >= 2 Gaia transits within +-30 d), take the
  per-transit Gaia G photometry of the fixed source (`source_id`, a Gaia DR3 id; mapped to its DR4 id only through
  work/ensemble/dr4_idmap.csv if DR4 renumbers it). Drop transits flagged rejected_by_photometry and non-finite magnitudes or
  times; keep variability-flag rejections (during an event they are the event). A transit is one transit_id: a transit_id
  listed more than once in a band counts once, with the median of its magnitudes. Transits 30-150 d from the event are used
  for neither the window nor the baseline.
    baseline  = transits with |t - t_event| > 150 d (at least 10, else "untestable (data)")
    ratio     = 10**(-0.4 (G - median baseline G))   per transit
    s         = 1.4826 * MAD of the baseline ratios
    threshold = 1 + max(0.15, 5 s)
    window    = transits with |t - t_event| <= 30 d (at least 2, else "untestable (data)")
    PASS if at least 2 window transits have ratio >= threshold; otherwise FAIL.
  Colour, for PASS events only: at the passing transits, dBP - dRP (each against its own baseline median, same 150 d rule, at
  least 5 baseline transits), inverse-variance mean D with error e_D (per band and transit: max(formal error, baseline robust
  scatter in mag / flux ratio) combined in quadrature with scatter / sqrt(n baseline)). "undetermined" if fewer than 5 BP or 5
  RP baseline transits, if the BP baseline median is fainter than 20.5, if no passing transit has both BP and RP, or if
  e_D > 0.05; else "achromatic" if |D| <= 0.10, "chromatic" otherwise.
  Ensemble statistic: the number of PASS events among the 47 testable-by-design events. Untestable-by-design events are never
  counted, whatever DR4 shows. Tested claim: "~20% of strong events are lens-like brightenings of the survey-matched Gaia star".

Changes allowed after DR4 lands (dr4_ensemble.md section 2.5): retrieval (release label, endpoint, request parameters, or DR4's
bulk files), the column mapping in src/oddsky/data/gaia_epoch.to_series (names; time zero-point; flux -> mag with DR4's zero
point), per-CCD -> per-transit averaging (median flux of valid CCDs), and the DR3->DR4 id map (work/ensemble/dr4_idmap.csv:
nearest DR4 source within 0.5" and 0.3 mag in G). This file, gaia_epoch.py and series.py are used as they are at the seal
commit; publish `git diff <seal> -- <those three files>` with the grade. Nothing else may change.

`ensemble_mc` is the forecast's Monte Carlo (dr4_ensemble.md section 3); the forecast script (work/ensemble/e4_ensemble.py) and this
grader both call it, so the grading percentiles are computed by the same code that made the forecast.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
WORK = os.path.join(HERE, "work", "ensemble")
SAMPLE = os.path.join(HERE, "dr4_ensemble_sample.csv")
FORECAST = os.path.join(WORK, "forecast.json")
IDMAP = os.path.join(WORK, "dr4_idmap.csv")

RULE = dict(window_d=30.0, baseline_gap_d=150.0, min_baseline=10, min_window=2, floor=0.15, nsig=5.0, n_up=2,
            min_baseline_colour=5, colour_tol=0.10, colour_max_err=0.05, bp_faint=20.5)


# ----------------------------------------------------------------------------------------------------------------------------
# The rule (numpy core; used verbatim by the Monte Carlo)
# ----------------------------------------------------------------------------------------------------------------------------
def judge(t: np.ndarray, mag: np.ndarray, t_ev: float, rule: dict = RULE) -> dict:
    """G-band verdict for one event. t, mag: valid G transits (rejected_by_photometry and non-finite already removed)."""
    t = np.asarray(t, float)
    mag = np.asarray(mag, float)
    dt = t - t_ev
    base = np.abs(dt) > rule["baseline_gap_d"]
    out = dict(status="", n_base=int(base.sum()), n_win=0, n_up=0, m0=np.nan, s=np.nan, threshold=np.nan, r_max=np.nan,
               dt_rmax=np.nan, up=np.zeros(len(t), bool))
    if base.sum() < rule["min_baseline"]:
        out["status"] = f"untestable (data): fewer than {rule['min_baseline']} baseline transits"
        return out
    m0 = float(np.median(mag[base]))
    r = 10 ** (-0.4 * (mag - m0))
    rb = r[base]
    s = float(1.4826 * np.median(np.abs(rb - np.median(rb))))
    thr = 1 + max(rule["floor"], rule["nsig"] * s)
    win = np.abs(dt) <= rule["window_d"]
    out.update(m0=m0, s=s, threshold=thr, n_win=int(win.sum()))
    if win.sum() < rule["min_window"]:
        out["status"] = f"untestable (data): fewer than {rule['min_window']} transits within +-{rule['window_d']:g} d"
        return out
    up = win & (r >= thr)
    i = np.flatnonzero(win)[np.argmax(r[win])]
    out.update(n_up=int(up.sum()), r_max=float(r[i]), dt_rmax=float(dt[i]), up=up)
    out["status"] = "pass" if up.sum() >= rule["n_up"] else "fail"
    return out


def _band_base(t, mag, err, t_ev, rule):
    base = np.abs(t - t_ev) > rule["baseline_gap_d"]
    if base.sum() < rule["min_baseline_colour"]:
        return None
    m0 = float(np.median(mag[base]))
    sc = float(1.4826 * np.median(np.abs(mag[base] - m0)))
    return m0, sc, int(base.sum())


def _err(err_j, dmag_j, b):
    """Per-transit colour error: the larger of the formal error and the baseline's robust scatter carried at constant flux
    (scatter / flux ratio), combined with the error of the baseline median (scatter / sqrt(n_baseline))."""
    ratio = 10 ** (-0.4 * dmag_j)
    return float(np.hypot(max(err_j, b[1] / max(ratio, 1e-3)), b[1] / np.sqrt(b[2])))


def colour(ids_up, bp: tuple, rp: tuple, t_ev: float, rule: dict = RULE) -> dict:
    """Colour verdict at the passing transits. ids_up: transit ids of the passing G transits. bp, rp: (ids, t, mag, err) arrays of
    valid BP / RP transits."""
    out = dict(colour="undetermined", D=np.nan, e_D=np.nan, n_pairs=0, bp_base=np.nan, note="")
    bb = _band_base(bp[1], bp[2], bp[3], t_ev, rule) if len(bp[0]) else None
    rb = _band_base(rp[1], rp[2], rp[3], t_ev, rule) if len(rp[0]) else None
    if bb is None or rb is None:
        out["note"] = "too few BP or RP baseline transits"
        return out
    out["bp_base"] = bb[0]
    if bb[0] > rule["bp_faint"]:
        out["note"] = f"BP baseline median fainter than {rule['bp_faint']:.1f}"
        return out
    bi = {k: j for j, k in enumerate(bp[0])}
    ri = {k: j for j, k in enumerate(rp[0])}
    d, e = [], []
    for k in ids_up:
        if k in bi and k in ri:
            jb, jr = bi[k], ri[k]
            db, dr = bp[2][jb] - bb[0], rp[2][jr] - rb[0]
            d.append(db - dr)
            e.append(np.hypot(_err(bp[3][jb], db, bb), _err(rp[3][jr], dr, rb)))
    out["n_pairs"] = len(d)
    if not d:
        out["note"] = "no passing transit has both BP and RP"
        return out
    w = 1 / np.square(e)
    D = float(np.sum(w * np.array(d)) / w.sum())
    eD = float(1 / np.sqrt(w.sum()))
    out.update(D=D, e_D=eD)
    if eD > rule["colour_max_err"]:
        out["note"] = f"e_D > {rule['colour_max_err']:.2f}"
        return out
    out["colour"] = "achromatic" if abs(D) <= rule["colour_tol"] else "chromatic"
    return out


# ----------------------------------------------------------------------------------------------------------------------------
# Applying the rule to fetched epoch photometry (oddsky.data.gaia_epoch.to_series format)
# ----------------------------------------------------------------------------------------------------------------------------
def grade_series(df: pd.DataFrame, t_ev: float, rule: dict = RULE) -> dict:
    ok = ((df.flag.astype(str) != "rejected_by_photometry") & np.isfinite(df.mag.astype(float))
          & np.isfinite(df.t_mjd.astype(float)))
    # One row per (band, transit id): a transit listed more than once counts once (median magnitude).
    d = (df[ok].groupby(["band", "camera"], as_index=False, sort=False)
               .agg(t_mjd=("t_mjd", "first"), mag=("mag", "median"), err=("err", "max"), flag=("flag", "first")))
    g = d[d.band == "G"].sort_values("t_mjd")
    res = judge(g.t_mjd.to_numpy(float), g.mag.to_numpy(float), t_ev, rule)
    up_ids = list(g.camera.astype(str).to_numpy()[res["up"]]) if len(g) else []
    res.pop("up")
    res.update(colour="", D=np.nan, e_D=np.nan, n_pairs=0, colour_note="")
    if res["status"] == "pass":

        def arr(b):
            x = d[d.band == b]
            return (x.camera.astype(str).to_numpy(), x.t_mjd.to_numpy(float), x.mag.to_numpy(float), x.err.to_numpy(float))
        c = colour(up_ids, arr("BP"), arr("RP"), t_ev, rule)
        res.update(colour=c["colour"], D=c["D"], e_D=c["e_D"], n_pairs=c["n_pairs"], colour_note=c["note"])
    return res


def fetch(ids: list[str], releases: tuple[str, ...]):
    sys.path.insert(0, os.path.join(ROOT, "src"))
    from oddsky.data import gaia_epoch
    got, report = gaia_epoch.fetch_report([int(s) for s in ids], releases=releases)
    return {str(k): v for k, v in got.items()}, report


# ----------------------------------------------------------------------------------------------------------------------------
# The ensemble Monte Carlo (forecast and grading)
# ----------------------------------------------------------------------------------------------------------------------------
SC = ("L", "R", "F", "N")


def draw_fL(rng, n):
    """Lens fraction ON THE SURVEY-MATCHED STAR among strong events (Gaia DR3 sweep, s5/s7), restricted to events like the
    test's (>= 2 GOST transits within +-30 d): P(VARIABLE matched star | in-span strong event) = 2/27 (J180402, J180839;
    J172057's lens was on a neighbour, not on its matched star) over P(VARIABLE matched star | known lens) = 14/20, flat
    priors, clipped to [0, 1]. Returns (f_L, P(VARIABLE | lens)); the second is reused as the DR3 flag efficiency for
    lenses."""
    po = rng.beta(2 + 1, 25 + 1, n)
    pk = rng.beta(14 + 1, 6 + 1, n)
    return np.clip(po / pk, 0, 1), pk


def ensemble_mc(sample: pd.DataFrame, n: int = 20000, seed: int = 20261031, fL=None, use: np.ndarray | None = None,
                resolved_known: bool = False, fR_ab=(1.5, 18.5), fF_ab=(1.0, 19.0), rho_range=(0.5, 1.0)) -> dict:
    """Distribution of the number of PASS events (and their colour verdicts).

    sample: dr4_ensemble_sample.csv rows (testable events), with the forecast columns q_* (P(pass | resolved, scenario)),
    a_* / u_* (P(achromatic / undetermined | pass, scenario)), p_res (P(resolved)), lr_onstar (off-target likelihood ratio for the
    on-star scenarios), in_dr3_span, nblock, w_* (fixed scenario weights for events with optical follow-up; NaN otherwise),
    lr_L_extra, lr_R_extra.
    fL: None = draw from the DR3 posterior; a float = hold the lens fraction fixed (falsification test).
    use: boolean mask of events to include (default all). resolved_known: condition on the included events being resolved.
    """
    rng = np.random.default_rng(seed)
    s = sample if use is None else sample[use]
    m = len(s)
    q = np.stack([s[f"q_{k}"].to_numpy(float) for k in SC], 1)          # (m, 4)
    a = np.stack([s[f"a_{k}"].to_numpy(float) for k in SC], 1)
    u = np.stack([s[f"u_{k}"].to_numpy(float) for k in SC], 1)
    pres = np.ones(m) if resolved_known else s.p_res.to_numpy(float)
    inspan = s.in_dr3_span.astype(bool).to_numpy()
    block = s.nblock.to_numpy(int) >= 2
    lr_on = s.lr_onstar.to_numpy(float)
    lrx = np.stack([s.lr_L_extra.to_numpy(float), s.lr_R_extra.to_numpy(float), np.ones(m), np.ones(m)], 1)
    wfix = np.stack([s[f"w_{k}"].to_numpy(float) for k in SC], 1)
    fixed = np.isfinite(wfix).all(1)

    f_L, e_L = draw_fL(rng, n)
    if fL is not None:
        f_L = np.full(n, float(fL))
    f_R = rng.beta(*fR_ab, n)
    f_F = rng.beta(*fF_ab, n)
    tot = f_L + f_R + f_F
    sc = 0.98 / np.maximum(tot, 0.98)
    f_L, f_R, f_F = f_L * sc, f_R * sc, f_F * sc
    f = np.stack([f_L, f_R, f_F, 1 - f_L - f_R - f_F], 1)                 # (n, 4)
    # Gaia DR3 VARIABLE-flag efficiency per scenario (for the in-span events, all unflagged), and how strongly a DR3 non-flag
    # and a DR4 pass are correlated (rho = 1: the flag fires only on events that would pass DR4).
    e = np.stack([e_L, rng.uniform(0.2, 0.6, n), rng.uniform(0.05, 0.3, n), np.zeros(n)], 1)
    rho = rng.uniform(*rho_range, n)

    # scenario weights per (draw, event)
    lr = np.ones((m, 4))
    lr[:, :3] *= lr_on[:, None]
    lr *= lrx
    lr[block, 2] = 0.0                                                     # a months-long block is not a short outburst
    W = f[:, None, :] * lr[None, :, :]                                     # (n, m, 4)
    W = np.where(fixed[None, :, None], np.nan_to_num(wfix)[None, :, :], W)  # events with optical follow-up: their own weights
    W = np.where(inspan[None, :, None], W * (1 - e[:, None, :]), W)       # in the DR3 span and not flagged VARIABLE
    W /= W.sum(2, keepdims=True)
    # pass probability per scenario, given resolved; in-span events: given unflagged in DR3
    Q = np.broadcast_to(q[None], (n, m, 4)).copy()
    qc = rho[:, None, None] * np.clip((Q - e[:, None, :]) / (1 - e[:, None, :]), 0, None) + (1 - rho[:, None, None]) * Q
    Q = np.where(inspan[None, :, None], qc, Q)

    # sample scenario, resolved, pass, colour
    cum = np.cumsum(W, 2)
    x = rng.random((n, m, 1))
    S = np.minimum((x > cum).sum(2), 3)                                    # (n, m)
    qs = np.take_along_axis(Q, S[..., None], 2)[..., 0]
    res = rng.random((n, m)) < pres[None, :]
    ps = res & (rng.random((n, m)) < qs)
    aa = a[np.arange(m)[None, :], S]
    uu = u[np.arange(m)[None, :], S]
    y = rng.random((n, m))
    ach = ps & (y < aa)
    und = ps & (y >= aa) & (y < aa + uu)
    chro = ps & ~ach & ~und
    npass = ps.sum(1)
    out = dict(n=n, m=m, npass=npass, nach=ach.sum(1), nund=und.sum(1), nchro=chro.sum(1), nres=res.sum(1),
               nlens_pass=(ps & (S == 0)).sum(1), f_L=f_L, p_event=ps.mean(0), p_lens_event=(S == 0).mean(0))
    return out


def pct(x, p):
    return float(np.percentile(x, p))


def falsification_thresholds(npass, alpha=0.05):
    """Largest k_lo with P(count <= k_lo) < alpha and smallest k_hi with P(count >= k_hi) < alpha (-1 / None if none)."""
    ks = np.arange(0, int(npass.max()) + 2)
    lo = [k for k in ks if np.mean(npass <= k) < alpha]
    hi = [k for k in ks if np.mean(npass >= k) < alpha]
    return (int(max(lo)) if lo else -1), (int(min(hi)) if hi else None)


def nuisance_bounds(sample, n=20000, use=None, resolved_known=True, fL=0.20):
    """The pre-registered nuisance bounds for a "falsified" verdict (dr4_ensemble.md 3.5). Low side (fewest non-lens passes):
    no non-lens on-star brightenings (f_R = f_F = 0) and on-star pass probabilities x0.85. High side (most): f_R mean 0.15,
    f_F mean 0.10 and a flat-star pass rate of at least 3%. Returns (r_lo, r_hi), ensemble_mc results at the given f_L."""
    low = sample.copy()
    for s_ in "LRF":
        low[f"q_{s_}"] = low[f"q_{s_}"] * 0.85
    high = sample.copy()
    high["q_N"] = np.maximum(high.q_N, 0.03)
    r_lo = ensemble_mc(low, n=n, fL=fL, use=use, resolved_known=resolved_known, fR_ab=(1e-3, 1e3), fF_ab=(1e-3, 1e3))
    r_hi = ensemble_mc(high, n=n, fL=fL, use=use, resolved_known=resolved_known, fR_ab=(3, 17), fF_ab=(2, 18))
    return r_lo, r_hi


FL_GRID = np.round(np.arange(0.0, 0.81, 0.02), 2)


def fL_posterior(sample, use, k_obs, grid=FL_GRID, n=4000):
    """Posterior of the lens fraction (flat prior on the grid) from an observed pass count, by the forecast's own Monte Carlo."""
    like = []
    for g in grid:
        r = ensemble_mc(sample, n=n, seed=7, fL=g, use=use, resolved_known=True)
        like.append(np.mean(r["npass"] == k_obs))
    like = np.array(like)
    post = like / like.sum() if like.sum() > 0 else like
    c = np.cumsum(post)
    return dict(grid=list(map(float, grid)), like=list(map(float, like)), median=float(np.interp(0.5, c, grid)),
                lo90=float(np.interp(0.05, c, grid)), hi90=float(np.interp(0.95, c, grid)))


# ----------------------------------------------------------------------------------------------------------------------------
# Command line
# ----------------------------------------------------------------------------------------------------------------------------
DR3_TEST = [  # the three events Gaia DR3 already confirmed (hunts/H-0009/work/gaia_dr3_sweep.csv), with the source that brightened
    dict(designation="J172057.02-414201.2", source_id="5959812622743175552", t_event_mjd=57272.162),
    dict(designation="J180402.28-181847.5", source_id="4143495279954502016", t_event_mjd=57280.169),
    dict(designation="J180839.93-151910.5", source_id="4145977633638478336", t_event_mjd=57468.906),
]


def gost_count(designation, t_ev, w=RULE["window_d"]):
    g = pd.read_csv(os.path.join(HERE, "..", "reviews", "gaia-dr3-sweep-2026-10-31", "data", "gost_transits.csv"))
    g = g[g.designation == designation]
    return int((np.abs(g.mjd - t_ev) <= w).sum())


def run_test_dr3():
    print(f"numpy {np.__version__}, pandas {pd.__version__}, python {sys.version.split()[0]}")
    os.makedirs(os.path.join(WORK, "dr3_test"), exist_ok=True)
    ids = [e["source_id"] for e in DR3_TEST]
    got, report = fetch(ids, releases=("Gaia DR3",))
    print("fetch report:", json.dumps({"releases": report["releases"]}, default=str))
    rows = []
    for e in DR3_TEST:
        df = got.get(e["source_id"])
        n30 = gost_count(e["designation"], e["t_event_mjd"])
        if df is None:
            rows.append(dict(**e, gost_n_fov_30=n30, status="untestable (data): no epoch photometry"))
            continue
        df.to_csv(os.path.join(WORK, "dr3_test", f"{e['source_id']}.csv"), index=False)
        r = grade_series(df, e["t_event_mjd"])
        rows.append(dict(**e, gost_n_fov_30=n30, **r))
    out = pd.DataFrame(rows)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    print(out.to_string(index=False))
    out.to_csv(os.path.join(WORK, "dr3_test", "grade_dr3_test.csv"), index=False)
    ok = (out.status == "pass").all()
    # negative control: the same stars with the event time moved to quiet epochs (+-400 d) must not pass
    ctl = []
    for e in DR3_TEST:
        df = got.get(e["source_id"])
        for sh in (-400.0, 400.0):
            r = grade_series(df, e["t_event_mjd"] + sh)
            ctl.append(dict(designation=e["designation"], shift_d=sh, status=r["status"], n_win=r["n_win"], r_max=r["r_max"],
                            threshold=r["threshold"]))
    ctl = pd.DataFrame(ctl)
    print("\nnegative control (event time moved +-400 d, inside the DR3 span where possible):")
    print(ctl.to_string(index=False))
    ok_ctl = not (ctl.status == "pass").any()
    # sliding control: one fake event time every 5 d across the DR3 span, at least 180 d from the real event
    n_test = n_pass = n_unres = 0
    for e in DR3_TEST:
        df = got.get(e["source_id"])
        for tf in np.arange(56863.0, 57900.0, 5.0):
            if abs(tf - e["t_event_mjd"]) < 180:
                continue
            st = grade_series(df, tf)["status"]
            if st.startswith("untestable"):
                n_unres += 1
            else:
                n_test += 1
                n_pass += st == "pass"
    print(f"sliding control (fake event every 5 d, >= 180 d from the event): {n_pass} passes in {n_test} testable trials "
          f"({n_unres} others had too few transits)")
    ok_ctl = ok_ctl and n_pass == 0
    print("\nself-test:", "PASS (all three DR3-confirmed events pass; no control passes)" if ok and ok_ctl else "FAIL")
    return ok and ok_ctl


def run_grade(releases):
    print(f"numpy {np.__version__}, pandas {pd.__version__}, python {sys.version.split()[0]} "
          "(sealed with numpy 2.5.4, pandas 2.3.3, Python 3.12.16)")
    smp = pd.read_csv(SAMPLE, dtype={"source_id": str, "alt_source_id": str})
    test = smp[smp.status == "testable"].reset_index(drop=True)
    idmap = {}
    if os.path.exists(IDMAP):
        mp = pd.read_csv(IDMAP, dtype=str)
        idmap = dict(zip(mp.dr3_source_id, mp.dr4_source_id, strict=True))
    want = [idmap.get(s, s) for s in test.source_id] + [idmap.get(s, s) for s in test.alt_source_id.dropna() if s]
    try:
        got, report = fetch(sorted(set(want)), releases=releases)
    except Exception as ex:  # noqa: BLE001
        print(f"fetch failed for {releases}: {type(ex).__name__}: {ex}")
        return None
    print("fetch report:", json.dumps({"releases": report["releases"]}, default=str))
    rows = []
    for r in test.itertuples():
        sid = idmap.get(r.source_id, r.source_id)
        df = got.get(sid)
        row = dict(designation=r.designation, source_id=r.source_id, dr4_source_id=sid, t_event_mjd=r.t_event_mjd)
        if df is None:
            row.update(status="untestable (data): no epoch photometry for the source")
        else:
            row.update(grade_series(df, r.t_event_mjd))
            row["release"] = report["source_release"].get(int(sid), "")
        if isinstance(r.alt_source_id, str) and r.alt_source_id:
            a = got.get(idmap.get(r.alt_source_id, r.alt_source_id))
            row["alt_status (not counted)"] = grade_series(a, r.t_event_mjd)["status"] if a is not None else "no data"
        rows.append(row)
    out = pd.DataFrame(rows)
    tag = releases[0].lower().replace("gaia ", "").replace(" ", "_")
    out.to_csv(os.path.join(WORK, f"grade_{tag}.csv"), index=False)
    pd.set_option("display.width", 250)
    print(out.drop(columns=[c for c in ("n_base",) if c in out]).to_string(index=False))

    fc = json.load(open(FORECAST))
    k = int((out.status == "pass").sum())
    nres = int(out.status.isin(["pass", "fail"]).sum())
    print(f"\nPASS {k} of {len(out)} testable-by-design events ({nres} resolved; "
          f"{len(out) - nres} untestable for lack of data)")
    print("forecast (all 47):", fc["headline"])
    # Pre-registered falsification test, recomputed for the events that actually resolved (section 3 of dr4_ensemble.md)
    use = out.status.isin(["pass", "fail"]).to_numpy()
    if not use.any():
        print("no event resolved: nothing to grade (check the DR4 fetch, the id map and the column mapping)")
        return None
    full = test.copy()
    mc20 = ensemble_mc(full, n=20000, fL=0.20, use=use, resolved_known=True)
    lo, hi = falsification_thresholds(mc20["npass"])
    p_le = float(np.mean(mc20["npass"] <= k))
    p_ge = float(np.mean(mc20["npass"] >= k))
    verdict = ("~20% FALSIFIED (too few passes)" if p_le < 0.05 else "~20% FALSIFIED (too many passes)" if p_ge < 0.05
               else "consistent with ~20%")
    post = fL_posterior(full, use, k)
    ach = int((out.colour == "achromatic").sum())
    chro = int((out.colour == "chromatic").sum())
    und = int((out.colour == "undetermined").sum())
    # secondary test: the number of achromatic passes, same rule
    alo, ahi = falsification_thresholds(mc20["nach"])
    a_le = float(np.mean(mc20["nach"] <= ach))
    a_ge = float(np.mean(mc20["nach"] >= ach))
    a_verdict = ("~20% FALSIFIED (too few achromatic passes)" if a_le < 0.05 else
                 "~20% FALSIFIED (too many achromatic passes)" if a_ge < 0.05 else "consistent with ~20%")
    # Robustness of a "falsified" verdict to the judgement-based non-lens priors (pre-registered nuisance bounds)
    r_lo, r_hi = nuisance_bounds(full, use=use)
    firm = ((p_le < 0.05 and np.mean(r_lo["npass"] <= k) < 0.05) or (p_ge < 0.05 and np.mean(r_hi["npass"] >= k) < 0.05))
    tier = "firm" if firm else ("conditional on the non-lens priors" if "FALSIFIED" in verdict else "")
    robust_lo, robust_hi = falsification_thresholds(r_lo["npass"])[0], falsification_thresholds(r_hi["npass"])[1]
    # forecast interval (fixed, inclusive, not recomputed) and colour hit condition
    i_lo, i_hi = fc["main"]["p10"], fc["main"]["p90"]
    det = ach + chro
    colour_hit = ("not graded (no determined colour)" if det == 0 else
                  ("hit" if ach / det >= 0.40 else "miss") + f" ({ach}/{det} achromatic; hit if >= 40%)")
    summ = dict(n_pass=k, n_resolved=nres, n_testable=len(out),
                interval=f"{i_lo:.0f}-{i_hi:.0f}", interval_hit=bool(i_lo <= k <= i_hi),
                claim="~20% of strong events are lens-like brightenings of the survey-matched Gaia star",
                falsified_if_at_most=lo, falsified_if_at_least=hi,
                P_le_k=p_le, P_ge_k=p_ge, verdict=verdict, verdict_tier=tier, robust_falsified_if_at_most=robust_lo,
                robust_falsified_if_at_least=robust_hi, n_achromatic=ach, colour_forecast=colour_hit,
                numpy=np.__version__, pandas=pd.__version__, python=sys.version.split()[0], achromatic_falsified_if_at_most=alo,
                achromatic_falsified_if_at_least=ahi, achromatic_verdict=a_verdict, fL_post_median=post["median"], fL_post_90=[post["lo90"], post["hi90"]], colour=dict(achromatic=ach, chromatic=chro,
                undetermined=und), achromatic_fraction_of_determined=(ach / (ach + chro)) if (ach + chro) else None)
    print(json.dumps(summ, indent=1))
    json.dump(summ, open(os.path.join(WORK, f"grade_{tag}_summary.json"), "w"), indent=1)
    return summ


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--test-dr3", action="store_true", help="grade the three DR3-confirmed events with Gaia DR3 data")
    ap.add_argument("--release", default="Gaia DR4")
    a = ap.parse_args()
    if a.test_dr3:
        sys.exit(0 if run_test_dr3() else 1)
    run_grade((a.release,))
