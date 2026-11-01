"""End-to-end difference-imaging run over one galaxy.

    python -m oddsky.imaging.pipeline M31 [--tiles T1 T2] [--workdir DIR] [--stage all|diff|cands]

Per tile and band (stage `diff`): load the epoch stack over the galaxy's window, build per-season
references (absolute season labels), empirical PSFs and masks, write difference (D) and noise (S)
stacks as .npy memmaps (full-season reference: one zero point per season), and detect in two
channels: (1) >= `thresh` sigma peaks in every epoch, against a leave-one-out reference; (2) the
reference-free season stacks NEOWISE-mean minus 2010-11 and last-1.5-yr minus 2010-11. Then (stage
`cands`): group detections across epochs, bands and overlapping tiles; a candidate needs >= 2 epoch
detections from both seasons OR a stacked detection; forced PSF photometry in W1 and W2 at every
epoch; per-band variability metrics and classes.

Outputs in <workdir>/<galaxy>/: detections.parquet, candidates.csv, lightcurves.parquet, and per
tile/band: D.npy, S.npy, scale.npy (noise factors on an 8x-binned grid), ref_s{0,1}.npy,
refvar_s{0,1}.npy, psf_s{0,1}.npy, mask.npy, stack_{neo-early,late-early}.npy, meta.json (with the
unWISE build of every epoch).
"""

from __future__ import annotations

import argparse
import gc
import json
import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from astropy.wcs import WCS
from scipy import ndimage

from . import PIXSCALE, ZP_VEGA, detect, diff, fetch, metrics, photometry, psf, tiles
from .galaxies import GALAXIES, Galaxy
from .stack import load_stack

log = logging.getLogger("oddsky.imaging")
SCALE_BIN = 8


@dataclass
class Config:
    bands: tuple = (1, 2)
    thresh: float = 5.0  # detection threshold, calibrated sigma
    min_epochs: int = 2  # distinct (band, epoch) detections for a candidate
    both_seasons: bool = True  # detections must come from both visit seasons (independent references)
    half: int = 2  # kernel half-size (5x5)
    block: int = 512  # kernel fitting block (px)
    box: int = 64  # noise-calibration box (px)
    group_arcsec: float = 4.0  # friends-of-friends linking length across epochs/bands
    bright_mag: dict = field(default_factory=lambda: {1: 10.0, 2: 9.5})  # mask stars brighter than this
    psf_peak_max: float = 2.0e4  # PSF stars must have peak pixels below this (unsaturated)
    ref_mjd_max: float | None = None  # None: per-season median of all epochs
    margin: int = 40  # px around the search ellipse's bounding box
    bkg_box: int = 24  # mesh background subtracted from each difference image (0 = off)
    unwise_mask: bool = True  # also mask unWISE bitmask artefacts (bright stars, ghosts, latents, spikes)
    loo: bool = True  # single-epoch detection against a leave-one-out median reference
    stack_channel: bool = True  # stacked (NEOWISE - 2010, late - 2010) detection channel
    stack_thresh: float = 5.0  # calibrated sigma in the season-combined stack
    stack_season_min: float = 2.0  # each season's stack must agree in sign at this significance


def window_for(gal: Galaxy, tile: str, margin: int) -> tuple[int, int, int, int] | None:
    w = tiles.wcs_for(tile)
    ra, dec = gal.boundary(720)
    gra, gdec = gal.grid(0.05)
    x, y = w.all_world2pix(np.r_[ra, gra], np.r_[dec, gdec], 0)
    inside = (x > -0.5) & (x < 2047.5) & (y > -0.5) & (y < 2047.5)
    if not inside.any():
        return None
    x0, x1 = int(max(0, np.floor(x.min()) - margin)), int(min(2048, np.ceil(x.max()) + margin + 1))
    y0, y1 = int(max(0, np.floor(y.min()) - margin)), int(min(2048, np.ceil(y.max()) + margin + 1))
    if x1 - x0 < 64 or y1 - y0 < 64:
        return None
    return y0, y1, x0, x1


def galaxy_tiles(gal: Galaxy) -> list[str]:
    ra, dec = gal.boundary(720)
    gra, gdec = gal.grid(0.05)
    return tiles.tiles_covering(np.r_[ra, gra], np.r_[dec, gdec])


def flux_of_mag(m: float) -> float:
    return 10 ** ((ZP_VEGA - m) / 2.5)


def tile_dir(workdir: Path, tile: str, band: int) -> Path:
    return workdir / tile / f"w{band}"


EARLY_MJD = metrics.EARLY_MJD  # WISE 2010-11
NEO_MJD = 56600.0  # NEOWISE-R from 2013 Dec
LATE_SPAN = 550.0  # "late" = the last ~1.5 yr (3-4 epochs)


def build_masks(st, gal: Galaxy, cfg: Config, ref0: np.ndarray, refvar0: np.ndarray):
    """(invalid, bright, nucleus, outside) boolean masks on the stack's window."""
    ny, nx = ref0.shape
    invalid = ~np.isfinite(refvar0)
    bright = detect.bright_star_mask(ref0, refvar0, flux_of_mag(cfg.bright_mag[st.band]))
    if cfg.unwise_mask and st.tile:
        from astropy.io import fits as _fits

        y0, y1, x0, x1 = st.window
        msk = _fits.getdata(fetch.fetch_mask(st.tile))[y0:y1, x0:x1]
        artefact = (msk.astype(np.int64) & fetch.ARTIFACT_BITS) != 0
        bright |= ndimage.binary_dilation(artefact, iterations=2)
    xn, yn = st.wcs.all_world2pix([[gal.ra, gal.dec]], 0)[0]
    nucleus = detect.circle_mask(ref0.shape, xn, yn, gal.nucleus_mask_arcsec / PIXSCALE)
    for mra, mdec, mrad in gal.extra_masks:
        xm, ym = st.wcs.all_world2pix([[mra, mdec]], 0)[0]
        nucleus |= detect.circle_mask(ref0.shape, xm, ym, mrad / PIXSCALE)
    yy, xx = np.mgrid[0:ny:4, 0:nx:4]
    ra_g, dec_g = st.wcs.all_pix2world(xx.ravel(), yy.ravel(), 0)
    outside = ~gal.inside(ra_g, dec_g).reshape(xx.shape)
    outside = np.repeat(np.repeat(outside, 4, 0), 4, 1)[:ny, :nx]
    return invalid, bright, nucleus, outside


def stack_channel(acc: dict, psfs: dict, noise_mask, det_mask, cfg: Config):
    """Reference-free stacks: within a season the reference cancels in (mean of set A) - (mean of
    set B) of the difference images. Pairs: NEOWISE-era mean minus 2010-11 ('neo-early') and the
    last ~1.5 yr minus 2010-11 ('late-early'). Seasons are combined by inverse variance; a peak
    must reach cfg.stack_thresh in the combined S/N map AND agree in sign at >= cfg.stack_season_min
    in every season that has both sets (two independent measurements). Returns
    {name: (combined diff, combined sigma, snr, peaks DataFrame-ready list)}."""
    out = {}
    for name, (A, B) in {"neo-early": ("neo", "early"), "late-early": ("late", "early")}.items():
        per = []
        for s in sorted(psfs):
            na, da = acc.get((s, A), (None, None))
            nb, db = acc.get((s, B), (None, None))
            if na is None or nb is None:
                continue
            with np.errstate(all="ignore"):
                d = na / da - nb / db
                v = 1 / da + 1 / db
            ok = (da > 0) & (db > 0)
            d = np.where(ok, d, np.nan).astype(np.float32)
            sg = np.where(ok, np.sqrt(v), np.nan).astype(np.float32)
            snr_s, *_ = detect.snr_map(d, sg, psfs[s], mask=noise_mask, box=cfg.box)
            per.append((s, d, sg, snr_s))
        if not per:
            continue
        w = [np.where(np.isfinite(sg), 1 / sg**2, 0) for _, _, sg, _ in per]
        wsum = np.sum(w, axis=0)
        with np.errstate(all="ignore"):
            comb = np.sum([np.where(np.isfinite(d), d, 0) * wi for (_, d, _, _), wi in zip(per, w, strict=True)], axis=0) / wsum
            csig = 1 / np.sqrt(wsum)
        comb = np.where(wsum > 0, comb, np.nan).astype(np.float32)
        csig = np.where(wsum > 0, csig, np.nan).astype(np.float32)
        pmean = np.mean([psfs[s] for s, *_ in per], axis=0)
        snr, F, E, _ = detect.snr_map(comb, csig, pmean, mask=noise_mask, box=cfg.box)
        x, y, v = detect.find_peaks(snr, cfg.stack_thresh, mask=det_mask)
        keep = []
        for k in range(x.size):
            xi, yi = int(round(x[k])), int(round(y[k]))
            ok = all(np.isfinite(sn[yi, xi]) and np.sign(sn[yi, xi]) == np.sign(v[k]) and abs(sn[yi, xi]) >= cfg.stack_season_min
                     for _, _, _, sn in per)
            if ok and len(per) >= (2 if cfg.both_seasons else 1):
                keep.append((x[k], y[k], v[k], F[yi, xi], E[yi, xi]))
        out[name] = (comb, csig, snr, keep)
    return out


def analyse_stack(st, gal: Galaxy, cfg: Config, out: Path | None = None, inject=None):
    """Difference imaging + both detection channels on an in-memory EpochStack.

    Detection (single-epoch channel) uses a LEAVE-ONE-OUT median reference, so an epoch never
    subtracts itself; photometry products (D, S) use the full-season median with the same kernel,
    so every epoch of a season shares one zero point (what long-term light curves need).
    `inject(st)` may modify st.img in place before anything is computed (completeness tests).
    Returns (detections DataFrame, products dict). With `out`, products are written to disk."""
    n, ny, nx = st.img.shape
    if inject is not None:
        inject(st)
    refs = diff.references(st.img, st.ivar, st.season, st.mjd, cfg.ref_mjd_max)
    ref0, refvar0 = refs[min(refs)]
    invalid, bright, nucleus, outside = build_masks(st, gal, cfg, ref0, refvar0)
    noise_mask = invalid | bright | nucleus
    det_mask = noise_mask | outside
    psfs = {}
    for s, (r, rv) in refs.items():
        try:
            stars = psf.find_stars(r, np.where(np.isfinite(rv), 1 / rv, 0), mask=bright | nucleus,
                                   flux_max=cfg.psf_peak_max)
            psfs[s] = psf.build_psf(r, stars)
            log.info("%s W%d season %d: PSF from %d stars, FWHM %.2f px", st.tile, st.band, s, len(stars), psf.fwhm(psfs[s]))
        except ValueError as e:
            log.warning("%s W%d season %d: %s; Gaussian PSF", st.tile, st.band, s, e)
            psfs[s] = psf.gaussian_psf(2.3 if st.band == 1 else 2.5)
    floors = {s: diff.residual_floor(r) for s, (r, _) in refs.items()}
    loo = {}
    if cfg.loo:
        for s in refs:
            sel = np.nonzero(st.season == s)[0]
            if cfg.ref_mjd_max is None and sel.size >= 3:
                lm = diff.loo_medians(st.img[sel], st.ivar[sel])
                loo.update({int(i): lm[k] for k, i in enumerate(sel)})
    if out is not None:
        out.mkdir(parents=True, exist_ok=True)
        np.save(out / "mask.npy", np.packbits(det_mask))
        for s, (r, rv) in refs.items():
            np.save(out / f"psf_s{s}.npy", psfs[s])
            np.save(out / f"ref_s{s}.npy", r)
            np.save(out / f"refvar_s{s}.npy", rv)
        D = np.lib.format.open_memmap(out / "D.npy", mode="w+", dtype=np.float32, shape=(n, ny, nx))
        S = np.lib.format.open_memmap(out / "S.npy", mode="w+", dtype=np.float32, shape=(n, ny, nx))
    else:
        D = np.empty((n, ny, nx), np.float32)
        S = np.empty((n, ny, nx), np.float32)
    scale = np.zeros((n, -(-ny // SCALE_BIN), -(-nx // SCALE_BIN)), np.float32)
    late_cut = st.mjd.max() - LATE_SPAN
    sets = {"early": st.mjd < EARLY_MJD, "neo": st.mjd > NEO_MJD, "late": st.mjd >= late_cut}
    acc: dict = {}
    rows = []
    for i in range(n):
        s = int(st.season[i])
        r, rv = refs[s]
        d, sg, kern = diff.difference(st.img[i], st.ivar[i], r, rv, use=~(bright | invalid), half=cfg.half,
                                      block=cfg.block, floor=floors[s])
        if cfg.bkg_box:
            d = d - diff.background_mesh(d, sg, cfg.bkg_box)
        D[i], S[i] = d, sg
        snr_c, F, E, c = detect.snr_map(d, sg, psfs[s], mask=noise_mask, box=cfg.box)
        scale[i] = c[::SCALE_BIN, ::SCALE_BIN]
        w = np.where(np.isfinite(d) & np.isfinite(sg), 1 / np.where(np.isfinite(sg), sg, 1) ** 2, 0).astype(np.float32)
        dz = np.where(w > 0, d, 0).astype(np.float32)
        for name, m in sets.items():
            if m[i]:
                num, den = acc.get((s, name), (np.zeros((ny, nx), np.float32), np.zeros((ny, nx), np.float32)))
                acc[(s, name)] = (num + dz * w, den + w)
        if i in loo:  # detection on the leave-one-out difference
            nsea = int((st.season == s).sum())
            dl, sl_, _ = diff.difference(st.img[i], st.ivar[i], loo[i], rv * nsea / max(nsea - 1, 1),
                                         half=cfg.half, block=cfg.block, floor=floors[s], kernels=kern)
            if cfg.bkg_box:
                dl = dl - diff.background_mesh(dl, sl_, cfg.bkg_box)
            snr, F, E, _ = detect.snr_map(dl, sl_, psfs[s], mask=noise_mask, box=cfg.box)
        else:
            snr = snr_c
        x, y, v = detect.find_peaks(snr, cfg.thresh, mask=det_mask)
        if x.size:
            ra, dec = st.wcs.all_pix2world(x, y, 0)
            xi, yi = np.round(x).astype(int), np.round(y).astype(int)
            rows.append(pd.DataFrame(dict(
                tile=st.tile, band=st.band, channel="epoch", epoch=int(st.epochs[i]), idx=i, mjd=st.mjd[i], season=s,
                x=x, y=y, ra=ra, dec=dec, snr=v, flux=F[yi, xi], err=E[yi, xi])))
    del loo
    stacks = stack_channel(acc, psfs, noise_mask, det_mask, cfg) if cfg.stack_channel else {}
    for name, (comb, csig, _snr, keep) in stacks.items():
        if keep:
            k = np.array(keep)
            ra, dec = st.wcs.all_pix2world(k[:, 0], k[:, 1], 0)
            rows.append(pd.DataFrame(dict(
                tile=st.tile, band=st.band, channel=name, epoch=-1, idx=-1, mjd=np.nan, season=-1,
                x=k[:, 0], y=k[:, 1], ra=ra, dec=dec, snr=k[:, 2], flux=k[:, 3], err=k[:, 4])))
        if out is not None:
            np.save(out / f"stack_{name}.npy", np.stack([comb, csig]))
    if out is not None:
        D.flush()
        S.flush()
        np.save(out / "scale.npy", scale)
    dets = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    products = dict(D=D, S=S, scale=scale, psfs=psfs, refs=refs, det_mask=det_mask, stacks=stacks)
    return dets, products


def process_tile_band(gal: Galaxy, tile: str, band: int, workdir: Path, cfg: Config) -> pd.DataFrame:
    t0 = time.time()
    win = window_for(gal, tile, cfg.margin)
    if win is None:
        return pd.DataFrame()
    st = load_stack(tile, band, window=win)
    out = tile_dir(workdir, tile, band)
    log.info("%s W%d: %d epochs, window %s", tile, band, st.n, win)
    dets, prod = analyse_stack(st, gal, cfg, out)
    meta = dict(tile=tile, band=band, window=list(win), epochs=st.epochs.tolist(), mjd=st.mjd.tolist(),
                season=st.season.tolist(), season_scheme="absolute (solar elongation side)", builds=st.builds,
                wcs=dict(st.wcs.to_header()), galaxy=gal.name, config=asdict(cfg))
    (out / "meta.json").write_text(json.dumps(meta, default=str))
    nstack = int((dets.channel != "epoch").sum()) if len(dets) else 0
    log.info("%s W%d: %d detections (%d stacked) in %.0f s", tile, band, len(dets), nstack, time.time() - t0)
    del st, prod
    gc.collect()
    return dets


def candidates_from(dets: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """Group detections on the sky. A group is a candidate if EITHER the single-epoch channel saw
    it in >= min_epochs distinct (band, epoch) images from both visit seasons, OR the stacked
    channel (which already demands agreement of both seasons) detected it in either band."""
    if dets.empty:
        return pd.DataFrame()
    dets = dets.copy()
    if "channel" not in dets:
        dets["channel"] = "epoch"
    dets["group"] = detect.group(dets.ra.to_numpy(), dets.dec.to_numpy(), cfg.group_arcsec)
    dets["w"] = dets.snr.abs()
    rows = []
    for gid, g in dets.groupby("group"):
        ge = g[g.channel == "epoch"]
        gs = g[g.channel != "epoch"]
        ep = set(zip(ge.band, ge.epoch, strict=True))
        epoch_ok = len(ep) >= cfg.min_epochs and (not cfg.both_seasons or ge.season.nunique() >= 2)
        stack_ok = len(gs) > 0
        if not (epoch_ok or stack_ok):
            continue
        use = g if epoch_ok and stack_ok else (ge if epoch_ok else gs)
        w = use.w.to_numpy()
        rows.append(dict(
            group=gid, ra=float(np.sum(use.ra * w) / w.sum()), dec=float(np.sum(use.dec * w) / w.sum()),
            channel="both" if (epoch_ok and stack_ok) else ("epoch" if epoch_ok else "stack"),
            n_det=len(ep), n_det_w1=len({e for b, e in ep if b == 1}), n_det_w2=len({e for b, e in ep if b == 2}),
            max_snr=float(ge.snr.max()) if len(ge) else np.nan, min_snr=float(ge.snr.min()) if len(ge) else np.nan,
            n_pos=int((ge.snr > 0).sum()), n_neg=int((ge.snr < 0).sum()),
            stack_snr=float(gs.snr.iloc[np.argmax(gs.snr.abs().to_numpy())]) if len(gs) else np.nan,
            stack_names=",".join(sorted({f"{c}:W{b}" for c, b in zip(gs.channel, gs.band, strict=True)})),
            tiles=",".join(sorted(set(g.tile)))))
    return pd.DataFrame(rows)


def _load_tile(workdir: Path, tile: str, band: int):
    d = tile_dir(workdir, tile, band)
    meta = json.loads((d / "meta.json").read_text())
    wcs = WCS(meta["wcs"])
    D = np.load(d / "D.npy", mmap_mode="r")
    S = np.load(d / "S.npy", mmap_mode="r")
    scale = np.load(d / "scale.npy")
    seasons = sorted(set(meta["season"]))
    psfs = {s: np.load(d / f"psf_s{s}.npy") for s in seasons}
    refs = {s: (np.load(d / f"ref_s{s}.npy", mmap_mode="r"), np.load(d / f"refvar_s{s}.npy", mmap_mode="r")) for s in seasons}
    return meta, wcs, D, S, scale, psfs, refs


def photometer(cands: pd.DataFrame, workdir: Path, tile_list: list[str], bands=(1, 2)) -> pd.DataFrame:
    """Forced photometry of every candidate in both bands, on the tile where it sits furthest from
    the window edge. Long-format light curves with diff and reference fluxes (nanomaggies)."""
    if cands.empty:
        return pd.DataFrame()
    # choose a home tile per candidate (by W1 window geometry)
    home = np.full(len(cands), "", object)
    best = np.full(len(cands), -1.0)
    for tile in tile_list:
        mp = tile_dir(workdir, tile, bands[0]) / "meta.json"
        if not mp.exists():
            continue
        meta = json.loads(mp.read_text())
        x, y = WCS(meta["wcs"]).all_world2pix(cands.ra.to_numpy(), cands.dec.to_numpy(), 0)
        y0, y1, x0, x1 = meta["window"]
        edge = np.minimum.reduce([x, y, (x1 - x0) - 1 - x, (y1 - y0) - 1 - y])
        better = edge > best
        home[better], best[better] = tile, edge[better]
    rows = []
    for tile in tile_list:
        sel = np.nonzero((home == tile) & (best > 13))[0]
        if sel.size == 0:
            continue
        for band in bands:
            meta, wcs, D, S, scale, psfs, refs = _load_tile(workdir, tile, band)
            season = np.array(meta["season"])
            x, y = wcs.all_world2pix(cands.ra.to_numpy()[sel], cands.dec.to_numpy()[sel], 0)
            for k, i in enumerate(sel):
                xi, yi = x[k], y[k]
                sc = scale[:, min(int(round(yi)) // SCALE_BIN, scale.shape[1] - 1), min(int(round(xi)) // SCALE_BIN, scale.shape[2] - 1)]
                f, e = photometry.forced_lightcurve(D, S, psfs, season, xi, yi, sc)
                rf = {s: photometry.reference_flux(np.asarray(r), np.asarray(rv), psfs[s], xi, yi) for s, (r, rv) in refs.items()}
                rows.append(pd.DataFrame(dict(
                    group=int(cands.group.iloc[i]), tile=tile, band=band, epoch=meta["epochs"], mjd=meta["mjd"],
                    season=season, flux=f, err=e, ref_flux=[rf[int(s)][0] for s in season],
                    ref_err=[rf[int(s)][1] for s in season], x=xi, y=yi)))
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def score(cands: pd.DataFrame, lcs: pd.DataFrame) -> pd.DataFrame:
    recs = []
    for gid, lc in lcs.groupby("group"):
        m = {}
        for b in (1, 2):
            lb = lc[lc.band == b].sort_values("mjd")
            rf = lb.groupby("season").ref_flux.first().to_dict()
            f_al = metrics.align_seasons(lb.flux.to_numpy(), lb.season.to_numpy(), rf)
            m[b] = metrics.band_metrics(lb.mjd.to_numpy(), f_al, lb.err.to_numpy(), lb.season.to_numpy())
            m[b]["ref_flux"] = float(np.nanmedian(lb.ref_flux)) if len(lb) else np.nan
        rec = dict(group=gid, **metrics.classify_bands(m[1], m[2]))
        for b in (1, 2):
            for k, v in m[b].items():
                rec[f"w{b}_{k}"] = v
        recs.append(rec)
    out = cands.merge(pd.DataFrame(recs), on="group", how="left")
    with np.errstate(all="ignore"):
        out["var_sig"] = np.sqrt(np.nanmax(np.c_[out.get("w1_chi2r", np.nan), out.get("w2_chi2r", np.nan)], axis=1))
        for b in (1, 2):
            # fraction of the early (2010-11) flux gone by the last three epochs; a lower bound in a
            # crowded field, where the reference PSF flux includes blended neighbours
            early_tot = out[f"w{b}_ref_flux"] + out[f"w{b}_early_mean"]
            out[f"w{b}_vanish_frac"] = -out[f"w{b}_delta_late"] / early_tot.where(early_tot > 0)
    out["dipole"] = dipole_flags(out)
    return out.sort_values("ds1_score", ascending=False).reset_index(drop=True)


def dipole_flags(c: pd.DataFrame, radius_arcsec: float = 10.0, sig: float = 5.0) -> np.ndarray:
    """A moving foreground star (or a subtraction dipole) leaves a fading and a brightening
    candidate side by side. Flag candidates with an opposite-sign long-term partner within
    radius_arcsec (both > sig in delta_late, either band)."""
    if c.empty:
        return np.zeros(0, bool)
    dl = np.nan_to_num(np.c_[c.get("w1_delta_late_sig", np.nan), c.get("w2_delta_late_sig", np.nan)])
    pick = np.argmax(np.abs(dl), axis=1)
    d = dl[np.arange(len(c)), pick]
    xyz = np.c_[np.cos(np.radians(c.dec)) * np.cos(np.radians(c.ra)),
                np.cos(np.radians(c.dec)) * np.sin(np.radians(c.ra)), np.sin(np.radians(c.dec))]
    from scipy.spatial import cKDTree

    pairs = cKDTree(xyz).query_pairs(np.radians(radius_arcsec / 3600), output_type="ndarray")
    flag = np.zeros(len(c), bool)
    for i, j in pairs:
        if abs(d[i]) > sig and abs(d[j]) > sig and np.sign(d[i]) != np.sign(d[j]):
            flag[i] = flag[j] = True
    return flag


def run(galaxy: str, workdir: Path, tile_list: list[str] | None = None, stage: str = "all",
        cfg: Config | None = None) -> pd.DataFrame | None:
    cfg = cfg or Config()
    gal = GALAXIES[galaxy]
    wd = workdir / galaxy
    wd.mkdir(parents=True, exist_ok=True)
    tile_list = tile_list or galaxy_tiles(gal)
    log.info("%s: tiles %s", galaxy, tile_list)
    if stage in ("all", "fetch"):
        for t in tile_list:
            fetch.fetch_tile(t, bands=cfg.bands)
    if stage in ("all", "diff"):
        dets = []
        for t in tile_list:
            for b in cfg.bands:
                dets.append(process_tile_band(gal, t, b, wd, cfg))
        dets = pd.concat([d for d in dets if not d.empty], ignore_index=True)
        dets.to_parquet(wd / "detections.parquet")
    if stage in ("all", "diff", "cands"):
        dets = pd.read_parquet(wd / "detections.parquet")
        cands = candidates_from(dets, cfg)
        log.info("%s: %d detections -> %d candidates (>= %d epochs)", galaxy, len(dets), len(cands), cfg.min_epochs)
        lcs = photometer(cands, wd, tile_list, cfg.bands)
        lcs.to_parquet(wd / "lightcurves.parquet")
        out = score(cands, lcs)
        out.to_csv(wd / "candidates.csv", index=False)
        return out
    return None


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("galaxy")
    ap.add_argument("--tiles", nargs="*")
    ap.add_argument("--workdir", default=str(fetch.cache_root() / "work"))
    ap.add_argument("--stage", default="all", choices=["all", "fetch", "diff", "cands"])
    ap.add_argument("--list-tiles", action="store_true")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    if a.list_tiles:
        print(" ".join(galaxy_tiles(GALAXIES[a.galaxy])))
    else:
        run(a.galaxy, Path(a.workdir), a.tiles, a.stage)
