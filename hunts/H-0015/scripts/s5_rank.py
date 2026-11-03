"""H-0015 s5: rank Oddsky's lens targets by how well Gaia DR4's epoch astrometry can measure or bound the lens mass.

For each target (data/targets_input.csv + Gaia DR3 inputs + its GOST transits over DR4's span):

  1. AL error scale k: Gaia DR3's published parallax_error against the error our precision model predicts for the same
     source from its DR3-span transits (five-parameter Fisher). k > 1 means the source is measured worse than the curve
     (crowding, colour, a wide companion, or a real astrometric disturbance) and is applied to DR4's per-transit errors.
     Clipped to [1, 5]; two-parameter DR3 sources (no parallax) get k = 2.
  2. Expected signal if the lens were a dark 1, 5 or 10 Msun object: lens distance and motion from the Galactic model
     (lenspop) for that sight line, conditioned on the target's photometric tE (and piE where measured), the source's
     DR3 proper motion and a source distance (bulge 8 +- 1 kpc; otherwise the DR3 parallax if >= 5 sigma, else GSP-Phot,
     else 4 +- 1.5 kpc); t0 +- its uncertainty; |u0| up to what the observed peak allows; astrometric source fraction
     fs ~ U(0.5, 1) (U(0.3, 0.9) with a neighbour within 1" or a multi-peak IPD fraction > 10%). The noise-free
     Delta chi^2 of the deflection (blend-offset terms included; trajectory known) at the target's transits with
     sigma_AL(G) x k, times 0.8 for dead time, gives P(Delta chi^2 >= 25) through the noncentral chi^2. The acceptance
     test (s4) checks this approximation against full fits.
  3. The same with a lens mass function (lenspop.mass_function_samples, event-rate weighted, conditioned on tE/piE):
     P(black hole | lens), P(detectable deflection | lens), P(black hole and detectable).
  4. Rank by P(lens) x max(P_det(population), P_det(5 Msun)): the probability that the event is a lens and that DR4 can
     measure its mass (detect the deflection of the lens the Galactic model puts there) or measure/exclude a 5 Msun dark
     lens (P(lens): the referee's or the sealed ensemble's; 0.05 where neither gives one). Known binary lenses are listed
     but not ranked (the point-lens astrometric model does not apply). Every P_det is also given for errors 1.7x worse.
     For events inside Gaia DR3's span, also the DR3 RUWE each mass would have caused (a pre-DR4 hint; approximate:
     RUWE^2 ~ 1 + <r^2>/sigma_CCD^2, r the deflection left after a five-parameter fit to the DR3-span transits).
  5. Full simulated fits (astrolens.fit_target) for the top targets and the named cases, with each target's own
     constraints (and ATLAS's real cadence and errors where a case has ATLAS data): P(detect), P(M > 3 Msun at >= 3 sigma),
     mass precision, and the 95% mass upper limit if there is no deflection.

Outputs: data/ranked_targets.csv, data/rank_fits.csv, data/rank_summary.json; big intermediates in ~/oddsky-runs/h0015/rank/.
Run: uv run python -I hunts/H-0015/scripts/s5_rank.py [--quick] [--workers 3] [--top 12]
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
from common import (  # noqa: E402
    DATA,
    DEAD_TIME_KEEP,
    DR3_END,
    DR4_END,
    DR4_START,
    ROOT,
    RUNS,
    load_targets,
    transits,
)

from oddsky.analysis import astrolens as al  # noqa: E402
from oddsky.analysis import lensing, lenspop  # noqa: E402

THRESH = 25.0
MASSES = (1.0, 5.0, 10.0)
PESSIMISTIC = 1.7      # per-transit errors 1.7x the nominal curve (about Rybicki et al. 2018's pre-launch errors at G 15-18)
BINARY_LENSES = {"2032454944878107008": "Gaia16aye: a binary lens (caustic crossings; Wyrzykowski et al. 2020 measured its "
                                          "masses); the point-lens astrometric model does not apply"}
OUT = RUNS / "rank"


def error_scale(r, t, th, px):
    """Gaia DR3 parallax_error / the parallax error our precision model predicts from the DR3-span transits."""
    if not np.isfinite(r.parallax_error):
        return 2.0, np.nan
    m = t <= DR3_END
    s = al.sigma_al_fov(np.full(m.sum(), r.phot_g_mean_mag))
    dt = (t[m] - 57388.5) / al.YEAR          # DR3 reference epoch J2016.0
    X = np.column_stack([np.sin(th[m]), np.cos(th[m]), dt * np.sin(th[m]), dt * np.cos(th[m]), px[m]]) / s[:, None]
    try:
        cov = np.linalg.inv(X.T @ X)
    except np.linalg.LinAlgError:
        return 2.0, np.nan
    pred = np.sqrt(cov[4, 4]) / np.sqrt(DEAD_TIME_KEEP)
    # never better than the curve: DR3's formal errors run ~15% below our model (median over targets) but are themselves
    # underestimated by ~10-30% (El-Badry et al. 2021), so the floor is 1
    return float(np.clip(r.parallax_error / pred, 1.0, 5.0)), float(pred)


def source_distance(r):
    lw = ((r.l + 180) % 360) - 180
    if abs(lw) < 12 and abs(r.b) < 8:
        return 8.0, 1.0, "bulge (8 +- 1 kpc)"
    if np.isfinite(r.parallax) and np.isfinite(r.parallax_error) and r.parallax / r.parallax_error >= 5:
        d = 1.0 / r.parallax
        return d, max(d * r.parallax_error / r.parallax, 0.05), "DR3 parallax"
    if np.isfinite(r.distance_gspphot):
        return r.distance_gspphot / 1000.0, 0.3 * r.distance_gspphot / 1000.0, "GSP-Phot"
    return 4.0, 1.5, "disc default (4 +- 1.5 kpc)"


def fs_prior(r):
    crowded = (getattr(r, "nb_flux_1as", 0) > 0.2) or (np.isfinite(r.ipd_frac_multi_peak) and r.ipd_frac_multi_peak > 10)
    return ((0.3, 0.9) if crowded else (0.5, 1.0)), bool(crowded)


def u0_max(amp):
    if not np.isfinite(amp) or amp <= 1.05:
        return 1.5
    # largest u0 whose unblended peak still reaches the observed ratio
    u = np.geomspace(1e-3, 3, 3000)
    a = lensing.magnification(u)
    return float(np.clip(u[np.argmin(np.abs(a - amp))], 0.03, 1.5))


def constraints(r):
    te = (r.tE_lo, r.tE_hi) if np.isfinite(r.tE_lo) and np.isfinite(r.tE_hi) else None
    pie = (r.piE_lo, r.piE_hi) if np.isfinite(r.piE_lo) and np.isfinite(r.piE_hi) else None
    return te, pie


def lens_draws(r, mass, n, seed, te, pie, mu_s, ds, dss):
    s = lenspop.sample_lenses(r.l, r.b, r.ra, r.dec, mass, n=n, ds=ds, ds_sig=dss, mu_s=mu_s,
                              mu_s_sig=(max(r.pmra_error, 0.05), max(r.pmdec_error, 0.05)) if mu_s else (0.3, 0.3),
                              te_range=te, pie_range=pie, rng=np.random.default_rng(seed))
    if s["n_eff"] < 20:
        return None, s
    return lenspop.resample(s, n, rng=np.random.default_rng(seed + 7)), s


def trajectories(rng, d, r, n):
    t0 = rng.normal(r.t0_mjd, r.t0_sig_d, n)
    um = u0_max(r.amp_obs)
    u0 = rng.uniform(0.0, um, n) * rng.choice([-1, 1], n)
    return np.column_stack([t0, d["tE"], u0, d["piE_N"], d["piE_E"]])


def ruwe_dr3(r, t, th, px, q, theta_e, fs):
    """Approximate Gaia DR3 RUWE caused by the deflection: residual after a 5-parameter fit over DR3-span transits."""
    m = t <= DR3_END
    if m.sum() < 8:
        return np.full(len(q), np.nan)
    tt, ss, cc = t[m], np.sin(th[m]), np.cos(th[m])
    dt = (tt - 57388.5) / al.YEAR
    B = np.column_stack([ss, cc, dt * ss, dt * cc, px[m]])
    Q, _ = np.linalg.qr(B)
    dn_s, de_s = lensing.sun_offsets(tt, r.ra, r.dec, float(round(np.median(q[:, 0]))))
    tau = (tt[None, :] - q[:, :1]) / q[:, 1:2] + q[:, 3:4] * dn_s + q[:, 4:5] * de_s
    beta = q[:, 2:3] + (-q[:, 3:4] * de_s + q[:, 4:5] * dn_s)
    un, ue = al.trajectory(tau, beta, q[:, 3:4], q[:, 4:5])
    dn, de = al.centroid_shift(un, ue, fs[:, None])
    S = (de * ss + dn * cc) * theta_e[:, None]
    S = S - (S @ Q) @ Q.T
    sig_ccd = float(np.exp(np.interp(r.phot_g_mean_mag, al._G_CCD, np.log(al._S_CCD))))
    return np.sqrt(1 + np.mean(S**2, axis=1) / sig_ccd**2)


def asimov(r, t, th, px, k, fsr, d, rng):
    n = len(d["tE"])
    q = trajectories(rng, d, r, n)
    fs = rng.uniform(*fsr, n)
    sig = al.sigma_al_fov(np.full(len(t), r.phot_g_mean_mag)) * k
    lam, sth = al.expected_dchi2(t, th, sig, px, r.ra, r.dec, q, d["theta_E"], fs, t0par=float(round(np.median(q[:, 0]))))
    lam = lam * DEAD_TIME_KEEP
    peak = d["theta_E"] / np.sqrt(8) * fs        # rough: the dilution at the shift's peak (u = sqrt 2, A = 1.34) ~ fs
    ruwe = ruwe_dr3(r, t, th, px, q, d["theta_E"], fs) if r.t0_mjd < DR3_END + 100 else np.full(n, np.nan)
    return lam, peak, sig, ruwe


def atlas_cadence(case: str):
    p = ROOT / f"cases/{case}/data/atlas.parquet"
    if not case or not p.exists():
        return None
    a = pd.read_parquet(p)
    a = a[(a.flag.fillna("") == "") & (a.dflux_ujy > 0) & (a.flux_ujy > 0)]
    a["night"] = np.floor(a.t_mjd)
    g = a.groupby(["band", "night"]).agg(t=("t_mjd", "mean"), rel=("dflux_ujy", lambda x: np.sqrt(np.sum(x**2)) / len(x)),
                                          f=("flux_ujy", "median")).reset_index()
    base = g.groupby("band").f.median()
    g["e"] = g.rel / g.band.map(base)
    g = g[(g.t >= DR4_START - 400) & (g.t <= DR4_END + 400) & (g.e < 0.2)]
    return g[["t", "e", "band"]].reset_index(drop=True)


def sim_fit(job):
    """Simulate one realisation for one target and hypothesis and fit it."""
    rng = np.random.default_rng(job["seed"])
    r = job["r"]
    t, th, px = transits(r["source_id"], keep=DEAD_TIME_KEEP, rng=rng)
    q = job["q"]
    t0par = float(round(q[0]))
    extra = None
    if job.get("atlas") is not None:
        a = job["atlas"]
        dn, de = lensing.sun_offsets(a["t"], r["ra"], r["dec"], t0par)
        tau = (a["t"] - q[0]) / q[1] + q[3] * dn + q[4] * de
        beta = q[2] + (-q[3] * de + q[4] * dn)
        fsa = job["fs"]
        f = fsa * lensing.magnification(np.hypot(tau, beta)) + 1 - fsa
        extra = al.PhotData(a["t"], f + rng.normal(0, a["e"] * f), a["e"] * f, a["band"])
    ph, ast = al.simulate(t, th, px, r["ra"], r["dec"], r["G"], q, job["theta_e"], fs=job["fs"], pm=(r["pmra"], r["pmdec"]),
                          parallax=0.2, sig_scale=r["k"], rng=rng, t0par=t0par, phot_extra=extra)
    rec = dict(source_id=r["source_id"], hyp=job["hyp"], seed=job["seed"], M_true=job["M"], kind=job.get("kind", ""),
               theta_e_true=job["theta_e"], tE_true=q[1], piE_true=float(np.hypot(q[3], q[4])), fs_true=job["fs"])
    try:
        out = al.fit_target(ph, ast, r["ra"], r["dec"], t0c=r["t0"] + rng.normal(0, min(r["t0_sig"], 30)),
                            te_hint=float(np.sqrt(r["tE_lo"] * r["tE_hi"])) if np.isfinite(r["tE_lo"]) else None,
                            piE_prior=r["piE_prior"], upper_limit=True, rng=rng)
        rec.update({kk: v for kk, v in out.items() if not isinstance(v, dict)})
    except Exception as e:  # noqa: BLE001
        rec["fit_error"] = f"{type(e).__name__}: {e}"[:200]
    return rec


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--top", type=int, default=12)
    ap.add_argument("--nfit", type=int, default=40)
    ap.add_argument("--no-fits", action="store_true")
    a = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    T = load_targets()
    nA = 150 if a.quick else 600
    rows, banks = [], {}
    t_start = time.time()
    for r in T.itertuples():
        seed = zlib.crc32(r.source_id.encode())
        rng = np.random.default_rng(seed)
        t, th, px = transits(r.source_id)
        rec = dict(source_id=r.source_id, name=r.name, case=r.case if isinstance(r.case, str) else "", set=r.set,
                   p_lens=r.p_lens, G=r.phot_g_mean_mag, bp_rp=r.bp_rp, l=r.l, b=r.b, ra=r.ra, dec=r.dec, ruwe=r.ruwe,
                   aen=r.astrometric_excess_noise, aen_sig=r.astrometric_excess_noise_sig, params=r.astrometric_params_solved,
                   pmra=r.pmra, pmdec=r.pmdec, parallax=r.parallax, parallax_error=r.parallax_error,
                   nb_flux_1as=getattr(r, "nb_flux_1as", 0.0), ipd_multi=r.ipd_frac_multi_peak, t0=r.t0_mjd, t0_sig=r.t0_sig_d,
                   tE_lo=r.tE_lo, tE_hi=r.tE_hi, piE_lo=r.piE_lo, piE_hi=r.piE_hi, amp_obs=r.amp_obs, tE_source=r.tE_source,
                   n_transits_dr4=len(t), n_transits_event=int(np.sum(np.abs(t - r.t0_mjd) < max(2 * np.nan_to_num(r.tE_hi, nan=100), 60))))
        if len(t) < 10 or not np.isfinite(r.phot_g_mean_mag):
            rec["status"] = "no transits or no G"
            rows.append(rec)
            continue
        k, pred = error_scale(r, t, th, px)
        ds, dss, dsrc = source_distance(r)
        fsr, crowded = fs_prior(r)
        te, pie = constraints(r)
        mu_s = (r.pmra, r.pmdec) if np.isfinite(r.pmra) else None
        rec.update(k=k, plx_err_pred=pred, ds=ds, ds_sig=dss, ds_source=dsrc, fs_lo=fsr[0], fs_hi=fsr[1], crowded=crowded,
                   sig_al_fov=float(al.sigma_al_fov(r.phot_g_mean_mag) * k))
        for M in MASSES:
            d, s = lens_draws(r, M, nA, seed + int(M * 10), te, pie, mu_s, ds, dss)
            if d is None:
                rec.update({f"pdet_{M:g}": 0.0, f"neff_{M:g}": s["n_eff"], f"note_{M:g}": "no Galactic-model lens of this mass fits tE/piE"})
                continue
            lam, peak, sig, ruwe = asimov(r, t, th, px, k, fsr, d, rng)
            pdet = al.detection_probability(lam, THRESH)
            rec[f"pdet_{M:g}_pess"] = float(al.detection_probability(lam / PESSIMISTIC**2, THRESH).mean())
            rec.update({f"pdet_{M:g}": float(pdet.mean()),
                        f"ruwe_dr3_pred_med_{M:g}": float(np.nanmedian(ruwe)) if np.isfinite(ruwe).any() else np.nan, f"lam_med_{M:g}": float(np.median(lam)),
                        f"thetaE_med_{M:g}": float(np.median(d["theta_E"])), f"thetaE_16_{M:g}": float(np.percentile(d["theta_E"], 16)),
                        f"thetaE_84_{M:g}": float(np.percentile(d["theta_E"], 84)), f"peakshift_med_{M:g}": float(np.median(peak)),
                        f"DL_med_{M:g}": float(np.median(d["D_L"])), f"piE_med_{M:g}": float(np.median(np.hypot(d["piE_N"], d["piE_E"]))),
                        f"tE_med_{M:g}": float(np.median(d["tE"])), f"neff_{M:g}": s["n_eff"], f"rate_{M:g}": s["rate"]})
            banks[(r.source_id, M)] = d
        # lens mass function, event-rate weighted and conditioned on the photometry
        over = 100 if pie is None else 300         # large draws: P(BH | lens) rests on few heavy samples
        mf, kind = lenspop.mass_function_samples(nA * over, rng=np.random.default_rng(seed + 99))
        s = lenspop.sample_lenses(r.l, r.b, r.ra, r.dec, mf, n=nA, oversample=over, ds=ds, ds_sig=dss, mu_s=mu_s, te_range=te,
                                  pie_range=pie, rng=np.random.default_rng(seed + 98))
        rec["pop_neff"] = s["n_eff"]
        if s["n_eff"] >= 20:
            w = s["weight"]
            rec["p_bh_given_lens"] = float(w[kind == "BH"].sum())
            rec["p_remnant_given_lens"] = float(w[kind != "star"].sum())
            rec["M_med_given_lens"] = float(np.average(mf, weights=w)) if w.sum() > 0 else np.nan
            d = lenspop.resample(s, nA, rng=np.random.default_rng(seed + 97))
            ki = kind[np.random.default_rng(seed + 97).choice(len(w), size=nA, p=w)]
            lam, peak, sig, _ = asimov(r, t, th, px, k, fsr, d, rng)
            pdet = al.detection_probability(lam, THRESH)
            rec["pdet_pop"] = float(pdet.mean())
            pp = al.detection_probability(lam / PESSIMISTIC**2, THRESH)
            rec["pdet_pop_pess"] = float(pp.mean())
            rec["pdet_pop_bh_pess"] = float(np.mean(pp * (ki == "BH")))
            rec["thetaE_med_pop"] = float(np.median(d["theta_E"]))
            rec["M_med_pop"] = float(np.median(d["mass"]))
            rec["pdet_pop_bh"] = float(np.mean(pdet * (ki == "BH")))
            rec["pdet_pop_m3"] = float(np.mean(pdet * (d["mass"] > 3)))
            banks[(r.source_id, "pop")] = (d, ki)
        else:
            rec["pop_note"] = f"n_eff {s['n_eff']:.0f}"
        rec["status"] = "ok"
        rows.append(rec)
    R = pd.DataFrame(rows)
    R["p_lens_note"] = np.where(R.p_lens.isna(), "no P(lens) in the source list; 0.05 assumed", "")
    R["p_lens"] = R.p_lens.fillna(0.05)
    # P(lens) x P(DR4 measures or bounds the mass): the larger of P(detect the deflection of the lens the Galaxy would put
    # there) and P(detect a 5 Msun dark lens, i.e. measure or exclude one)
    R["p_measure_or_bound"] = np.maximum(R.pdet_pop.fillna(0), R.get("pdet_5", pd.Series(0, index=R.index)).fillna(0))
    R["score"] = R.p_lens * R.p_measure_or_bound
    R["exclude_note"] = R.source_id.map(BINARY_LENSES).fillna("")
    # what each target is for (referee): catalogued OGLE/KMTNet events are known lenses (positive controls, not Oddsky
    # discoveries); most strong NEOWISE events are unlikely lenses (effectively null controls)
    R["role"] = R.set.map({"case": "Oddsky lens case", "h0010": "Oddsky lens candidate (H-0010)",
                           "h0010_known": "known OGLE/KMTNet lens (control)",
                           "strong": "NEOWISE brightening (mostly a null control)",
                           "case_after_span": "Oddsky lens case, event after DR4 (pre-event tail)"}).fillna("")
    R.loc[R.exclude_note != "", "score"] = -1.0
    R["exp_det_pop"] = R.p_lens * R.pdet_pop.fillna(0) * (R.exclude_note == "")
    R["exp_det_bh"] = R.p_lens * R.pdet_pop_bh.fillna(0) * (R.exclude_note == "")
    R["exp_det_pop_pess"] = R.p_lens * R.pdet_pop_pess.fillna(0) * (R.exclude_note == "")
    R = R.sort_values(["score", "exp_det_pop"], ascending=False).reset_index(drop=True)
    R.insert(0, "rank", np.arange(1, len(R) + 1))
    print(f"Asimov ranking done in {time.time() - t_start:.0f} s")
    R.to_csv(DATA / "ranked_targets.csv", index=False, float_format="%.5g")

    summ = dict(n_targets=len(R), n_ok=int((R.status == "ok").sum()),
                expected_detections_pop=float(R.exp_det_pop.sum()), expected_bh_detections=float(R.exp_det_bh.sum()),
                score_ge_0p5=int((R.score >= 0.5).sum()), pdet5_ge_0p5=int((R.get("pdet_5", 0) >= 0.5).sum()), pdet10_ge_0p5=int((R.get("pdet_10", 0) >= 0.5).sum()),
                pdet1_ge_0p5=int((R.get("pdet_1", 0) >= 0.5).sum()))
    if a.no_fits:
        (DATA / "rank_summary.json").write_text(json.dumps(summ, indent=1))
        print(json.dumps(summ, indent=1))
        return
    # ---- full simulated fits for the top targets and the named cases
    named = {"OS-0016", "OS-0020", "OS-0021", "OS-0026", "OS-0027", "OS-0029"}
    sel = R[(R.status == "ok") & (R.exclude_note == "") & ((R["rank"] <= a.top) | R.case.isin(named))]
    jobs = []
    nfit = 8 if a.quick else a.nfit
    for r in sel.itertuples():
        base = dict(source_id=r.source_id, ra=r.ra, dec=r.dec, G=r.G, k=r.k, pmra=np.nan_to_num(r.pmra), pmdec=np.nan_to_num(r.pmdec),
                    t0=r.t0, t0_sig=r.t0_sig, tE_lo=r.tE_lo, tE_hi=r.tE_hi,
                    piE_prior=((r.piE_lo + r.piE_hi) / 2, (r.piE_hi - r.piE_lo) / 4) if np.isfinite(r.piE_lo) else None)
        atl = atlas_cadence(r.case) if r.case in ("OS-0016", "OS-0020", "OS-0021") else None
        atl = atl.to_dict("list") if atl is not None else None
        if atl is not None:
            atl = {kk: np.asarray(v) for kk, v in atl.items()}
        rng = np.random.default_rng(zlib.crc32(r.source_id.encode()) + 5)
        hyps = [(M, banks.get((r.source_id, M))) for M in MASSES] + [("pop", banks.get((r.source_id, "pop")))]
        for M, bank in hyps:
            if bank is None:
                continue
            if M == "pop":
                d, ki = bank
            else:
                d, ki = bank, None
            idx = rng.integers(len(d["tE"]), size=nfit)
            for j, i in enumerate(idx):
                q = np.array([rng.normal(r.t0, r.t0_sig), d["tE"][i], rng.uniform(0, u0_max(r.amp_obs)) * rng.choice([-1, 1]),
                              d["piE_N"][i], d["piE_E"][i]])
                jobs.append(dict(r=base, hyp=str(M), M=float(d["mass"][i]), kind="" if ki is None else str(ki[i]), q=q,
                                 theta_e=float(d["theta_E"][i]), fs=float(rng.uniform(r.fs_lo, r.fs_hi)), atlas=atl,
                                 seed=int(zlib.crc32(f"{r.source_id}|{M}|{j}".encode()))))
    print(f"{len(jobs)} per-target simulated fits for {len(sel)} targets")
    t1 = time.time()
    recs = []
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        for i, rec in enumerate(ex.map(sim_fit, jobs, chunksize=2)):
            recs.append(rec)
            if (i + 1) % 100 == 0:
                print(f"  {i + 1}/{len(jobs)} {time.time() - t1:.0f} s", flush=True)
    F = pd.DataFrame(recs)
    F.to_csv(OUT / ("rank_fits_quick.csv" if a.quick else "rank_fits.csv"), index=False)
    F["det"] = F.dchi2 >= THRESH
    F["m_gt3_3sig"] = F.det & (F.M_gt3_sigma >= 3)
    agg = F.groupby(["source_id", "hyp"]).agg(n=("det", "size"), p_det=("det", "mean"), p_m_gt3_3sig=("m_gt3_3sig", "mean"),
                                              M_ul95_med=("M_ul95", "median"),
                                              theta_ul95_med=("theta_e_ul95", "median"),
                                              relsig_M=("M_best", lambda x: np.nan)).reset_index()
    rel = F[F.det].assign(rs=lambda x: (x.M_hi68 - x.M_lo68) / (2 * x.M_best)).groupby(["source_id", "hyp"]).rs.median()
    agg["relsig_M_det_median"] = [rel.get((s, h), np.nan) for s, h in zip(agg.source_id, agg.hyp, strict=True)]
    agg = agg.drop(columns=["relsig_M"])
    agg.to_csv(DATA / "rank_fits.csv", index=False, float_format="%.4g")
    summ["fit_targets"] = len(sel)
    summ["fit_seconds"] = round(time.time() - t1)
    (DATA / "rank_summary.json").write_text(json.dumps(summ, indent=1))
    print(json.dumps(summ, indent=1))
    print(agg.to_string())


if __name__ == "__main__":
    main(sys.argv[1:])
