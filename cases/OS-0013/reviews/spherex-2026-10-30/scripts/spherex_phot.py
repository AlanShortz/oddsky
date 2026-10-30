"""Forced PSF photometry (and aperture photometry) of OS-0013 and its NEOWISE comparison stars on SPHEREx QR
L2 cutouts. Usage: [OS13_HALF=6] [OS13_FREE_DMAG=3] [OS13_BG=1] [OS13_PSF_MODE=auto] [OS13_CENTROID=0] spherex_phot.py <cutout_dir> <data_dir> <out_csv>
Model per source stamp (13x13 native px, 6.15"/px): sum_k F_k PSF_zone(x-x_k, y-y_k) + plane background.
Positions fixed at catalogue positions (Gaia DR3 propagated to the image epoch where matched, else CatWISE);
'bright' neighbours (W1 < W1_source + 3 mag, i.e. > ~6% of the source) have free fluxes, fainter ones are
subtracted at their catalogue-interpolated flux. PSF = per-exposure SPHEREx PSF of the nearest zone (10x
oversampled, +-5 native px), integrated over native pixels."""
import sys, glob, os, warnings
import numpy as np, pandas as pd
from astropy.io import fits
from astropy.wcs import WCS
from scipy.ndimage import map_coordinates
warnings.simplefilter("ignore")

cdir, ddir, outcsv = sys.argv[1], sys.argv[2], sys.argv[3]
RA0, DEC0 = 220.96627, -76.19612
HALF = int(os.environ.get("OS13_HALF", 6))  # stamp half-size, native px
CENTROID = os.environ.get("OS13_CENTROID", "0") == "1"  # also fit the measured source's position (slow)
BG_ORDER = int(os.environ.get("OS13_BG", 1))  # background polynomial order in the stamp (1 = plane, 2 = quadratic)
FREE_DMAG = float(os.environ.get("OS13_FREE_DMAG", 3))  # neighbours brighter than W1_src + this are free
BAD = sum(1 << b for b in [0, 1, 2, 4, 5, 6, 7, 9, 10, 11, 14, 15, 17, 19, 22, 23, 24, 26, 27, 28])
ARCSEC2_SR = (np.pi / 180 / 3600) ** 2
ZP = {"RP": (0.777, 2555.0), "J": (1.235, 1594.0), "H": (1.662, 1024.0), "K": (2.159, 666.7), "W1": (3.353, 309.54), "W2": (4.603, 171.787)}

# ---------------- catalogues
gaia = pd.read_csv(f"{ddir}/gaia.csv")
cw = pd.read_csv(f"{ddir}/catwise.csv")
aw = pd.read_csv(f"{ddir}/allwise.csv")
steps = pd.read_csv(f"{os.path.dirname(os.path.abspath(__file__))}/../../../data/external/referee_2026-10-27/f13.tbl.steps.csv")

def sky_sep(ra1, de1, ra2, de2):
    return 3600 * np.hypot((ra1 - ra2) * np.cos(np.radians(de2)), de1 - de2)

cw = cw[cw.w1mpro < 16.5].reset_index(drop=True)
src = []
for _, r in cw.iterrows():
    d = sky_sep(gaia.ra.values, gaia.dec.values, r.ra, r.dec)
    j = np.argmin(d)
    g = gaia.iloc[j] if (d[j] < 2.5 and gaia.phot_g_mean_mag.iloc[j] < 20) else None
    da = sky_sep(aw.ra.values, aw.dec.values, r.ra, r.dec); ja = np.argmin(da)
    a = aw.iloc[ja] if da[ja] < 3 else None
    mags = {"W1": r.w1mpro, "W2": r.w2mpro if np.isfinite(r.w2mpro) else r.w1mpro}
    if g is not None and np.isfinite(g.phot_rp_mean_mag): mags["RP"] = g.phot_rp_mean_mag
    if a is not None:
        for b, c in (("J", "j_m_2mass"), ("H", "h_m_2mass"), ("K", "k_m_2mass")):
            if np.isfinite(a[c]): mags[b] = a[c]
    src.append(dict(name=r.source_name, ra=g.ra if g is not None else r.ra, dec=g.dec if g is not None else r.dec,
                    pmra=g.pmra if g is not None and np.isfinite(g.pmra) else 0.0,
                    pmdec=g.pmdec if g is not None and np.isfinite(g.pmdec) else 0.0,
                    epoch=2016.0 if g is not None else 2015.4, mags=mags,
                    allwise=a.designation if a is not None else "", w1=r.w1mpro))
# Gaia-only sources (no CatWISE within 2.5") with G < 17.5: crude IR flux from RP with a Rayleigh-Jeans slope
for _, g in gaia[gaia.phot_g_mean_mag < 17.5].iterrows():
    if np.min(sky_sep(cw.ra.values, cw.dec.values, g.ra, g.dec)) < 2.5: continue
    rp = g.phot_rp_mean_mag if np.isfinite(g.phot_rp_mean_mag) else g.phot_g_mean_mag - 0.6
    w1 = rp - 1.2  # K-type-ish RP-W1, used only to decide free/fixed
    src.append(dict(name=f"Gaia{g.source_id}", ra=g.ra, dec=g.dec, pmra=np.nan_to_num(g.pmra), pmdec=np.nan_to_num(g.pmdec),
                    epoch=2016.0, mags={"RP": rp}, allwise="", w1=w1))
src = pd.DataFrame(src)

def ref_flux_mjy(mags, lam):
    """log-log interpolation of catalogue fluxes (mJy) to wavelength lam (um); RJ (F_nu ~ lam^-2) beyond the ends
    when only WISE is present, else linear extrapolation in log-log of the end segment."""
    bands = sorted(mags, key=lambda b: ZP[b][0])
    x = np.log([ZP[b][0] for b in bands]); y = np.log([ZP[b][1] * 1e3 * 10 ** (-0.4 * mags[b]) for b in bands])
    l = np.log(lam)
    if len(x) == 1:
        return np.exp(y[0] - 2 * (l - x[0]))
    if l < x[0] and set(bands) <= {"W1", "W2"}:  # WISE-only: K-star-like F_nu(lam)/F_nu(W1), flat-ish to 1.6 um
        return np.exp(y[0] + 1.0 * (x[0] - max(l, np.log(1.6))))
    if l <= x[0]: i = 0
    elif l >= x[-1]: i = len(x) - 2
    else: i = np.searchsorted(x, l) - 1
    s = (y[i + 1] - y[i]) / (x[i + 1] - x[i])
    return np.exp(y[i] + s * (l - x[i]))

# measured sources: target + the 27 NEOWISE field stars of C1 (pre-step W2 9.5-12.5)
st = steps.merge(aw, left_on="allwise_cntr", right_on="cntr")
st = st[(st.pre_w2 > 9.5) & (st.pre_w2 < 12.5)]
meas = []
for _, r in st.iterrows():
    k = np.argmin(sky_sep(src.ra.values, src.dec.values, r.ra, r.dec))
    meas.append(dict(sidx=k, allwise=r.designation, pre_w1=r.pre_w1, pre_w2=r.pre_w2, d_w1=r.d_w1, d_w2=r.d_w2,
                     sep=r.sep_w2, ext_flg=r.ext_flg, cc=r.cc_flags, J=r.j_m_2mass, H=r.h_m_2mass, K=r.k_m_2mass))
# plus the target's AllWISE neighbours within 40" with W1 < 14 (diagnostic only; AllWISE 2010 mags as reference)
nbr = aw[(sky_sep(aw.ra.values, aw.dec.values, RA0, DEC0) < 40) & (sky_sep(aw.ra.values, aw.dec.values, RA0, DEC0) > 3)
         & (aw.w1mpro < 14)]
for _, r in nbr.iterrows():
    k = np.argmin(sky_sep(src.ra.values, src.dec.values, r.ra, r.dec))
    meas.append(dict(sidx=k, allwise=r.designation, pre_w1=r.w1mpro, pre_w2=r.w2mpro, d_w1=np.nan, d_w2=np.nan,
                     sep=sky_sep(r.ra, r.dec, RA0, DEC0), ext_flg=r.ext_flg, cc=r.cc_flags, J=r.j_m_2mass, H=r.h_m_2mass,
                     K=r.k_m_2mass, neighbour=True))
meas = pd.DataFrame(meas); meas["neighbour"] = meas.neighbour.fillna(False).astype(bool)
print(len(src), "model sources;", len(meas), "measured sources", flush=True)

# ---------------- PSF helpers
PSF_MODE = os.environ.get("OS13_PSF_MODE", "auto")  # 'sum': integrate oversampled PSF over the native pixel;
# 'sample': treat it as a pixel-integrated ePSF and point-sample it (x os^2). 'auto' (default): sum for the QR2
# PSF cube, sample for the QR3 EPSF table -- the choices that minimise chi2 on the field stars (tested).
def load_psf(h, xd, yd):
    """PSF of the zone nearest detector position (xd, yd): (array[y, x], oversampling, centre index)."""
    if "PSF" in h:
        ph = h["PSF"].header; zones = [int(z) for z in ph["ZONES"].split(",")]
        zc = np.array([[ph[f"XCTR_{z}"], ph[f"YCTR_{z}"]] for z in zones])
        i = np.argmin(np.hypot(zc[:, 0] - xd, zc[:, 1] - yd))
        return h["PSF"].data[i].astype(float), int(ph["OVERSAMP"]), (h["PSF"].data.shape[-1] - 1) / 2, "sum"
    e = h["EPSF"].data
    i = np.argmin(np.hypot(e["XCENTER"] - xd, e["YCENTER"] - yd))
    a = np.array(e["EPSF"][i], dtype=float)
    return a, int(h["EPSF"].header["OVSMPX"]), (a.shape[-1] - 1) / 2, "sample"

def psf_native(P, dx, dy, xs, ys):
    """native-pixel PSF values at pixels (xs, ys) for a source at sub-pixel position (dx, dy)."""
    cube, os_, c, native_mode = P
    if (PSF_MODE if PSF_MODE != "auto" else native_mode) == "sample":
        v = map_coordinates(cube, [(c + os_ * (ys - dy)).ravel(), (c + os_ * (xs - dx)).ravel()], order=3, mode="constant", cval=0.0)
        return v.reshape(xs.shape) * os_ ** 2
    sub = np.arange(os_) - (os_ - 1) / 2
    ox = c + os_ * (xs - dx)[..., None, None] + sub[None, None, None, :]
    oy = c + os_ * (ys - dy)[..., None, None] + sub[None, None, :, None]
    ox = np.broadcast_to(ox, xs.shape + (os_, os_)); oy = np.broadcast_to(oy, xs.shape + (os_, os_))
    v = map_coordinates(cube, [oy.ravel(), ox.ravel()], order=1, mode="constant", cval=0.0)
    return v.reshape(xs.shape + (os_ * os_,)).sum(-1)

rows = []
files = sorted(glob.glob(f"{cdir}/*.fits"))
for fi, fn in enumerate(files):
    h = fits.open(fn)
    hd = h["IMAGE"].header
    img = h["IMAGE"].data.astype(float); var = h["VARIANCE"].data.astype(float); flg = h["FLAGS"].data
    ny, nx = img.shape
    w = WCS(hd); ww = WCS(hd, fobj=h, key="W")
    mjd = hd["MJD-AVG"]; yr = 2000 + (mjd - 51544.5) / 365.25
    omega = hd["OMEGA_MEDIAN"] * ARCSEC2_SR
    det = int(hd["DETECTOR"])
    # source pixel positions at this epoch
    dt = yr - src.epoch.values
    ra = src.ra.values + dt * src.pmra.values / 3.6e6 / np.cos(np.radians(src.dec.values))
    de = src.dec.values + dt * src.pmdec.values / 3.6e6
    px, py = w.all_world2pix(ra, de, 0)
    good = (flg & BAD) == 0
    for _, m in meas.iterrows():
        if CENTROID and (det not in (3, 6) or m.neighbour or m.pre_w2 > 11.6):
            continue  # centroid mode: K-band (D3) and W2-like (D6) images, target and comps with W2 < 11.6 only
        k = m.sidx; x0, y0 = px[k], py[k]
        ix, iy = int(round(x0)), int(round(y0))
        if ix - HALF < 0 or iy - HALF < 0 or ix + HALF >= nx or iy + HALF >= ny:
            continue
        lam, dlam = [float(v) for v in ww.pixel_to_world_values(x0, y0)]
        sl = (slice(iy - HALF, iy + HALF + 1), slice(ix - HALF, ix + HALF + 1))
        Y, X = np.mgrid[iy - HALF:iy + HALF + 1, ix - HALF:ix + HALF + 1].astype(float)
        d = img[sl]; v = var[sl]; g = good[sl] & np.isfinite(d) & np.isfinite(v) & (v > 0)
        # PSF zone nearest the source (detector coords = cutout + offset of the linear 'A' WCS)
        xd, yd = x0 + 1 - hd["CRPIX1A"] + hd["CRVAL1A"], y0 + 1 - hd["CRPIX2A"] + hd["CRVAL2A"]
        cube = load_psf(h, xd, yd)
        # model components
        near = np.where((np.abs(px - x0) < HALF + 5.5) & (np.abs(py - y0) < HALF + 5.5))[0]
        fixed = np.zeros_like(d); cols = []; names = []
        for j in near:
            pj = psf_native(cube, px[j], py[j], X, Y)
            if pj.sum() < 1e-4: continue
            if j == k or src.w1.iloc[j] < src.w1.iloc[k] + FREE_DMAG:
                cols.append(pj); names.append(j)
            else:
                fixed += pj * ref_flux_mjy(src.mags.iloc[j], lam) / (omega * 1e9)
        ci = names.index(k)
        u, vv = (X - x0) / HALF, (Y - y0) / HALF
        bgt = [np.ones_like(d), u, vv] + ([u * u, u * vv, vv * vv] if BG_ORDER >= 2 else [])
        A = np.array(cols + bgt).reshape(len(cols) + len(bgt), -1).T
        b = (d - fixed).ravel(); wgt = 1 / np.sqrt(v.ravel()); gg = g.ravel()
        nbad_core = int((~g)[HALF - 1:HALF + 2, HALF - 1:HALF + 2].sum())
        if gg.sum() < A.shape[1] + 10:
            continue
        Aw = A[gg] * wgt[gg, None]; bw = b[gg] * wgt[gg]
        coef, *_ = np.linalg.lstsq(Aw, bw, rcond=None)
        res = bw - Aw @ coef; dof = gg.sum() - A.shape[1]; chi2 = (res ** 2).sum() / dof
        cov = np.linalg.pinv(Aw.T @ Aw)
        f = coef[ci] * omega * 1e9; ef = np.sqrt(cov[ci, ci]) * omega * 1e9
        # aperture photometry (r=2 px) with an annulus 4-7 px, raw and with fitted/fixed neighbours removed
        r = np.hypot(X - x0, Y - y0)
        nb = fixed.copy()
        for c, j in zip(coef[:len(names)], names):
            if j != k: nb += c * psf_native(cube, px[j], py[j], X, Y)
        ap = r < 2.0; an = (r > 4) & (r < 7) & g
        out = {}
        for tag, im in (("ap_raw", d), ("ap_nbsub", d - nb)):
            if (~g[ap]).any() or an.sum() < 10:
                out[tag] = np.nan; continue
            bg = np.median(im[an])
            out[tag] = (im[ap] - bg).sum() * omega * 1e9
        cen = {}
        if CENTROID:  # grid search of the measured source's position (0.1 px over +-0.6 px, then 0.02 px), neighbours fixed
            best = (np.inf, 0.0, 0.0)
            for grid in (np.arange(-0.6, 0.601, 0.1), np.arange(-0.1, 0.101, 0.02)):
                bx, by = best[1], best[2]
                for ddx in bx + grid:
                    for ddy in by + grid:
                        A2 = A.copy(); A2[:, ci] = psf_native(cube, x0 + ddx, y0 + ddy, X, Y).ravel()
                        A2w = A2[gg] * wgt[gg, None]
                        c2, *_ = np.linalg.lstsq(A2w, bw, rcond=None)
                        r2 = ((bw - A2w @ c2) ** 2).sum()
                        if r2 < best[0]: best = (r2, ddx, ddy)
            r0, d0 = w.all_pix2world([[x0, y0], [x0 + best[1], y0 + best[2]]], 0).T
            cen = dict(cdx=best[1], cdy=best[2], dra_as=(r0[1] - r0[0]) * 3600 * np.cos(np.radians(d0[0])), ddec_as=(d0[1] - d0[0]) * 3600)
        apcorr = psf_native(cube, x0, y0, X, Y)[ap].sum()  # PSF fraction in the aperture (within the +-5 px model)
        rows.append(dict(file=os.path.basename(fn), release="qr3" if "EPSF" in h else "qr2", obs_id=hd["OBSID"], det=det, mjd=mjd, lam=lam, dlam=dlam,
                         allwise=m.allwise, sidx=k, x=x0, y=y0, f_psf=f, e_psf=ef, chi2=chi2, nfree=len(names),
                         nbad_core=nbad_core, f_ap_raw=out["ap_raw"], f_ap_nbsub=out["ap_nbsub"], apfrac=apcorr,
                         fixed_in_ap=(fixed[ap].sum() * omega * 1e9), **cen))
    if fi % 50 == 0:
        print(fi, len(files), len(rows), flush=True)
pd.DataFrame(rows).to_csv(outcsv, index=False)
meas.to_csv(outcsv.replace(".csv", "_sources.csv"), index=False)
print("wrote", outcsv, len(rows))
