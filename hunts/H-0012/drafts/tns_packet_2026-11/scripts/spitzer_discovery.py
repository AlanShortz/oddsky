"""TNS packet 2026-11, NGC 4945 obscured #3: Spitzer/IRAC discovery and last-non-detection numbers.

Coordinator decision (2026-11-03): the discovery is the Spitzer 2018-06-02 detection, not the first WISE >= 5 sigma
epoch. This script makes the Spitzer numbers report-grade:

1. Exposure times AT THE SOURCE (the analogue of the NEOWISE L1b frame index used for WISE): IRSA SIA (spitzer_sha)
   with a 0.0001-deg circle returns the individual IRAC BCD frames that contain the position; the mean of their
   (t_min + t_max)/2 per band and AOR is the exposure mid-time, and their count x frame time the exposure time.
2. Photometry: the H-0013 difference-aperture method (oddsky.imaging.spitzer: 2.4" aperture, 6-15" annulus,
   aperture correction, empirical error from 12 apertures 10" away) on the 61x61 grids cached by spitzer_ngc4945.py,
   with the reference = median of the flat 2013-2016 epochs, LEAVE-ONE-OUT (an epoch never enters its own
   reference). 2017 is excluded from the reference because [3.6] 2017-06 is already +3 sigma.
3. [4.5] on 2018-06-02: that mosaic did not fully cover the 36" grid, so spitzer_ngc4945.py skipped it. It is
   downloaded once (13 MB), sampled where covered, measured if the aperture and annulus are covered, and deleted.

    uv run python hunts/H-0012/drafts/tns_packet_2026-11/scripts/spitzer_discovery.py
Output: ~/oddsky-runs/imaging/scratch/tns-packet-2026-11/spitzer/discovery.json
"""
import io
import json
import time
from pathlib import Path

import httpx
import numpy as np
import pandas as pd
from astropy.time import Time

from oddsky.imaging import spitzer

S = Path.home() / "oddsky-runs/imaging/scratch/tns-packet-2026-11/spitzer"
RA, DEC = 196.469582, -49.416175  # Spitzer centroid of the brightening (packet position)
RA0, DEC0 = 196.469838, -49.416317  # grid centre used by spitzer_ngc4945.py (Gaia-tied WISE centroid)
LAB = "NGC4945_obs3"
n, px = spitzer.N_GRID, spitzer.PX
c = n // 2
yy, xx = np.mgrid[:n, :n]
conv = 1e6 * (px / 206265) ** 2 * 1e6
# the packet position in the cached grid (grid x increases to the west)
gx = c - (RA - RA0) * np.cos(np.radians(DEC0)) * 3600 / px
gy = c + (DEC - DEC0) * 3600 / px


def ab(f):
    return float(-2.5 * np.log10(f * 1e-6 / 3631))


def measure(d, band, x0=gx, y0=gy):
    r = np.hypot(xx - x0, yy - y0)
    ap = r <= spitzer.AP_R / px
    sky = (r > spitzer.SKY_R[0] / px) & (r < spitzer.SKY_R[1] / px)
    if not np.isfinite(d[ap]).all() or np.isfinite(d[sky]).sum() < 0.5 * sky.sum():
        return None
    d = d - np.nanmedian(d[sky])
    offs = []
    for a in np.linspace(0, 2 * np.pi, 12, endpoint=False):
        cx, cy = x0 + 10 / px * np.cos(a), y0 + 10 / px * np.sin(a)
        m = np.hypot(xx - cx, yy - cy) <= spitzer.AP_R / px
        if np.isfinite(d[m]).all():
            offs.append(np.nansum(d[m]))
    k = spitzer.APCORR[band]
    return np.nansum(d[ap]) * conv * k, np.nanstd(offs) * conv * k, len(offs)


# ---------------------------------------------------------------- 1. BCD frames containing the source
r = httpx.get(spitzer.SIA_URL, params=dict(COLLECTION="spitzer_sha", POS=f"circle {RA} {DEC} 0.0001",
                                            RESPONSEFORMAT="CSV"), timeout=300, headers={"User-Agent": spitzer.UA})
r.raise_for_status()
fr = pd.read_csv(io.StringIO(r.text), on_bad_lines="skip")
fr = fr[fr.access_url.astype(str).str.endswith("_bcd.fits") & (fr.dataproduct_subtype == "science")
        & fr.energy_bandpassname.isin(["IRAC1", "IRAC2"])].copy()
fr["aor"] = fr.access_url.str.extract(r"/r(\d+)/")[0]
fr["band"] = fr.energy_bandpassname.map(spitzer.BANDS)
fr["mid"] = 0.5 * (fr.t_min + fr.t_max)
fr.to_csv(S / "bcd_frames_at_source.csv", index=False)
timing = {}
for (aor, band), g in fr.groupby(["aor", "band"]):
    timing[f"{aor}_{band}"] = dict(aor=aor, band=band, n_frames=len(g), mjd_mid=float(g.mid.mean()),
                                   utc_mid=Time(g.mid.mean(), format="mjd").iso[:19],
                                   utc_first=Time(g.t_min.min(), format="mjd").iso[:19],
                                   utc_last=Time(g.t_max.max(), format="mjd").iso[:19],
                                   frame_s=round(float((g.t_max - g.t_min).median() * 86400), 1),
                                   exptime_s=round(float(g.t_exptime.sum()), 1),
                                   proposal=str(g.proposal_id.iloc[0]), pi=str(g.proposal_pi.iloc[0]))
print("BCD frames containing the source:", len(fr), "in", fr.aor.nunique(), "AORs", flush=True)

# ---------------------------------------------------------------- 2. LOO light curve on the cached grids
samples = []
for f in sorted((S / "samples").glob(f"{LAB}__*.npz")):
    z = np.load(f)
    if z["ok"]:
        name = f.name.split("__", 1)[1][:-4]
        samples.append((name.split("_")[1], float(z["mjd"]), z["im"], name))

# ---------------------------------------------------------------- 3. [4.5] on 2018-06-02 (partial coverage)
extra = {}
sia = json.loads((S / "sia.json").read_text())[1]
row = [x for x in sia if "60808960" in x["url"] and x["band"] == "I2"]
if row:
    from astropy.io import fits
    from scipy.ndimage import map_coordinates
    from astropy.wcs import WCS

    tmp = S / "_tmp_i2_60808960.fits"
    try:
        with httpx.Client(headers={"User-Agent": spitzer.UA}, timeout=300, follow_redirects=True) as cl:
            with cl.stream("GET", row[0]["url"]) as resp:
                resp.raise_for_status()
                with open(tmp, "wb") as fh:
                    for ch in resp.iter_bytes(1 << 20):
                        fh.write(ch)
        time.sleep(2)
        with fits.open(tmp) as h:
            data = h[0].data.astype(float)
            w = WCS(h[0].header)
            mjd = float(h[0].header.get("MJD_OBS", row[0]["t_min"]))
        gra, gdec = spitzer.grid_radec(RA0, DEC0)
        X, Y = w.all_world2pix(gra.ravel(), gdec.ravel(), 0)
        im = map_coordinates(data, [Y, X], order=1, cval=np.nan).reshape(n, n)
        im[((X < 0) | (Y < 0) | (X > data.shape[1] - 1) | (Y > data.shape[0] - 1)).reshape(n, n)] = np.nan
        extra["I2_60808960"] = dict(covered_fraction=float(np.isfinite(im).mean()))
        samples.append(("I2", mjd, im, row[0]["url"].rsplit("/", 1)[-1]))
    except Exception as e:  # noqa: BLE001
        extra["I2_60808960"] = {"error": f"{type(e).__name__}: {e} (not a null result)"}
    finally:
        tmp.unlink(missing_ok=True)

out = {"timing_at_source": timing, "extra": extra, "position_in_grid_px": [float(gx), float(gy)], "lc": {}}
for band in ("I1", "I2"):
    rows = sorted([s for s in samples if s[0] == band], key=lambda s: s[1])
    yr = np.array([2000 + (s[1] - 51544.5) / 365.25 for s in rows])
    ref_ok = (yr > 2013.0) & (yr < 2017.0)
    lc = []
    for i, s in enumerate(rows):
        refi = [j for j in np.where(ref_ok)[0] if j != i]
        ref = np.nanmedian(np.array([rows[j][2] for j in refi]), 0)
        m = measure(s[2] - ref, band)
        aor = s[3].split("_")[2]
        t = timing.get(f"{aor}_{band}")
        rec = dict(year=round(float(yr[i]), 3), aor=aor, file=s[3], in_ref=bool(ref_ok[i]), n_ref=len(refi),
                   mjd_mosaic=s[1], utc_mid_at_source=t["utc_mid"] if t else None,
                   mjd_mid_at_source=t["mjd_mid"] if t else None, n_frames_at_source=t["n_frames"] if t else None,
                   exptime_s=t["exptime_s"] if t else None)
        if m is None:
            rec["note"] = "aperture or annulus not covered"
        else:
            f, e, no = m
            rec.update(uJy=round(float(f), 1), e_uJy=round(float(e), 1), snr=round(float(f / e), 1), n_offset_ap=no,
                       lim5_AB=round(ab(5 * e), 2), lim3_AB=round(ab(3 * e), 2))
            if f > 0:
                rec.update(AB=round(ab(f), 2), e_AB=round(1.0857 * e / f, 2))
        lc.append(rec)
    out["lc"][band] = lc
    print(band)
    for x in lc:
        print("   ", x["year"], x.get("utc_mid_at_source"), x.get("n_frames_at_source"), x.get("uJy"), "+-", x.get("e_uJy"),
              x.get("snr"), x.get("AB"), "lim5", x.get("lim5_AB"), "REF" if x["in_ref"] else "", x.get("note", ""))
print(json.dumps(extra))
(S / "discovery.json").write_text(json.dumps(out, indent=1))
