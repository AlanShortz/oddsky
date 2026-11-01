"""Event models in Gaia G at GOST transit times, per scenario. Every model returns dm(t): G minus the star's true
quiescent G (negative = brighter).

Targets 1-2 (ATLAS): the atlas10 referee's annual-parallax point-lens fits (all 14 reduction variants,
hunts/H-0008/reviews/claude-referee-atlas10-2026-10-30/data/r3_<k>.json; t0par = 57980 / 58311 as in r3_fits.py).
G sees ratio(t) = 1 + k * fs_o * (A(t) - 1), fs_o = fitted ATLAS-o source flux / ATLAS-o baseline (mean of the o units).
k converts the ATLAS-o ratio to the Gaia star's own ratio. k < 1 if the ATLAS forced-photometry baseline is biased low
(referee: ATLAS baselines 0.7-1.0x the o flux expected from Gaia); k > 1 if ATLAS's baseline holds neighbours Gaia
resolves (J173150: Gaia star 0.95 of the ATLAS-weighted flux). Draw k ~ U(0.65, 1.10).

Targets 3-6 (NEOWISE only): draws from priors weighted by the NEOWISE W1 visit likelihood (all visits, sigma =
sqrt(err^2 + 0.03^2), baseline = median of visits > 400 d from the event).
  L  lens on the Gaia star: t0 between the bracketing quiet visits, tE log-U(20, 200) d (J160706: separate rise/fall tE,
     each log-U(20, 400) d, because the decline is steeper than the rise), u0 U(0, 1.2), fs_W1 U(0.1, 1);
     achromatic; fs_G = fs_W1 + (1 - fs_W1) U(0, 1) (Gaia's 0.2" resolution removes some or all of the WISE 6" blend).
  R  real non-lens event on the Gaia star with the same smooth time profile as L but chromatic: G amplitude (mag) = W1
     amplitude (mag) x U(0.3, 2.0).
  F  short outburst: rise e-fold tau/3, decay e-fold tau, tau log-U(1, 20) d, peak time such that the NEOWISE visit sits
     anywhere from the peak to 3 tau after it; W1 amplitude matched at the visit; G amplitude (mag) = W1 x U(0.5, 2.5);
     must not violate the bracketing quiet visits.
  N  artifact, or event on a different (Gaia-invisible or neighbouring) star: dm = 0.
"""
import json
import os

import numpy as np
import pandas as pd
from targets import LC_DIRS, T

from oddsky.analysis.lensing import magnification, sun_offsets

REF = os.path.join(os.path.dirname(__file__), "..", "..", "..", "H-0008", "reviews", "claude-referee-atlas10-2026-10-30", "data")
T0PAR = {"J163539": 57980.0, "J173150": 58311.0}


def ref_fits(k):
    d = json.load(open(os.path.join(REF, f"r3_{k}.json")))
    out = {}
    for v, r in d.items():
        p = r["res"]["parallax"]
        info = r["info"]
        fo = [p["amp"][s] / info[s]["base"] for s in p["amp"] if s.startswith("ATLAS_o")]
        out[v] = dict(p=p["p"], fs_o=float(np.mean(fo)), chi2=p["chi2"])
    return out


def lens_A(t, ra, dec, p, t0par):
    t0, te, u0, pn, pe = p
    dn, de = sun_offsets(t, ra, dec, t0par)
    tau = (t - t0) / te + pn * dn + pe * de
    beta = u0 + (-pn * de + pe * dn)
    return magnification(np.hypot(tau, beta))


def atlas_draws(k, t, rng, n=400):
    """List of dm arrays at times t for targets 1-2: variants cycled, k random."""
    fits = ref_fits(k)
    tg = T[k]
    A = {v: lens_A(t, tg["ra"], tg["dec"], f["p"], T0PAR[k]) for v, f in fits.items()}
    keys = list(fits)
    out, meta = [], []
    for i in range(n):
        v = keys[i % len(keys)]
        kk = rng.uniform(0.65, 1.10)
        ratio = 1 + kk * fits[v]["fs_o"] * (A[v] - 1)
        out.append(-2.5 * np.log10(ratio))
        meta.append((v, kk))
    return out, meta


def neowise(k):
    tg = T[k]
    for d in LC_DIRS:
        p = os.path.join(d, f"pixel={tg['pixel']}.parquet")
        if os.path.exists(p):
            lc = pd.read_parquet(p)
            lc = lc[lc.allwise_cntr == np.int64(tg["cntr"])].sort_values("t")
            if len(lc):
                base = np.median(lc.w1[np.abs(lc.t - tg["t_nw"]) > 400])
                return lc.t.to_numpy(float), (lc.w1 - base).to_numpy(float), np.hypot(lc.w1_err.to_numpy(float), 0.03)
    raise FileNotFoundError(k)


ASYM = {"J160706"}  # symmetric point lens misses the 58178 decline visit by 4 sigma (chi2 35 vs 21 visits): rise/fall tE free


def magA(t, t0, te, u0, te2=None):
    """Point-lens magnification; with te2, tE applies before t0 and te2 after (asymmetric proxy for parallax)."""
    tt = te if te2 is None else np.where(t < t0, te, te2)
    return magnification(np.hypot((t - t0) / tt, u0))


def lens_posterior(k, rng, n_prior=600_000):
    """Importance-weighted lens draws (t0, tE, u0, fs_W1[, tE2]) given the NEOWISE W1 visits.
    For targets in ASYM: tE (rise) and tE2 (fall) each log-U(20, 400) d."""
    tv, dw, ew = neowise(k)
    tn = T[k]["t_nw"]
    ev = np.argmin(np.abs(tv - tn))
    # bracketing quiet visits: the nearest visits before/after the event block with |dW1| < 0.15
    quiet = np.abs(dw) < 0.15
    lo = tv[(tv < tn) & quiet].max()
    hi = tv[(tv > tn) & quiet].min()
    asym = k in ASYM
    if asym:  # focused box (a broad box gave ESS 3): the visits need the peak near 57980 and a slow rise
        n_prior = 2_000_000
        t0 = rng.uniform(57880, 58080, n_prior)
        te = np.exp(rng.uniform(np.log(60), np.log(400), n_prior))
        te2 = np.exp(rng.uniform(np.log(30), np.log(300), n_prior))
        u0 = rng.uniform(0, 0.5, n_prior)
        fs = rng.uniform(0.3, 1.0, n_prior)
    else:
        t0 = rng.uniform(lo, hi, n_prior)
        te = np.exp(rng.uniform(np.log(20), np.log(200), n_prior))
        te2 = te
        u0 = rng.uniform(0, 1.2, n_prior)
        fs = rng.uniform(0.1, 1.0, n_prior)
    chi2 = np.zeros(n_prior)
    for ti, di, ei in zip(tv, dw, ew, strict=True):
        A = magA(ti, t0, te, u0, te2)
        m = -2.5 * np.log10(1 + fs * (A - 1))
        chi2 += ((m - di) / ei) ** 2
    w = np.exp(-0.5 * (chi2 - chi2.min()))
    w /= w.sum()
    ess = 1 / np.sum(w**2)
    return dict(t0=t0, te=te, te2=te2, u0=u0, fs=fs, w=w, ess=ess, chi2min=chi2.min(), nvis=len(tv), lo=lo, hi=hi, tv=tv, dw=dw, ev=ev)


def sample(post, rng, n):
    i = rng.choice(len(post["w"]), n, p=post["w"])
    return {kk: post[kk][i] for kk in ("t0", "te", "te2", "u0", "fs")}


def lens_dm(t, d, fsG):
    A = magA(t, d["t0"], d["te"], d["u0"], d["te2"])
    return -2.5 * np.log10(1 + fsG * (A - 1))


def scenario_draws(k, t, rng, n=400):
    """dm arrays at times t for scenarios L, R, F (N is zeros)."""
    post = lens_posterior(k, rng)
    S = sample(post, rng, n)
    L, R = [], []
    for i in range(n):
        d = {kk: S[kk][i] for kk in S}
        fsG = d["fs"] + (1 - d["fs"]) * rng.uniform()
        L.append(lens_dm(t, d, fsG))
        R.append(lens_dm(t, d, d["fs"]) * rng.uniform(0.3, 2.0))
    # F: short outbursts
    tv, dw = post["tv"], post["dw"]
    tvis, amp_w1 = tv[post["ev"]], dw[post["ev"]]
    F, tries = [], 0
    while len(F) < n and tries < 100 * n:
        tries += 1
        tau = np.exp(rng.uniform(np.log(1), np.log(20)))
        lag = rng.uniform(0, 3 * tau)  # visit is lag days after the peak
        tp = tvis - lag
        shape_vis = np.exp(-lag / tau)
        fpk = (10 ** (-0.4 * amp_w1) - 1) / shape_vis  # W1 excess flux at peak (fraction of baseline)

        def prof(x, tp=tp, tau=tau):
            return np.where(x >= tp, np.exp(-np.clip(x - tp, 0, None) / tau), np.exp(np.clip(x - tp, None, 0) / (tau / 3)))
        others = np.abs(tv - tvis) > 5
        mw = -2.5 * np.log10(1 + fpk * prof(tv[others]))
        if np.any(np.abs(mw - dw[others]) > 0.15):
            continue
        g = -2.5 * np.log10(1 + fpk * prof(t)) * rng.uniform(0.5, 2.5)
        F.append(g)
    return dict(L=L, R=R, F=F, post=post, S=S)
