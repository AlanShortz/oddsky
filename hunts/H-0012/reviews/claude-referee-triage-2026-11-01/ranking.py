"""Referee: why does N6946-BH1 rank #65 behind M31/M33 faders, and what score fixes that without
being tuned on BH1 alone?

    uv run python hunts/H-0012/reviews/claude-referee-triage-2026-11-01/ranking.py

Reads the merged table (~/oddsky-runs/h0012-xmatch/merged_h0012a.parquet) and the run's light curves.
For every failed-SN-like row it computes
  rough_wB   sqrt(chi2_nu) of the season-aligned light curve about its own 5-point running median
             (an LPV/AGB star zig-zags about any smooth trend; DS1 and BH1 do not)
  pre_chi2   chi2_nu about a constant of the epochs BEFORE the fade began (onset = first epoch whose
             3-pt running median falls 3 sigma below the 2010-11 level), when >= 4 such epochs exist
  L_fade     nu L_nu of the lost light (W1), from the merged table
then re-scores with the factors below and reports DS1/BH1 ranks and the make-up of the top 30.
Writes ranking.csv and ranking.json.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from oddsky.imaging import metrics

HERE = Path(__file__).resolve().parent
RUN = Path("~/oddsky-runs/h0012a").expanduser()
M = pd.read_parquet(Path("~/oddsky-runs/h0012-xmatch/merged_h0012a.parquet").expanduser())
F = M[M.triage_class == "failed-SN-like"].copy()


def lc_feats(lc):
    out = {}
    for b in (1, 2):
        lb = lc[lc.band == b].sort_values("mjd")
        g = (np.isfinite(lb.flux) & np.isfinite(lb.err) & (lb.err > 0)).to_numpy()
        if g.sum() < 8:
            continue
        rf = lb.groupby("season").ref_flux.first().to_dict()
        f = metrics.align_seasons(lb.flux.to_numpy(), lb.season.to_numpy(), rf)[g]
        e = lb.err.to_numpy()[g]
        t = lb.mjd.to_numpy()[g]
        sm5 = metrics.running_median(f, 5)
        rough = float(np.sqrt(np.mean(((f - sm5) / e) ** 2)))
        early = t < metrics.EARLY_MJD
        w = 1 / e**2
        base = np.sum(w[early] * f[early]) / np.sum(w[early]) if early.any() else f[0]
        sm3 = metrics.running_median(f, 3)
        below = np.nonzero((sm3 < base - 3 * e) & ~early)[0]
        onset = below[0] if below.size else f.size
        pre = slice(0, onset)
        if onset >= 4:
            fp, ep = f[pre], e[pre]
            mu = np.sum(fp / ep**2) / np.sum(1 / ep**2)
            pre_chi2 = float(np.mean(((fp - mu) / ep) ** 2))
        else:
            pre_chi2 = np.nan
        out[b] = dict(rough=rough, pre_chi2=pre_chi2, n_pre=int(onset), t_onset=float(t[min(onset, f.size - 1)]))
    return out


feats = {}
for (tile, gal), g in F.groupby(["tile", "phot_galaxy"]):
    p = RUN / tile / gal / "lightcurves.parquet"
    if not p.exists():
        continue
    lcs = pd.read_parquet(p)
    lcs = lcs[lcs.group.isin(set(g.group))]
    for gid, lc in lcs.groupby("group"):
        feats[(tile, gal, gid)] = lc_feats(lc)
for b in (1, 2):
    for k in ("rough", "pre_chi2", "n_pre", "t_onset"):
        F[f"{k}_w{b}"] = [feats.get((r.tile, r.phot_galaxy, r.group), {}).get(b, {}).get(k, np.nan) for r in F.itertuples()]
F["rough"] = np.nanmin(F[["rough_w1", "rough_w2"]].to_numpy(float), axis=1)  # the smoother band
F["rough_max"] = np.nanmax(F[["rough_w1", "rough_w2"]].to_numpy(float), axis=1)
F["pre_chi2"] = np.nanmax(F[["pre_chi2_w1", "pre_chi2_w2"]].to_numpy(float), axis=1)


def soft_above(x, thr, dex=0.25):
    """~1 well above thr, 0.5 at thr, falls off below (logistic in log10)."""
    with np.errstate(all="ignore"):
        z = (np.log10(np.asarray(x, float)) - np.log10(thr)) / dex
    return np.where(np.isfinite(z), 1 / (1 + np.exp(-z * 2.2)), 0.0)


def rescore(df, use_rough=True, use_pre=False, use_lfade=True, use_colour=True, use_pm=True, l_thr=4e3, rough_ref=1.5):
    s = df.fsn_score.to_numpy(float).copy()
    if use_rough:  # zig-zag about a smooth curve: LPV/AGB
        s *= np.clip((rough_ref / np.fmax(df.rough_max.to_numpy(float), 1e-3)) ** 2, 0, 1)
    if use_pre:  # variable before the fade began (only testable when >= 6 pre-fade epochs, i.e. onset >= 2015,
        # and not for rise-then-fade, whose 'pre-fade' segment is the rise itself)
        ok = (np.nan_to_num(df[["n_pre_w1", "n_pre_w2"]].max(axis=1).to_numpy(float)) >= 6) & (df.cls != "rise-then-fade").to_numpy()
        pc = np.where(ok, np.nan_to_num(df.pre_chi2.to_numpy(float), nan=1.0), 1.0)
        s *= np.clip(3.0 / np.fmax(pc, 1e-3), 0, 1)
    if use_lfade:  # the lost W1 light must be what a >= 3e4 L_sun photosphere emits in W1 (0.14 x 3e4 = 4e3)
        s *= soft_above(np.fmax(df.L_fade_w1.to_numpy(float), 1e-3), l_thr)
    if use_colour:  # undo the redness bonus (f_IR up to x2) and penalise a static AGN/dusty-AGB colour
        col = np.where(df.cls == "rise-then-fade", df.colour_up, df.colour_fade)
        s /= 1 + np.clip(np.nan_to_num(col) / 0.5, 0, 1)
        aw = pd.to_numeric(df.allwise_w1w2, errors="coerce").to_numpy(float)
        s *= np.where(aw >= 0.8, 0.3, 1.0)
    if use_pm:  # SIMBAD high-proper-motion star within 3": a moving foreground star the Gaia 2" match missed
        pm = (df.simbad_otype.astype(str) == "PM*").to_numpy() & (pd.to_numeric(df.simbad_sep, errors="coerce").to_numpy(float) < 3)
        s *= np.where(pm, 0.02, 1.0)
    return s


def ranks(df, score):
    order = np.argsort(-score, kind="stable")
    r = np.empty(len(df), int)
    r[order] = np.arange(1, len(df) + 1)
    return r


F = F[F.fsn_score > 0].copy()
F["rank_now"] = ranks(F, F.fsn_score.to_numpy())
variants = {
    "baseline": {},
    "rough only": dict(use_lfade=False, use_colour=False, use_pm=False),
    "pre (onset>=2015) only": dict(use_pre=True, use_rough=False, use_lfade=False, use_colour=False, use_pm=False),
    "L_fade only": dict(use_rough=False, use_colour=False, use_pm=False),
    "colour only": dict(use_rough=False, use_lfade=False, use_pm=False),
    "PM* only": dict(use_rough=False, use_lfade=False, use_colour=False),
    "rough + L_fade": dict(use_colour=False, use_pm=False),
    "rough + L_fade + PM*": dict(use_colour=False),
    "all four (proposed)": dict(),
    "all four + pre": dict(use_pre=True),
    "all, L_thr 2e3": dict(l_thr=2e3),
    "all, L_thr 1e4": dict(l_thr=1e4),
    "all, rough_ref 1.2": dict(rough_ref=1.2),
    "all, rough_ref 2.0": dict(rough_ref=2.0),
    "all but colour": dict(use_colour=False),
}
res = {}
for name, kw in variants.items():
    sc = F.fsn_score.to_numpy() if name == "baseline" else rescore(F, **kw)
    rk = ranks(F, sc)
    F[f"s_{name}"] = sc
    d = {}
    for kn in ("M31-2014-DS1", "N6946-BH1"):
        k = np.nonzero(F.known_name.to_numpy() == kn)[0]
        d[kn] = int(rk[k[0]]) if k.size else None
    top = F.iloc[np.argsort(-sc)[:30]]
    d["top30_by_galaxy"] = top.galaxy.value_counts().to_dict()
    d["top30_known_agb"] = int((top.what == "known LPV/AGB").sum())
    d["top30_unknown"] = int((top.what.str.startswith("unknown")).sum())
    # negative controls: catalogued AGB/LPV stars and Gaia-variable red stars among the failed-SN-like
    agb = F.what == "known LPV/AGB"
    d["median_rank_known_agb"] = float(np.median(rk[agb.to_numpy()])) if agb.any() else None
    res[name] = d
    print(f"{name:24s} DS1 #{d['M31-2014-DS1']}  BH1 #{d['N6946-BH1']}  top30 {d['top30_by_galaxy']}  "
          f"known-AGB median rank {d['median_rank_known_agb']}")
F["rank_proposed"] = ranks(F, F["s_all four (proposed)"].to_numpy())
cols = ["rank_now", "rank_proposed", "known_name", "what", "galaxy", "ra", "dec", "cls", "fsn_shape", "rough_w1", "rough_w2",
        "pre_chi2", "n_pre_w1", "L_fade_w1", "L_fade_w2", "colour_fade", "allwise_w1w2", "Lbol_pre_est", "fsn_score",
        "s_all four (proposed)"]
F.sort_values("rank_proposed")[cols].to_csv(HERE / "ranking.csv", index=False)
(HERE / "ranking.json").write_text(json.dumps(res, indent=1))
pd.set_option("display.width", 250)
print(F.sort_values("rank_proposed")[cols].head(30).round(2).to_string())
print("\nBH1/DS1 features:")
print(F[F.known_name.isin(["N6946-BH1", "M31-2014-DS1"])][cols].round(2).to_string())
print("\nthe 64 rows above BH1 now: median rough_max %.2f, L_fade_w1 %.0f; share M31/M33 %.2f" % (
    F[F.rank_now < 65].rough_max.median(), F[F.rank_now < 65].L_fade_w1.median(),
    F[F.rank_now < 65].galaxy.isin(["MESSIER031", "MESSIER033"]).mean()))
