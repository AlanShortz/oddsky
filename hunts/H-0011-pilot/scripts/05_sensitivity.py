"""H-0011 pilot, step 5: injection-recovery on the real light curves of the MC RSG sample.

Each star's own NEOWISE visits (its real pulsation, noise, saturation and cadence) are multiplied, in flux, by a
failed-supernova template starting at t0, then run through exactly the statistics and flags of 04_search.py.
Recovered = flagged by B (one-way IR change) or D (rise-then-fade shape). The false-positive rate is the flag rate
on the un-injected sample.

Onsets t0 on a 0.5-yr grid 2005-2023; injected visits fainter than W1 = 15 are dropped (non-detections).
IR templates (flux ratio to the progenitor; t' = t - t0 in years):
  DS1     M31-2014-DS1-like (De et al. 2024): +50% over 2 yr, then exponential decline through the progenitor level
          one year after peak (tau = 1/ln 1.5 = 2.47 yr in W1, 3.5 yr in W2), i.e. ~2 mag below by t' = 8
  BH1     N6946-BH1-like (Gerke+2015, Adams+2017, Basinger+2021): x1.3 outburst for 1 yr, flat for 5 yr, then a
          factor-2 fade over 2 yr (tau 2.9 yr) to a floor of 15% (JWST: 13-25% of the progenitor at 14 yr)
  SHROUD  dust-enshrouded / merger-like: IR rises to x2 (W1) / x2.5 (W2) over 2 yr and stays
  SLOW    a minimal case: a 1-mag W1 fade spread linearly over 6 yr (no precursor)
Optical (Gaia DR3 epoch G, 2014.6-2017.4), for stars with epoch photometry:
  DS1-opt optical fade beginning at t0 + 2 yr, x100 over 3 yr (1.5 mag/yr)
  BH1-opt optical fade beginning at t0 + 1 yr, >5 mag within 2 yr (2.5 mag/yr)
Gaia recovered = flag A criteria (dG >= 0.5 mag, z >= 4, Kendall tau >= 0.4); the injected IR in the Gaia era is rising or flat in
both templates, so the "IR holds" half of flag A is satisfied by construction.

Writes work/sensitivity_ir.csv, work/sensitivity_gaia.csv, figures/sensitivity.png.
"""
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location("s4", HERE / "04_search.py")
s4 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s4)
import plotlib as P  # noqa: E402

WORK = s4.WORK
T0_GRID = np.arange(2005.0, 2023.01, 0.5)
W1_LIMIT = 15.0  # injected visits fainter than this are dropped (NEOWISE single-exposure W1 limit ~15.3)


def r_ir(name: str, tp: np.ndarray, band: str) -> np.ndarray:
    r = np.ones_like(tp)
    a = tp > 0
    if name == "DS1":
        tau = 2.47 if band == "W1" else 3.5
        rise = (tp > 0) & (tp <= 2)
        r[rise] = 1 + 0.25 * tp[rise]
        dec = tp > 2
        r[dec] = 1.5 * np.exp(-(tp[dec] - 2) / tau)
    elif name == "BH1":
        r[(tp > 0) & (tp <= 1)] = 1.3
        dec = tp > 6
        r[dec] = np.maximum(np.exp(-(tp[dec] - 6) / 2.9), 0.15)
    elif name == "SHROUD":
        peak = 2.0 if band == "W1" else 2.5
        r[a] = 1 + (peak - 1) * np.clip(tp[a] / 2, 0, 1)
    elif name == "SLOW":
        if band == "W1":
            r[a] = 10 ** (-0.4 * np.clip(tp[a] / 6, 0, 1))
        else:
            r[a] = 10 ** (-0.4 * 0.7 * np.clip(tp[a] / 6, 0, 1))
    return r


def flags_for(row: dict, ref: pd.DataFrame, dt: pd.DataFrame) -> tuple[bool, bool]:
    """The B and D flags of 04_search.py for one (possibly injected) light curve, drift-corrected the same way."""
    if not np.isfinite(row.get("W1_med", np.nan)):
        return False, False
    st = s4.apply_drift(pd.DataFrame([row]), dt).iloc[0]
    d10 = row.get("W1_d2010", np.nan) if row.get("W1_med", 0) >= 7.5 else np.nan
    x = ref["W1_d2010"].dropna()
    z10 = (d10 - x.median()) / (1.4826 * (x - x.median()).abs().median()) if np.isfinite(d10) else 0.0
    B = (abs(st.z_W1_dc) >= 5 and abs(st.W1_dc) >= 0.4 and abs(st.W1_tau_c) >= 0.4) or \
        (abs(z10) >= 5 and abs(d10) >= 0.5 and abs(row["W1_tau"]) >= 0.3 and np.sign(d10) == np.sign(row["W1_delta"]))
    D = (row.get("W1_exc_min", 0) <= -0.3) and (st.W1_dc >= 0.5) and (row.get("W1_fade_after_peak", 0) >= 0.8)
    return bool(B), bool(D)


def star_row(v: pd.DataFrame) -> dict:
    out = {}
    for band in ("W1", "W2"):
        for k, val in s4.band_stats(v[v.band == band]).items():
            out[f"{band}_{k}"] = val
    return out


def main():
    ref = pd.read_csv(WORK / "stats_mc.csv")
    dt = pd.read_csv(WORK / "saturation_drift.csv")
    visits = pd.read_parquet(WORK / "neowise_visits_mc.parquet")
    rows = []
    sids = ref.loc[ref.W1_n >= 8, "oid"].tolist()
    for i, sid in enumerate(sids):
        v0 = visits[visits.sid == sid]
        t = s4.yr(v0.t_mjd.to_numpy())
        base = star_row(v0)
        bB, bD = flags_for(base, ref, dt)
        rows.append(dict(sid=sid, template="none", t0=np.nan, B=bB, D=bD, W1_med=base.get("W1_med")))
        for name in ("DS1", "BH1", "SHROUD", "SLOW"):
            for t0 in T0_GRID:
                v = v0.copy()
                for band in ("W1", "W2"):
                    m = v.band == band
                    v.loc[m, "mag"] = v.loc[m, "mag"] - 2.5 * np.log10(r_ir(name, t[m.to_numpy()] - t0, band))
                v = v[v.mag <= W1_LIMIT]
                rr = star_row(v)
                B, D = flags_for(rr, ref, dt)
                rows.append(dict(sid=sid, template=name, t0=t0, B=B, D=D, W1_med=base.get("W1_med"),
                                 W1_delta=rr.get("W1_delta")))
        if i % 100 == 0:
            print(i, len(sids), flush=True)
    res = pd.DataFrame(rows)
    res["rec"] = res.B | res.D
    res.to_csv(WORK / "sensitivity_ir.csv", index=False)
    fp = res[res.template == "none"].rec.mean()
    summ = res[res.template != "none"].groupby(["template", "t0"]).rec.mean().unstack(0)
    print("false-positive rate (flag rate on real data):", round(fp, 4))
    print(summ.round(2).to_string())
    ctl = res[res.template != "none"].groupby(["template", "sid"]).rec.sum().groupby("template").mean() * 0.5
    print("effective control time per star (yr of onset window with recovery, 2005-2023):", ctl.round(2).to_dict())
    win = res[(res.template != "none") & (res.t0 >= 2014) & (res.t0 <= 2021)]
    print("mean recovery for t0 in 2014-2021:", win.groupby("template").rec.mean().round(3).to_dict())
    sat = win.assign(sat=win.W1_med < 8).groupby(["template", "sat"]).rec.mean().round(3)
    print("by saturation (W1 < 8):", sat.to_dict())

    # Gaia
    gs = None
    ep_path = WORK / "gaia_epoch_mc.parquet"
    if ep_path.exists():
        ep = pd.read_parquet(ep_path)
        gref = ref.dropna(subset=["g_dG"])
        med = gref.g_dG.median()
        mad = 1.4826 * (gref.g_dG - med).abs().median()
        grow = []
        for sidg, g in ep[ep.band == "G"].groupby("source_id"):
            g = g[(g.flag.fillna("") != "rejected_by_photometry") & np.isfinite(g.mag)].sort_values("t_mjd")
            if len(g) < 10:
                continue
            t = s4.yr(g.t_mjd.to_numpy())
            for name, delay, rate in (("DS1-opt", 2.0, 1.5), ("BH1-opt", 1.0, 2.5)):
                for t0 in T0_GRID:
                    dm = np.clip((t - t0 - delay) * rate, 0, 5)
                    m = g.mag.to_numpy() + dm
                    q = max(3, len(m) // 4)
                    dG = np.median(m[-q:]) - np.median(m[:q])
                    tau = s4.stats.kendalltau(t, m)[0]
                    grow.append(dict(source_id=sidg, template=name, t0=t0,
                                     rec=bool((dG >= 0.5) and ((dG - med) / mad >= 4) and tau >= 0.4)))
        gs = pd.DataFrame(grow)
        gs.to_csv(WORK / "sensitivity_gaia.csv", index=False)
        print("Gaia stars", gs.source_id.nunique())
        print(gs.groupby(["template", "t0"]).rec.mean().unstack(0).round(2).to_string())

    fig, ax = P.plt.subplots(figsize=(7, 3.6))
    cols = {"DS1": P.C["W1"], "BH1": P.C["W2"], "SHROUD": P.C["G"], "SLOW": "#6250d6"}
    for name in ("DS1", "BH1", "SHROUD", "SLOW"):
        ax.plot(summ.index, summ[name], "o-", ms=4, lw=1.6, color=cols[name], label=f"NEOWISE {name}")
    if gs is not None and len(gs):
        gsum = gs.groupby(["template", "t0"]).rec.mean().unstack(0)
        frac = gs.source_id.nunique() / len(sids)
        for name, ls in (("DS1-opt", "--"), ("BH1-opt", ":")):
            ax.plot(gsum.index, gsum[name] * frac, ls, lw=1.6, color=P.C["muted"],
                    label=f"Gaia DR3 {name} (x {frac:.0%} with epochs)")
    ax.axvspan(2013.9, 2024.6, color="#f2f2ef", zorder=0)
    ax.set_xlabel("event onset t0 (year)")
    ax.set_ylabel("fraction of RSGs recovered")
    ax.set_ylim(-0.02, 1.02)
    ax.set_title(f"Injection-recovery on {len(sids)} MC RSG light curves (false-positive rate {fp:.1%})", loc="left",
                 fontsize=9)
    ax.legend(fontsize=7, loc="center left", bbox_to_anchor=(1.0, 0.5))
    fig.savefig(P.FIG / "sensitivity.png", dpi=130, bbox_inches="tight")


if __name__ == "__main__":
    main()
