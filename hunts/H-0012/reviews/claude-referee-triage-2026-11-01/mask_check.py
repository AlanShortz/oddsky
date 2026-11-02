"""Why SN 2011dh (M51) and SN 2014J (M82) were missed: rebuild the runner's masks and difference
stacks for NGC5194 on 2029p469 and MESSIER082 on 1507p696 exactly as infra/gcp/imaging_tile.py does
(galaxy_from_row, default Config), then report each mask component at the SN positions, forced W1/W2
photometry there, and the masked fraction of the search area.

    uv run python hunts/H-0012/reviews/claude-referee-triage-2026-11-01/mask_check.py

Scratch stacks go to $TMPDIR/h0012_referee_triage (deleted by hand afterwards); small outputs
(mask_check.json, mask_check_*.png, sn_forced_*.csv) next to this script.
"""
import json
import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from astropy.io import fits
from scipy import ndimage

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "infra" / "gcp"))
from imaging_tile import galaxy_from_row  # noqa: E402

from oddsky.imaging import F0_JY, PIXSCALE, detect, diff, fetch, photometry  # noqa: E402
from oddsky.imaging.pipeline import Config, analyse_stack, build_masks, window_for  # noqa: E402
from oddsky.imaging.stack import load_stack  # noqa: E402

SCR = Path(os.environ.get("TMPDIR", "/tmp")) / "h0012_referee_triage"
T = pd.read_csv(ROOT / "hunts/H-0012/work/targets_10mpc.csv").set_index("Name", drop=False)
CASES = {
    ("NGC5194", "2029p469"): [("SN 2011dh", 202.52104, 47.16969, "2011-06-01"), ("AT 2019abn", 202.42717, 47.18786, "2019-01-22"),
                              ("SN 2005cs", 202.46979, 47.17651, "2005-06-28"), ("M51 nucleus (NED)", 202.469575, 47.195258, "")],
    ("MESSIER082", "1507p696"): [("SN 2014J", 148.92558, 69.67391, "2014-01-21"), ("AT 2020cnn", 149.0700, 69.6950, "2020-02-12"),
                                 ("M82 nucleus (2.2um peak)", 148.96969, 69.67938, "")],
}
cfg = Config()
out = {}
for (gname, tile), sne in CASES.items():
    gal = galaxy_from_row(T.loc[gname])
    rec = dict(galaxy=gname, tile=tile, centre=[gal.ra, gal.dec], a26_arcmin=gal.d25_arcmin,
               nucleus_mask_arcsec=gal.nucleus_mask_arcsec, bands={})
    for band in (1, 2):
        win = window_for(gal, tile, cfg.margin)
        st = load_stack(tile, band, window=win)
        dets, prod = analyse_stack(st, gal, cfg, out=None)
        refs = prod["refs"]
        ref0, refvar0 = refs[min(refs)]
        invalid, bright, nucleus, outside = build_masks(st, gal, cfg, ref0, refvar0)
        # separate the two halves of `bright`: reference-peak circles vs unWISE bitmask
        bright_peaks = detect.bright_star_mask(ref0, refvar0, 10 ** ((22.5 - cfg.bright_mag[band]) / 2.5))
        y0, y1, x0, x1 = st.window
        msk = fits.getdata(fetch.fetch_mask(tile))[y0:y1, x0:x1].astype(np.int64)
        art = ndimage.binary_dilation((msk & fetch.ARTIFACT_BITS) != 0, iterations=2)
        det_mask = prod["det_mask"]
        search = ~outside
        frac = dict(search_px=int(search.sum()),
                    masked_total=float((det_mask & search).sum() / search.sum()),
                    bright_peaks=float((bright_peaks & search).sum() / search.sum()),
                    unwise_bits=float((art & search).sum() / search.sum()),
                    nucleus=float((nucleus & search).sum() / search.sum()),
                    invalid=float((invalid & search).sum() / search.sum()))
        # fraction of the galaxy's (sky-subtracted) W1/W2 light that falls on masked pixels
        sky = np.nanmedian(ref0[outside]) if outside.any() else 0.0
        lightmap = np.clip(np.nan_to_num(ref0 - sky), 0, None) * search
        frac["light_masked"] = float((lightmap * det_mask).sum() / max(lightmap.sum(), 1e-9))
        bits_hist = {}
        for b in range(31):
            m = ((msk >> b) & 1).astype(bool) & search
            if m.any():
                bits_hist[b] = float(m.sum() / search.sum())
        frac["bit_fractions"] = bits_hist
        season = st.season
        D, S, psfs = prod["D"], prod["S"], prod["psfs"]
        sn_rows = {}
        for name, ra, dec, disc in sne:
            x, y = st.wcs.all_world2pix([[ra, dec]], 0)[0]
            xi, yi = int(round(x)), int(round(y))
            inwin = 0 <= xi < ref0.shape[1] and 0 <= yi < ref0.shape[0]
            r = dict(x=float(x), y=float(y), in_window=bool(inwin))
            if inwin:
                bits = int(msk[yi, xi])
                r.update(det_masked=bool(det_mask[yi, xi]), bright_peak=bool(bright_peaks[yi, xi]),
                         unwise_art=bool(art[yi, xi]), nucleus=bool(nucleus[yi, xi]), outside=bool(outside[yi, xi]),
                         invalid=bool(invalid[yi, xi]), bits_set=[b for b in range(31) if bits >> b & 1],
                         ref_pix_nmgy=float(ref0[yi, xi]),
                         dist_to_unmasked_px=float(ndimage.distance_transform_edt(det_mask)[yi, xi]),
                         sep_from_centre_arcsec=float(np.hypot(((ra - gal.ra + 180) % 360 - 180) * np.cos(np.radians(dec)),
                                                               dec - gal.dec) * 3600))
                f, e = photometry.forced_lightcurve(D, S, psfs, season, x, y)
                ujy = F0_JY[band] * 1e-3
                pd.DataFrame(dict(epoch=st.epochs, mjd=st.mjd, season=season, flux_ujy=f * ujy, err_ujy=e * ujy)).to_csv(
                    HERE / f"sn_forced_{name.replace(' ', '_').replace('(', '').replace(')', '')}_w{band}.csv", index=False)
                k = int(np.nanargmax(f)) if np.isfinite(f).any() else 0
                r.update(max_flux_ujy=float(np.nanmax(f) * ujy), max_mjd=float(st.mjd[k]), max_snr=float(f[k] / e[k]))
                # nearest single-epoch detections at that position in this rerun (masked pixels can't have any)
                if len(dets):
                    s = np.hypot((dets.ra - ra) * np.cos(np.radians(dec)), dets.dec - dec) * 3600
                    r["n_det_within_6"] = int((s < 6).sum())
            sn_rows[name] = r
        rec["bands"][band] = dict(window=list(st.window), epochs=st.epochs.tolist(), mjd=[float(m) for m in st.mjd],
                                  fractions=frac, positions=sn_rows)
        # figure
        fig, ax = plt.subplots(1, 3, figsize=(15, 5))
        v0, v1 = np.nanpercentile(ref0, [5, 99.7])
        ax[0].imshow(np.arcsinh((ref0 - v0) / (v1 - v0) * 20), origin="lower", cmap="gray")
        ax[0].set_title(f"{gname} W{band} reference")
        comp = np.zeros(ref0.shape + (3,))
        comp[..., 0] = bright_peaks
        comp[..., 1] = art
        comp[..., 2] = np.maximum(nucleus.astype(float), outside * 0.3)
        ax[1].imshow(comp, origin="lower")
        ax[1].set_title("R: bright-peak circles  G: unWISE bits  B: nucleus (dim: outside)")
        ax[2].imshow(np.arcsinh((ref0 - v0) / (v1 - v0) * 20) * ~det_mask, origin="lower", cmap="gray")
        ax[2].set_title(f"unmasked search pixels; masked {frac['masked_total']:.1%} of area, {frac['light_masked']:.1%} of light")
        for a in ax:
            for name, ra, dec, _ in sne:
                x, y = st.wcs.all_world2pix([[ra, dec]], 0)[0]
                a.plot(x, y, "o", mfc="none", mec="yellow", ms=12)
                a.text(x + 6, y + 6, name, color="yellow", fontsize=7)
        fig.tight_layout()
        fig.savefig(HERE / f"mask_check_{gname}_w{band}.png", dpi=70)
        plt.close(fig)
        print(gname, band, json.dumps(frac)[:400], flush=True)
        for n_, r_ in sn_rows.items():
            print("   ", n_, r_, flush=True)
        del st, prod, D, S
    out[gname] = rec
(HERE / "mask_check.json").write_text(json.dumps(out, indent=1, default=str))
