"""H-0012 acceptance tests: where does a known object land in the blind candidate list, and does its
recovered light curve match the published one?

    uv run python hunts/H-0012/scripts/acceptance.py M31       # M31-2014-DS1 vs De et al. 2024
    uv run python hunts/H-0012/scripts/acceptance.py NGC6946   # SN 2017eaw (control) and N6946-BH1

Reads the pipeline outputs in ~/oddsky-runs/imaging/work/<galaxy>/ (run first:
`python -m oddsky.imaging.pipeline <galaxy>`). The known positions are used ONLY here, after the
search. Writes work/acceptance_<galaxy>.json and figures/.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from astropy.wcs import WCS

from oddsky.imaging import fetch, flux_to_mjy, metrics, photometry
from oddsky.imaging.metrics import EARLY_MJD
from oddsky.imaging.pipeline import tile_dir

HERE = Path(__file__).resolve().parents[1]
W1C, W2C, INK, MUTED = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e"
PUBLISHED = Path("~/oddsky-runs/imaging/papers/ds1repo/photometry.csv").expanduser()  # De et al. repo
NULL_FOR = {"N6946-BH1"}  # forced photometry at the exact position + empirical nulls, candidate or not

KNOWN = {
    "M31": {"M31-2014-DS1": (11.306125, 41.542539)},  # 00:45:13.47 +41:32:33.14 (Gaia; De et al. 2024)
    "NGC6946": {
        "SN 2017eaw": (308.684333, 60.193289),  # 20:34:44.240 +60:11:35.84 (TNS)
        "N6946-BH1": (308.864833, 60.135636),  # 20:35:27.56 +60:08:08.29 (Adams et al. 2017)
        "SN 2008S": (308.688958, 60.099389),  # 20:34:45.35 +60:05:57.8 (ILRT; Prieto et al. 2008)
    },
}


def sep_arcsec(c, ra, dec):
    return np.hypot((c.ra - ra) * np.cos(np.radians(dec)), c.dec - dec) * 3600


def aligned(lc: pd.DataFrame, band: int) -> pd.DataFrame:
    lb = lc[lc.band == band].sort_values("mjd").copy()
    rf = lb.groupby("season").ref_flux.first().to_dict()
    lb["f"] = metrics.align_seasons(lb.flux.to_numpy(), lb.season.to_numpy(), rf)
    early = lb.mjd < EARLY_MJD
    w = 1 / lb.err[early] ** 2
    lb["df"] = lb.f - np.sum(w * lb.f[early]) / np.sum(w)  # change relative to WISE 2010-2011
    lb["df_mjy"] = flux_to_mjy(lb.df, band)
    lb["err_mjy"] = flux_to_mjy(lb.err, band)
    return lb


def forced_at(galaxy: str, ra: float, dec: float, tiles: list[str]) -> pd.DataFrame:
    """Forced photometry at an arbitrary position (for objects with no candidate, e.g. BH1)."""
    wd = fetch.cache_root() / "work" / galaxy
    rows = []
    for tile in tiles:
        for band in (1, 2):
            d = tile_dir(wd, tile, band)
            meta = json.loads((d / "meta.json").read_text())
            wcs = WCS(meta["wcs"])
            x, y = wcs.all_world2pix([[ra, dec]], 0)[0]
            D = np.load(d / "D.npy", mmap_mode="r")
            S = np.load(d / "S.npy", mmap_mode="r")
            sc = np.load(d / "scale.npy")
            season = np.array(meta["season"])
            psfs = {s: np.load(d / f"psf_s{s}.npy") for s in set(meta["season"])}
            k = sc[:, int(round(y)) // 8, int(round(x)) // 8]
            f, e = photometry.forced_lightcurve(D, S, psfs, season, x, y, k)
            rf = {s: photometry.reference_flux(np.load(d / f"ref_s{s}.npy"), np.load(d / f"refvar_s{s}.npy"), psfs[s], x, y)[0] for s in psfs}
            rows.append(pd.DataFrame(dict(band=band, epoch=meta["epochs"], mjd=meta["mjd"], season=season, flux=f, err=e,
                                          ref_flux=[rf[int(s)] for s in season])))
    return pd.concat(rows, ignore_index=True)


def null_distribution(galaxy: str, tile: str, ra: float, dec: float, n: int = 300, seed: int = 1) -> dict:
    """The same late-vs-2010 statistic at random positions at a similar elliptical radius (+-0.15)
    in the galaxy, away from candidates: how often does an empty spot look like the target?"""
    from oddsky.imaging.galaxies import GALAXIES

    gal = GALAXIES[galaxy]
    r0 = float(gal.ellipse_r(ra, dec))
    rng = np.random.default_rng(seed)
    gra, gdec = gal.grid(0.002)
    rr = gal.ellipse_r(gra, gdec)
    sel = np.nonzero(np.abs(rr - r0) < 0.15)[0]
    pick = rng.choice(sel, min(n, sel.size), replace=False)
    stats = {1: [], 2: []}
    for k in pick:
        lc = forced_at(galaxy, gra[k], gdec[k], [tile])
        for b in (1, 2):
            a = aligned(lc, b)
            m = metrics.band_metrics(a.mjd, a.f, a.err, a.season)
            if "delta_late_sig" in m and np.isfinite(m["delta_late_sig"]):
                stats[b].append((m["delta_late_sig"], m["delta_neo_sig"]))
    out = {}
    for b in (1, 2):
        out[f"w{b}"] = {}
        for j, key in enumerate(("delta_late_sig", "delta_neo_sig")):
            v = np.array(stats[b])[:, j]
            out[f"w{b}"][key] = dict(n=int(v.size), std=float(np.std(v)), mad_std=float(1.4826 * np.median(np.abs(v - np.median(v)))),
                                     p1_16_50_84_99=[float(x) for x in np.percentile(v, [1, 16, 50, 84, 99])],
                                     min=float(v.min()), frac_below_minus4=float(np.mean(v < -4)))
    return out


def null_on_sources(galaxy: str, tile: str, ra: float, dec: float, c: pd.DataFrame, n: int = 300) -> dict:
    """The same statistic on reference-image sources (local maxima) whose W1 reference PSF flux is
    within a factor 2 of the target's, at elliptical radius within +-0.3, not candidates. A star-
    dependent systematic between the 2010-11 WISE and NEOWISE epochs (PSF, calibration) would show
    here as a shifted or widened distribution."""
    from scipy import ndimage

    from oddsky.imaging.galaxies import GALAXIES

    gal = GALAXIES[galaxy]
    wd = fetch.cache_root() / "work" / galaxy
    d = tile_dir(wd, tile, 1)
    meta = json.loads((d / "meta.json").read_text())
    wcs = WCS(meta["wcs"])
    ref = np.load(d / "ref_s0.npy")
    rv = np.load(d / "refvar_s0.npy")
    psf0 = np.load(d / "psf_s0.npy")
    x0, y0 = wcs.all_world2pix([[ra, dec]], 0)[0]
    f0 = photometry.reference_flux(ref, rv, psf0, x0, y0)[0]
    sm = ndimage.uniform_filter(ref, 3)
    pk = (sm == ndimage.maximum_filter(sm, 5))
    pk[:15, :] = pk[-15:, :] = pk[:, :15] = pk[:, -15:] = False
    ys, xs = np.nonzero(pk)
    pra, pdec = wcs.all_pix2world(xs, ys, 0)
    r0 = float(gal.ellipse_r(ra, dec))
    keep = (np.abs(gal.ellipse_r(pra, pdec) - r0) < 0.3) & (np.hypot(xs - x0, ys - y0) > 5)
    for cra, cdec in zip(c.ra, c.dec, strict=True):
        keep &= np.hypot((pra - cra) * np.cos(np.radians(cdec)), pdec - cdec) * 3600 > 8
    idx = np.nonzero(keep)[0]
    fl = np.array([photometry.reference_flux(ref, rv, psf0, xs[k], ys[k])[0] for k in idx])
    ok = idx[(fl > 0.5 * f0) & (fl < 2 * f0)]
    rng = np.random.default_rng(2)
    ok = rng.choice(ok, min(n, ok.size), replace=False)
    stats = {1: [], 2: []}
    for k in ok:
        lc = forced_at(galaxy, pra[k], pdec[k], [tile])
        for b in (1, 2):
            a = aligned(lc, b)
            m = metrics.band_metrics(a.mjd, a.f, a.err, a.season)
            if np.isfinite(m.get("delta_late_sig", np.nan)):
                stats[b].append((m["delta_late_sig"], m["delta_neo_sig"]))
    out = dict(target_w1_ref_flux=float(f0), n_sources=int(ok.size))
    for b in (1, 2):
        out[f"w{b}"] = {}
        for j, key in enumerate(("delta_late_sig", "delta_neo_sig")):
            v = np.array(stats[b])[:, j]
            out[f"w{b}"][key] = dict(n=int(v.size), median=float(np.median(v)), mad_std=float(1.4826 * np.median(np.abs(v - np.median(v)))),
                                     min=float(v.min()), max=float(v.max()))
    return out


def ranks(c: pd.DataFrame, i: int) -> dict:
    row = c.loc[i]
    var = c[c.cls != "not-variable"]
    return dict(
        n_candidates=len(c), n_variable=len(var),
        rank_ds1_score=int((c.ds1_score > row.ds1_score).sum() + 1),
        rank_var_sig=int((c.var_sig > row.var_sig).sum() + 1),
        rank_in_class=int(((c.cls == row.cls) & (c.ds1_score > row.ds1_score)).sum() + 1),
        n_in_class=int((c.cls == row.cls).sum()),
        rank_vanish_w2=int((c.w2_vanish_frac.fillna(-9) > row.w2_vanish_frac).sum() + 1) if np.isfinite(row.w2_vanish_frac) else None,
    )


def compare_published(lcs: dict[int, pd.DataFrame]) -> dict:
    pub = pd.read_csv(PUBLISHED)
    pub = pub[pub.instrument == "NEOWISE"]
    out = {}
    for b in (1, 2):
        p = pub[pub["filter"] == f"W{b}"].sort_values("MJD")
        p = p.assign(dpub=p.flux_mJy - p.flux_mJy[p.MJD < EARLY_MJD].mean())
        ours = lcs[b]
        j = [int(np.argmin(np.abs(ours.mjd.to_numpy() - t))) for t in p.MJD]
        dt = np.abs(ours.mjd.to_numpy()[j] - p.MJD.to_numpy())
        m = dt < 10
        a, e = ours.df_mjy.to_numpy()[j][m], ours.err_mjy.to_numpy()[j][m]
        q = p.dpub.to_numpy()[m]
        slope = float(np.sum(a * q / e**2) / np.sum(q**2 / e**2))
        resid = a - q
        out[f"W{b}"] = dict(
            n_matched=int(m.sum()), pearson_r=float(np.corrcoef(a, q)[0, 1]), slope_ours_vs_published=slope,
            rms_resid_mjy=float(np.sqrt(np.mean(resid**2))), median_err_mjy=float(np.median(e)),
            chi2r_vs_published=float(np.mean((resid / e) ** 2)),
            published_peak=dict(mjd=float(p.MJD.iloc[np.argmax(p.dpub)]), dmjy=float(p.dpub.max())),
            ours_peak=dict(mjd=float(ours.mjd.iloc[np.argmax(ours.df_mjy)]), dmjy=float(ours.df_mjy.max())),
            ours_last=dict(mjd=float(ours.mjd.iloc[-1]), dmjy=float(ours.df_mjy.iloc[-1]), err=float(ours.err_mjy.iloc[-1])),
            published_last=dict(mjd=float(p.MJD.iloc[-1]), dmjy=float(p.dpub.iloc[-1])),
        )
    return out


def cutout(arr, x, y, h=20):
    xi, yi = int(round(x)), int(round(y))
    return np.asarray(arr[max(0, yi - h) : yi + h + 1, max(0, xi - h) : xi + h + 1])


def figure_object(galaxy: str, name: str, tile: str, ra: float, dec: float, lcs: dict, path: Path,
                  published: bool = False, panel_epochs=None):
    wd = fetch.cache_root() / "work" / galaxy
    band = 2
    d = tile_dir(wd, tile, band)
    meta = json.loads((d / "meta.json").read_text())
    x, y = WCS(meta["wcs"]).all_world2pix([[ra, dec]], 0)[0]
    D = np.load(d / "D.npy", mmap_mode="r")
    S = np.load(d / "S.npy", mmap_mode="r")
    ref = np.load(d / "ref_s0.npy", mmap_mode="r")
    mjd = np.array(meta["mjd"])
    if panel_epochs is None:
        targets = [55300, 56700, 57200, 57600, 57760, 58120, 58700, 59400, 60100]
        panel_epochs = sorted({int(np.argmin(np.abs(mjd - t))) for t in targets})
    n = len(panel_epochs)
    fig = plt.figure(figsize=(12, 7.2), facecolor="#fcfcfb")
    gs = fig.add_gridspec(2, n + 2, height_ratios=[1, 1.25], hspace=0.35, wspace=0.08)
    ax = fig.add_subplot(gs[0, 0])
    c = cutout(ref, x, y)
    v = np.nanpercentile(c, [1, 99.5])
    ax.imshow(c, origin="lower", cmap="Greys", vmin=v[0], vmax=v[1])
    ax.plot([20], [20], marker="+", ms=18, mew=1.2, color=W2C)
    ax.set_title(f"W2 ref.\n{c.shape[0] * 2.75 / 60:.1f}'", fontsize=9, color=INK)
    ax.set_xticks([]), ax.set_yticks([])
    sp = tile_dir(wd, tile, 1) / "stack_neo-early.npy"
    if sp.exists():  # the stacked channel: (NEOWISE mean - 2010-11 mean), W1, in sigma
        meta1 = json.loads((tile_dir(wd, tile, 1) / "meta.json").read_text())
        x1, y1 = WCS(meta1["wcs"]).all_world2pix([[ra, dec]], 0)[0]
        comb, csig = np.load(sp)
        a2 = fig.add_subplot(gs[0, 1])
        a2.imshow(cutout(comb / csig, x1, y1), origin="lower", cmap="RdBu_r", vmin=-6, vmax=6)
        a2.plot([20], [20], marker="o", ms=14, mfc="none", mec=INK, mew=0.6, alpha=0.6)
        a2.set_title("W1 stack\nNEO\u22122010", fontsize=9, color=INK)
        a2.set_xticks([]), a2.set_yticks([])
    sig = np.nanmedian(np.asarray(S[panel_epochs[0]]))
    lim = 6 * sig
    for k, i in enumerate(panel_epochs):
        a = fig.add_subplot(gs[0, k + 2]) if k + 2 < n + 2 else None
        if a is None:
            break
        a.imshow(cutout(D[i], x, y), origin="lower", cmap="RdBu_r", vmin=-lim, vmax=lim)
        a.set_xticks([]), a.set_yticks([])
        yr = 1858.87 + mjd[i] / 365.25
        a.set_title(f"{yr:.1f}", fontsize=9, color=INK)
        a.plot([20], [20], marker="o", ms=14, mfc="none", mec=INK, mew=0.6, alpha=0.6)
    if len(panel_epochs) > n:
        pass
    axl = fig.add_subplot(gs[1, :])
    for b, col in ((1, W1C), (2, W2C)):
        lb = lcs[b]
        axl.errorbar(lb.mjd, lb.df_mjy, lb.err_mjy, fmt="o-", ms=5, lw=1.5, color=col, mec="#fcfcfb", mew=1,
                     capsize=0, label=f"W{b}, this pipeline (blind)")
    if published and PUBLISHED.exists():
        pub = pd.read_csv(PUBLISHED)
        pub = pub[pub.instrument == "NEOWISE"]
        axl.axvspan(pub.MJD.max() + 30, mjd.max() + 60, color="#f0efec", zorder=0)
        axl.text(pub.MJD.max() + 60, 0.97, "after the published light curve", transform=axl.get_xaxis_transform(),
                 fontsize=8, color=MUTED, va="top")
        for b, col in ((1, W1C), (2, W2C)):
            p = pub[pub["filter"] == f"W{b}"]
            dp = p.flux_mJy - p.flux_mJy[p.MJD < EARLY_MJD].mean()
            axl.plot(p.MJD, dp, ls="none", marker="s", ms=8, mfc="none", mec=col, mew=1.1, alpha=0.9,
                     label=f"W{b}, De et al. 2024 (ZOGY)")
    axl.axhline(0, color=MUTED, lw=0.6)
    axl.set_xlabel("MJD", color=INK)
    axl.set_ylabel("flux change since 2010-11 (mJy)", color=INK)
    sec = axl.secondary_xaxis("top", functions=(lambda m: 1858.87 + m / 365.25, lambda yr: (yr - 1858.87) * 365.25))
    sec.set_xlabel("year", color=MUTED)
    for s in ("right",):
        axl.spines[s].set_visible(False)
    axl.grid(alpha=0.25, lw=0.5)
    axl.legend(frameon=False, fontsize=8, ncol=2, loc="best")
    fig.suptitle(f"{name} in {galaxy}: stacked W1 (NEOWISE mean \u2212 2010-11, pixel S/N) and W2 single-epoch difference "
                 f"images (epoch \u2212 its season's median; red brighter, blue fainter, \u00b16\u03c3); forced-photometry light curve",
                 fontsize=9.5, color=INK)
    fig.savefig(path, dpi=150, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)


def figure_metric_plane(c: pd.DataFrame, highlight: dict, path: Path, title: str):
    order = ["lpv-like", "irregular", "rise-then-fade", "fading", "brightening", "transient", "season-locked"]
    cols = ["#2a78d6", "#c3c2b7", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#6250d6"]
    fig, ax = plt.subplots(figsize=(7.5, 5.2), facecolor="#fcfcfb")
    eta = np.nanmin(np.c_[c.w1_eta, c.w2_eta], axis=1)
    dl = np.nanmax(np.abs(np.c_[c.w1_delta_late_sig, c.w2_delta_late_sig]), axis=1)
    for cls, col in zip(order, cols, strict=True):
        m = (c.cls == cls).to_numpy()
        if m.any():
            ax.scatter(eta[m], dl[m], s=10, color=col, alpha=0.75, lw=0, label=f"{cls} ({m.sum()})")
    for name, i in highlight.items():
        ax.scatter(eta[i], dl[i], s=160, marker="*", color=INK, zorder=5)
        ax.annotate(name, (eta[i], dl[i]), xytext=(8, 6), textcoords="offset points", fontsize=9, color=INK)
    ax.set_yscale("log")
    ax.set_xlabel("von Neumann ratio η (smooth → visit-to-visit scatter)", color=INK)
    ax.set_ylabel("|late − 2010-11| significance (σ)", color=INK)
    ax.axvline(1.2, color=MUTED, lw=0.6, ls="--")
    ax.grid(alpha=0.25, lw=0.5)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    ax.set_title(title, fontsize=10, color=INK)
    fig.savefig(path, dpi=150, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)


def figure_gallery(c: pd.DataFrame, lcs: pd.DataFrame, path: Path, n: int = 12, title: str = ""):
    top = c.head(n)
    k = int(np.ceil(len(top) / 3))
    fig, axs = plt.subplots(k, 3, figsize=(12, 2.3 * k), sharex=True, facecolor="#fcfcfb")
    for ax, (_, r) in zip(axs.ravel(), top.iterrows(), strict=False):
        lc = lcs[lcs.group == r.group]
        for b, col in ((1, W1C), (2, W2C)):
            lb = aligned(lc, b)
            ax.errorbar(lb.mjd, lb.df_mjy, lb.err_mjy, fmt="o-", ms=3, lw=1, color=col, capsize=0)
        ax.axhline(0, color=MUTED, lw=0.5)
        flag = " dipole" if r.get("dipole", False) else ""
        ax.set_title(f"#{_ + 1} {r.ra:.4f} {r.dec:+.4f}  {r.cls}{flag}", fontsize=8, color=INK)
        ax.tick_params(labelsize=7)
        ax.spines[["top", "right"]].set_visible(False)
    for ax in axs.ravel()[len(top):]:
        ax.set_visible(False)
    fig.supylabel("flux change since 2010-11 (mJy); W1 blue, W2 orange", fontsize=9, color=INK)
    fig.supxlabel("MJD", fontsize=9, color=INK)
    fig.suptitle(title, fontsize=10, color=INK)
    fig.tight_layout()
    fig.savefig(path, dpi=130, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)


def main(galaxy: str):
    wd = fetch.cache_root() / "work" / galaxy
    c = pd.read_csv(wd / "candidates.csv")
    lcs = pd.read_parquet(wd / "lightcurves.parquet")
    figs = HERE / "figures"
    figs.mkdir(exist_ok=True)
    res = dict(galaxy=galaxy, n_candidates=len(c), classes=c.cls.value_counts().to_dict(),
               n_dipole=int(c.dipole.sum()), objects={})
    highlight = {}
    for name, (ra, dec) in KNOWN[galaxy].items():
        s = sep_arcsec(c, ra, dec)
        i = int(np.argmin(s))
        entry = dict(ra=ra, dec=dec, nearest_candidate_arcsec=float(s.iloc[i]))
        al = None
        if s.iloc[i] < 4.0:
            row = c.loc[i]
            highlight[name] = i
            entry.update(ranks(c, i))
            entry.update({k: (row[k].item() if hasattr(row[k], "item") else row[k]) for k in
                          ["cls", "cls_w1", "cls_w2", "gate_band", "band_agree", "channel", "stack_snr", "stack_names",
                           "ds1_score", "var_sig", "n_det", "n_det_w1", "n_det_w2", "max_snr", "min_snr",
                           "w1_eta", "w2_eta", "w1_n_turns", "w2_n_turns", "w1_delta_late_sig", "w2_delta_late_sig",
                           "w1_delta_neo_sig", "w2_delta_neo_sig",
                           "w1_vanish_frac", "w2_vanish_frac", "w1_ref_flux", "w2_ref_flux", "dipole", "tiles"] if k in row})
            lc = lcs[lcs.group == row.group]
            tile = lc.tile.iloc[0]
            al = {b: aligned(lc, b) for b in (1, 2)}
            entry["lightcurve"] = {f"W{b}": al[b][["epoch", "mjd", "season", "df_mjy", "err_mjy"]].round(4).to_dict("records") for b in (1, 2)}
            if name == "M31-2014-DS1" and PUBLISHED.exists():
                entry["vs_published"] = compare_published(al)
        if name in NULL_FOR:
            tiles = sorted({t for ts in c.tiles for t in str(ts).split(",")})
            lc = forced_at(galaxy, ra, dec, tiles[:1])
            tile = tiles[0]
            al = {b: aligned(lc, b) for b in (1, 2)}
            for b in (1, 2):
                m = metrics.band_metrics(al[b].mjd, al[b].f, al[b].err, al[b].season)
                entry[f"w{b}_forced"] = dict(chi2r=m.get("chi2r"), n_sig3=m.get("n_sig3"),
                                             median_err_mjy=float(np.median(al[b].err_mjy)),
                                             max_abs_change_mjy=float(np.nanmax(np.abs(al[b].df_mjy))),
                                             delta_late_mjy=float(flux_to_mjy(m.get("delta_late", np.nan), b)),
                                             delta_late_sig=m.get("delta_late_sig"),
                                             delta_neo_mjy=float(flux_to_mjy(m.get("delta_neo", np.nan), b)),
                                             delta_neo_sig=m.get("delta_neo_sig"))
            entry["lightcurve"] = {f"W{b}": al[b][["epoch", "mjd", "df_mjy", "err_mjy"]].round(4).to_dict("records") for b in (1, 2)}
            entry["null"] = null_distribution(galaxy, tile, ra, dec)
            entry["null_on_sources"] = null_on_sources(galaxy, tile, ra, dec, c)
        if al is None:  # not a candidate and no null requested: forced photometry for the figure
            tiles = sorted({t for ts in c.tiles for t in str(ts).split(",")})
            tile = tiles[0]
            lc = forced_at(galaxy, ra, dec, tiles[:1])
            al = {b: aligned(lc, b) for b in (1, 2)}
        res["objects"][name] = entry
        slug = name.replace(" ", "_").replace("-", "_")
        figure_object(galaxy, name, tile, ra, dec, al, figs / f"{galaxy}_{slug}.png", published=(name == "M31-2014-DS1"))
    figure_metric_plane(c, highlight, figs / f"{galaxy}_metric_plane.png",
                        f"{galaxy}: {len(c)} candidates (detected ≥ 5σ in ≥ 2 epochs, both seasons)")
    figure_gallery(c, lcs, figs / f"{galaxy}_top_ds1score.png", 15, f"{galaxy}: top 15 by DS1-likeness score")
    (HERE / "work" / f"acceptance_{galaxy}.json").write_text(json.dumps(res, indent=1, default=str))
    short = {k: {kk: vv for kk, vv in v.items() if kk != "lightcurve"} for k, v in res["objects"].items()}
    print(json.dumps(dict(classes=res["classes"], n=res["n_candidates"], n_dipole=res["n_dipole"], objects=short), indent=1, default=str))


if __name__ == "__main__":
    main(sys.argv[1])
