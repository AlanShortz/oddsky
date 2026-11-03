"""H-0015 s4: acceptance test of the joint photometric + along-scan astrometric lens fitter on simulated Gaia DR4 data.

  (a) injection-recovery: dark lenses of 0.1-30 Msun in front of sources of G 12-20, at the real positions of our targets
      (their GOST transit times, scan angles and AL parallax factors over DR4's span, 20% of transits dropped at random for
      dead time), with lens distance, relative proper motion and piE drawn from the Galactic model (lenspop) for that sight
      line and mass, t0 anywhere in the span, |u0| < 1, source fraction fs 0.5-1 (the same blending in G photometry and in
      the astrometric window). Gaia G photometry at the same transits is the only photometry (conservative: real targets
      also have ATLAS/NEOWISE). The fitter is told t0 to +-20 d and tE to a factor ~1.35, as our targets' photometry does.
      Nominal errors: EDR3 per-CCD residual scatter (Lindegren+21) / sqrt(8) + 0.05 mas per transit; a pessimistic run
      uses Rybicki+18's pre-launch per-FoV errors (about 2x worse at G 15-18).
  (b) OGLE-2011-BLG-0462 (Mroz, Udalski & Gould 2022: t0 HJD 2455763.33, tE 239.7 d, u0 0.00263, piE (N, E) = (0.073,
      -0.050), theta_E 5.68 mas, M 7.88 Msun; source I_S 19.8 with ~20x more blend light, a neighbour 0.38" away): at its
      real Gaia scan times, with the Gaia DR3 source at the position (4056442477683080960, G 17.93, 0.17" away) as the blend
      + source, fs ~0.05. Then counterfactuals: the same lens peaking mid-DR4, blended and unblended.
  (c) null tests (theta_E = 0) to calibrate false positives: clean errors; errors underestimated by 30%; an unresolved
      neighbour offset 50-300 mas inside the window (the blend-offset pull); 3% of transits replaced by 8-sigma outliers.

Detection = Delta chi^2 (no deflection minus deflection, both with the blend-offset terms) >= 25 after the fitter's error
rescaling and clipping. Outputs: ~/oddsky-runs/h0015/acceptance/*.csv (every realisation), hunts/H-0015/acceptance/
summary.json and tables. Run: uv run python -I hunts/H-0015/scripts/s4_acceptance.py [--quick] [--workers 3]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import zlib
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DEAD_TIME_KEEP, DR4_END, DR4_START, HUNT, RUNS, load_targets, transits  # noqa: E402

from oddsky.analysis import astrolens as al  # noqa: E402
from oddsky.analysis import lenspop  # noqa: E402

OUT = RUNS / "acceptance"
SUM = HUNT / "acceptance"
MASSES = [0.1, 0.3, 1.0, 3.0, 10.0, 30.0]
GS = [12.0, 14.0, 16.0, 18.0, 20.0]
THRESH = 25.0
OB = dict(t0=55762.83, tE=239.7, u0=0.00263, piEN=0.073, piEE=-0.050, theta_e=5.68, M=7.88, G=17.93, fs=0.048,
          ra=267.917458, dec=-29.890639, pos="OB110462")


def positions():
    t = load_targets()
    t = t[t.ra.notna()]
    g = pd.read_csv(HUNT / "data/gost_transits.csv.gz", dtype={"source_id": str})
    have = set(g.source_id)
    t = t[t.source_id.isin(have)].drop_duplicates("source_id")
    bulge = (np.abs(((t.l + 180) % 360) - 180) < 12) & (np.abs(t.b) < 8)
    return [dict(pos=r.source_id, ra=r.ra, dec=r.dec, l=r.l, b=r.b, ds=8.0 if bl else 4.0, ds_sig=1.0 if bl else 1.5)
            for r, bl in zip(t.itertuples(), bulge, strict=True)]


def lens_bank(p, mass, n=400, seed=0):
    s = lenspop.sample_lenses(p["l"], p["b"], p["ra"], p["dec"], mass, n=n, ds=p["ds"], ds_sig=p["ds_sig"], mu_s=None,
                              te_range=(3.0, 1500.0), rng=np.random.default_rng(seed))
    r = lenspop.resample(s, n, rng=np.random.default_rng(seed + 1))
    return np.column_stack([r["tE"], r["theta_E"], r["piE_N"], r["piE_E"], r["D_L"]])


def run_one(job):
    """One simulated target, fitted. job: dict with kind, seed, G, pos dict, lens row or None, and options."""
    rng = np.random.default_rng(job["seed"])
    p = job["pos"]
    t, th, px = transits(p["pos"], keep=DEAD_TIME_KEEP, rng=rng)
    kind = job["kind"]
    if job.get("lens") is not None:
        tE, theta_e, pin, pie, dl = job["lens"]
    else:
        tE = float(np.exp(rng.uniform(np.log(20), np.log(300))))
        theta_e, dl = 0.0, np.nan
        ang = rng.uniform(0, 2 * np.pi)
        pe = float(np.exp(rng.uniform(np.log(0.02), np.log(0.5))))
        pin, pie = pe * np.cos(ang), pe * np.sin(ang)
    t0 = job.get("t0", float(rng.uniform(DR4_START + 60, DR4_END - 60)))
    u0 = job.get("u0", float(rng.uniform(-1, 1)))
    if kind.startswith("ctrl"):
        u0 = 100.0           # a control star: flat photometry; the fitter still gets the (fake) event's t0 and tE hints
    fs = job.get("fs", float(rng.uniform(0.5, 1.0)))
    q = np.array([t0, tE, u0, pin, pie])
    sig_scale = 1.3 if kind == "null_underest" else 1.0
    blend_vec = (0.0, 0.0)
    if kind == "null_blend":
        fs = float(rng.uniform(0.3, 0.9))
        d = rng.uniform(50, 300)
        a = rng.uniform(0, 2 * np.pi)
        blend_vec = (d * (1 - fs) * np.cos(a), d * (1 - fs) * np.sin(a))
    G = job["G"]
    t0par = float(round(t0))
    ph, ast = al.simulate(t, th, px, p["ra"], p["dec"], G, q, theta_e, fs=fs, pm=(-3.0, -5.0), parallax=0.2,
                          sig_scale=sig_scale, blend_vec=blend_vec, precision=job.get("precision", "edr3"), rng=rng,
                          t0par=t0par)
    if kind == "null_underest":
        ast = al.AstroData(ast.t, ast.theta, ast.w, ast.sigma / 1.3, ast.plx)
    if kind == "null_outliers":
        m = rng.uniform(size=len(ast)) < 0.03
        ast.w[m] += rng.choice([-8, 8], m.sum()) * ast.sigma[m]
    if kind == "null_bigoutlier":                       # one value 100 mas off (DR4 has values outside the window)
        j = rng.integers(len(ast))
        ast.w[j] += rng.choice([-1, 1]) * 100.0
    extra = {}
    if kind in ("null_binary", "ctrl_binary"):
        # the referee's binary source: circular photocentre orbit, random orientation, P 0.3-3 yr, along-scan rms
        # f x sigma_CCD with f 0.2-0.95, so that DR3's RUWE ~ sqrt(1 + f^2) stays <= 1.4
        s_ccd = float(np.exp(np.interp(G, al._G_CCD, np.log(al._S_CCD))))
        P = float(np.exp(rng.uniform(np.log(0.3 * 365.25), np.log(3 * 365.25))))
        ph0, inc, Om = rng.uniform(0, 2 * np.pi), np.arccos(rng.uniform(-1, 1)), rng.uniform(0, 2 * np.pi)
        x, y = np.cos(2 * np.pi * ast.t / P + ph0), np.sin(2 * np.pi * ast.t / P + ph0) * np.cos(inc)
        dN, dE = x * np.cos(Om) - y * np.sin(Om), x * np.sin(Om) + y * np.cos(Om)
        wo = dE * np.sin(ast.theta) + dN * np.cos(ast.theta)
        f = float(rng.uniform(0.2, 0.95))
        amp = f * s_ccd / max(float(np.std(wo)), 1e-9)
        ast.w += amp * wo
        extra = dict(bin_P=P, bin_f=f, bin_amp=amp)
    lam, sth = al.expected_dchi2(ast.t, ast.theta, ast.sigma, ast.plx, p["ra"], p["dec"], q[None], theta_e, fs, t0par=t0par)
    rec = dict(kind=kind, seed=job["seed"], pos=p["pos"], G=G, M=job.get("M", 0.0), tE=tE, u0=u0, t0=t0, theta_e_true=theta_e,
               piE_true=float(np.hypot(pin, pie)), fs_true=fs, D_L=dl, n_transits=len(t), lam=float(lam[0]),
               sig_theta_known=float(sth[0]), precision=job.get("precision", "edr3"), **extra)
    t0c = t0 + rng.normal(0, 20)
    te_hint = tE * float(np.exp(rng.normal(0, 0.3)))
    try:
        r = al.fit_target(ph, ast, p["ra"], p["dec"], t0c=t0c, te_hint=te_hint, upper_limit=job.get("ul", False), rng=rng)
        rec.update({k: v for k, v in r.items() if not isinstance(v, dict)})
        rec["fs_G_fit"] = r["fs"].get("G", np.nan)
    except Exception as e:  # noqa: BLE001  a failed fit is a recorded failure, not a non-detection
        rec["fit_error"] = f"{type(e).__name__}: {e}"[:200]
    return rec


def jobs_injection(pos, n_per, precision, seed0, quick):
    rng = np.random.default_rng(seed0)
    banks = {}
    out = []
    k = 0
    for M in MASSES:
        for G in GS:
            for _ in range(n_per):
                p = pos[rng.integers(len(pos))]
                key = (p["pos"], M)
                if key not in banks:
                    banks[key] = lens_bank(p, M, n=200 if quick else 400, seed=zlib.crc32(f"{key[0]}|{key[1]}".encode()))
                b = banks[key]
                lens = b[rng.integers(len(b))]
                out.append(dict(kind="inject", seed=seed0 + k, G=G, M=M, pos=p, lens=tuple(lens), precision=precision,
                                ul=(k % 4 == 0)))
                k += 1
    return out


def jobs_null(pos, n_per, seed0):
    rng = np.random.default_rng(seed0)
    out = []
    k = 0
    for kind in ("null_clean", "null_underest", "null_blend", "null_outliers"):
        for G in GS:
            for _ in range(n_per):
                out.append(dict(kind=kind, seed=seed0 + k, G=G, pos=pos[rng.integers(len(pos))], lens=None,
                                ul=(kind == "null_clean")))
                k += 1
    return out


def jobs_ob110462(n, seed0):
    p = dict(pos=OB["pos"], ra=OB["ra"], dec=OB["dec"])
    lens = (OB["tE"], OB["theta_e"], OB["piEN"], OB["piEE"], 1.49)
    scen = [("ob_real", OB["t0"], OB["fs"], OB["G"]), ("ob_real_unblended", OB["t0"], 1.0, OB["G"]),
            ("ob_mid_dr4", 57813.0, OB["fs"], OB["G"]), ("ob_mid_dr4_unblended", 57813.0, 1.0, OB["G"]),
            ("ob_mid_dr4_unblended_G16", 57813.0, 1.0, 16.0)]
    out = []
    k = 0
    for kind, t0, fs, G in scen:
        for _ in range(n):
            out.append(dict(kind=kind, seed=seed0 + k, G=G, M=OB["M"], pos=p, lens=lens, t0=t0, u0=OB["u0"], fs=fs, ul=True))
            k += 1
    return out


def jobs_recheck(pos, seed0, n_inj=10, n_null=30, n_new=40, n_ctrl=150):
    """Referee re-check with the robust fitter: an injection subset, the four nulls, a 100-mas outlier, binary sources
    (target-like: with a photometric event) and control-like stars (flat photometry, fake hints; clean and binary)."""
    out = jobs_injection(pos, n_inj, "edr3", seed0, False)
    out += jobs_null(pos, n_null, seed0 + 100000)
    rng = np.random.default_rng(seed0 + 7)
    k = 0
    for kind, n in (("null_bigoutlier", n_new), ("null_binary", n_new)):
        for G in GS[:4]:
            for _ in range(n):
                out.append(dict(kind=kind, seed=seed0 + 200000 + k, G=G, pos=pos[rng.integers(len(pos))], lens=None))
                k += 1
    # controls: G drawn from the F1 targets' magnitudes
    tg = pd.read_csv(HUNT / "data/ranked_targets.csv")
    gpool = tg.G.dropna().clip(12, 20.5).to_numpy()
    for kind in ("ctrl_clean", "ctrl_binary"):
        for _ in range(n_ctrl):
            out.append(dict(kind=kind, seed=seed0 + 300000 + k, G=float(rng.choice(gpool)), pos=pos[rng.integers(len(pos))],
                            lens=None))
            k += 1
    return out


def summarise(d: pd.DataFrame) -> dict:
    s = {}
    d = d.copy()
    d["det"] = d.dchi2 >= THRESH
    inj = d[d.kind == "inject"]
    for prec, g in inj.groupby("precision"):
        tab = g.pivot_table(index="M", columns="G", values="det", aggfunc="mean")
        s[f"pdet_{prec}"] = {f"{m:g}": {f"{gg:g}": round(float(v), 3) for gg, v in row.items()} for m, row in tab.iterrows()}
        dd = g[g.det & g.M_best.notna()].copy()
        dd["relsig"] = (dd.M_hi68 - dd.M_lo68) / (2 * dd.M_best)
        dd["cover"] = (dd.M_lo68 <= dd.M) & (dd.M <= dd.M_hi68)
        dd["cover95"] = (dd.M_lo95 <= dd.M) & (dd.M <= dd.M_hi95)
        dd["cover_cov68"] = (dd.M_16 <= dd.M) & (dd.M <= dd.M_84)
        tab2 = dd.pivot_table(index="M", columns="G", values="relsig", aggfunc="median")
        s[f"mass_relsig_median_{prec}"] = {f"{m:g}": {f"{gg:g}": round(float(v), 3) for gg, v in row.items() if np.isfinite(v)}
                                          for m, row in tab2.iterrows()}
        s[f"mass_coverage68_profile_{prec}"] = round(float(dd.cover.mean()), 3) if len(dd) else None
        s[f"mass_coverage95_profile_{prec}"] = round(float(dd.cover95.mean()), 3) if len(dd) else None
        s[f"mass_coverage68_covariance_{prec}"] = round(float(dd.cover_cov68.mean()), 3) if len(dd) else None
        s[f"mass_bounded95_{prec}"] = round(float((~dd.M_hi95_open & ~dd.M_lo95_open).mean()), 3) if len(dd) else None
        tab3 = g.assign(meas=g.det & (g.M_hi68 / g.M_best < 1.5) & (g.M_lo68 / g.M_best > 1 / 1.5)).pivot_table(
            index="M", columns="G", values="meas", aggfunc="mean")
        s[f"p_mass_to_50pct_{prec}"] = {f"{m:g}": {f"{gg:g}": round(float(v), 3) for gg, v in row.items()} for m, row in tab3.iterrows()}
        s[f"n_detected_with_mass_{prec}"] = int(len(dd))
        # by tE and u0 (all masses and magnitudes pooled; G <= 18)
        g2 = g[g.G <= 18]
        s[f"pdet_by_tE_{prec}_G<=18"] = {str(k): round(float(v), 3) for k, v in
                                          g2.groupby(pd.cut(g2.tE, [0, 30, 100, 300, 3000]), observed=False).det.mean().items()}
        s[f"pdet_by_abs_u0_{prec}_G<=18"] = {str(k): round(float(v), 3) for k, v in
                                              g2.groupby(pd.cut(g2.u0.abs(), [0, 0.2, 0.5, 1.0]), observed=False).det.mean().items()}
        # the fast ranking approximation against the full fits
        ok = g.lam > 0
        pred = al.detection_probability(g.lam[ok].to_numpy(), THRESH)
        s[f"asimov_check_{prec}"] = dict(pred_mean=round(float(pred.mean()), 3), obs_mean=round(float(g.det[ok].mean()), 3),
                                         by_lam_bin={str(k): dict(pred=round(float(al.detection_probability(np.array([v.lam.median()]), THRESH)[0]), 3),
                                                                  obs=round(float(v.det.mean()), 3), n=len(v))
                                                     for k, v in g[ok].groupby(pd.cut(g.lam[ok], [0, 5, 15, 25, 40, 80, 1e9]), observed=False)})
        dd2 = g[g.det & g.sig_theta_e.notna()]
        pull = (dd2.theta_e - dd2.theta_e_true) / dd2.sig_theta_e
        s[f"theta_e_pull_robust_std_{prec}"] = round(float(1.4826 * (pull - pull.median()).abs().median()), 3) if len(dd2) > 5 else None
    nul = d[d.kind.str.startswith(("null", "ctrl"))]
    sigf = (d.dchi2 >= 25) & (d.err_scale <= 3) & (d.theta_e > 0) & (d.theta_e <= 50)
    s["null"] = {k: dict(n=len(g), fp_rate_25=round(float((g.dchi2 >= 25).mean()), 4),
                         fp_rate_significant=round(float(sigf[g.index].mean()), 4),
                         theta_e_of_significant=[round(float(x), 2) for x in g.theta_e[sigf[g.index]]],
                         median_kept=float(g.n_astro.median()) if "n_astro" in g else None,
                         min_kept_frac=round(float((g.n_astro / (g.n_astro + g.n_astro_clipped)).min()), 3) if "n_astro" in g else None, fp_rate_16=round(float((g.dchi2 >= 16).mean()), 4),
                         fp_rate_9=round(float((g.dchi2 >= 9).mean()), 4), q99_dchi2=round(float(g.dchi2.quantile(0.99)), 2),
                         median_err_scale=round(float(g.err_scale.median()), 3), fit_errors=int(g.get("fit_error", pd.Series(dtype=str)).notna().sum()))
                 for k, g in nul.groupby("kind")}
    s["null_asymptotic"] = dict(p_ge_25=0.5 * 5.7330e-7, p_ge_16=0.5 * 6.334e-5, p_ge_9=0.5 * 2.700e-3)
    ob = d[d.kind.str.startswith("ob_")]
    s["ob110462"] = {k: dict(n=len(g), lam_median=round(float(g.lam.median()), 2), pdet=round(float(g.det.mean()), 3),
                             theta_e_fit_median=round(float(g.theta_e.median()), 3),
                             theta_e_ul95_median=round(float(g.theta_e_ul95.median()), 3) if "theta_e_ul95" in g else None,
                             M_best_median=round(float(g.M_best.median()), 2) if "M_best" in g and g.M_best.notna().any() else None,
                             M_ul95_median=round(float(g.M_ul95.median()), 2) if "M_ul95" in g else None,
                             sig_theta_known_median=round(float(g.sig_theta_known.median()), 3),
                             n_transits=int(g.n_transits.median()))
                     for k, g in ob.groupby("kind")}
    return s


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--parts", default="inject,pessimistic,null,ob")
    ap.add_argument("--tag", default=None)
    a = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    SUM.mkdir(parents=True, exist_ok=True)
    pos = positions()
    print(f"{len(pos)} real positions with GOST transits")
    n_inj, n_pess, n_null, n_ob = (4, 2, 6, 6) if a.quick else (30, 10, 60, 100)
    parts = a.parts.split(",")
    jobs = []
    if "inject" in parts:
        jobs += jobs_injection(pos, n_inj, "edr3", 100000, a.quick)
    if "pessimistic" in parts:
        jobs += jobs_injection(pos, n_pess, "rybicki18", 200000, a.quick)
    if "null" in parts:
        jobs += jobs_null(pos, n_null, 300000)
    if "ob" in parts:
        jobs += jobs_ob110462(n_ob, 400000)
    if "recheck" in parts:
        jobs += jobs_recheck(pos, 500000)
    print(f"{len(jobs)} simulated targets, {a.workers} workers")
    t0 = time.time()
    recs = []
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        for i, r in enumerate(ex.map(run_one, jobs, chunksize=4)):
            recs.append(r)
            if (i + 1) % 200 == 0:
                print(f"  {i + 1}/{len(jobs)} in {time.time() - t0:.0f} s", flush=True)
                pd.DataFrame(recs).to_csv(OUT / ("partial_quick.csv" if a.quick else "partial.csv"), index=False)
    d = pd.DataFrame(recs)
    tag = a.tag or ("quick" if a.quick else "full")
    d.to_csv(OUT / f"acceptance_{tag}.csv", index=False)
    s = summarise(d)
    s["meta"] = dict(n=len(d), seconds=round(time.time() - t0), threshold=THRESH, positions=len(pos), tag=tag,
                     generated_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    (SUM / f"summary_{tag}.json").write_text(json.dumps(s, indent=1, default=str))
    print(json.dumps(s, indent=1, default=str)[:6000])


if __name__ == "__main__":
    main(sys.argv[1:])
