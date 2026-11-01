"""H-0011 pilot, step 4: per-star statistics, population-relative flags, candidates.

Per star and band (W1, W2), from NEOWISE-R visits (2014.0-2024.5) plus the 2010 AllWISE-MEP visits:
  early   = median of the first 4 NEOWISE visits (2014.0-2015.6)
  late    = median of the last 4 NEOWISE visits (2022.6-2024.5)
  delta   = late - early (mag; > 0 is fading)
  d2010   = late - median(2010 AllWISE-MEP visits)
  amp     = 1.4826 * MAD of all NEOWISE visits (pulsation amplitude proxy)
  tau     = Kendall tau of mag vs time (one-way-ness)
  exc     = most extreme 2-visit running median minus early (catches rise-then-return)
  dcol    = delta(W1-W2) late - early
Population-relative: robust z = (x - median) / (1.4826 MAD) over the sample.

Gaia DR3 epoch G (2014.6-2017.4, ~40 FoV transits): dG = median(last 25%) - median(first 25%), Theil-Sen slope,
Kendall tau. Gaia vs 1990s V (SIMBAD V, mostly MCPS / Massey 2002): G - V against the population's colour relation.

Flags:
  A  optical fade with IR holding: Gaia dG >= 0.5 mag, z_dG >= 4 and Gaia Kendall tau >= 0.4 (monotonic), while W1
     over 2014-2017.5 is flat or rising
  B  large one-way IR change: drift-corrected |delta_W1| >= 0.4 mag, >= 5 x the robust scatter of stars of the same
     W1 brightness, and |tau| >= 0.4 (bin median removed); or |z(d2010_W1)| >= 5,
     |d2010_W1| >= 0.5 mag, |tau| >= 0.3, same sign (2010 baseline only for W1 >= 7.5, see saturation note)
  C  Gaia-era optical deficit: (G - V) residual >= 1.5 mag above the population relation (faded since the V epoch)
  D  failed-SN IR shape: W1 rise >= 0.3 mag (exc_min <= -0.3) followed by a fade of >= 0.8 mag from that peak, ending
     >= 0.5 mag (drift-corrected) below the 2014-15 level

usage: 04_search.py   (runs mc, gal, cal)
Writes work/stats_<s>.csv, work/flags_<s>.csv, work/saturation_drift.csv.
Delta and tau are corrected for the NEOWISE saturation drift per W1 brightness bin (drift_table) before flagging.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

WORK = Path(__file__).resolve().parents[1] / "work"
MJD2000 = 51544.5


def yr(mjd):
    return 2000.0 + (np.asarray(mjd, float) - MJD2000) / 365.25


def robust_z(x: pd.Series, ref: pd.Series | None = None) -> pd.Series:
    r = (ref if ref is not None else x).dropna()
    med = r.median()
    mad = 1.4826 * (r - med).abs().median()
    return (x - med) / mad


def band_stats(v: pd.DataFrame) -> dict:
    """v: visits of one star in one band (NEOWISE + WISE_MEP)."""
    out = {}
    neo = v[v.survey == "NEOWISE"].sort_values("t_mjd")
    mep = v[v.survey == "WISE_MEP"]
    out["n"] = len(neo)
    if len(neo) < 8:
        return out
    t, m = yr(neo.t_mjd), neo.mag.to_numpy()
    out["med"] = float(np.median(m))
    out["sat_frac"] = float(neo.flag.fillna("").str.contains("saturated").mean())
    out["early"] = float(np.median(m[:4]))
    out["late"] = float(np.median(m[-4:]))
    out["delta"] = out["late"] - out["early"]
    out["amp"] = float(1.4826 * np.median(np.abs(m - np.median(m))))
    out["ptp"] = float(np.ptp(m))
    tau, p = stats.kendalltau(t, m)
    out["tau"], out["tau_p"] = float(tau), float(p)
    out["slope"] = float(stats.theilslopes(m, t)[0])
    rm = pd.Series(m).rolling(2).median().to_numpy()[1:]
    i = int(np.nanargmax(np.abs(rm - out["early"])))
    out["exc"] = float(rm[i] - out["early"])
    out["exc_min"] = float(np.nanmin(rm) - out["early"])  # strongest brightening
    imin = int(np.nanargmin(rm))
    out["t_brightest"] = float(t[imin + 1])
    out["fade_after_peak"] = float(np.median(m[-4:]) - np.nanmin(rm))
    w = t < 2017.5
    out["delta_gaia_era"] = float(np.median(m[w][-3:]) - np.median(m[w][:3])) if w.sum() >= 6 else np.nan
    out["d2010"] = out["late"] - float(np.median(mep.mag)) if len(mep) else np.nan
    out["m2010"] = float(np.median(mep.mag)) if len(mep) else np.nan
    return out


def ir_stats(visits: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for sid, g in visits.groupby("sid"):
        r = {"sid": sid}
        for band in ("W1", "W2"):
            for k, val in band_stats(g[g.band == band]).items():
                r[f"{band}_{k}"] = val
        rows.append(r)
    df = pd.DataFrame(rows)
    if "W2_early" in df:
        df["dcol"] = (df.W1_late - df.W2_late) - (df.W1_early - df.W2_early)
    return df


def gaia_stats(ep: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for sid, g in ep.groupby("source_id"):
        d = g[(g.band == "G") & (g.flag.fillna("") != "rejected_by_photometry") & np.isfinite(g.mag)].sort_values("t_mjd")
        if len(d) < 10:
            continue
        t, m = yr(d.t_mjd), d.mag.to_numpy()
        q = max(3, len(d) // 4)
        tau, p = stats.kendalltau(t, m)
        bp = g[(g.band == "BP") & np.isfinite(g.mag)].sort_values("t_mjd").mag.to_numpy()
        rp = g[(g.band == "RP") & np.isfinite(g.mag)].sort_values("t_mjd").mag.to_numpy()
        rows.append(dict(source_id=sid, g_n=len(d), g_t0=float(t[0]), g_t1=float(t[-1]),
                         g_dG=float(np.median(m[-q:]) - np.median(m[:q])), g_slope=float(stats.theilslopes(m, t)[0]),
                         g_tau=float(tau), g_tau_p=float(p), g_amp=float(1.4826 * np.median(np.abs(m - np.median(m)))),
                         g_ptp=float(np.percentile(m, 95) - np.percentile(m, 5)),
                         g_dBP=float(np.median(bp[-q:]) - np.median(bp[:q])) if len(bp) > 2 * q else np.nan,
                         g_dRP=float(np.median(rp[-q:]) - np.median(rp[:q])) if len(rp) > 2 * q else np.nan))
    return pd.DataFrame(rows)


BINS = [-5, 2, 3, 4, 5, 6, 7, 7.5, 8, 8.5, 9, 20]


def build(which: str) -> pd.DataFrame:
    s = pd.read_csv(WORK / f"sample_{which}.csv", dtype={"gaia_dr3": "Int64"})
    v = pd.read_parquet(WORK / f"neowise_visits_{which}.parquet")
    st = s.merge(ir_stats(v), left_on="oid", right_on="sid", how="left")
    gpath = WORK / f"gaia_{which}.csv"
    if gpath.exists():
        g = pd.read_csv(gpath)
        st = st.merge(g, left_on="gaia_dr3", right_on="source_id", how="left", suffixes=("", "_gaia"))
        # the left join turns source_id into float64 (19 digits do not survive); restore it from the exact Int64 id
        st["source_id"] = st["gaia_dr3"].where(st["source_id"].notna())
        ep_path = WORK / f"gaia_epoch_{which}.parquet"
        if ep_path.exists():
            st = st.merge(gaia_stats(pd.read_parquet(ep_path)), on="source_id", how="left")
    # crowding: fraction of raw NEOWISE exposures (within 3") with nb > 1 or a neighbour-contamination flag
    raw = pd.read_parquet(WORK / f"neowise_exp_{which}.parquet", columns=["sid", "nb", "sep", "w1sat", "cc_flags"])
    raw["cc_contam"] = raw.cc_flags.astype(str).str[:2].str.contains("[hdopHDOP]", regex=True)
    crowd = raw.groupby("sid").agg(nb_frac=("nb", lambda x: float((x > 1).mean())), sep_med=("sep", "median"),
                                   cc_frac=("cc_contam", "mean"),
                                   w1sat_med=("w1sat", "median"), n_exp=("nb", "size"))
    st = st.merge(crowd, left_on="oid", right_index=True, how="left")
    # NEOWISE profile-fit photometry of saturated stars runs brighter than AllWISE-MEP (median offset -0.05 mag at
    # W1 7-7.5, -0.25 at 6-7, -0.9 below 6 in the MC sample), so the 2010 baseline is used only where W1 >= 7.5 / W2 >= 6.5
    st.loc[~(st.W1_med >= 7.5), "W1_d2010"] = np.nan
    st.loc[~(st.W2_med >= 6.5), "W2_d2010"] = np.nan
    return st


def drift_table(pop: pd.DataFrame) -> pd.DataFrame:
    """Saturation drift: NEOWISE profile-fit magnitudes of saturated stars creep brighter over 2014-2024 (median W1
    late-early -0.2 to -0.5 mag at W1 3-5, -0.08 at 6-7, zero fainter than 7.5). Per-bin median and robust scatter of
    delta and tau, from the MC + Galactic RSGs together, so every star is judged against stars of its own brightness."""
    rows = []
    for band in ("W1", "W2"):
        b = pd.cut(pop[f"{band}_med"], BINS)
        for iv, g in pop.groupby(b, observed=True):
            d = g[f"{band}_delta"].dropna()
            if len(d) < 5:
                continue
            rows.append(dict(band=band, lo=iv.left, hi=iv.right, n=len(d), med=d.median(),
                             mad=max(1.4826 * (d - d.median()).abs().median(), 0.02),
                             tau_med=g[f"{band}_tau"].median()))
    return pd.DataFrame(rows)


def apply_drift(st: pd.DataFrame, dt: pd.DataFrame) -> pd.DataFrame:
    st = st.copy()
    for band in ("W1", "W2"):
        t = dt[dt.band == band].reset_index(drop=True)
        idx = np.clip(np.searchsorted(t.hi.to_numpy(), st[f"{band}_med"].fillna(99).to_numpy()), 0, len(t) - 1)
        st[f"{band}_drift"] = t.med.to_numpy()[idx]
        st[f"{band}_scale"] = t.mad.to_numpy()[idx]
        st[f"{band}_dc"] = st[f"{band}_delta"] - st[f"{band}_drift"]
        st[f"z_{band}_dc"] = st[f"{band}_dc"] / st[f"{band}_scale"]
        st[f"{band}_tau_c"] = st[f"{band}_tau"] - t.tau_med.to_numpy()[idx]
    return st


def flag(st: pd.DataFrame, ref: pd.DataFrame) -> pd.DataFrame:
    for c in ("W1_d2010", "W2_d2010", "dcol", "W1_amp", "W1_delta_gaia_era"):
        if c in st:
            st[f"z_{c}"] = robust_z(st[c], ref[c])
    if "g_dG" in st and "g_dG" in ref:
        st["z_g_dG"] = robust_z(st["g_dG"], ref["g_dG"])
    # Gaia-era deficit relative to the 1990s V: G - V vs the population colour relation in (V - K)
    if {"phot_g_mean_mag", "V", "K"} <= set(st.columns) and "phot_g_mean_mag" in ref:
        st["GmV"] = st.phot_g_mean_mag - st.V
        st["VmK"] = st.V - st.K
        r = ref.assign(GmV=ref.phot_g_mean_mag - ref.V, VmK=ref.V - ref.K).dropna(subset=["GmV", "VmK"])
        r = r[(r.VmK > 2) & (r.VmK < 7)]
        coef = np.polyfit(r.VmK, r.GmV, 2)
        res_ref = r.GmV - np.polyval(coef, r.VmK)
        st["GmV_res"] = st.GmV - np.polyval(coef, st.VmK.clip(2, 7))
        st["z_GmV_res"] = robust_z(st["GmV_res"], res_ref)
    f = pd.DataFrame(index=st.index)
    # monotonic (Gaia tau >= 0.4): without it the flag fires on long-period variables caught at different phases
    # (first pilot pass: HV 859, HV 2572, HV 2576, Gaia LPV periods 569/620/257 d, amplitudes 0.5-1.2 mag)
    f["A_optfade_irholds"] = ((st.get("g_dG", np.nan) >= 0.5) & (st.get("z_g_dG", 0) >= 4)
                              & (st.get("g_tau", np.nan) >= 0.4) & (st.W1_delta_gaia_era <= 0.1))
    # one-way: a large drift-corrected late-minus-early change that is also monotonic (|tau| >= 0.4 after removing the
    # brightness bin's median tau), so Mira-like pulsators caught at different phases do not trip it; the 2010
    # baseline only where it is calibrated (W1 >= 7.5)
    f["B_ir_oneway"] = (((st.z_W1_dc.abs() >= 5) & (st.W1_dc.abs() >= 0.4) & (st.W1_tau_c.abs() >= 0.4))
                        | ((st.z_W1_d2010.abs() >= 5) & (st.W1_d2010.abs() >= 0.5) & (st.W1_tau.abs() >= 0.3)
                           & (np.sign(st.W1_d2010) == np.sign(st.W1_delta))))
    f["C_gaia_deficit"] = (st.get("GmV_res", np.nan) >= 1.5)
    f["D_failedSN_shape"] = (st.W1_exc_min <= -0.3) & (st.W1_dc >= 0.5) & (st.W1_fade_after_peak >= 0.8)
    st = pd.concat([st.drop(columns=[c for c in f.columns if c in st]), f], axis=1)
    st["n_flags"] = f.sum(axis=1)
    return st


COLS = ["main_id", "galaxy", "sp_type", "logL", "K", "W1_med", "W1_sat_frac", "W1_delta", "W1_dc", "z_W1_dc",
        "W1_d2010", "W1_tau", "W1_amp", "W1_exc_min", "W2_dc", "dcol", "g_n", "g_dG", "z_g_dG", "GmV_res", "nb_frac",
        "cc_frac", "A_optfade_irholds", "B_ir_oneway", "C_gaia_deficit", "D_failedSN_shape"]


def main():
    raw = {w: build(w) for w in ("mc", "gal", "cal")}
    dt = drift_table(pd.concat([raw["mc"], raw["gal"]], ignore_index=True))
    dt.to_csv(WORK / "saturation_drift.csv", index=False)
    print(dt.round(3).to_string())
    out = {}
    for w in ("mc", "gal", "cal"):
        st = apply_drift(raw[w], dt)
        ref = out["mc"] if w == "cal" else st  # calibrators are judged against the MC RSGs
        out[w] = st = flag(st, ref)
        st.to_csv(WORK / f"stats_{w}.csv", index=False)
        fl = st[st.n_flags > 0].sort_values("n_flags", ascending=False)
        fl[[c for c in COLS if c in fl]].to_csv(WORK / f"flags_{w}.csv", index=False)
        print("\n==", w, "stars", len(st), "with NEOWISE", int(st.W1_n.fillna(0).ge(8).sum()),
              "with Gaia epoch", int(st.get("g_n", pd.Series(dtype=float)).notna().sum()))
        print(st[[c for c in COLS if c.endswith(("irholds", "oneway", "deficit", "shape"))]].sum().to_string())
        with pd.option_context("display.width", 250, "display.max_columns", 40):
            print(fl[[c for c in COLS if c in fl]].head(40).to_string())


if __name__ == "__main__":
    main()
