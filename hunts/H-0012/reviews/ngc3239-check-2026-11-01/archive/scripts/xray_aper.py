"""Simple aperture photometry at the claimed position on Chandra evt2 / Swift XRT PC cleaned event files.
usage: python -I xray_aper.py <evtfile> <chandra|xrt>"""
import sys, numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from astropy.coordinates import SkyCoord
import astropy.units as u
f, kind = sys.argv[1], sys.argv[2]
tgt = SkyCoord(156.2910, 17.1639, unit='deg')
others = {"eRASS/LSXPS J102508.0+170946": SkyCoord(156.28341,17.16305,unit='deg'),
          "NGC3239 NED centre": SkyCoord(156.270475,17.16363,unit='deg'),
          "SN2012A": SkyCoord("10h25m07.39s +17d09m14.6s")}
h = fits.open(f, memmap=False)
ev = h['EVENTS']; hd = ev.header; d = ev.data
cols = [c.upper() for c in ev.columns.names]
ix, iy = cols.index('X')+1, cols.index('Y')+1
w = WCS(naxis=2)
w.wcs.ctype = [hd[f'TCTYP{ix}'], hd[f'TCTYP{iy}']]
w.wcs.crval = [hd[f'TCRVL{ix}'], hd[f'TCRVL{iy}']]
w.wcs.crpix = [hd[f'TCRPX{ix}'], hd[f'TCRPX{iy}']]
w.wcs.cdelt = [hd[f'TCDLT{ix}'], hd[f'TCDLT{iy}']]
pi_kev = d['energy']/1000. if 'ENERGY' in cols else d['PI']*0.01
if kind=='chandra':
    sel = (pi_kev>0.5)&(pi_kev<7.0); rs, b1, b2 = 2.0, 6.0, 15.0; band='0.5-7 keV'
else:
    sel = (d['PI']>=30)&(d['PI']<=1000); rs, b1, b2 = 12.0, 50.0, 100.0; band='0.3-10 keV'
x, y = d['x'][sel], d['y'][sel]
ra, dec = w.wcs_pix2world(x, y, 1)
ec = SkyCoord(ra, dec, unit='deg')
expo = hd.get('EXPOSURE', hd.get('LIVETIME'))
print(f"file={f.split('/')[-1]} obj={hd.get('OBJECT')} date-obs={hd.get('DATE-OBS')} exposure={expo:.0f}s band={band} nev={sel.sum()}")
def phot(c, label):
    sep = ec.separation(c).arcsec
    n = int((sep<rs).sum()); nb = int(((sep>b1)&(sep<b2)).sum())
    ab = (b2**2-b1**2)/rs**2; bexp = nb/ab
    # 3-sigma (99.73%) KBN upper limit
    # Kraft, Burrows & Nousek (1991) Bayesian upper limit, flat prior s>=0, numerically
    sg = np.linspace(0, n + 10*np.sqrt(n+1) + 20, 200001)
    lp = n*np.log(sg+bexp+1e-300) - (sg+bexp); pst = np.exp(lp-lp.max()); cdf = np.cumsum(pst); cdf/=cdf[-1]
    hi = float(sg[np.searchsorted(cdf, 0.9973)]); lo = float(sg[np.searchsorted(cdf, 0.00135)])
    print(f"  {label:32s} r<{rs}\": N={n}  bkg_expected={bexp:.2f} (annulus {b1}-{b2}\": {nb})  net={n-bexp:.2f}  KBN99.73% interval=[{lo:.2f},{hi:.2f}] cts  -> rate_UL={hi/expo:.2e} ct/s")
    return n, bexp, hi
phot(tgt, "CLAIM 156.2910 +17.1639")
for k,c in others.items(): phot(c, k)
# brightest event concentration within 40" of the target (crude source finding on 2" grid)
if kind=='chandra':
    m = ec.separation(tgt).arcsec < 40
    print("  events within 40\" of claim:", m.sum())
    dra = (ra[m]-tgt.ra.deg)*np.cos(np.radians(tgt.dec.deg))*3600; dde=(dec[m]-tgt.dec.deg)*3600
    H, xe, ye = np.histogram2d(dra, dde, bins=40, range=[[-40,40],[-40,40]])
    for i,j in zip(*np.unravel_index(np.argsort(H.ravel())[::-1][:6], H.shape)):
        print(f"    2\"-pixel peak: dRA*cosD={0.5*(xe[i]+xe[i+1]):+.0f}\" dDec={0.5*(ye[j]+ye[j+1]):+.0f}\"  counts={int(H[i,j])}")
