"""e3: per-event pass probabilities under each scenario, by simulating Gaia DR4 photometry at the GOST transit times and applying
the pre-registered rule (judge / colour from dr4_ensemble_grade.py, imported, not copied).
Run from the repo root:  uv run python -I hunts/H-0009/predictions/work/ensemble/e3_scenarios.py

Scenarios (what the Gaia source does at the NEOWISE time):
  L  lens (or lens-like: smooth, achromatic) brightening of the tested Gaia star. Point lens, t0 between the bracketing quiet
     NEOWISE visits, tE log-U(20, 200) d (log-U(20, 400) d for 2-4-visit blocks), u0 U(0, 1.2), fs_W1 U(0.1, 1); draws weighted
     by the NEOWISE visits (peak and block visits = their dW1 +- 0.05; the bracketing quiet visits and one more on each side
     = 0 +- 0.07). Gaia resolves part of the WISE blend: fs_G = fs_W1 + (1 - fs_W1) U(0, 1). BP and RP blend fractions scatter
     around fs_G by (1 - fs_G) N(0, 0.15) (blends of another colour inside Gaia's BP/RP window).
  R  real non-lens brightening of the Gaia star, same time profiles as L: G excess flux = q x W1 excess, q log-U(0.1, 1.5);
     bluer when brighter, dBP - dRP = kappa dG with kappa U(0.3, 1.0) (dust clearing, accretion).
  F  short outburst (dwarf-nova-like): decay e-fold tau log-U(1, 20) d, rise tau/3, the NEOWISE visit 0-3 tau after the peak,
     W1 amplitude matched at the visit; dG = g x dW1(t), g U(0.5, 2.5); kappa U(0.5, 1.5).
  N  nothing on the Gaia star (IR-only event, event on a neighbour, NEOWISE artifact): flat.
Observation model per realisation: GOST transits in the DR4 span, 10% lost; per-transit G noise = the DR3 floor x1.5
(gaialib.sigma_G, checked against the DR3 baselines of the three confirmed sources: 0.035/0.019/0.008 predicted vs
0.028/0.019/0.007 observed); BP and RP noise from the same three sources and the Gaia DR3 documentation (sigma_BP, sigma_RP);
intrinsic stellar jitter log-U(0.003, 0.05) mag; 2% per-transit outliers of +-0.2-1.0 mag; 1% per-epoch (both fields of view)
brightward outliers of 0.15-0.6 mag (a neighbour drifting into the window). BP available on 92% of transits (50% if BP > 21),
RP on 95%. 2% of sources have no DR4 epoch photometry at all (id mapping). In 3% of realisations DR4 rejects every transit more
than 0.5 mag above the source's median (the earlier proposal's pessimistic branch; DR3 did not do this to the three confirmed
events). Lens draws with an effective sample size below 300 are redrawn from 1.5 million prior samples.
Writes work/ensemble/scenario_pass.csv: per event p_res, q_S = P(pass | resolved, S), a_S / u_S = P(achromatic / undetermined |
pass, S), plus diagnostics (ESS of the lens draws, median ratio at the best window transit under L)."""
import ast
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
PRED = os.path.abspath(os.path.join(HERE, "..", ".."))
ROOT = os.path.abspath(os.path.join(PRED, "..", "..", ".."))
sys.path.insert(0, PRED)
sys.path.insert(0, os.path.join(ROOT, "src"))
from dr4_ensemble_grade import RULE, colour, judge  # noqa: E402

from oddsky.analysis.lensing import magnification  # noqa: E402

N_DRAW = {"L": 1200, "R": 1200, "F": 1200, "N": 3000}
P_NODATA = 0.02
P_REJECT_BRIGHT = 0.03
rng = np.random.default_rng(31)


def sigma_G(G):
    g = np.array([12, 13, 15, 16, 17, 18, 18.5, 19, 20, 21])
    s = np.array([0.0012, 0.0015, 0.003, 0.005, 0.008, 0.013, 0.020, 0.030, 0.06, 0.12])
    return 1.5 * np.interp(G, g, s)


def sigma_BP(m):
    g = np.array([14, 16, 17, 17.7, 18.5, 19.3, 20, 20.5, 21, 21.7])
    s = np.array([0.008, 0.015, 0.025, 0.04, 0.06, 0.095, 0.17, 0.28, 0.5, 1.2])
    return np.interp(m, g, s)


def sigma_RP(m):
    g = np.array([12, 14, 15, 16, 17, 17.5, 18, 19, 20])
    s = np.array([0.004, 0.006, 0.008, 0.011, 0.025, 0.035, 0.05, 0.10, 0.20])
    return np.interp(m, g, s)


def visits(r):
    """NEOWISE constraints: (times, dW1, sigma)."""
    bd = ast.literal_eval(r.block_dw1)
    nb = len(bd)
    tt = np.linspace(r.t_first, r.t_last, nb) if nb > 1 else np.array([r.t_event_mjd])
    tt[np.argmin(np.abs(tt - r.t_event_mjd))] = r.t_event_mjd
    t = list(tt) + [r.t_prev, r.t_next, r.t_prev - 182.6, r.t_next + 182.6]
    d = list(bd) + [0, 0, 0, 0]
    e = [0.05] * nb + [0.07] * 4
    return np.array(t), np.array(d, float), np.array(e)


def lens_draws(r, n_out, n_prior=150_000):
    tv, dv, ev = visits(r)
    lo, hi = r.t_prev, r.t_next
    tmax = 400 if r.nblock >= 2 else 200
    t0 = rng.uniform(lo, hi, n_prior)
    te = np.exp(rng.uniform(np.log(20), np.log(tmax), n_prior))
    u0 = rng.uniform(0, 1.2, n_prior)
    fs = rng.uniform(0.1, 1.0, n_prior)
    chi2 = np.zeros(n_prior)
    for ti, di, ei in zip(tv, dv, ev, strict=True):
        A = magnification(np.hypot((ti - t0) / te, u0))
        m = -2.5 * np.log10(1 + fs * (A - 1))
        chi2 += ((m - di) / ei) ** 2
    w = np.exp(-0.5 * (chi2 - chi2.min()))
    w /= w.sum()
    ess = 1 / np.sum(w ** 2)
    if ess < 300 and n_prior < 1_000_000:
        return lens_draws(r, n_out, n_prior=1_500_000)
    i = rng.choice(n_prior, n_out, p=w)
    return dict(t0=t0[i], te=te[i], u0=u0[i], fs=fs[i]), ess, float(chi2.min())


def epochs(t):
    g = np.zeros(len(t), int)
    g[1:] = np.cumsum(np.diff(t) > 0.5)
    return g


def observe(T, ep, dG, dBP, dRP, G0, BP0, RP0):
    """One realisation of DR4 photometry. Returns (ids, tG, mG), bp tuple, rp tuple, or None if no data."""
    if rng.random() < P_NODATA:
        return None
    n = len(T)
    keep = rng.random(n) > 0.10
    jit = np.exp(rng.uniform(np.log(0.003), np.log(0.05)))
    out = np.zeros(n)
    o = rng.random(n) < 0.02
    out[o] = rng.choice([-1, 1], o.sum()) * rng.uniform(0.2, 1.0, o.sum())
    ne = ep.max() + 1
    eo = rng.random(ne) < 0.01
    off = np.where(eo, -rng.uniform(0.15, 0.6, ne), 0.0)[ep]
    out = out + off
    mG = G0 + dG
    gG = mG + rng.normal(0, 1, n) * np.hypot(sigma_G(mG), jit) + out
    ids = np.arange(n)
    if rng.random() < P_REJECT_BRIGHT:  # DR4 processing rejects transits far above the source's median (pessimistic branch)
        keep &= ~(gG - np.median(gG) < -0.5)
    res = [(ids[keep], T[keep], gG[keep])]
    for m0, dm, sf, avail, jf in ((BP0, dBP, sigma_BP, 0.92, 1.3), (RP0, dRP, sigma_RP, 0.95, 0.8)):
        if not np.isfinite(m0):
            res.append((np.array([], int), np.array([]), np.array([]), np.array([])))
            continue
        mb = m0 + dm
        sb = np.hypot(sf(mb), jf * jit)
        av = keep & (rng.random(n) < (avail if m0 < 21 else 0.5))
        mm = mb + rng.normal(0, 1, n) * sb + out * rng.uniform(0.5, 1.5, n)
        res.append((ids[av], T[av], mm[av], sb[av] / 1.2))  # formal errors a little smaller than the true scatter
    return res


def evaluate(T, ep, t_ev, dG, dBP, dRP, G0, BP0, RP0):
    o = observe(T, ep, dG, dBP, dRP, G0, BP0, RP0)
    if o is None:
        return "nodata", None
    (ids, tg, mg), bp, rp = o
    j = judge(tg, mg, t_ev)
    if j["status"] != "pass":
        return ("unres" if j["status"].startswith("untestable") else "fail"), None
    c = colour(list(ids[j["up"]]), bp, rp, t_ev)
    return "pass", c["colour"]


def mag(x):
    return -2.5 * np.log10(np.clip(x, 1e-6, None))


smp = pd.read_csv(os.path.join(PRED, "dr4_ensemble_sample.csv"), dtype={"source_id": str, "alt_source_id": str})
gs = pd.read_csv(os.path.join(HERE, "gost_sample.csv"))
rows = []
for r in smp[smp.status == "testable"].itertuples():
    T = np.sort(gs[gs.designation == r.designation].mjd.to_numpy())
    ep = epochs(T)
    G0, BP0, RP0 = r.G, r.BP, r.RP
    t_ev = r.t_event_mjd
    LD, ess, chi2 = lens_draws(r, max(N_DRAW["L"], N_DRAW["R"]))
    tally = {k: dict(n=0, nodata=0, unres=0, pass_=0, ach=0, und=0) for k in "LRFN"}
    best_L = []
    for k in "LRFN":
        for i in range(N_DRAW[k]):
            if k in "LR":
                A = magnification(np.hypot((T - LD["t0"][i]) / LD["te"][i], LD["u0"][i]))
                fsw = LD["fs"][i]
                if k == "L":
                    fsg = fsw + (1 - fsw) * rng.uniform()
                    fb = np.clip(fsg + (1 - fsg) * rng.normal(0, 0.15), 0.02, 1)
                    fr = np.clip(fsg + (1 - fsg) * rng.normal(0, 0.15), 0.02, 1)
                    dG, dBP, dRP = mag(1 + fsg * (A - 1)), mag(1 + fb * (A - 1)), mag(1 + fr * (A - 1))
                    w = np.abs(T - t_ev) <= RULE["window_d"]
                    best_L.append(float(np.max(1 + fsg * (A[w] - 1))))
                else:
                    q = np.exp(rng.uniform(np.log(0.1), np.log(1.5)))
                    dG = mag(1 + q * fsw * (A - 1))
                    kap = rng.uniform(0.3, 1.0)
                    dBP, dRP = dG * (1 + kap / 2), dG * (1 - kap / 2)
            elif k == "F":
                tau = np.exp(rng.uniform(0, np.log(20)))
                lag = rng.uniform(0, 3 * tau)
                tp = t_ev - lag
                fpk = (10 ** (-0.4 * r.dw1) - 1) / np.exp(-lag / tau)
                prof = np.where(T >= tp, np.exp(-np.clip(T - tp, 0, None) / tau), np.exp(np.clip(T - tp, None, 0) / (tau / 3)))
                dG = mag(1 + fpk * prof) * rng.uniform(0.5, 2.5)
                kap = rng.uniform(0.5, 1.5)
                dBP, dRP = dG * (1 + kap / 2), dG * (1 - kap / 2)
            else:
                dG = dBP = dRP = np.zeros(len(T))
            st, col = evaluate(T, ep, t_ev, dG, dBP, dRP, G0, BP0, RP0)
            tl = tally[k]
            tl["n"] += 1
            if st == "nodata":
                tl["nodata"] += 1
            elif st == "unres":
                tl["unres"] += 1
            elif st == "pass":
                tl["pass_"] += 1
                tl["ach"] += col == "achromatic"
                tl["und"] += col == "undetermined"
    row = dict(designation=r.designation, ess_L=round(ess, 1), chi2min_L=round(chi2, 2),
               L_best_ratio_med=round(float(np.median(best_L)), 3), L_best_ratio_p10=round(float(np.percentile(best_L, 10)), 3))
    nres_all = sum(tl["n"] - tl["nodata"] - tl["unres"] for tl in tally.values())
    row["p_res"] = round(nres_all / sum(tl["n"] for tl in tally.values()), 4)
    for k, tl in tally.items():
        nres = tl["n"] - tl["nodata"] - tl["unres"]
        row[f"q_{k}"] = round(tl["pass_"] / nres, 4) if nres else 0.0
        row[f"a_{k}"] = round(tl["ach"] / tl["pass_"], 4) if tl["pass_"] else 0.0
        row[f"u_{k}"] = round(tl["und"] / tl["pass_"], 4) if tl["pass_"] else 1.0
    rows.append(row)
    print(f"{r.designation} G {G0:5.2f} BP {BP0:5.2f} n30 {r.gost_n_fov_30} ess {ess:7.0f} p_res {row['p_res']:.3f}  "
          + "  ".join(f"{k}: q {row[f'q_{k}']:.3f} a {row[f'a_{k}']:.2f} u {row[f'u_{k}']:.2f}" for k in "LRFN"), flush=True)

out = pd.DataFrame(rows)
out.to_csv(os.path.join(HERE, "scenario_pass.csv"), index=False)
print("\nmean q:", {k: round(out[f"q_{k}"].mean(), 3) for k in "LRFN"}, " mean p_res", round(out.p_res.mean(), 3))
