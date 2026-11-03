"""TNS packet 2026-11: light curves, empirical noise and centroids for the H-0012 infrared-only candidates.

Only M81's tile (1507p696) is fully cached locally; the other tiles were processed in the cloud (h0012b) and only
their per-candidate products are on disk (~/oddsky-runs/h0012b/<tile>/<galaxy>/{lightcurves.parquet, cutouts.npz}).
So, for every candidate, from those products:

1. Leave-one-out re-referencing. The pipeline's forced PSF fluxes are differences against a full-run per-season
   median reference, which contains the event. Forced photometry is linear in the image, so subtracting the median
   of the *pre-event* epochs of the same visit season (excluding the epoch itself: leave-one-out) gives the flux
   against a pre-event reference, as recompute_numbers.py does for OS-0030 on the full stacks.
2. Empirical noise. The same re-referencing is applied to the 41x41-px difference cutouts. A Gaussian PSF is fitted
   at 24 offset positions (rings of 8 and 12 px) in every epoch; their robust scatter, scaled to the pipeline flux
   scale, is an empirical per-epoch error (galaxy-light residuals included). The quoted error is the larger of the
   propagated pipeline error and the empirical one.
3. Centroid. A Gaussian with free position is fitted to the S/N-weighted sum of the event-epoch difference cutouts
   (W1+W2), and converted to RA/Dec with the unWISE tile WCS (oddsky.imaging.tiles.wcs_for).
4. Quick-look figure (light curve + stamps) per candidate, written to the scratch directory.

    uv run python hunts/H-0012/drafts/tns_packet_2026-11/scripts/lc_screen.py
Outputs: ~/oddsky-runs/imaging/scratch/tns-packet-2026-11/lc/
"""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from oddsky.imaging import F0_JY
from oddsky.imaging.tiles import wcs_for

RUNS = Path.home() / "oddsky-runs/h0012b"
OUT = Path.home() / "oddsky-runs/imaging/scratch/tns-packet-2026-11/lc"
OUT.mkdir(parents=True, exist_ok=True)
REPO = Path(__file__).resolve().parents[5]
FWHM_PX = {1: 6.1 / 2.75, 2: 6.4 / 2.75}


def yr(mjd):
    return 2000.0 + (np.asarray(mjd, float) - 51544.5) / 365.25


# rank in triage_h0012b (obscured-transient ranking) -> pre-event window in decimal years [start, end)
CANDS = {
    3: (2009.0, 2018.0),    # NGC 4945 obscured #3: flat 2010-2017
    8: (2014.0, 2023.5),    # M81 = OS-0035: flat 2014-2023.2 (2010 is still the tail of the 2009.9 event)
    13: (2009.0, 2012.0),   # NGC 55: secular brightening since 2010
    17: (2009.0, 2016.0),   # Holmberg II
    20: (2013.5, 2018.0),   # M101 #20
    23: (2009.0, 2012.0),   # IC 342 #23
    27: (2009.0, 2016.5),   # UGCA 127 #27
    29: (2009.0, 2020.5),   # NGC 1744 #29
    31: (2009.0, 2018.5),   # NGC 300 #31
    32: (2009.0, 2021.9),   # NGC 4214 #32
    33: (2009.0, 2012.0),   # NGC 253 #33
    34: (2009.0, 2012.0),   # NGC 4656 #34
    35: (2013.5, 2018.7),   # NGC 4656 #35 (2010 elevated: excluded from the reference)
    36: (2009.0, 2018.7),   # KKR 59 #36
    37: (2009.0, 2022.9),   # NGC 925 #37
    39: (2009.0, 2019.9),   # ESO 274-001 #39
}


def gauss_psf(fwhm, size=13, dx=0.0, dy=0.0):
    s = fwhm / 2.3548
    h = size // 2
    yy, xx = np.mgrid[-h:h + 1, -h:h + 1]
    g = np.exp(-((xx - dx) ** 2 + (yy - dy) ** 2) / (2 * s * s))
    return g / g.sum()


def gfit(img, x, y, fwhm, rad=3.0):
    """Linear Gaussian-PSF amplitude (+ constant) at (x, y) in a 2-D image."""
    xi, yi = int(round(x)), int(round(y))
    h = 6
    if xi - h < 0 or yi - h < 0 or xi + h >= img.shape[1] or yi + h >= img.shape[0]:
        return np.nan
    st = gauss_psf(fwhm, 2 * h + 1, x - xi, y - yi)
    d = img[yi - h:yi + h + 1, xi - h:xi + h + 1]
    yy, xx = np.mgrid[-h:h + 1, -h:h + 1]
    ok = (np.hypot(xx - (x - xi), yy - (y - yi)) <= rad) & np.isfinite(d)
    A = np.c_[st[ok], np.ones(ok.sum())]
    p, *_ = np.linalg.lstsq(A, d[ok], rcond=None)
    return p[0]


def centroid_fit(img, x0, y0, fwhm):
    """Least-squares Gaussian position fit (grid + refine) on a 2-D image; returns x, y, formal sigma."""
    best = None
    for dx in np.arange(-1.5, 1.51, 0.05):
        for dy in np.arange(-1.5, 1.51, 0.05):
            xi, yi = int(round(x0)), int(round(y0))
            h = 4
            st = gauss_psf(fwhm, 2 * h + 1, x0 + dx - xi, y0 + dy - yi)
            d = img[yi - h:yi + h + 1, xi - h:xi + h + 1]
            A = np.c_[st.ravel(), np.ones(st.size)]
            p, res, *_ = np.linalg.lstsq(A, d.ravel(), rcond=None)
            r = float(((A @ p - d.ravel()) ** 2).sum())
            if best is None or r < best[0]:
                best = (r, dx, dy, p[0])
    return x0 + best[1], y0 + best[2], best[3]


def run(rank, T):
    r = T[T.rank_obs == rank].iloc[0]
    gal, tile, gid = r.uid.split("|")
    gid = int(gid)
    d = RUNS / tile / gal
    lc = pd.read_parquet(d / "lightcurves.parquet")
    lc = lc[lc.group == gid].copy()
    z = np.load(d / "cutouts.npz")
    lo, hi = CANDS[rank]
    rows, cubes = [], {}
    for band in (1, 2):
        b = lc[lc.band == band].sort_values("epoch").reset_index(drop=True)
        conv = F0_JY[band] * 1e-3  # nmgy -> uJy
        t = yr(b.mjd)
        pre = (t >= lo) & (t < hi) & np.isfinite(b.flux)
        key = f"{gid}_w{band}_diff"
        cube = z[key] if key in z else None  # (n_epoch_in_run, 41, 41)
        x0 = 20 + (float(b.x.iloc[0]) - round(float(b.x.iloc[0])))
        y0 = 20 + (float(b.y.iloc[0]) - round(float(b.y.iloc[0])))
        # epoch index in cube: the run's epoch list -> the cube's first axis follows the run's epochs
        run_epochs = sorted(lc.epoch.unique())
        new_cube = np.full((len(b), 41, 41), np.nan, np.float32) if cube is not None else None
        for i in range(len(b)):
            s = b.season.iloc[i]
            refi = [j for j in np.where(pre & (b.season == s))[0] if j != i]
            f0 = np.median(b.flux.iloc[refi]) if refi else np.nan
            ef0 = 1.2533 * np.std(b.flux.iloc[refi], ddof=1) / np.sqrt(len(refi)) if len(refi) > 1 else np.nan
            flux = (b.flux.iloc[i] - f0) * conv
            err_p = np.hypot(b.err.iloc[i], ef0) * conv
            emp = np.nan
            if cube is not None and cube.shape[0] == len(run_epochs):
                ci = run_epochs.index(int(b.epoch.iloc[i]))
                cref = [run_epochs.index(int(b.epoch.iloc[j])) for j in refi]
                Di = cube[ci] - np.median(cube[cref], 0) if cref else cube[ci]
                new_cube[i] = Di
                offs = []
                for rad, n in ((8, 12), (12, 12)):
                    for a in np.linspace(0, 2 * np.pi, n, endpoint=False) + (0.26 if rad == 12 else 0):
                        offs.append(gfit(Di, x0 + rad * np.cos(a), y0 + rad * np.sin(a), FWHM_PX[band]))
                offs = np.array(offs)
                offs = offs[np.isfinite(offs)]
                emp_g = 1.4826 * np.median(np.abs(offs - np.median(offs)))
                cen_g = gfit(Di, x0, y0, FWHM_PX[band])
            else:
                emp_g = cen_g = np.nan
            rows.append(dict(rank=rank, uid=r.uid, band=band, epoch=int(b.epoch.iloc[i]), season=int(s),
                             tile_mid_mjd=float(b.mjd.iloc[i]), year=float(t[i]), in_ref=bool(pre[i]), n_ref=len(refi),
                             uJy=flux, e_pipe=err_p, gauss_flux=cen_g, gauss_emp_sigma=emp_g))
        cubes[band] = new_cube
    out = pd.DataFrame(rows)
    # scale Gaussian-PSF fluxes to the pipeline PSF flux scale using the significant epochs
    for band in (1, 2):
        m = (out.band == band)
        sel = m & (out.uJy.abs() > 5 * out.e_pipe) & np.isfinite(out.gauss_flux)
        if sel.sum() >= 2:
            scale = float((out.uJy[sel] * out.gauss_flux[sel]).sum() / (out.gauss_flux[sel] ** 2).sum())
        else:
            scale = np.nan
        out.loc[m, "gauss_scale"] = scale
    # gauss fluxes are in cutout (nmgy) units; the scale converts them to pipeline uJy directly
    out["e_emp"] = out.gauss_emp_sigma * out.gauss_scale
    out["e_uJy"] = np.fmax(out.e_pipe, out.e_emp.fillna(0))
    out["snr"] = out.uJy / out.e_uJy
    out["AB"] = np.where(out.uJy > 0, -2.5 * np.log10(out.uJy.clip(lower=1e-9) * 1e-6 / 3631), np.nan)
    out["e_AB"] = 1.0857 * out.e_uJy / out.uJy.abs()
    out["AB_lim5"] = -2.5 * np.log10(5 * out.e_uJy * 1e-6 / 3631)
    out["AB_lim3"] = -2.5 * np.log10(3 * out.e_uJy * 1e-6 / 3631)
    out["Vega"] = np.where(out.uJy > 0, -2.5 * np.log10(out.uJy.clip(lower=1e-9) * 1e-6 / out.band.map(F0_JY)), np.nan)

    # centroid on the S/N-weighted sum of event epochs (both bands)
    cen = None
    ev = out[(out.snr >= 5) & (out.year >= CANDS[rank][1])]
    if len(ev) and cubes[1] is not None:
        acc = np.zeros((41, 41))
        wsum = 0.0
        for _, e in ev.iterrows():
            b = lc[lc.band == e.band].sort_values("epoch").reset_index(drop=True)
            i = int(np.where(b.epoch == e.epoch)[0][0])
            img = cubes[int(e.band)][i]
            if not np.isfinite(img[12:29, 12:29]).all():
                continue
            img = np.nan_to_num(img)
            w = e.snr / max(e.gauss_flux, 1e-9) if e.gauss_flux > 0 else 0  # normalise to unit flux, weight by S/N
            acc += w * img
            wsum += w
        b1 = lc[lc.band == 1].iloc[0]
        x0 = 20 + (float(b1.x) - round(float(b1.x)))
        y0 = 20 + (float(b1.y) - round(float(b1.y)))
        cx, cy, amp = centroid_fit(acc / max(wsum, 1e-9), x0, y0, 0.5 * (FWHM_PX[1] + FWHM_PX[2]))
        # bootstrap over event epochs for a statistical error
        rng = np.random.default_rng(1)
        bs = []
        evl = list(ev.itertuples())
        for _ in range(60):
            pick = rng.integers(0, len(evl), len(evl))
            a2 = np.zeros((41, 41))
            ws = 0.0
            for k in pick:
                e = evl[k]
                b = lc[lc.band == e.band].sort_values("epoch").reset_index(drop=True)
                i = int(np.where(b.epoch == e.epoch)[0][0])
                img = cubes[int(e.band)][i]
                if not np.isfinite(img[12:29, 12:29]).all() or e.gauss_flux <= 0:
                    continue
                img = np.nan_to_num(img)
                w = e.snr / e.gauss_flux
                a2 += w * img
                ws += w
            if ws > 0:
                bx, by, _ = centroid_fit(a2 / ws, x0, y0, 0.5 * (FWHM_PX[1] + FWHM_PX[2]))
                bs.append((bx, by))
        bs = np.array(bs)
        w = wcs_for(tile)
        # pipeline x, y are window pixels: the window origin is an integer offset from the tile pixel grid
        Xc, Yc = w.all_world2pix([[r.ra, r.dec]], 0)[0]
        ox, oy = round(float(b1.x) - Xc), round(float(b1.y) - Yc)
        b1 = b1.copy()
        b1["x"], b1["y"] = float(b1.x) - ox, float(b1.y) - oy
        X = float(b1.x) + (cx - x0)
        Y = float(b1.y) + (cy - y0)
        ra, dec = w.all_pix2world([[X, Y]], 0)[0]
        ra0, dec0 = w.all_pix2world([[float(b1.x), float(b1.y)]], 0)[0]
        sx, sy = (bs.std(0) * 2.75) if len(bs) > 5 else (np.nan, np.nan)
        cen = dict(ra=float(ra), dec=float(dec), sig_ra_arcsec=float(sx), sig_dec_arcsec=float(sy),
                   offset_from_triage_arcsec=float(np.hypot((ra - r.ra) * np.cos(np.radians(dec)), dec - r.dec) * 3600),
                   phot_pos=[float(ra0), float(dec0)], n_epochs=len(ev))
        np.save(OUT / f"stack_{rank}.npy", acc / max(wsum, 1e-9))
    for band in (1, 2):
        if cubes[band] is not None:
            np.save(OUT / f"cube_{rank}_w{band}.npy", cubes[band])
    return r, out, cen


def quicklook(r, out, cen, rank):
    fig = plt.figure(figsize=(12, 6.2))
    ax = fig.add_axes([0.06, 0.42, 0.9, 0.52])
    for band, c in ((1, "tab:blue"), (2, "tab:red")):
        b = out[out.band == band]
        ax.errorbar(b.year, b.uJy, b.e_uJy, fmt="o", ms=4, color=c, label=f"W{band}")
    ax.axhline(0, color="k", lw=0.5)
    lo, hi = CANDS[rank]
    ax.axvspan(lo, hi, color="0.9", zorder=0)
    ax.set_ylabel("flux vs pre-event ref (uJy)")
    ax.set_title(f"#{rank} {r.uid}  ({r.ra:.5f} {r.dec:+.5f})  d={r.dist_mpc} Mpc  cls={r.cls}")
    ax.legend()
    cube1 = np.load(OUT / f"cube_{rank}_w1.npy") if (OUT / f"cube_{rank}_w1.npy").exists() else None
    cube2 = np.load(OUT / f"cube_{rank}_w2.npy") if (OUT / f"cube_{rank}_w2.npy").exists() else None
    if cube1 is not None:
        b1 = out[out.band == 1].reset_index(drop=True)
        idx = np.linspace(0, len(b1) - 1, 8).astype(int)
        imax = int(np.nanargmax(b1.uJy.to_numpy()))
        idx = sorted(set(list(idx) + [imax]))[:9]
        vm = np.nanpercentile(np.abs(cube1[imax]), 99.5)
        for k, i in enumerate(idx):
            for row, cube in enumerate((cube1, cube2)):
                if cube is None:
                    continue
                a = fig.add_axes([0.04 + k * 0.105, 0.2 - row * 0.19, 0.1, 0.18])
                a.imshow(cube[i][8:33, 8:33], origin="lower", cmap="gray", vmin=-vm, vmax=vm)
                a.set_xticks([]); a.set_yticks([])
                if row == 0:
                    a.set_title(f"{b1.year[i]:.2f}", fontsize=8)
    fig.savefig(OUT / f"quicklook_{rank}.png", dpi=80)
    plt.close(fig)


def main():
    T = pd.read_csv(REPO / "hunts/H-0012/work/triage_h0012b.csv")
    allr, cens = [], {}
    for rank in CANDS:
        r, out, cen = run(rank, T)
        quicklook(r, out, cen, rank)
        allr.append(out)
        b = {bd: out[(out.band == bd) & (out.snr >= 5) & (out.year >= CANDS[rank][1])] for bd in (1, 2)}
        first = {bd: (float(b[bd].year.min()) if len(b[bd]) else None) for bd in (1, 2)}
        cens[rank] = dict(uid=r.uid, centroid=cen, first_ge5sigma_year=first,
                          gauss_scale={bd: float(out[out.band == bd].gauss_scale.iloc[0]) for bd in (1, 2)})
        print(f"#{rank} {r.uid}: first>=5sig {first}; centroid {cen}", flush=True)
    pd.concat(allr).to_csv(OUT / "lc_all.csv", index=False)
    (OUT / "centroids.json").write_text(json.dumps(cens, indent=1, default=float))


if __name__ == "__main__":
    main()
