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

from . import PIXSCALE, ZP_VEGA, detect, diff, fetch, masks, metrics, photometry, psf, tiles
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
    # v2 (masks.py): release unWISE bright-star footprints that are the galaxy's own light; search them with a
    # fine (fine_box px) noise calibration and flag candidates there as low-confidence
    release_galaxy_cores: bool = True
    fine_box: int = 16  # noise-calibration box in high-surface-brightness / released regions (px)
    hsb_nmgy: float = 1000.0  # reference surface brightness (9-px median, nmgy/px) above which fine_box applies
    sat_valid_frac: float = 0.5  # pixels valid in fewer than this fraction of epochs are saturated cores


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


def _bitmask_cutout(st, pad: int):
    """The unWISE bitmask over the stack's window padded by `pad` px (clipped to the tile), its WCS, and
    the window's offset inside the cut-out. Synthetic stacks (no tile) may carry `st.bitmask` (window-sized)."""
    if getattr(st, "bitmask", None) is not None:
        return np.asarray(st.bitmask, np.int64), st.wcs, (0, 0)
    if not st.tile:
        return None, None, (0, 0)
    from astropy.io import fits as _fits

    from .stack import window_wcs

    y0, y1, x0, x1 = st.window
    py0, py1, px0, px1 = max(0, y0 - pad), min(tiles.NPIX, y1 + pad), max(0, x0 - pad), min(tiles.NPIX, x1 + pad)
    msk = _fits.getdata(fetch.fetch_mask(st.tile))[py0:py1, px0:px1].astype(np.int64)
    return msk, window_wcs(tiles.wcs_for(st.tile), py0, px0), (x0 - px0, y0 - py0)


def build_mask_set(st, gal: Galaxy, cfg: Config, ref0: np.ndarray, refvar0: np.ndarray, valid_frac=None,
                   psf0: np.ndarray | None = None) -> masks.MaskSet:
    """v2 masks on the stack's window (see masks.py): reference-peak circles, unWISE artefact bits minus
    the released galaxy-core footprints (low-confidence), saturated cores, nucleus and companion circles,
    the search region, and the high-surface-brightness zone that gets the fine noise calibration."""
    ny, nx = ref0.shape
    invalid = ~np.isfinite(refvar0)
    peaks = detect.bright_star_mask(ref0, refvar0, flux_of_mag(cfg.bright_mag[st.band]))
    bright_all = peaks.copy()
    bright = peaks.copy()
    lowconf = np.zeros((ny, nx), bool)
    saturated = np.zeros((ny, nx), bool)
    stars: list = []
    if cfg.unwise_mask:
        msk_p, wcs_p, (ox, oy) = _bitmask_cutout(st, pad=150)
        if msk_p is not None:
            msk = msk_p[oy:oy + ny, ox:ox + nx]
            artefact = (msk & fetch.ARTIFACT_BITS) != 0
            dil = ndimage.binary_dilation(artefact, iterations=2)
            bright_all |= dil
            if cfg.release_galaxy_cores:
                stars = masks.classify_centres(msk_p, wcs_p, gal, ref=ref0, psf=psf0, ref_off=(ox, oy))
                rel = masks.release_map(msk_p, stars)[oy:oy + ny, ox:ox + nx]
                other = (msk & (fetch.ARTIFACT_BITS & ~masks.FAMILY_BITS)) != 0  # ghosts, latents, off-edge
                keep = other | (((msk & masks.FAMILY_BITS) != 0) & ~rel)
                keep_d = ndimage.binary_dilation(keep, iterations=2)
                lowconf = rel & ~keep_d
                bright |= keep_d
                # the model saturation zone of genuine stars (released galaxy light: saturation comes from coverage)
                saturated |= ndimage.binary_dilation(((msk & masks.bits(masks.SATURATION)) != 0) & ~rel, iterations=2)
            else:
                bright |= dil
    if valid_frac is not None:
        saturated |= ndimage.binary_dilation((valid_frac < cfg.sat_valid_frac) & (valid_frac > 0), iterations=2)
    saturated &= ~invalid
    lowconf &= ~saturated
    xn, yn = st.wcs.all_world2pix([[gal.ra, gal.dec]], 0)[0]
    nucleus = detect.circle_mask(ref0.shape, xn, yn, gal.nucleus_mask_arcsec / PIXSCALE)
    for mra, mdec, mrad in gal.extra_masks:
        xm, ym = st.wcs.all_world2pix([[mra, mdec]], 0)[0]
        nucleus |= detect.circle_mask(ref0.shape, xm, ym, mrad / PIXSCALE)
    yy, xx = np.mgrid[0:ny:4, 0:nx:4]
    ra_g, dec_g = st.wcs.all_pix2world(xx.ravel(), yy.ravel(), 0)
    outside = ~gal.inside(ra_g, dec_g).reshape(xx.shape)
    outside = np.repeat(np.repeat(outside, 4, 0), 4, 1)[:ny, :nx]
    # surface brightness: 9-px median of the 2x-binned reference (stars removed), back to full size
    b = np.nan_to_num(ref0[: ny - ny % 2, : nx - nx % 2]).reshape(ny // 2, 2, nx // 2, 2).mean(axis=(1, 3))
    sb = ndimage.median_filter(b, size=5)
    sb = np.repeat(np.repeat(sb, 2, 0), 2, 1)
    hsb = np.zeros((ny, nx), bool)
    hsb[: sb.shape[0], : sb.shape[1]] = sb > cfg.hsb_nmgy
    hsb = ndimage.binary_dilation(hsb, iterations=4) & ~outside
    return masks.MaskSet(invalid=invalid, bright=bright, bright_all=bright_all, nucleus=nucleus, outside=outside,
                         lowconf=lowconf, saturated=saturated, hsb=hsb, stars=stars)


def build_masks(st, gal: Galaxy, cfg: Config, ref0: np.ndarray, refvar0: np.ndarray):
    """(invalid, bright, nucleus, outside) boolean masks on the stack's window (v1 interface; `bright`
    follows cfg.release_galaxy_cores and includes saturated cores). See build_mask_set."""
    ms = build_mask_set(st, gal, cfg, ref0, refvar0)
    return ms.invalid, ms.bright | ms.saturated, ms.nucleus, ms.outside


def stack_channel(acc: dict, psfs: dict, noise_mask, det_mask, cfg: Config, fine=None):
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
            snr_s, *_ = detect.snr_map(d, sg, psfs[s], mask=noise_mask, box=cfg.box, fine=fine, fine_box=cfg.fine_box)
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
        snr, F, E, _ = detect.snr_map(comb, csig, pmean, mask=noise_mask, box=cfg.box, fine=fine, fine_box=cfg.fine_box)
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
    valid_frac = (st.ivar > 0).mean(axis=0)
    ms = build_mask_set(st, gal, cfg, ref0, refvar0, valid_frac=valid_frac)
    psfs = {}
    for s, (r, rv) in refs.items():
        try:
            stars = psf.find_stars(r, np.where(np.isfinite(rv), 1 / rv, 0), mask=ms.bright_all | ms.nucleus | ms.saturated,
                                   flux_max=cfg.psf_peak_max)
            psfs[s] = psf.build_psf(r, stars)
            log.info("%s W%d season %d: PSF from %d stars, FWHM %.2f px", st.tile, st.band, s, len(stars), psf.fwhm(psfs[s]))
        except ValueError as e:
            log.warning("%s W%d season %d: %s; Gaussian PSF", st.tile, st.band, s, e)
            psfs[s] = psf.gaussian_psf(2.3 if st.band == 1 else 2.5)
    if cfg.release_galaxy_cores and not getattr(gal, "bright_sources", ()) and any(
            not st_.own and st_.why.startswith("fallback") for st_ in ms.stars):
        # fallback rule: redo the point-source test with the empirical PSF
        ms = build_mask_set(st, gal, cfg, ref0, refvar0, valid_frac=valid_frac, psf0=psfs[min(psfs)])
    noise_mask, det_mask, fine = ms.noise_mask, ms.det_mask, ms.fine
    invalid = ms.invalid
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
        np.save(out / "maskbits.npy", ms.codes())
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
        d, sg, kern = diff.difference(st.img[i], st.ivar[i], r, rv, use=~(ms.bright_all | ms.saturated | invalid), half=cfg.half,
                                      block=cfg.block, floor=floors[s])
        if cfg.bkg_box:
            d = d - diff.background_mesh(d, sg, cfg.bkg_box)
        D[i], S[i] = d, sg
        snr_c, F, E, c = detect.snr_map(d, sg, psfs[s], mask=noise_mask, box=cfg.box, fine=fine, fine_box=cfg.fine_box)
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
            snr, F, E, _ = detect.snr_map(dl, sl_, psfs[s], mask=noise_mask, box=cfg.box, fine=fine, fine_box=cfg.fine_box)
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
    stacks = stack_channel(acc, psfs, noise_mask, det_mask, cfg, fine=fine) if cfg.stack_channel else {}
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
    if len(dets):  # v2: flag detections on released galaxy-core footprint (searched with the fine noise floor)
        xi = np.clip(np.round(dets.x.to_numpy()).astype(int), 0, nx - 1)
        yi = np.clip(np.round(dets.y.to_numpy()).astype(int), 0, ny - 1)
        dets["low_confidence"] = ms.lowconf[yi, xi]
    products = dict(D=D, S=S, scale=scale, psfs=psfs, refs=refs, det_mask=det_mask, stacks=stacks, masks=ms,
                    mask_census=ms.census(ref0))
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
                wcs=dict(st.wcs.to_header()), galaxy=gal.name, config=asdict(cfg), mask_census=prod["mask_census"])
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
            tiles=",".join(sorted(set(g.tile))),
            low_confidence=bool(use.low_confidence.fillna(False).astype(bool).any()) if "low_confidence" in use else False))
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


def mask_codes_at(workdir: Path, tile: str, ra, dec, band: int = 1) -> np.ndarray:
    """masks.MB_* codes (maskbits.npy) at sky positions; 255 outside the window or without maskbits."""
    d = tile_dir(workdir, tile, band)
    ra, dec = np.atleast_1d(ra), np.atleast_1d(dec)
    if not (d / "maskbits.npy").exists():
        return np.full(ra.size, 255, np.uint8)
    mb = np.load(d / "maskbits.npy")
    x, y = WCS(json.loads((d / "meta.json").read_text())["wcs"]).all_world2pix(ra, dec, 0)
    xi, yi = np.round(x).astype(int), np.round(y).astype(int)
    ok = (xi >= 0) & (yi >= 0) & (xi < mb.shape[1]) & (yi < mb.shape[0])
    out = np.full(ra.size, 255, np.uint8)
    out[ok] = mb[yi[ok], xi[ok]]
    return out


def forced_known(known: pd.DataFrame, workdir: Path, tile: str, bands=(1, 2), edge: int = 13) -> pd.DataFrame:
    """v2 recall channel: forced PSF photometry at every known position (TNS transients, local known
    objects) inside this tile's window, WHATEVER the masks say. Long format, as photometer, plus the
    object name and the mask code at the position (masks.MB_*: why a blind search could or could not
    have found it). The local noise factor comes from scale.npy, so masked or low-confidence pixels get
    the empirical noise of their surroundings; read 'mask_code' before trusting a flux there."""
    if known is None or known.empty:
        return pd.DataFrame()
    rows = []
    for band in bands:
        d = tile_dir(workdir, tile, band)
        if not (d / "meta.json").exists():
            continue
        meta, wcs, D, S, scale, psfs, refs = _load_tile(workdir, tile, band)
        season = np.array(meta["season"])
        x, y = wcs.all_world2pix(known.ra.to_numpy(float), known.dec.to_numpy(float), 0)
        ny, nx = D.shape[1:]
        codes = mask_codes_at(workdir, tile, known.ra.to_numpy(float), known.dec.to_numpy(float), band)
        for k in range(len(known)):
            xi, yi = x[k], y[k]
            if not (edge <= xi < nx - edge and edge <= yi < ny - edge):
                continue
            sc = scale[:, min(int(round(yi)) // SCALE_BIN, scale.shape[1] - 1), min(int(round(xi)) // SCALE_BIN, scale.shape[2] - 1)]
            f, e = photometry.forced_lightcurve(D, S, psfs, season, xi, yi, sc)
            rf = {s: photometry.reference_flux(np.asarray(r), np.asarray(rv), psfs[s], xi, yi) for s, (r, rv) in refs.items()}
            o = known.iloc[k]
            rows.append(pd.DataFrame(dict(
                name=str(o["name"]), type=str(o.get("type", "")), disc=str(o.get("disc", "")), tile=tile, band=band,
                epoch=meta["epochs"], mjd=meta["mjd"], season=season, flux=f, err=e,
                ref_flux=[rf[int(s_)][0] for s_ in season], x=xi, y=yi, edge_px=float(min(xi, yi, nx - 1 - xi, ny - 1 - yi)),
                mask_code=int(codes[k]), mask=masks.describe(int(codes[k])) if codes[k] != 255 else "no maskbits")))
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def recall_summary(lc: pd.DataFrame, disc_mjd: float | None = None, thresh: float = 5.0) -> dict:
    """One known object's forced light curve -> recall numbers per band: the largest season-aligned
    change from the 2010-11 level in sigma (and when), the number of epochs >= thresh sigma, and
    whether those come from both visit seasons (what the blind epoch channel needs)."""
    out = {}
    for b in (1, 2):
        lb = lc[lc.band == b].sort_values("mjd")
        g = np.isfinite(lb.flux.to_numpy(float)) & np.isfinite(lb.err.to_numpy(float)) & (lb.err.to_numpy(float) > 0)
        if g.sum() < 5:
            continue
        lb = lb[g]
        rf = lb.groupby("season").ref_flux.first().to_dict()
        f = metrics.align_seasons(lb.flux.to_numpy(), lb.season.to_numpy(), rf)
        e = lb.err.to_numpy(float)
        t = lb.mjd.to_numpy(float)
        early = t < metrics.EARLY_MJD
        if not early.any():
            early = np.arange(f.size) < 2
        w = 1 / e[early] ** 2
        base = float(np.sum(w * f[early]) / np.sum(w))
        z = (f - base) / np.hypot(e, 1 / np.sqrt(np.sum(w)))
        if disc_mjd is not None and np.isfinite(disc_mjd):  # after discovery only, if known
            z_after = np.where(t >= disc_mjd - 30, z, 0)
        else:
            z_after = z
        k = int(np.argmax(np.abs(z_after)))
        hit = np.abs(z_after) >= thresh
        out[b] = dict(max_sig=float(z_after[k]), t_max=float(t[k]), dflux_max=float(f[k] - base), n_sig=int(hit.sum()),
                      both_seasons=bool(lb.season.to_numpy()[hit].size and np.unique(lb.season.to_numpy()[hit]).size >= 2),
                      pre_max_sig=float(np.max(np.abs(np.where(t < (disc_mjd if disc_mjd else -1) - 30, z, 0)))) if disc_mjd else np.nan)
    return out


def score(cands: pd.DataFrame, lcs: pd.DataFrame) -> pd.DataFrame:
    if lcs is None or lcs.empty or "group" not in lcs:
        # no candidate of this galaxy falls inside this tile's photometry window (a galaxy spanning several tiles,
        # e.g. NGC 628): keep the candidates, unscored here; the tile that holds them measures them
        out = cands.copy()
        out["cls"] = "no-photometry"
        return out
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
