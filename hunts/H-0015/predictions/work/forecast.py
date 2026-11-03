"""H-0015 forecast numbers (F1-F5 of dr4_astrometric_forecast.md), revised after the referee (2026-11-02).

Inputs (all committed): ../data/ranked_targets.csv (s5), ../data/forecast_fits.csv (s8: per-target fits with the robust
fitter), ../data/controls.csv (s7), ../acceptance/summary_recheck.json and the raw re-check table
~/oddsky-runs/h0015/acceptance/acceptance_recheck.csv (s4 --parts recheck). Writes work/forecast.json and
../predictions/dr4_astrometric_sample.csv. Run: uv run python -I hunts/H-0015/predictions/work/forecast.py

Conventions used throughout:
  * BH share: the Galactic model's P(black hole | lens) halved (BH_DISCOUNT): the model makes too few ordinary long events
    (median tE 14 d against ~20 d observed), so its black-hole share of long events is about 2x generous. One calibration
    everywhere: F2, F3 and the honest odds.
  * error scenarios: nominal and 1.7x worse, weights 0.5/0.5.
  * false positives: per target FP = (1 - f_b) FP_clean + f_b FP_binary + FP_other, with f_b ~ U(0.05, 0.25) the fraction of
    stars with an undetected astrometric binary companion (wobble below DR3's RUWE 1.4) and FP_other ~ U(0, 0.5%) for what
    no simulation contains; FP_clean and FP_binary measured in the re-check (target-like nulls with a photometric event;
    control-like nulls with flat photometry). Marginalised by Monte Carlo, jointly for F1 and F5.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binom

HERE = Path(__file__).resolve().parent
H = HERE.parents[1]
DATA = H / "data"
RECHECK = Path.home() / "oddsky-runs/h0015/acceptance/acceptance_recheck.csv"
W_NOMINAL = 0.5
BH_DISCOUNT = 0.5
FB_RANGE = (0.05, 0.25)
FP_OTHER_MAX = 0.005
RUWE_MAX = 1.4
F1_RANGE = (2, 6)
F2_MAX, F3_MAX = 3.0, 5.0
F5_MAX_FRAC = 0.015
N_MC = 400


def poisson_binomial(p):
    d = np.zeros(len(p) + 1)
    d[0] = 1.0
    for x in p:
        d[1:] = d[1:] * (1 - x) + d[:-1] * x
        d[0] *= 1 - x
    return d


def laplace(k, n):
    return (k + 1) / (n + 2)


def p_kind_given_lens(source_id, n=4000, over=100, seed=11):
    """P(lens mass | lens, the event's photometry) from a large Galactic-model draw, with the BH share discounted."""
    sys.path.insert(0, str(H / "scripts"))
    from common import load_targets
    from s5_rank import constraints, source_distance

    from oddsky.analysis import lenspop

    T = load_targets()
    r = next(T[T.source_id == source_id].itertuples())
    te, pie = constraints(r)
    ds, dss, _ = source_distance(r)
    mf, kind = lenspop.mass_function_samples(n * over, rng=np.random.default_rng(seed))
    mu_s = (r.pmra, r.pmdec) if np.isfinite(r.pmra) else None
    smp = lenspop.sample_lenses(r.l, r.b, r.ra, r.dec, mf, n=n, oversample=over, ds=ds, ds_sig=dss, mu_s=mu_s, te_range=te,
                                pie_range=pie, rng=np.random.default_rng(seed + 1))
    w = smp["weight"].copy()
    p_bh_model = float(w[kind == "BH"].sum())
    w[kind == "BH"] *= BH_DISCOUNT
    w /= w.sum()
    return mf, kind, w, smp["n_eff"], p_bh_model


def main():
    R = pd.read_csv(DATA / "ranked_targets.csv", dtype={"source_id": str})
    F = pd.read_csv(DATA / "forecast_fits.csv", dtype={"source_id": str})
    C = pd.read_csv(DATA / "controls.csv", dtype={"source_id": str})
    acc = pd.read_csv(RECHECK)
    F["sig"] = (F.dchi2 >= 25) & (F.err_scale <= 3) & (F.theta_e > 0) & (F.theta_e <= 50)
    acc["sig"] = (acc.dchi2 >= 25) & (acc.err_scale <= 3) & (acc.theta_e > 0) & (acc.theta_e <= 50)

    # ---- false-positive rates from the re-check
    def rate(kinds):
        g = acc[acc.kind.isin(kinds)]
        return laplace(int(g.sig.sum()), len(g)), int(g.sig.sum()), len(g)

    fp_clean, kc, nc = rate(["null_clean", "null_underest", "null_outliers", "null_bigoutlier"])
    fp_bin, kb, nb = rate(["null_binary"])
    fpc_clean, kcc, ncc = rate(["ctrl_clean"])
    fpc_bin, kcb, ncb = rate(["ctrl_binary"])
    rng = np.random.default_rng(2026)
    fb = rng.uniform(*FB_RANGE, N_MC)
    other = rng.uniform(0, FP_OTHER_MAX, N_MC)
    fp_t = (1 - fb) * fp_clean + fb * fp_bin + other
    fp_c = (1 - fb) * fpc_clean + fb * fpc_bin + other

    # ---- samples
    R["in_span"] = R.set != "case_after_span"
    R["f1"] = R.in_span & (R.exclude_note.fillna("") == "") & (R.ruwe.fillna(9) <= RUWE_MAX) & (R.status == "ok")
    s = R[R.f1]
    sid = {c: R[R.case == c].source_id.iloc[0] for c in ("OS-0016", "OS-0020", "OS-0021")}

    # ---- F1: Poisson-binomial over targets, mixed over error scenarios and the false-positive prior
    dist = np.zeros(len(s) + 1)
    for w, col in ((W_NOMINAL, "pdet_pop"), (1 - W_NOMINAL, "pdet_pop_pess")):
        pl = s.p_lens.to_numpy() * s[col].fillna(0).to_numpy()
        for f in fp_t[::8]:
            dist += w * poisson_binomial(pl + (1 - pl) * f) / len(fp_t[::8])
    p_f1 = float(dist[F1_RANGE[0]:F1_RANGE[1] + 1].sum())
    mean_f1 = float(np.sum(np.arange(len(dist)) * dist))

    # ---- F5: controls, binomial over the eligible controls (all assumed eligible), same prior draws
    n_ctrl = len(C)
    kmax = int(np.ceil(F5_MAX_FRAC * n_ctrl)) - 1          # "fraction < 2.5%": k <= kmax
    p_f5 = float(np.mean(binom.cdf(kmax, n_ctrl, fp_c)))
    f5_alt = {f"{x:.3f}": round(float(np.mean(binom.cdf(int(np.ceil(x * n_ctrl)) - 1, n_ctrl, fp_c))), 3)
              for x in (0.015, 0.02, 0.025, 0.03, 0.04)}

    def frac(g, cond):
        return float(cond(g).mean()) if len(g) else np.nan

    def hyp(target, h, scale=1.0):
        return F[(F.target == target) & (F.hyp == h) & (F.scale == scale)]

    def mixed(target, h, cond):
        """nominal/pessimistic mixture of P(cond) for hypothesis h; where only 1 Msun / theta0 / nonlens have a pessimistic
        run, other hypotheses take the same pessimistic/nominal ratio as the 1 Msun run."""
        pn = frac(hyp(target, h), cond)
        pp_runs = hyp(target, h, 1.7)
        if len(pp_runs):
            pp = frac(pp_runs, cond)
        else:
            r1n, r1p = frac(hyp(target, "1.0"), cond), frac(hyp(target, "1.0", 1.7), cond)
            pp = pn * (r1p / r1n) if r1n and np.isfinite(r1n) and r1n > 0 else pn
        return W_NOMINAL * pn + (1 - W_NOMINAL) * pp, pn, pp

    masses = np.array([0.3, 1.0, 3.0, 5.0, 10.0])

    def p_given_M(target, cond, zero_hyp):
        vals = np.array([mixed(target, f"{m:g}" if m < 1 else f"{m:.1f}", cond)[0] for m in masses])
        p0 = mixed(target, zero_hyp, cond)[0]
        vals = np.where(np.isfinite(vals), vals, np.nan)
        def at(M):
            M = np.asarray(M, float)
            v = np.interp(np.log(np.clip(M, 0.3, 10.0)), np.log(masses), np.nan_to_num(vals, nan=0.0))
            return np.where(M < 0.05, p0, v)
        return at, dict(zip([f"{m:g}" for m in masses], [round(float(v), 3) for v in vals], strict=True)), p0

    # ---- F2: OS-0020, M_ul95 finite and < 3 Msun
    c2 = lambda g: np.isfinite(g.M_ul95) & (g.M_ul95 < F2_MAX)  # noqa: E731
    at2, tab2, p02 = p_given_M("OS-0020", c2, "theta0")
    mf, kind, w, neff2, pbh2 = p_kind_given_lens(sid["OS-0020"])
    pl2 = float(R[R.source_id == sid["OS-0020"]].p_lens.iloc[0])
    p_true_lens2 = float(np.sum(w * at2(mf)))
    p_f2 = pl2 * p_true_lens2 + (1 - pl2) * p02

    # ---- F3: OS-0021, conditional on resolution (M_ul95 finite, or a significant heavy deflection)
    c3t = lambda g: np.isfinite(g.M_ul95) & (g.M_ul95 < F3_MAX) & ~(g.sig & (g.M_lo95 >= F3_MAX))  # noqa: E731
    c3r = lambda g: np.isfinite(g.M_ul95) | (g.sig & (g.M_lo95 >= F3_MAX))  # noqa: E731
    at3t, tab3t, p03t = p_given_M("OS-0021", c3t, "nonlens")
    at3r, tab3r, p03r = p_given_M("OS-0021", c3r, "nonlens")
    mf3, kind3, w3, neff3, pbh3 = p_kind_given_lens(sid["OS-0021"])
    pl3 = float(R[R.source_id == sid["OS-0021"]].p_lens.iloc[0])
    pt = pl3 * float(np.sum(w3 * at3t(mf3))) + (1 - pl3) * p03t
    pr = pl3 * float(np.sum(w3 * at3r(mf3))) + (1 - pl3) * p03r
    p_f3 = pt / pr

    # ---- F4: OS-0016, significant deflection
    pl4 = float(R[R.source_id == sid["OS-0016"]].p_lens.iloc[0])
    p4, p4n, p4p = mixed("OS-0016", "pop", lambda g: g.sig)
    p_f4 = float(pl4 * p4 + (1 - pl4 * p4) * fp_t.mean())

    # ---- honest odds: black-hole mass claims (significant, M > 3 Msun at >= 3 sigma), discounted BH share
    rf = pd.read_csv(DATA / "rank_fits.csv", dtype={"source_id": str})
    rf["hyp"] = rf.hyp.astype(str)
    claims = []
    for x in R[(R.exclude_note.fillna("") == "") & R.in_span & (R.status == "ok")].itertuples():
        pbh = BH_DISCOUNT * (0.0 if not np.isfinite(x.p_bh_given_lens) else x.p_bh_given_lens)
        g = rf[rf.source_id == x.source_id]
        if len(g):
            c5 = g[g.hyp == "5.0"].p_m_gt3_3sig
            c10 = g[g.hyp == "10.0"].p_m_gt3_3sig
            c = float(np.interp(7.8, [5, 10], [c5.iloc[0] if len(c5) else 0.0, c10.iloc[0] if len(c10) else 0.0]))
            claims.append(x.p_lens * pbh * c)
        else:
            claims.append(x.p_lens * BH_DISCOUNT * (0.0 if not np.isfinite(x.pdet_pop_bh) else x.pdet_pop_bh) * 0.3)
    claims = np.array(claims)
    binary_sig_theta = acc[(acc.kind == "null_binary") & acc.sig].theta_e.round(2).tolist()
    honest = dict(bh_discount=BH_DISCOUNT, expected_bh_claims=float(claims.sum()),
                  p_at_least_one=float(1 - poisson_binomial(claims)[0]),
                  expected_bh_deflections=float(BH_DISCOUNT * (R.p_lens * R.pdet_pop_bh.fillna(0) * (R.exclude_note.fillna("") == "")).sum()),
                  expected_spurious_detections_in_F1=float(len(s) * fp_t.mean()),
                  binary_false_positive_theta_e=binary_sig_theta)

    # ---- the sample (targets F1-F4, controls F5)
    tags = []
    smp = R[R.in_span & (R.status == "ok")][["rank", "source_id", "name", "case", "set", "p_lens", "G", "ruwe", "t0", "tE_lo",
                                              "tE_hi", "piE_lo", "piE_hi", "pdet_pop", "pdet_pop_pess", "pdet_5", "score",
                                              "exclude_note"]].copy()
    for x in smp.itertuples():
        t = []
        if x.source_id in set(s.source_id):
            t.append("F1")
        for k, c in (("F2", "OS-0020"), ("F3", "OS-0021"), ("F4", "OS-0016")):
            if x.source_id == sid[c]:
                t.append(k)
        tags.append(";".join(t))
    smp.insert(0, "forecast", tags)
    smp = smp[smp.forecast != ""]
    ctl = C.assign(forecast="F5", set="control", case="", rank=np.nan, p_lens=0.0)[
        ["forecast", "rank", "source_id", "name", "case", "set", "p_lens", "G", "ruwe", "t0", "tE_lo", "tE_hi", "matched_target"]]
    pd.concat([smp, ctl], ignore_index=True).to_csv(H / "predictions/dr4_astrometric_sample.csv", index=False, float_format="%.6g")

    out = dict(
        conventions=dict(w_nominal=W_NOMINAL, bh_discount=BH_DISCOUNT, fb_range=FB_RANGE, fp_other_max=FP_OTHER_MAX),
        false_positives=dict(fp_clean=fp_clean, clean_k_n=[kc, nc], fp_binary=fp_bin, binary_k_n=[kb, nb],
                             ctrl_clean=fpc_clean, ctrl_clean_k_n=[kcc, ncc], ctrl_binary=fpc_bin, ctrl_binary_k_n=[kcb, ncb],
                             fp_target_mean=float(fp_t.mean()), fp_target_5_95=[float(np.percentile(fp_t, 5)), float(np.percentile(fp_t, 95))],
                             fp_control_mean=float(fp_c.mean()), fp_control_5_95=[float(np.percentile(fp_c, 5)), float(np.percentile(fp_c, 95))]),
        F1=dict(n=int(len(s)), mean=mean_f1, p=p_f1, range=list(F1_RANGE), dist=[round(float(x), 4) for x in dist[:14]],
                expected_from_lenses_nominal=float((s.p_lens * s.pdet_pop.fillna(0)).sum()),
                expected_from_lenses_pess=float((s.p_lens * s.pdet_pop_pess.fillna(0)).sum()),
                expected_false=float(len(s) * fp_t.mean()), n_known_ogle_kmtnet=int((s.set == "h0010_known").sum()),
                n_neowise=int((s.set == "strong").sum()), neowise_median_p_lens=float(s[s.set == "strong"].p_lens.median())),
        F2=dict(source_id=sid["OS-0020"], p_lens=pl2, p_bh_model=pbh2, n_eff=neff2, p_true_given_M=tab2, p_true_theta0=p02,
                p_true_given_lens=p_true_lens2, p=float(p_f2)),
        F3=dict(source_id=sid["OS-0021"], p_lens=pl3, p_bh_model=pbh3, n_eff=neff3, p_true_given_M=tab3t, p_resolved_given_M=tab3r,
                p_true_nonlens=p03t, p_resolved_nonlens=p03r, p_true=pt, p_resolved=pr, p=float(p_f3)),
        F4=dict(source_id=sid["OS-0016"], p_lens=pl4, p_sig_nominal=p4n, p_sig_pess=p4p, p=p_f4),
        F5=dict(n_controls=n_ctrl, threshold_frac=F5_MAX_FRAC, k_max=kmax, p=p_f5, p_by_threshold=f5_alt),
        honest_odds=honest, versions=dict(numpy=np.__version__, pandas=pd.__version__, python=sys.version.split()[0]))
    (HERE / "forecast.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({k: v for k, v in out.items() if k != "F1"} | {"F1": {k: v for k, v in out["F1"].items() if k != "dist"}},
                     indent=1, default=float))


if __name__ == "__main__":
    main()
