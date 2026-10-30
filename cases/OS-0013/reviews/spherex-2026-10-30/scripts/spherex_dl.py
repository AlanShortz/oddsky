"""Download IBE cutouts (0.2 deg) of every SPHEREx QR L2 spectral image covering OS-0013 (from the IRSA SIA
query saved in data/sia_spherex.csv) and save slim copies: IMAGE, FLAGS, VARIANCE, ZODI, WCS-WAVE and only the PSF
zones that overlap the cutout (QR2: PSF cube, 11x11 zones; QR3: EPSF table, 21x21 zones). Usage: spherex_dl.py <sia_csv> <outdir>"""
import sys, os, csv, io, time, urllib.request
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from astropy.io import fits

RA, DEC, SIZE = 220.96627, -76.19612, 0.2
sia, out = sys.argv[1], sys.argv[2]
rows = [r for r in csv.DictReader(open(sia)) if r["obs_collection"] in ("spherex_qr2", "spherex_qr3")
        and r["dataproduct_subtype"] == "science"]
print(len(rows), "images")

def one(r):
    try:
        return _one(r)
    except Exception as e:
        return f"{out}/{r['obs_id']}", f"ERROR {type(e).__name__}: {e}"

def _one(r):
    det = r["energy_bandpassname"].split("-D")[1]
    fn = f"{out}/{r['obs_id']}_D{det}.fits"
    if os.path.exists(fn):
        return fn, "exists"
    url = f"{r['access_url']}?center={RA},{DEC}&size={SIZE}"
    for k in range(4):
        try:
            with urllib.request.urlopen(url, timeout=180) as u:
                raw = u.read()
            break
        except Exception as e:
            err = e; time.sleep(15 * (k + 1))
    else:
        return fn, f"FAIL {err}"
    h = fits.open(io.BytesIO(raw))
    hd = h["IMAGE"].header
    ny, nx = h["IMAGE"].data.shape
    # 'A' WCS is a plain LINEAR offset (do not let astropy apply the SIP terms to it)
    X = np.array([0, nx - 1]) + 1 - hd["CRPIX1A"] + hd["CRVAL1A"]
    Y = np.array([0, ny - 1]) + 1 - hd["CRPIX2A"] + hd["CRVAL2A"]
    if "PSF" in h:  # QR2: 10x-oversampled 101x101 PSF cube, 11x11 zones described in the header
        ph = h["PSF"].header
        zl = [(z, ph[f"XCTR_{z}"], ph[f"YCTR_{z}"], ph[f"XWID_{z}"], ph[f"YWID_{z}"]) for z in range(1, 122)]
    else:  # QR3: EPSF binary table, 21x21 zones, 5x-oversampled 33x33
        e = h["EPSF"].data
        zl = [(i + 1, e["XCENTER"][i], e["YCENTER"][i], e["XWIDTH"][i], e["YWIDTH"][i]) for i in range(len(e))]
    keep = [z for z, xc, yc, xw, yw in zl
            if xc + xw / 2 >= min(X) - 1 and xc - xw / 2 <= max(X) + 1 and yc + yw / 2 >= min(Y) - 1 and yc - yw / 2 <= max(Y) + 1]
    if "PSF" in h:
        psf = fits.ImageHDU(h["PSF"].data[[z - 1 for z in keep]], header=ph, name="PSF")
    else:
        psf = fits.BinTableHDU(h["EPSF"].data[[z - 1 for z in keep]], header=h["EPSF"].header, name="EPSF")
    psf.header["ZONES"] = ",".join(map(str, keep))
    hl = fits.HDUList([h[0], h["IMAGE"], h["FLAGS"], h["VARIANCE"], h["ZODI"], psf, h["WCS-WAVE"]])
    hl[0].header["SRCURL"] = r["access_url"]
    hl.writeto(fn + ".tmp", overwrite=True)
    os.replace(fn + ".tmp", fn)
    return fn, f"ok zones={keep}"

with ThreadPoolExecutor(3) as ex:
    for i, (fn, s) in enumerate(ex.map(one, rows)):
        if not s.startswith("ok") or i % 50 == 0:
            print(i, os.path.basename(fn), s, flush=True)
print("done")
