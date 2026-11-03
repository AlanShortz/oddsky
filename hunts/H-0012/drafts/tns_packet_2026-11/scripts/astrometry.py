"""TNS packet 2026-11: Gaia DR3 tie of the WISE transient centroids, and per-epoch centroid stability.

For each ready candidate the transient centroid (lc_screen.py: Gaussian position fit to the S/N-weighted sum of the
event-epoch difference cutouts) is in the unWISE tile WCS. The tile's astrometric zero point is measured here with
the same Gaussian fit on stars in a cached unWISE W1 image of the same tile (M81: the median of the 2014.6-2023.2
epochs; NGC 4945: the only cached epoch, 13 = 2019-01), matched to Gaia DR3 (G 13-17.5, |pm| < 20 mas/yr, propagated
to the image epoch). The median WISE-Gaia offset is subtracted from the transient centroid; the error is the
bootstrap centroid error (lc_screen.py) plus the error of the median offset, plus a 0.2" floor for PSF/colour
systematics of a centroid on difference images.

Gaia DR3 is read from the VizieR mirror at vizier.idia.ac.za (CDS times out from this machine); failure is an error.

    uv run python hunts/H-0012/drafts/tns_packet_2026-11/scripts/astrometry.py
Output: ~/oddsky-runs/imaging/scratch/tns-packet-2026-11/astrometry/astrometry.json
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from astropy.io import fits
from astropy.wcs import WCS

sys.path.insert(0, str(Path(__file__).parent))
from lc_screen import FWHM_PX, centroid_fit  # noqa: E402

from oddsky.imaging import fetch  # noqa: E402

OUT = Path.home() / "oddsky-runs/imaging/scratch/tns-packet-2026-11/astrometry"
OUT.mkdir(parents=True, exist_ok=True)
LC = Path.home() / "oddsky-runs/imaging/scratch/tns-packet-2026-11/lc"
CEN = json.loads((LC / "centroids.json").read_text())

SRC = {
    3: dict(label="NGC4945_obs3", tile="1974m500", epochs=[13], ep_year=2019.07),
    8: dict(label="M81_OS-0035", tile="1507p696", epochs=list(range(4, 21)), ep_year=2019.0),
}


def gaia_box(ra, dec, rad_deg):
    import io
    import time

    import requests

    last = None
    for _ in range(3):
        try:
            q = requests.get("https://vizier.idia.ac.za/viz-bin/asu-tsv", timeout=180, params={
                "-source": "I/355/gaiadr3", "-c": f"{ra} {dec}", "-c.rd": rad_deg, "Gmag": "13..17.5",
                "-out": "Source,RA_ICRS,DE_ICRS,pmRA,pmDE,Gmag", "-out.max": 20000})
            q.raise_for_status()
            lines = [ln for ln in q.text.splitlines() if ln and not ln.startswith("#")]
            d = pd.read_csv(io.StringIO("\n".join([lines[0]] + lines[3:])), sep="\t", dtype={"Source": str})
            for c in ("RA_ICRS", "DE_ICRS", "pmRA", "pmDE", "Gmag"):
                d[c] = pd.to_numeric(d[c].astype(str).str.strip(), errors="coerce")
            if not len(d):
                raise RuntimeError("empty Gaia table (error, not a null result)")
            return d
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(10)
    raise RuntimeError(f"Gaia DR3 via IDIA failed: {last}")


res = {}
for rank, s in SRC.items():
    cen = CEN[str(rank)]["centroid"]
    ra0, dec0 = cen["ra"], cen["dec"]
    imgs = []
    for e in s["epochs"]:
        p = fetch.local_path(s["tile"], 1, e, "img-m")
        if p.exists():
            imgs.append(fits.getdata(p).astype(np.float32))
            hdr = fits.getheader(p)
    img = np.median(np.stack(imgs), 0) if len(imgs) > 1 else imgs[0]
    del imgs
    w = WCS(hdr)
    X0, Y0 = w.all_world2pix([[ra0, dec0]], 0)[0]
    try:
        g = gaia_box(ra0, dec0, 0.35)
        status = f"ok ({len(g)} Gaia DR3 stars G 13-17.5 within 0.35 deg)"
    except Exception as ex:  # noqa: BLE001
        res[s["label"]] = {"gaia_status": f"ERROR {type(ex).__name__}: {ex}"}
        print(s["label"], "Gaia ERROR", ex)
        continue
    g = g[np.hypot(g.pmRA.fillna(0), g.pmDE.fillna(0)) < 20]
    dt = s["ep_year"] - 2016.0
    g["ra_e"] = g.RA_ICRS + g.pmRA.fillna(0) * dt / 3.6e6 / np.cos(np.radians(g.DE_ICRS))
    g["de_e"] = g.DE_ICRS + g.pmDE.fillna(0) * dt / 3.6e6
    x, y = w.all_world2pix(np.c_[g.ra_e, g.de_e], 0).T
    # isolation: no other Gaia G < 19 star within 12" (use the same G 13-17.5 list as a proxy) and inside the image
    rows = []
    for i in range(len(g)):
        xi, yi = x[i], y[i]
        if not (10 < xi < img.shape[1] - 10 and 10 < yi < img.shape[0] - 10):
            continue
        dd = np.hypot(x - xi, y - yi)
        if (dd[(dd > 0)] < 4.5).any():
            continue
        cut = img[int(round(yi)) - 6:int(round(yi)) + 7, int(round(xi)) - 6:int(round(xi)) + 7]
        if not np.isfinite(cut).all() or cut.max() <= 0:
            continue
        cx, cy, amp = centroid_fit(img, xi, yi, FWHM_PX[1])
        if abs(cx - xi) > 1.4 or abs(cy - yi) > 1.4 or amp <= 0:
            continue
        rw, dw = w.all_pix2world([[cx, cy]], 0)[0]
        rows.append(dict(G=float(g.Gmag.iloc[i]), dra=(rw - g.ra_e.iloc[i]) * np.cos(np.radians(dw)) * 3600,
                         ddec=(dw - g.de_e.iloc[i]) * 3600, r_deg=float(np.hypot(xi - X0, yi - Y0) * 2.75 / 3600)))
    st = pd.DataFrame(rows)
    st.to_csv(OUT / f"gaia_offsets_{s['label']}.csv", index=False)
    # restrict to the 60 nearest well-measured stars
    st = st.sort_values("r_deg").head(60)
    mra, mde = float(st.dra.median()), float(st.ddec.median())
    sra = float(1.2533 * st.dra.std() / np.sqrt(len(st)))
    sde = float(1.2533 * st.ddec.std() / np.sqrt(len(st)))
    ra_t = ra0 - mra / 3600 / np.cos(np.radians(dec0))
    de_t = dec0 - mde / 3600
    e_ra = float(np.sqrt(cen["sig_ra_arcsec"] ** 2 + sra ** 2 + 0.2 ** 2))
    e_de = float(np.sqrt(cen["sig_dec_arcsec"] ** 2 + sde ** 2 + 0.2 ** 2))
    from astropy.coordinates import SkyCoord
    import astropy.units as u

    c = SkyCoord(ra_t, de_t, unit="deg")
    res[s["label"]] = dict(
        gaia_status=status, n_stars=len(st), star_scatter_arcsec=[float(st.dra.std()), float(st.ddec.std())],
        wise_minus_gaia_arcsec=[mra, mde], err_of_offset_arcsec=[sra, sde],
        centroid_tile_wcs=[ra0, dec0], centroid_bootstrap_arcsec=[cen["sig_ra_arcsec"], cen["sig_dec_arcsec"]],
        position_gaia_tied=[float(ra_t), float(de_t)],
        sexagesimal=c.to_string("hmsdms", sep=":", precision=3),
        err_arcsec=[e_ra, e_de], err_quote_arcsec=round(max(e_ra, e_de, 0.3), 1))
    print(s["label"], json.dumps(res[s["label"]], indent=0), flush=True)

# per-epoch centroid stability (moving-object / blend test): fit each event epoch separately
for rank, s in SRC.items():
    out = pd.read_csv(LC / "lc_all.csv")
    out = out[(out["rank"] == rank) & (out.snr >= 8)]
    per = []
    for band in (1, 2):
        cube = np.load(LC / f"cube_{rank}_w{band}.npy")
        b = out[out.band == band]
        allb = pd.read_csv(LC / "lc_all.csv")
        allb = allb[(allb["rank"] == rank) & (allb.band == band)].reset_index(drop=True)
        for _, e in b.iterrows():
            i = int(np.where(allb.epoch == e.epoch)[0][0])
            im = np.nan_to_num(cube[i])
            cx, cy, _ = centroid_fit(im, 20.0, 20.0, FWHM_PX[band])
            per.append(dict(band=band, epoch=int(e.epoch), year=round(float(e.year), 3), snr=round(float(e.snr), 1),
                            dx_arcsec=round((cx - 20) * 2.75, 2), dy_arcsec=round((cy - 20) * 2.75, 2)))
    per = pd.DataFrame(per)
    res[s["label"]]["per_epoch_centroids"] = per.to_dict("records")
    res[s["label"]]["per_epoch_rms_arcsec"] = [float(per.dx_arcsec.std()), float(per.dy_arcsec.std())]
    print(s["label"], "per-epoch centroid offsets (cutout frame, arcsec):")
    print(per.to_string())
(OUT / "astrometry.json").write_text(json.dumps(res, indent=1, default=float))
