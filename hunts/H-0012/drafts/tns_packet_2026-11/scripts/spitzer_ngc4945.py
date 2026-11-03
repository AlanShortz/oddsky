"""TNS packet 2026-11: Spitzer/IRAC (incl. SPIRITS 2014-2019) at NGC 4945 obscured #3, to confirm the onset of the
WISE rise with a second observatory and to measure a Spitzer position.

oddsky.imaging.spitzer (the H-0013 tool): IRSA SIA query, each post-BCD mosaic downloaded once, sampled on a 61x61
grid of 0.6" pixels around the position, deleted (sequential, 2 s pauses; failures recorded as errors). Here the
difference light curve is re-referenced to the median of the pre-2018 warm-mission epochs, and the variable's
position is the centroid of (mean of the 2019 epochs - pre-2018 median) [4.5], fitted with a Gaussian.

    uv run python hunts/H-0012/drafts/tns_packet_2026-11/scripts/spitzer_ngc4945.py
Output: ~/oddsky-runs/imaging/scratch/tns-packet-2026-11/spitzer/
"""
import json
from pathlib import Path

import numpy as np

from oddsky.imaging import spitzer

OUT = Path.home() / "oddsky-runs/imaging/scratch/tns-packet-2026-11/spitzer"
OUT.mkdir(parents=True, exist_ok=True)
RA, DEC = 196.469838, -49.416317  # Gaia-tied WISE centroid (astrometry.py)
LAB = "NGC4945_obs3"

status, rows = spitzer.sia_query(RA, DEC)
(OUT / "sia.json").write_text(json.dumps([status, rows], indent=1))
print("SIA:", status, len(rows), "mosaics", flush=True)
if not status.startswith("ok"):
    raise SystemExit(f"SIA ERROR: {status}")
rows = sorted(rows, key=lambda r: r["t_min"])
res, errors = spitzer.fetch_samples(rows, {LAB: (RA, DEC)}, OUT / "samples", pause=2.0)
(OUT / "errors.json").write_text(json.dumps(errors, indent=1))
print("errors:", len(errors), flush=True)
samples = res[LAB]
n, px = spitzer.N_GRID, spitzer.PX
yy, xx = np.mgrid[:n, :n]
r = np.hypot(xx - n // 2, yy - n // 2)
ap = r <= spitzer.AP_R / px
sky = (r > spitzer.SKY_R[0] / px) & (r < spitzer.SKY_R[1] / px)
conv = 1e6 * (px / 206265) ** 2 * 1e6
out = {}
for band in ("I1", "I2"):
    rws = sorted([s for s in samples if s[0] == band], key=lambda s: s[1])
    if len(rws) < 3:
        out[band] = {"n": len(rws)}
        continue
    mjd = np.array([s[1] for s in rws])
    cube = np.array([s[2] for s in rws])
    yr = 2000 + (mjd - 51544.5) / 365.25
    pre = (yr > 2009.5) & (yr < 2018.0)  # warm mission, before the WISE onset
    ref = np.nanmedian(cube[pre], 0)
    lc = []
    for i in range(len(cube)):
        d = cube[i] - ref
        d = d - np.nanmedian(d[sky])
        offs = []
        for a in np.linspace(0, 2 * np.pi, 12, endpoint=False):
            cx, cy = n // 2 + 10 / px * np.cos(a), n // 2 + 10 / px * np.sin(a)
            offs.append(np.nansum(d[np.hypot(xx - cx, yy - cy) <= spitzer.AP_R / px]))
        lc.append(dict(year=round(float(yr[i]), 3), mjd=float(mjd[i]), in_ref=bool(pre[i]),
                       duJy=round(float(np.nansum(d[ap]) * conv * spitzer.APCORR[band]), 1),
                       err=round(float(np.nanstd(offs) * conv * spitzer.APCORR[band]), 1), file=rws[i][3]))
    late = yr > 2018.8
    cen = None
    if late.sum():
        dm = np.nanmean(cube[late], 0) - ref
        dm = dm - np.nanmedian(dm[sky])
        best = None
        c = n // 2
        sig = (1.9 if band == "I2" else 1.7) / px / 2.3548
        for dx in np.arange(-4, 4.01, 0.1):
            for dy in np.arange(-4, 4.01, 0.1):
                g = np.exp(-((xx - c - dx) ** 2 + (yy - c - dy) ** 2) / (2 * sig ** 2))
                m = (np.hypot(xx - c, yy - c) < 8) & np.isfinite(dm)
                A = np.c_[g[m], np.ones(m.sum())]
                p, *_ = np.linalg.lstsq(A, dm[m], rcond=None)
                rr = float(((A @ p - dm[m]) ** 2).sum())
                if best is None or rr < best[0]:
                    best = (rr, dx, dy, p[0])
        # the sampling grid's RA/Dec per pixel (x increases to the west), interpolated at the fitted centre
        gra, gdec = spitzer.grid_radec(RA, DEC)
        jx, jy = c + best[1], c + best[2]
        ix, iy = int(np.floor(jx)), int(np.floor(jy))
        fx, fy = jx - ix, jy - iy
        ra_v = (gra[iy, ix] * (1 - fx) * (1 - fy) + gra[iy, ix + 1] * fx * (1 - fy) + gra[iy + 1, ix] * (1 - fx) * fy
                + gra[iy + 1, ix + 1] * fx * fy)
        de_v = (gdec[iy, ix] * (1 - fx) * (1 - fy) + gdec[iy, ix + 1] * fx * (1 - fy) + gdec[iy + 1, ix] * (1 - fx) * fy
                + gdec[iy + 1, ix + 1] * fx * fy)
        cen = dict(ra=float(ra_v), dec=float(de_v), amp=float(best[3]), n_late=int(late.sum()),
                   offset_from_wise_arcsec=float(np.hypot((ra_v - RA) * np.cos(np.radians(DEC)), de_v - DEC) * 3600))
        np.save(OUT / f"late_minus_ref_{band}.npy", dm.astype(np.float32))
    out[band] = dict(n=len(rws), lc=lc, centroid=cen)
    print(band, json.dumps({k: v for k, v in out[band].items() if k != "lc"}), flush=True)
    for x in lc:
        print("   ", x["year"], x["duJy"], "+-", x["err"], "ref" if x["in_ref"] else "", flush=True)
(OUT / "spitzer_ngc4945.json").write_text(json.dumps(out, indent=1))
