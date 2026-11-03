"""H-0015 s8: per-target simulated fits for forecasts F2-F4 with the robust fitter (referee changes, 2026-11-02).

  OS-0020 (F2)  dark lenses of 0.3, 1, 3, 5, 10 Msun from the Galactic model with its photometric constraints (tE 120-190 d,
                piE 0.25-0.55, the fitter's piE prior 0.40 +- 0.075), and "theta0": its photometric event with no
                deflection (a non-lens or a negligible-mass lens)
  OS-0021 (F3)  the same masses (tE 120-490 d, no piE constraint), plus "nonlens": a smooth, non-microlensing brightening
                (Gaussian in time, 60-200 d wide, x7.7 at peak, 10% weaker in ATLAS c than o, ATLAS peak compressed above x4
                as if partly saturated, 2% correlated noise) with no deflection, fitted with the lens model as on the day
  OS-0016 (F4)  the Galactic model's lens population (a mass function, event-rate weighted, conditioned on tE 47-56 d and
                piE 0.6-1.6)
Each with the target's GOST transits (20% dropped), G, DR3 error scale, Gaia G photometry at the transits and ATLAS's real
nightly cadence and errors from the case file. "pess" variants use errors 1.7x larger.
Output: data/forecast_fits.csv (one row per fit) and a printed summary. Run:
  uv run python -I hunts/H-0015/scripts/s8_forecast_sims.py [--n 30] [--workers 3]
"""
from __future__ import annotations

import argparse
import sys
import time
import zlib
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA, DEAD_TIME_KEEP, load_targets, transits  # noqa: E402
from s5_rank import atlas_cadence, constraints, source_distance, u0_max  # noqa: E402

from oddsky.analysis import astrolens as al  # noqa: E402
from oddsky.analysis import lensing, lenspop  # noqa: E402

TARGETS = {"OS-0020": "6020322385418675200", "OS-0021": "5952322268527918208", "OS-0016": "170329679884731008"}
PESS = 1.7


def base(r, rk):
    return dict(source_id=r.source_id, ra=r.ra, dec=r.dec, G=r.phot_g_mean_mag, k=rk.k, pmra=np.nan_to_num(r.pmra),
                pmdec=np.nan_to_num(r.pmdec), t0=r.t0_mjd, t0_sig=r.t0_sig_d, tE_lo=r.tE_lo, tE_hi=r.tE_hi,
                fs_lo=rk.fs_lo, fs_hi=rk.fs_hi,
                piE_prior=((r.piE_lo + r.piE_hi) / 2, (r.piE_hi - r.piE_lo) / 4) if np.isfinite(r.piE_lo) else None)


def run_fit(job):
    rng = np.random.default_rng(job["seed"])
    b = job["b"]
    t, th, px = transits(b["source_id"], keep=DEAD_TIME_KEEP, rng=rng)
    q = job["q"]
    t0par = float(round(q[0]))
    fs = job["fs"]
    a = job["atlas"]
    if job["hyp"] == "nonlens":
        w = q[1]
        prof = lambda tt: 1 + 6.7 * np.exp(-0.5 * ((tt - q[0]) / w) ** 2)  # noqa: E731
        fG = fs * prof(t) + 1 - fs
        sg = al.sigma_g_transit(b["G"] - 2.5 * np.log10(fG)) * fG / 1.0857
        ph = al.PhotData(t, fG + rng.normal(0, sg), sg, ["G"] * len(t))
        fa = fs * prof(a["t"]) + 1 - fs
        fa = np.where(a["band"] == "ATLAS_c", 1 + 0.9 * (fa - 1), fa)
        fa = np.where(fa > 4, 4 + 0.5 * (fa - 4), fa)
        red = np.convolve(rng.normal(0, 0.02, len(fa) + 10), np.ones(10) / np.sqrt(10), "same")[:len(fa)]
        extra = al.PhotData(a["t"], fa * (1 + red) + rng.normal(0, a["e"] * fa), a["e"] * fa, a["band"])
        ph = al.PhotData(np.r_[ph.t, extra.t], np.r_[ph.f, extra.f], np.r_[ph.e, extra.e], np.r_[ph.group, extra.group])
        sig = al.sigma_al_fov(np.full(len(t), b["G"])) * b["k"] * job["scale"]
        dt = (t - al.J2017_5) / al.YEAR
        wv = b["pmra"] * dt * np.sin(th) + b["pmdec"] * dt * np.cos(th) + 0.2 * px + rng.normal(0, sig)
        ast = al.AstroData(t, th, wv, sig, px)
    else:
        extra = None
        if a is not None:
            dn, de = lensing.sun_offsets(a["t"], b["ra"], b["dec"], t0par)
            tau = (a["t"] - q[0]) / q[1] + q[3] * dn + q[4] * de
            beta = q[2] + (-q[3] * de + q[4] * dn)
            f = fs * lensing.magnification(np.hypot(tau, beta)) + 1 - fs
            extra = al.PhotData(a["t"], f + rng.normal(0, a["e"] * f), a["e"] * f, a["band"])
        ph, ast = al.simulate(t, th, px, b["ra"], b["dec"], b["G"], q, job["theta_e"], fs=fs, pm=(b["pmra"], b["pmdec"]),
                              parallax=0.2, sig_scale=b["k"] * job["scale"], rng=rng, t0par=t0par, phot_extra=extra)
    rec = dict(target=job["target"], source_id=b["source_id"], hyp=job["hyp"], scale=job["scale"], seed=job["seed"],
               M_true=job["M"], kind=job["kind"], theta_e_true=job["theta_e"], tE_true=q[1],
               piE_true=float(np.hypot(q[3], q[4])) if job["hyp"] != "nonlens" else np.nan)
    try:
        te_hint = float(np.sqrt(b["tE_lo"] * b["tE_hi"])) if np.isfinite(b["tE_lo"]) else None
        out = al.fit_target(ph, ast, b["ra"], b["dec"], t0c=b["t0"] + rng.normal(0, min(b["t0_sig"], 30)), te_hint=te_hint,
                            piE_prior=b["piE_prior"], upper_limit=True, rng=rng)
        rec.update({k: v for k, v in out.items() if not isinstance(v, dict)})
    except Exception as e:  # noqa: BLE001
        rec["fit_error"] = f"{type(e).__name__}: {e}"[:200]
    return rec


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args(argv)
    T = load_targets().set_index("source_id", drop=False)
    RK = pd.read_csv(DATA / "ranked_targets.csv", dtype={"source_id": str}).set_index("source_id")
    jobs = []
    for name, sid in TARGETS.items():
        r, rk = T.loc[sid], RK.loc[sid]
        b = base(r, rk)
        atl = atlas_cadence(name)
        atl = {k: np.asarray(v) for k, v in atl.to_dict("list").items()} if atl is not None else None
        te, pie = constraints(r)
        ds, dss, _ = source_distance(r)
        mu_s = (r.pmra, r.pmdec) if np.isfinite(r.pmra) else None
        rng = np.random.default_rng(zlib.crc32(sid.encode()) + 15)
        hyps = []
        if name in ("OS-0020", "OS-0021"):
            hyps = [(M, 1.0) for M in (0.3, 1.0, 3.0, 5.0, 10.0)] + [("theta0" if name == "OS-0020" else "nonlens", 1.0),
                                                                      (1.0, PESS), ("theta0" if name == "OS-0020" else "nonlens", PESS)]
        else:
            hyps = [("pop", 1.0), ("pop", PESS)]
        for hyp, scale in hyps:
            n = a.n if scale == 1.0 else max(a.n * 2 // 3, 10)
            if hyp == "pop":
                mf, kind = lenspop.mass_function_samples(600 * 300, rng=np.random.default_rng(5))
                s = lenspop.sample_lenses(r.l, r.b, r.ra, r.dec, mf, n=600, oversample=300, ds=ds, ds_sig=dss, mu_s=mu_s,
                                          te_range=te, pie_range=pie, rng=np.random.default_rng(6))
                idx = np.random.default_rng(7).choice(len(s["weight"]), size=n, p=s["weight"])
                draws = [(s["tE"][i], s["theta_E"][i], s["piE_N"][i], s["piE_E"][i], mf[i], kind[i]) for i in idx]
            elif hyp in ("theta0", "nonlens"):
                s = lenspop.sample_lenses(r.l, r.b, r.ra, r.dec, 0.5, n=400, ds=ds, ds_sig=dss, mu_s=mu_s, te_range=te,
                                          pie_range=pie, rng=np.random.default_rng(8))
                idx = np.random.default_rng(9).choice(len(s["weight"]), size=n, p=s["weight"])
                draws = [(s["tE"][i], 0.0, s["piE_N"][i], s["piE_E"][i], 0.0, "none") for i in idx]
            else:
                s = lenspop.sample_lenses(r.l, r.b, r.ra, r.dec, float(hyp), n=400, ds=ds, ds_sig=dss, mu_s=mu_s,
                                          te_range=te, pie_range=pie, rng=np.random.default_rng(int(10 * float(hyp))))
                if s["n_eff"] < 5:
                    print(name, hyp, "no admissible Galactic-model lens; skipped")
                    continue
                idx = np.random.default_rng(11).choice(len(s["weight"]), size=n, p=s["weight"])
                draws = [(s["tE"][i], s["theta_E"][i], s["piE_N"][i], s["piE_E"][i], float(hyp), "fixed") for i in idx]
            for j, (tE, th, pn, pe, M, kd) in enumerate(draws):
                if hyp == "nonlens":
                    q = np.array([rng.normal(r.t0_mjd, r.t0_sig_d), rng.uniform(60, 200), 0.0, 0.0, 0.0])
                else:
                    q = np.array([rng.normal(r.t0_mjd, r.t0_sig_d), tE, rng.uniform(0, u0_max(r.amp_obs)) * rng.choice([-1, 1]),
                                  pn, pe])
                jobs.append(dict(target=name, b=b, hyp=str(hyp), scale=scale, q=q, theta_e=float(th), M=float(M), kind=str(kd),
                                 fs=float(rng.uniform(rk.fs_lo, rk.fs_hi)), atlas=atl,
                                 seed=int(zlib.crc32(f"{sid}|{hyp}|{scale}|{j}".encode()))))
    print(f"{len(jobs)} fits")
    t1 = time.time()
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        recs = list(ex.map(run_fit, jobs, chunksize=2))
    F = pd.DataFrame(recs)
    F.to_csv(DATA / "forecast_fits.csv", index=False, float_format="%.5g")
    F["sig"] = (F.dchi2 >= 25) & (F.err_scale <= 3) & (F.theta_e > 0) & (F.theta_e <= 50)
    print(f"{time.time() - t1:.0f} s")
    print(F.groupby(["target", "hyp", "scale"]).agg(n=("sig", "size"), p_sig=("sig", "mean"),
                                                     ul_finite=("M_ul95", lambda x: np.isfinite(x).mean()),
                                                     ul_lt3=("M_ul95", lambda x: (x < 3).mean()),
                                                     ul_lt5=("M_ul95", lambda x: (x < 5).mean()),
                                                     ul_med=("M_ul95", "median"), errors=("fit_error", lambda x: x.notna().sum())
                                                     if "fit_error" in F else ("sig", lambda x: 0)).round(3).to_string())


if __name__ == "__main__":
    main(sys.argv[1:])
