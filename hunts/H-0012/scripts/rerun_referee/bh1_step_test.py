# RE-RUN COPY (H-0012 builder, 2026-11-01) of the referee's script in
# hunts/H-0012/reviews/claude-referee-2026-11-01/, unchanged except this note, run on the pipeline
# outputs AFTER the referee-round fixes (leave-one-out references, absolute seasons, stacked channel,
# halo bits unmasked, scatter floor 0.8). Outputs are written next to this copy, not over the referee's.
"""Referee test (2026-11-01): is N6946-BH1's 2010 -> NEOWISE W1/W2 step instrumental?

Re-runs the H-0012 difference imaging on the NGC 6946 window (tile 3090p605) with several
reference / PSF / kernel variants, then measures the same forced-photometry statistics
(delta_neo, delta_late; metrics.band_metrics after acceptance.aligned-style season alignment) at

  * BH1 itself,
  * every reference-image point source in the window (local maxima), binned by flux, so that a
    calibration step that scales with source flux shows up as a trend of delta_neo with flux,
  * a grid of positions within 2.5' of BH1, binned by the local high-pass (structured) surface
    brightness of the reference, i.e. resolved bright regions.

    uv run python hunts/H-0012/reviews/claude-referee-2026-11-01/bh1_step_test.py

Writes bh1_step_test.json and bh1_step_test.png next to this script. Read-only on the pipeline
outputs; recomputes the differences in memory (window 425 x 438 px, 24 epochs: light).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from astropy.io import fits
from scipy import ndimage

from oddsky.imaging import PIXSCALE, detect, diff, fetch, flux_to_mjy, metrics, photometry
from oddsky.imaging import psf as psfm
from oddsky.imaging.galaxies import GALAXIES
from oddsky.imaging.pipeline import Config, flux_of_mag, window_for
from oddsky.imaging.stack import load_stack

HERE = Path(__file__).resolve().parent
GAL = GALAXIES["NGC6946"]
TILE = "3090p605"
BH1 = (308.864833, 60.135636)
SN17 = (308.684333, 60.193289)
EARLY = metrics.EARLY_MJD


def masks(st, refs, band, cfg):
    ref0, refvar0 = refs[min(refs)]
    invalid = ~np.isfinite(refvar0)
    bright = detect.bright_star_mask(ref0, refvar0, flux_of_mag(cfg.bright_mag[band]))
    win = st.window
    msk = fits.getdata(fetch.fetch_mask(TILE))[win[0]:win[1], win[2]:win[3]]
    bright |= ndimage.binary_dilation((msk.astype(np.int64) & fetch.ARTIFACT_BITS) != 0, iterations=2)
    xn, yn = st.wcs.all_world2pix([[GAL.ra, GAL.dec]], 0)[0]
    nucleus = detect.circle_mask(ref0.shape, xn, yn, GAL.nucleus_mask_arcsec / PIXSCALE)
    return invalid, bright, nucleus


def run_variant(st, band, ref_mode="all", psf_mode="ref", half=2, mesh=24, cfg=Config()):
    """Difference stack for one variant. ref_mode: 'all' (pipeline), 'neo' (NEOWISE-only
    reference), 'early' (2010-11 WISE epochs only, the De et al. choice). psf_mode: 'ref' (PSF
    from the season reference, pipeline) or 'early' (PSF from the 2010-11 epoch of the season)."""
    mjd, season = st.mjd, st.season
    refs = {}
    for s in (0, 1):
        sel = season == s
        if ref_mode == "neo":
            sel = sel & (mjd > 56600)
        elif ref_mode == "early":
            sel = sel & (mjd < EARLY)
        refs[s] = diff.masked_median(st.img[sel], st.ivar[sel])
    invalid, bright, nucleus = masks(st, refs, band, cfg)
    noise_mask = invalid | bright | nucleus
    psfs = {}
    for s, (r, rv) in refs.items():
        src = r
        if psf_mode == "early":
            i = np.nonzero((season == s) & (mjd < EARLY))[0][0]
            src = st.img[i]
        stars = psfm.find_stars(src, np.where(np.isfinite(rv), 1 / rv, 0), mask=bright | nucleus,
                                flux_max=cfg.psf_peak_max)
        try:
            psfs[s] = psfm.build_psf(src, stars)
        except ValueError:
            psfs[s] = psfm.gaussian_psf(2.3 if band == 1 else 2.5)
    floors = {s: diff.residual_floor(r) for s, (r, _) in refs.items()}
    n, ny, nx = st.img.shape
    D = np.empty((n, ny, nx), np.float32)
    S = np.empty((n, ny, nx), np.float32)
    C = np.empty((n, ny, nx), np.float32)
    ksum = np.empty(n)
    for i in range(n):
        s = int(season[i])
        r, rv = refs[s]
        d, sg, ks = diff.difference(st.img[i], st.ivar[i], r, rv, use=~(bright | invalid), half=half,
                                    block=cfg.block, floor=floors[s])
        ksum[i] = float(np.mean([k.sum() for _, k, _ in ks]))
        if mesh:
            d = d - diff.background_mesh(d, sg, mesh)
        _, _, _, c = detect.snr_map(d, sg, psfs[s], mask=noise_mask, box=cfg.box)
        D[i], S[i], C[i] = d, sg, c
    return dict(D=D, S=S, C=C, psfs=psfs, refs=refs, ksum=ksum, mask=noise_mask)


def stats_at(v, st, x, y):
    """delta_neo / delta_late (flux, sigma) at pixel (x, y), as acceptance.py computes them."""
    xi, yi = int(round(x)), int(round(y))
    if not (13 <= xi < st.img.shape[2] - 13 and 13 <= yi < st.img.shape[1] - 13):
        return None
    sc = v["C"][:, yi, xi]
    f, e = photometry.forced_lightcurve(v["D"], v["S"], v["psfs"], st.season, x, y, sc)
    rf = {s: photometry.reference_flux(r, rv, v["psfs"][s], x, y)[0] for s, (r, rv) in v["refs"].items()}
    fa = metrics.align_seasons(f, st.season, rf)
    m = metrics.band_metrics(st.mjd, fa, e, st.season)
    if "delta_neo" not in m:
        return None
    return dict(dneo=m["delta_neo"], dneo_sig=m["delta_neo_sig"], dlate=m["delta_late"],
                dlate_sig=m["delta_late_sig"], ref=float(np.nanmean(list(rf.values()))),
                f=fa.tolist(), e=e.tolist())


def sources(v, st, exclude):
    """Reference local maxima (5x5) with a positive PSF flux, away from the edges and masks."""
    r0 = v["refs"][0][0]
    sm = ndimage.uniform_filter(r0, 3)
    pk = (sm == ndimage.maximum_filter(sm, 5))
    pk[:15, :] = pk[-15:, :] = pk[:, :15] = pk[:, -15:] = False
    pk &= ~v["mask"]
    ys, xs = np.nonzero(pk)
    keep = np.ones(xs.size, bool)
    for ex, ey, rad in exclude:
        keep &= np.hypot(xs - ex, ys - ey) > rad
    return xs[keep].astype(float), ys[keep].astype(float)


def main():
    cfg = Config()
    out = dict(variants={}, sources={}, grid={})
    win = window_for(GAL, TILE, cfg.margin)
    for band in (1, 2):
        st = load_stack(TILE, band, window=win)
        xb, yb = st.wcs.all_world2pix([[*BH1]], 0)[0]
        xs17, ys17 = st.wcs.all_world2pix([[*SN17]], 0)[0]
        print(f"W{band}: {st.n} epochs, mjd {st.mjd.min():.0f}-{st.mjd.max():.0f}, BH1 at px ({xb:.1f}, {yb:.1f})",
              flush=True)
        variants = {
            "pipeline": dict(),
            "ref_neo_only": dict(ref_mode="neo"),
            "ref_2010_only": dict(ref_mode="early"),
            "psf_from_2010": dict(psf_mode="early"),
            "kernel_7x7": dict(half=3),
            "no_mesh": dict(mesh=0),
        }
        for name, kw in variants.items():
            v = run_variant(st, band, cfg=cfg, **kw)
            s = stats_at(v, st, xb, yb)
            out["variants"].setdefault(name, {})[f"W{band}"] = dict(
                dneo_ujy=1e3 * float(flux_to_mjy(s["dneo"], band)), dneo_sig=s["dneo_sig"],
                dlate_ujy=1e3 * float(flux_to_mjy(s["dlate"], band)), dlate_sig=s["dlate_sig"],
                ref_flux_nmgy=s["ref"], kernel_sum=v["ksum"].round(4).tolist(),
                lc_ujy=(1e3 * flux_to_mjy(np.array(s["f"]) - np.average(np.array(s["f"])[st.mjd < EARLY]), band)).round(1).tolist())
            print(f"  {name:15s} BH1 dneo {out['variants'][name][f'W{band}']['dneo_ujy']:+6.1f} uJy "
                  f"({s['dneo_sig']:+5.1f} sig)  dlate {out['variants'][name][f'W{band}']['dlate_ujy']:+6.1f} uJy "
                  f"({s['dlate_sig']:+5.1f})  kernel sums 2010 {v['ksum'][st.mjd < EARLY].round(3)} "
                  f"NEO median {np.median(v['ksum'][st.mjd > 56600]):.3f}", flush=True)
            if name != "pipeline":
                del v
                continue
            # ---- control sample 1: every reference point source in the window
            xs, ys = sources(v, st, [(xb, yb, 4), (xs17, ys17, 6)])
            rows = []
            for x, y in zip(xs, ys, strict=True):
                r = stats_at(v, st, x, y)
                if r is None or not np.isfinite(r["dneo_sig"]):
                    continue
                ra, dec = st.wcs.all_pix2world([[x, y]], 0)[0]
                rows.append(dict(x=x, y=y, ra=float(ra), dec=float(dec), ref=r["ref"], dneo=r["dneo"],
                                 dneo_sig=r["dneo_sig"], dlate=r["dlate"], dlate_sig=r["dlate_sig"],
                                 rell=float(GAL.ellipse_r(ra, dec))))
            out["sources"][f"W{band}"] = rows
            # ---- control sample 2: grid around BH1, binned by local structured brightness
            r0 = v["refs"][0][0]
            hp = r0 - ndimage.median_filter(r0, size=15, mode="nearest")
            grows = []
            for dy in range(-54, 55, 3):
                for dx in range(-54, 55, 3):
                    if np.hypot(dx, dy) < 3:
                        continue
                    x, y = xb + dx, yb + dy
                    xi, yi = int(round(x)), int(round(y))
                    if not (15 <= xi < r0.shape[1] - 15 and 15 <= yi < r0.shape[0] - 15) or v["mask"][yi, xi]:
                        continue
                    r = stats_at(v, st, x, y)
                    if r is None or not np.isfinite(r["dneo_sig"]):
                        continue
                    grows.append(dict(dx=dx, dy=dy, hp=float(hp[yi, xi]), ref_pix=float(r0[yi, xi]), ref=r["ref"],
                                      dneo=r["dneo"], dneo_sig=r["dneo_sig"], dlate_sig=r["dlate_sig"]))
            out["grid"][f"W{band}"] = grows
            out.setdefault("bh1_env", {})[f"W{band}"] = dict(
                ref_pix=float(r0[int(round(yb)), int(round(xb))]), hp=float(hp[int(round(yb)), int(round(xb))]),
                sky_median=float(np.nanmedian(r0)), window_px=list(win))
            del v
        del st
    (HERE / "bh1_step_test.json").write_text(json.dumps(out, default=float))
    print("wrote", HERE / "bh1_step_test.json")


if __name__ == "__main__":
    sys.exit(main())
