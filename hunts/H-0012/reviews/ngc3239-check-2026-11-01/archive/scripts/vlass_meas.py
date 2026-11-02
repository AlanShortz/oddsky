"""Measure VLASS QL cutouts at the claimed position. usage: python -I vlass_meas.py <dir>"""
import sys, numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from astropy.coordinates import SkyCoord
import astropy.units as u
d = sys.argv[1]
tgt = SkyCoord(156.2910, 17.1639, unit='deg')
refs = {"NVSS/VLASS1 extended src 41\" SW": SkyCoord("10h25m07.45s +17d09m27.3s"), "NGC3239 NED centre": SkyCoord(156.270475,17.16363,unit='deg'),"SN2012A":SkyCoord("10h25m07.39s +17d09m14.6s")}
for e in ["1.2","2.2","3.2"]:
    h = fits.open(f"{d}/vlass{e}_cutout.fits")[0]; hr = fits.open(f"{d}/vlass{e}.rms_cutout.fits")[0]
    im = np.squeeze(h.data).astype(float)*1e6; rms = np.squeeze(hr.data).astype(float)*1e6  # uJy/beam
    w = WCS(h.header).celestial
    yy, xx = np.mgrid[:im.shape[0], :im.shape[1]]
    ra, dec = w.wcs_pix2world(xx, yy, 0)
    sep = SkyCoord(ra, dec, unit='deg').separation(tgt).arcsec
    px = np.unravel_index(np.argmin(sep), sep.shape)
    hdr = h.header
    print(f"== VLASS{e}  DATE-OBS={hdr.get('DATE-OBS')}  BMAJ={hdr.get('BMAJ',0)*3600:.2f}\" BMIN={hdr.get('BMIN',0)*3600:.2f}\" shape={im.shape} pix={abs(hdr.get('CDELT1',0))*3600:.2f}\"")
    m1 = sep < 1.5; m5 = sep < 5
    ann = (sep > 10) & (sep < 60)
    loc_std = 1.4826*np.nanmedian(np.abs(im[ann]-np.nanmedian(im[ann])))
    print(f"  value at nearest pixel ({sep[px]:.2f}\" off): {im[px]:.0f} uJy/beam;  rms-map there: {rms[px]:.0f} uJy/beam;  local robust std (10-60\" annulus): {loc_std:.0f} uJy/beam")
    print(f"  max within 1.5\": {np.nanmax(im[m1]):.0f} uJy/beam  (= {np.nanmax(im[m1])/rms[px]:.1f} sigma);  max within 5\": {np.nanmax(im[m5]):.0f} uJy/beam (= {np.nanmax(im[m5])/rms[px]:.1f} sigma) at {sep[m5][np.nanargmax(im[m5])]:.1f}\"")
    print(f"  3-sigma upper limit (3*rms + max(0,peak@pos)): {3*rms[px]+max(0,im[px]):.0f} uJy;  plain 3*rms: {3*rms[px]:.0f} uJy")
    m60 = (sep < 60) & (im > 5*rms)
    if m60.any():
        # list local maxima > 5 sigma within 60"
        from scipy.ndimage import maximum_filter
        mx = (im == maximum_filter(im, size=5)) & m60
        for j,i in zip(*np.where(mx)):
            c = SkyCoord(ra[j,i], dec[j,i], unit='deg')
            print(f"    >5sigma peak {im[j,i]:.0f} uJy/beam ({im[j,i]/rms[j,i]:.1f}sig) at {c.to_string('hmsdms',precision=2)}  sep={sep[j,i]:.1f}\"")
    else:
        print("    no >5sigma pixels within 60\"")
