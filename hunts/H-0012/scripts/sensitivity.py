"""H-0012 sensitivity: per-epoch 5-sigma point-source depth inside a galaxy's search region, checked
by injecting fake point sources into real difference images.

    uv run python hunts/H-0012/scripts/sensitivity.py M31 0118p408
    uv run python hunts/H-0012/scripts/sensitivity.py NGC6946 3090p605

Depth: 5 x the calibrated PSF-flux error (detect.snr_map) at every unmasked pixel, summarised in
bins of elliptical radius (units of the D25 semi-major axis), for EVERY epoch (range reported).
Injection (4 epochs): 60 sources per image per magnitude, >= 20 px apart, added to the DIFFERENCE
image with the season PSF; recovered if a >= 5 sigma peak lies within 1.5 px. This is a per-epoch,
post-subtraction test of the noise calibration only: the kernel fit is bypassed and the candidate
rule is not applied (scripts/completeness.py does that, injecting into raw epochs). The plateau
(recovery 1-1.5 mag above the limit) is reported because it is below 100% (blending, masks, the
1.5-px match). Writes work/sensitivity_<galaxy>.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

from oddsky.imaging import F0_JY, ZP_VEGA, detect, fetch
from oddsky.imaging.galaxies import GALAXIES
from oddsky.imaging.pipeline import tile_dir
from oddsky.imaging.psf import shifted

HERE = Path(__file__).resolve().parents[1]
LSUN = 3.828e33
MPC = 3.0857e24
LAM_UM = {1: 3.368, 2: 4.618}


def nuLnu_lsun(mag: float, band: int, d_mpc: float) -> float:
    fnu = F0_JY[band] * 10 ** (-mag / 2.5) * 1e-23  # erg/s/cm2/Hz
    nu = 2.998e14 / LAM_UM[band]
    return 4 * np.pi * (d_mpc * MPC) ** 2 * nu * fnu / LSUN


def mag(flux):
    return ZP_VEGA - 2.5 * np.log10(flux)


def main(galaxy: str, tile: str, epochs=(4, 9, 14, 19), seed: int = 0):
    epochs = tuple(epochs)
    gal = GALAXIES[galaxy]
    wd = fetch.cache_root() / "work" / galaxy
    rng = np.random.default_rng(seed)
    out = dict(galaxy=galaxy, tile=tile, bands={})
    for band in (1, 2):
        d = tile_dir(wd, tile, band)
        meta = json.loads((d / "meta.json").read_text())
        from astropy.wcs import WCS

        wcs = WCS(meta["wcs"])
        D = np.load(d / "D.npy", mmap_mode="r")
        S = np.load(d / "S.npy", mmap_mode="r")
        n, ny, nx = D.shape
        mask = np.unpackbits(np.load(d / "mask.npy"))[: ny * nx].reshape(ny, nx).astype(bool)
        yy, xx = np.mgrid[0:ny:4, 0:nx:4]
        ra, dec = wcs.all_pix2world(xx.ravel(), yy.ravel(), 0)
        r4 = gal.ellipse_r(ra, dec).reshape(xx.shape)
        rmap = np.repeat(np.repeat(r4, 4, 0), 4, 1)[:ny, :nx]
        bins = [(0, 0.3), (0.3, 0.6), (0.6, 1.0), (1.0, gal.search_scale)]
        season = meta["season"]
        rows = []
        inj = {}
        for i in range(n):
            s = season[i]
            psf = np.load(d / f"psf_s{s}.npy")
            Di = np.array(D[i])
            Si = np.array(S[i])
            snr, F, E, c = detect.snr_map(Di, Si, psf, mask=mask)
            lim = 5 * E
            row = dict(epoch=meta["epochs"][i], mjd=meta["mjd"][i])
            for lo, hi in bins:
                sel = (~mask) & (rmap >= lo) & (rmap < hi) & np.isfinite(lim)
                row[f"m5_r{lo}-{hi}"] = float(mag(np.median(lim[sel]))) if sel.sum() > 100 else None
            sel = (~mask) & (rmap < gal.search_scale) & np.isfinite(lim)
            row["m5_all"] = float(mag(np.median(lim[sel])))
            rows.append(row)
            if i not in epochs:
                continue
            # injection-recovery on a grid of magnitudes around the median depth
            ok = np.argwhere(sel[20:-20, 20:-20]) + 20
            for dm in np.arange(-1.5, 1.01, 0.25).round(2):
                m = row["m5_all"] + dm
                pick = ok[rng.choice(len(ok), min(400, len(ok)), replace=False)]
                chosen = []
                for y, x in pick:
                    if all((y - yc) ** 2 + (x - xc) ** 2 > 400 for yc, xc in chosen):
                        chosen.append((y, x))
                    if len(chosen) >= 60:
                        break
                Dj = Di.copy()
                h = psf.shape[0] // 2
                pos = []
                for y, x in chosen:
                    fx, fy = x + rng.uniform(-0.5, 0.5), y + rng.uniform(-0.5, 0.5)
                    xi, yi = int(round(fx)), int(round(fy))
                    if yi - h < 0 or xi - h < 0 or yi + h + 1 > ny or xi + h + 1 > nx:
                        continue
                    Dj[yi - h : yi + h + 1, xi - h : xi + h + 1] += 10 ** ((ZP_VEGA - m) / 2.5) * shifted(psf, fx - xi, fy - yi)
                    pos.append((fx, fy))
                snr_j, *_ = detect.snr_map(Dj, Si, psf, mask=mask)
                px, py, pv = detect.find_peaks(snr_j, 5.0, mask=mask)
                rec = sum(1 for fx, fy in pos if px.size and np.min(np.hypot(px - fx, py - fy)) < 1.5)
                k = f"{dm:+.2f}"  # relative to this epoch's median 5-sigma depth
                a, b = inj.get(k, (0, 0))
                inj[k] = (a + rec, b + len(pos))
        frac = {k: v[0] / v[1] for k, v in sorted(inj.items(), key=lambda kv: float(kv[0])) if v[1]}
        ms = np.array([float(k) for k in frac])
        fs = np.array(list(frac.values()))
        dm50 = float(np.interp(0.5, fs[::-1], ms[::-1])) if (fs.max() >= 0.5 and fs.min() <= 0.5) else None
        m5 = float(np.median([r["m5_all"] for r in rows]))
        m50 = None if dm50 is None else m5 + dm50
        m5s = np.array([r["m5_all"] for r in rows])
        out["bands"][band] = dict(
            epochs=rows, recovery_vs_dm=frac, dm50_injected=dm50, m50_injected=m50, m5_median=m5,
            m5_range=[float(m5s.min()), float(m5s.max())], m5_p10_p90=[float(np.percentile(m5s, 10)), float(np.percentile(m5s, 90))],
            plateau={k: frac[k] for k in ("-1.50", "-1.25", "-1.00") if k in frac},
            nuLnu_lsun_at={str(dd): nuLnu_lsun(m5, band, dd) for dd in (gal.dist_mpc, 1.0, 4.0, 10.0)},
        )
        print(f"{galaxy} {tile} W{band}: median 5-sigma depth {m5:.2f} Vega; 50% injected recovery at "
              f"{dm50:+.2f} mag from it ({m50:.2f})" if m50 else f"{galaxy} {tile} W{band}: depth {m5:.2f}")
        print(f"    5-sigma depth range over {len(rows)} epochs: {m5s.min():.2f}-{m5s.max():.2f}")
        print("    recovery:", {k: round(v, 2) for k, v in frac.items()})
    p = HERE / "work" / f"sensitivity_{galaxy}.json"
    p.write_text(json.dumps(out, indent=1))
    print("wrote", p)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
