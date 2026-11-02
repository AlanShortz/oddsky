"""H-0013 injection-recovery: synthetic periodic dust-formation outbursts added to REAL H-0012 light curves.

    uv run python hunts/H-0013/scripts/inject.py [--per-galaxy 25] [--n-shuffle 100] [--seed 3]

Hosts: up to --per-galaxy scanned sources per galaxy (so M31's 20,000 light curves do not dominate), drawn at
random from every class (quiet sources, LPVs, irregular variables, transients: the real confusion), excluding
anything the scan itself calls recurrent. Each host gets one outburst train:

- P log-uniform in 2-12 yr, phase uniform, rise tau_r U(0.1, 0.5) yr, decline tau_d U(0.3, min(1.5, P/2.5)) yr;
- W2 amplitude: peak nu L_nu log-uniform in 10^3.5 - 10^5.5 L_sun at the host galaxy's distance (OS-0031's humps
  are ~5-7 x 10^4 L_sun per band at 3.2 Mpc; WR 140 at its 2001 maximum is ~10x fainter);
- colour of the outburst light W1-W2 U(0.6, 1.6) Vega (hot to ~600 K dust).

Recovery = the full light-curve decision (oddsky.imaging.recurrence.light_verdict == 'recurrent', F >= F_MIN) AND
p_shuffle <= P_SHUFFLE_MAX (n-shuffle within-season shuffles), with the period recovered within 10% (reported
separately; harmonics count as recovered-wrong-period). The H-0012 candidate stage is emulated from the injected
signal alone (>= 2 epoch-band images at >= 5 sigma above the season median, from both seasons), because the hosts are
already candidates; completeness is reported with and without it.

False positives: a separate random sample of real light curves from EVERY class (recurrent ones included, up to
--per-galaxy per galaxy) is turned into surrogates with the time structure destroyed: (a) one within-season shuffle
(white null) and (b) one Fourier phase randomisation (red-noise null: same power spectrum, so quasi-periodic AGB/AGN-
like wandering survives). Each surrogate goes through the full decision; the fraction that passes is the false-
positive rate per source for that null. The real population's pass rate is in the rank output.

Writes ~/oddsky-runs/h0013/inject.parquet and hunts/H-0013/work/injection_summary.json, figures/completeness.png.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import h0013  # noqa: E402

from oddsky.imaging import F0_JY  # noqa: E402
from oddsky.imaging import recurrence as rc  # noqa: E402

log = logging.getLogger("h0013.inject")
LAMBDA_UM = {1: 3.368, 2: 4.618}
C_UM_HZ, LSUN_W, MPC_M = 2.99792458e14, 3.828e26, 3.0856775814913673e22


def lsun_to_nmgy(L, band, dist_mpc):
    nu = C_UM_HZ / LAMBDA_UM[band]
    ujy = L * LSUN_W / (4 * np.pi * (dist_mpc * MPC_M) ** 2 * nu) * 1e32
    return ujy / (F0_JY[band] * 1e-3)


def candidate_stage(lc: rc.LightCurve, sig: np.ndarray) -> bool:
    """H-0012's single-epoch rule from the injected signal alone: >= 2 epoch-band detections at >= 5 sigma
    against the season median, from both visit seasons."""
    seasons = set()
    n = 0
    for b in range(2):
        ok = lc.ok[b]
        for ss in (0, 1):
            m = ok & (lc.season == ss)
            if m.sum() < 2:
                continue
            z = (sig[b, m] - np.median(sig[b, m])) / lc.e[b, m]
            k = int((z >= 5).sum())
            if k:
                n += k
                seasons.add(ss)
    return n >= 2 and len(seasons) == 2


def decide(lc: rc.LightCurve, n_shuffle: int, seed: int) -> dict:
    a = rc.analyse(lc)
    v, why = rc.light_verdict(a)
    out = dict(P_rec=a["P_yr"], F=a["F"], n_cyc=a["n_cycles_det"], S=a["S"], R=a["R"], light=v, why=",".join(why))
    out["p_shuffle"] = np.nan
    if v == "recurrent":
        null = rc.shuffle_null(lc, n_shuffle, seed=seed)
        out["p_shuffle"] = rc.p_value(null, a["F"])
    out["recovered"] = bool(v == "recurrent" and np.nan_to_num(out["p_shuffle"], nan=1) <= rc.P_SHUFFLE_MAX)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--per-galaxy", type=int, default=25)
    ap.add_argument("--n-shuffle", type=int, default=100)
    ap.add_argument("--seed", type=int, default=3)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    rng = np.random.default_rng(a.seed)
    scan = pd.read_parquet(h0013.OUT / "scan.parquet")
    pool = scan[(scan.light_verdict != "recurrent") & np.isfinite(scan.dist_mpc)]
    hosts = pool.groupby("galaxy", group_keys=False).apply(
        lambda g: g.sample(min(len(g), a.per_galaxy), random_state=int(rng.integers(1 << 31))))
    log.info("%d hosts from %d galaxies", len(hosts), hosts.galaxy.nunique())
    m = h0013.load_merged()
    m = m[m.uid.isin(set(hosts.uid))]
    rows = []
    t0 = time.time()
    for i, (r, L) in enumerate(h0013.iter_lightcurves(m)):
        d = float(r.dist_mpc)
        P = float(np.exp(rng.uniform(np.log(2), np.log(12))))
        ph = float(rng.uniform(0, P))
        tr = float(rng.uniform(0.1, 0.5))
        td = float(rng.uniform(0.3, min(1.5, P / rc.TAU_D_MAX_FRAC)))
        logL = float(rng.uniform(3.5, 5.5))
        col = float(rng.uniform(0.6, 1.6))
        a2 = lsun_to_nmgy(10**logL, 2, d)
        # W1 amplitude from the Vega colour of the outburst light (both in Vega nanomaggies)
        a1 = a2 * 10 ** (-0.4 * col)
        t0_inj = L.t.min() + ph
        h = rc.periodic_template(L.t, P, t0_inj, tr, td)
        # peak of the profile train (>1 for overlapping declines); amplitudes refer to a single outburst's peak
        sig = np.array([a1, a2])[:, None] * h[None, :]
        inj = rc.LightCurve(L.t, L.season, L.y + sig, L.e, L.epoch)
        # how many outburst peaks fall inside data (within 0.5 yr of an epoch)
        peaks = t0_inj + P * np.arange(-5, 10)
        n_peaks = int(sum(np.min(np.abs(L.t - p)) < 0.5 for p in peaks))
        rec = decide(inj, a.n_shuffle, seed=i)
        rows.append(dict(uid=r.uid, galaxy=r.galaxy, dist_mpc=d, host_cls=r.cls, host_var_sig=r.var_sig, P=P, t0=t0_inj,
                         tau_r=tr, tau_d=td, logL_w2=logL, colour=col, amp_w2=a2, amp_w1=a1,
                         snr_w2=a2 / float(np.nanmedian(L.e[1])), n_peaks_in_data=n_peaks,
                         cand_stage=candidate_stage(L, sig), **rec,
                         P_ok=bool(abs(rec["P_rec"] / P - 1) < 0.1)))
        if (i + 1) % 200 == 0:
            log.info("%d injections, %.0f s", i + 1, time.time() - t0)
    df = pd.DataFrame(rows)
    df.to_parquet(h0013.OUT / "inject.parquet")
    # false positives from surrogates of real light curves of every class
    fp_hosts = scan[np.isfinite(scan.dist_mpc)].groupby("galaxy", group_keys=False).apply(
        lambda g: g.sample(min(len(g), a.per_galaxy), random_state=int(rng.integers(1 << 31))))
    lv = dict(zip(scan.uid, scan.light_verdict, strict=False))
    m2 = h0013.load_merged()
    m2 = m2[m2.uid.isin(set(fp_hosts.uid))]
    fps = []
    for i, (r, L) in enumerate(h0013.iter_lightcurves(m2)):
        perm = np.arange(L.t.size)
        for ss in (0, 1):
            mm = np.nonzero(L.season == ss)[0]
            perm[mm] = rng.permutation(mm)
        Ls = rc.LightCurve(L.t, L.season, L.y[:, perm], L.e[:, perm], L.epoch)
        Lp = phase_surrogate(L, rng)
        ds, dp = decide(Ls, a.n_shuffle, seed=60_000 + i), decide(Lp, a.n_shuffle, seed=70_000 + i)
        fps.append(dict(uid=r.uid, galaxy=r.galaxy, cls=r.cls, real_light=lv.get(r.uid, ""),
                        fp_shuffle=ds["recovered"], fp_phase=dp["recovered"], F_shuffle=ds["F"], F_phase=dp["F"],
                        why_shuffle=ds["why"], why_phase=dp["why"]))
        if (i + 1) % 200 == 0:
            log.info("%d surrogates, %.0f s", i + 1, time.time() - t0)
    fpd = pd.DataFrame(fps)
    fpd.to_parquet(h0013.OUT / "false_positives.parquet")
    summary = summarise(df)
    summary["false_positives"] = dict(n_sources=len(fpd), shuffle_rate=round(float(fpd.fp_shuffle.mean()), 4),
                                      n_shuffle=int(fpd.fp_shuffle.sum()), phase_rate=round(float(fpd.fp_phase.mean()), 4),
                                      n_phase=int(fpd.fp_phase.sum()),
                                      phase_by_class={k: int(g.fp_phase.sum()) for k, g in fpd.groupby("cls")},
                                      phase_by_real_light_verdict={k: [int(g.fp_phase.sum()), len(g)] for k, g in fpd.groupby("real_light")})
    (h0013.WORK / "injection_summary.json").write_text(json.dumps(summary, indent=1))
    figure(df, h0013.HERE / "figures" / "completeness.png")
    log.info("done: %s", json.dumps(summary["overall"]))


def phase_surrogate(L: rc.LightCurve, rng) -> rc.LightCurve:
    """One Fourier phase-randomised surrogate (as recurrence.phase_null builds them)."""
    y0 = rc._season_offsets_removed(L)
    late = np.nonzero(L.t > 2013.0)[0]
    early = np.nonzero(L.t <= 2013.0)[0]
    filled = np.array([np.interp(L.t[late], L.t[late][L.ok[b, late]], y0[b, late][L.ok[b, late]]) if L.ok[b, late].sum() >= 4
                       else np.zeros(late.size) for b in range(2)])
    mean = filled.mean(1, keepdims=True)
    Fz = np.fft.rfft(filled - mean, axis=1)
    ph = rng.uniform(0, 2 * np.pi, Fz.shape[1])
    ph[0] = 0.0
    if late.size % 2 == 0:
        ph[-1] = 0.0
    sur = np.fft.irfft(Fz * np.exp(1j * ph)[None, :], n=late.size, axis=1) + mean
    y = y0.copy()
    y[:, late] = np.where(L.ok[:, late], sur, np.nan)
    e = L.e.copy()
    if early.size > 1:
        pe = rng.permutation(early)
        y[:, early], e[:, early] = y0[:, pe], L.e[:, pe]
    return rc.LightCurve(L.t, L.season, y, e, L.epoch)


def _rate(g, col="recovered"):
    return dict(n=int(len(g)), rate=round(float(g[col].mean()), 3) if len(g) else None)


def summarise(df: pd.DataFrame) -> dict:
    df = df.copy()
    df["full"] = df.recovered & df.cand_stage
    out = dict(overall=dict(n=len(df), recovered=round(float(df.recovered.mean()), 3),
                            recovered_with_candidate_stage=round(float(df.full.mean()), 3),
                            period_within_10pct_of_recovered=round(float(df[df.recovered].P_ok.mean()), 3)))
    snr_bins = [0, 2, 4, 8, 16, 32, 1e9]
    out["by_snr_w2"] = {f"{lo}-{hi}": _rate(df[(df.snr_w2 >= lo) & (df.snr_w2 < hi)]) for lo, hi in zip(snr_bins[:-1], snr_bins[1:], strict=False)}
    Lb = [3.5, 4.0, 4.5, 5.0, 5.5]
    out["by_logL_w2"] = {f"{lo}-{hi}": _rate(df[(df.logL_w2 >= lo) & (df.logL_w2 < hi)]) for lo, hi in zip(Lb[:-1], Lb[1:], strict=False)}
    out["by_logL_w2_with_candidate_stage"] = {f"{lo}-{hi}": _rate(df[(df.logL_w2 >= lo) & (df.logL_w2 < hi)], "full")
                                              for lo, hi in zip(Lb[:-1], Lb[1:], strict=False)}
    Pb = [2, 3, 4.5, 6, 8, 12]
    bright = df[df.snr_w2 >= 8]
    out["by_P_bright(snr_w2>=8)"] = {f"{lo}-{hi}": _rate(bright[(bright.P >= lo) & (bright.P < hi)]) for lo, hi in zip(Pb[:-1], Pb[1:], strict=False)}
    out["by_n_peaks_in_data_bright"] = {str(k): _rate(bright[bright.n_peaks_in_data == k]) for k in sorted(bright.n_peaks_in_data.unique())}
    out["by_host_class_bright"] = {k: _rate(g) for k, g in bright.groupby("host_cls")}
    db = [0, 1, 2, 4, 7, 11]
    out["by_distance_logL_ge_4.5"] = {f"{lo}-{hi} Mpc": _rate(df[(df.logL_w2 >= 4.5) & (df.dist_mpc >= lo) & (df.dist_mpc < hi)])
                                      for lo, hi in zip(db[:-1], db[1:], strict=False)}
    return out


def figure(df: pd.DataFrame, path: Path):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(1, 3, figsize=(13, 3.8))
    bins = np.array([0.5, 1, 2, 4, 8, 16, 32, 64, 128])
    x = np.sqrt(bins[:-1] * bins[1:])
    for col, lab, c in (("recovered", "light curve + shuffle null", "#1f5fa8"), ("full", "and H-0012 candidate stage", "#d1495b")):
        d = df.assign(full=df.recovered & df.cand_stage)
        r = [d[(d.snr_w2 >= lo) & (d.snr_w2 < hi)][col].mean() for lo, hi in zip(bins[:-1], bins[1:], strict=False)]
        ax[0].plot(x, r, "o-", color=c, label=lab)
    ax[0].set_xscale("log")
    ax[0].set_xlabel("W2 outburst amplitude / per-epoch error")
    ax[0].set_ylabel("recovered fraction")
    ax[0].legend(fontsize=8, frameon=False)
    ax[0].set_ylim(-0.02, 1.02)
    Pb = np.array([2, 3, 4.5, 6, 8, 12])
    for lo_snr, c in ((8, "#1f5fa8"), (16, "#2a9d8f")):
        d = df[df.snr_w2 >= lo_snr]
        r = [d[(d.P >= lo) & (d.P < hi)].recovered.mean() for lo, hi in zip(Pb[:-1], Pb[1:], strict=False)]
        ax[1].plot(np.sqrt(Pb[:-1] * Pb[1:]), r, "o-", color=c, label=f"S/N >= {lo_snr}")
    ax[1].set_xlabel("injected period (yr)")
    ax[1].set_ylim(-0.02, 1.02)
    ax[1].legend(fontsize=8, frameon=False)
    Lb = np.arange(3.5, 5.75, 0.25)
    for lo_d, hi_d, c in ((0, 2, "#1f5fa8"), (2, 5, "#2a9d8f"), (5, 11, "#d1495b")):
        d = df[(df.dist_mpc >= lo_d) & (df.dist_mpc < hi_d)].assign(full=lambda z: z.recovered & z.cand_stage)
        r = [d[(d.logL_w2 >= lo) & (d.logL_w2 < hi)].full.mean() for lo, hi in zip(Lb[:-1], Lb[1:], strict=False)]
        ax[2].plot(Lb[:-1] + 0.125, r, "o-", color=c, label=f"{lo_d}-{hi_d} Mpc")
    ax[2].set_xlabel("log W2 outburst peak nu L_nu (L_sun)")
    ax[2].set_ylim(-0.02, 1.02)
    ax[2].legend(fontsize=8, frameon=False)
    ax[2].set_title("incl. candidate stage", fontsize=9)
    fig.suptitle("H-0013 injection-recovery: periodic outbursts in real H-0012 light curves", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=110)


if __name__ == "__main__":
    main()
