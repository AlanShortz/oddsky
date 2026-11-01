"""Referee checks on M31-2014-DS1 (2026-11-01).

1. Late fade: is the change between the paper's last epoch (2021 Dec) and 2024 Jul significant in
   the pipeline's own photometry, once (a) the epoch-to-epoch scatter and (b) epoch-dependent zero
   points measured on non-variable stars of similar flux near DS1 are taken into account? And what
   "fraction of the 2010 flux left" follows on De et al.'s flux scale (our changes are 1.09x / 1.05x
   theirs)?
2. Ranking robustness: recompute classes and ds1_score for all 16,145 candidates from
   lightcurves.parquet under perturbed thresholds; report DS1's rank each time.

    uv run python hunts/H-0012/reviews/claude-referee-2026-11-01/ds1_checks.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import ndimage

from oddsky.imaging import fetch, flux_to_mjy, metrics, photometry
from oddsky.imaging.pipeline import SCALE_BIN, _load_tile

HERE = Path(__file__).resolve().parent
WD = fetch.cache_root() / "work" / "M31"
DS1 = (11.306125, 41.542539)
TILE = "0118p408"
PUB = Path("~/oddsky-runs/imaging/papers/ds1repo/photometry.csv").expanduser()


def aligned(f, season, rf, mjd):
    fa = metrics.align_seasons(f, season, rf)
    e = mjd < metrics.EARLY_MJD
    return fa - np.nanmean(fa[e])


def late_fade():
    out = {}
    cands = pd.read_csv(WD / "candidates.csv", usecols=["ra", "dec", "var_sig"])
    for band in (1, 2):
        meta, wcs, D, S, scale, psfs, refs = _load_tile(WD, TILE, band)
        season = np.array(meta["season"])
        mjd = np.array(meta["mjd"])
        x0, y0 = wcs.all_world2pix([[*DS1]], 0)[0]

        def lc(x, y):
            sc = scale[:, min(int(round(y)) // SCALE_BIN, scale.shape[1] - 1), min(int(round(x)) // SCALE_BIN, scale.shape[2] - 1)]
            f, e = photometry.forced_lightcurve(D, S, psfs, season, x, y, sc)
            rf = {s: photometry.reference_flux(np.asarray(r), np.asarray(rv), psfs[s], x, y)[0] for s, (r, rv) in refs.items()}
            return aligned(f, season, rf, mjd), e, np.mean(list(rf.values()))

        f_ds1, e_ds1, ref_ds1 = lc(x0, y0)
        # control stars: reference maxima within 300 px (13.75') of DS1, ref flux within x3 of DS1's,
        # not within 8" of any candidate with var_sig > 3 (i.e. not variable)
        h = 300
        xi, yi = int(round(x0)), int(round(y0))
        r0 = np.asarray(refs[0][0][max(0, yi - h): yi + h, max(0, xi - h): xi + h])
        oy, ox = max(0, yi - h), max(0, xi - h)
        sm = ndimage.uniform_filter(r0, 3)
        pk = (sm == ndimage.maximum_filter(sm, 7)) & (r0 > ref_ds1 / 6)
        ys, xs = np.nonzero(pk)
        xs, ys = xs + ox, ys + oy
        ra, dec = wcs.all_pix2world(xs, ys, 0)
        var = cands[cands.var_sig > 3]
        from scipy.spatial import cKDTree

        t = cKDTree(np.c_[var.ra * np.cos(np.radians(41.5)), var.dec])
        dd, _ = t.query(np.c_[ra * np.cos(np.radians(41.5)), dec])
        keep = (dd * 3600 > 8) & (np.hypot(xs - x0, ys - y0) > 5)
        ctrl = []
        for x, y in zip(xs[keep], ys[keep], strict=True):
            f, e, rf = lc(float(x), float(y))
            if np.isfinite(f).sum() >= 22 and 0.33 * ref_ds1 < rf < 3 * ref_ds1:
                ctrl.append(f)
            if len(ctrl) >= 150:
                break
        C = np.array(ctrl)
        zp = np.nanmedian(C, axis=0)  # epoch zero-point offsets (nanomaggies) of non-variable stars
        zp_err = 1.2533 * np.nanstd(C, axis=0) / np.sqrt(np.isfinite(C).sum(0))
        scat = np.nanstd(C, axis=0)  # empirical per-epoch scatter of a non-variable star of this flux
        k19 = int(np.argmin(np.abs(mjd - 59576)))  # 2021 Dec, the paper's last epoch
        late = np.arange(k19 + 1, mjd.size)
        d_raw = np.mean(f_ds1[late]) - f_ds1[k19]
        d_cor = np.mean((f_ds1 - zp)[late]) - (f_ds1 - zp)[k19]
        # error from the control stars' own (late mean - e19) scatter: the empirical null
        null = np.nanmean(C[:, late], axis=1) - C[:, k19]
        # linear trend 2021 Dec - 2024 Jul
        tt = (mjd[k19:] - mjd[k19]) / 365.25
        A = np.c_[tt, np.ones_like(tt)]
        y = (f_ds1 - zp)[k19:]
        p = np.linalg.lstsq(A, y, rcond=None)[0]
        res = y - A @ p
        slope_err = np.sqrt(np.sum(res**2) / (len(y) - 2) / np.sum((tt - tt.mean()) ** 2))
        pub = pd.read_csv(PUB)
        pub = pub[(pub.instrument == "NEOWISE") & (pub["filter"] == f"W{band}")]
        f2010 = pub.flux_mJy[pub.MJD < metrics.EARLY_MJD].mean()
        slope_vs_pub = {1: 1.0871, 2: 1.0465}[band]
        last_ours = flux_to_mjy(f_ds1[-1], band)
        out[f"W{band}"] = dict(
            n_control=int(len(C)), ref_flux_ds1_nmgy=float(ref_ds1),
            control_zp_mjy=[round(float(flux_to_mjy(z, band)), 4) for z in zp],
            control_zp_err_mjy=[round(float(flux_to_mjy(z, band)), 4) for z in zp_err],
            control_scatter_mjy=[round(float(flux_to_mjy(z, band)), 4) for z in scat],
            ds1_df_mjy=[round(float(flux_to_mjy(z, band)), 4) for z in f_ds1],
            pipeline_err_mjy=[round(float(flux_to_mjy(z, band)), 4) for z in e_ds1],
            change_after_2021Dec_raw_mjy=float(flux_to_mjy(d_raw, band)),
            change_after_2021Dec_zpcorr_mjy=float(flux_to_mjy(d_cor, band)),
            null_sigma_mjy=float(flux_to_mjy(np.nanstd(null), band)),
            change_sig_vs_null=float(d_cor / np.nanstd(null)),
            trend_2021_2024_mjy_per_yr=float(flux_to_mjy(p[0], band)),
            trend_err=float(flux_to_mjy(slope_err, band)),
            published_2010_total_mjy=float(f2010),
            frac_left_2024_on_our_scale=float(1 + last_ours / f2010),
            frac_left_2024_on_pub_scale=float(1 + last_ours / slope_vs_pub / f2010),
            frac_left_2021_published=float(pub.flux_mJy.iloc[-1] / f2010),
        )
        print(f"W{band}: {len(C)} control stars; DS1 change after 2021 Dec {flux_to_mjy(d_raw, band):+.3f} mJy raw, "
              f"{flux_to_mjy(d_cor, band):+.3f} zp-corrected, null sigma {flux_to_mjy(np.nanstd(null), band):.3f} "
              f"-> {d_cor / np.nanstd(null):+.1f} sigma; trend {flux_to_mjy(p[0], band):+.3f}+-{flux_to_mjy(slope_err, band):.3f} mJy/yr; "
              f"frac left 2024 ours {1 + last_ours / f2010:.2f}, on pub scale {1 + last_ours / slope_vs_pub / f2010:.2f}, "
              f"pub 2021 {pub.flux_mJy.iloc[-1] / f2010:.2f}", flush=True)
        print("   control zp (mJy):", [round(float(flux_to_mjy(z, band)), 3) for z in zp], flush=True)
    return out


_CACHE = {}


def metrics_for(lcs, turn_frac):
    if turn_frac in _CACHE:
        return _CACHE[turn_frac]
    recs = []
    for gid, lc in lcs.groupby("group"):
        m = {}
        for b in (1, 2):
            lb = lc[lc.band == b].sort_values("mjd")
            rf = lb.groupby("season").ref_flux.first().to_dict()
            f = metrics.align_seasons(lb.flux.to_numpy(), lb.season.to_numpy(), rf)
            m[b] = metrics.band_metrics(lb.mjd.to_numpy(), f, lb.err.to_numpy(), lb.season.to_numpy())
            if turn_frac != 0.15 and m[b].get("n", 0) >= 5 and "amp" in m[b]:
                sm = metrics.running_median(f[np.isfinite(f)], 3)
                m[b]["n_turns"] = metrics.zigzag_turns(sm, max(3 * m[b]["med_err"], turn_frac * m[b]["amp"]))
        recs.append((gid, m[1], m[2]))
    _CACHE[turn_frac] = recs
    return recs


def rescore(lcs, cands, eta_cut=1.2, rise_min=5, fade_min=3, turn_free=2, burst=True, smooth_on=True,
            turn_frac=0.15):
    recs = metrics_for(lcs, turn_frac)
    out = []
    for gid, m1, m2 in recs:
        ms = [m for m in (m1, m2) if m.get("n", 0) >= 5 and "chi2r" in m]
        if not ms:
            out.append((gid, "no-data", 0.0))
            continue
        best = max(ms, key=lambda m: m["chi2r"])
        if best["n_sig3"] < 3 or best["chi2r"] < 5:
            out.append((gid, "not-variable", 0.0))
            continue
        eta = np.nanmin([m["eta"] for m in ms])
        turns = min(m["n_turns"] for m in ms)
        dl = max(ms, key=lambda m: abs(np.nan_to_num(m.get("delta_late_sig", 0))))
        dls = abs(np.nan_to_num(dl.get("delta_late_sig", 0.0)))
        rise = np.nanmax([np.nan_to_num(m.get("rise_sig", 0)) for m in ms])
        fade = np.nanmax([np.nan_to_num(m.get("fade_sig", 0)) for m in ms])
        smooth = float(np.clip((2.0 - eta) / 2.0, 0, 1)) if smooth_on else 1.0
        score = float(max(dls, min(rise, fade)) * smooth / (1 + max(0, turns - turn_free)))
        cls = "irregular"
        if max(np.nan_to_num(m.get("season_split", 0)) for m in ms) > 4 and eta > 2.5:
            cls, score = "season-locked", score * 0.1
        elif burst and best.get("burst_frac", 0) > 0.8:
            cls = "transient"
        elif eta > eta_cut and turns >= 4:
            cls = "lpv-like"
        elif eta < eta_cut and turns <= 3:
            if rise > rise_min and fade > fade_min:
                cls = "rise-then-fade"
            elif dls > 5:
                cls = "fading" if dl["delta_late"] < 0 else "brightening"
            elif rise > 5 or fade > 5:
                cls = "transient"
        out.append((gid, cls, score))
    r = pd.DataFrame(out, columns=["group", "cls2", "score2"])
    return cands.merge(r, on="group", how="left")


def ranking():
    cands = pd.read_csv(WD / "candidates.csv")
    lcs = pd.read_parquet(WD / "lightcurves.parquet")
    i = int(np.argmin(np.hypot((cands.ra - DS1[0]) * np.cos(np.radians(DS1[1])), cands.dec - DS1[1])))
    gid = int(cands.group.iloc[i])
    variants = {
        "baseline": {},
        "eta_cut_1.0": dict(eta_cut=1.0),
        "eta_cut_1.5": dict(eta_cut=1.5),
        "rise3_fade3": dict(rise_min=3, fade_min=3),
        "rise5_fade5": dict(rise_min=5, fade_min=5),
        "penalise_every_turn": dict(turn_free=0),
        "turn_free_1": dict(turn_free=1),
        "no_burst_class": dict(burst=False),
        "no_smoothness": dict(smooth_on=False),
        "turn_thresh_3sig_only": dict(turn_frac=0.0),
    }
    res = {}
    for name, kw in variants.items():
        c = rescore(lcs, cands, **kw)
        row = c[c.group == gid].iloc[0]
        nd = c[~c.dipole]
        res[name] = dict(
            cls=row.cls2, score=float(row.score2),
            rank_all=int((c.score2 > row.score2).sum() + 1),
            rank_no_dipole=int((nd.score2 > row.score2).sum() + 1),
            rank_in_class=int(((c.cls2 == row.cls2) & (c.score2 > row.score2)).sum() + 1),
            n_in_class=int((c.cls2 == row.cls2).sum()))
        print(name, res[name], flush=True)
    # simple alternative rankings with no DS1-shaped design
    for key in ("w1_delta_late_sig", "w2_delta_late_sig"):
        v = -cands[key].fillna(0)
        res[f"rank_by_most_negative_{key}"] = int((v > v.iloc[i]).sum() + 1)
        nd = cands[~cands.dipole]
        vv = -nd[key].fillna(0)
        res[f"rank_by_most_negative_{key}_no_dipole"] = int((vv > -cands[key].iloc[i]).sum() + 1)
    print({k: v for k, v in res.items() if k.startswith("rank_by")})
    return res


def main():
    out = dict(late_fade=late_fade(), ranking=ranking())
    (HERE / "ds1_checks.json").write_text(json.dumps(out, indent=1, default=float))
    print("wrote", HERE / "ds1_checks.json")


if __name__ == "__main__":
    main()
