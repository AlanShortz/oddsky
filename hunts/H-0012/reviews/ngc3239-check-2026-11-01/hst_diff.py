"""HST difference imaging and photometry at the NGC 3239 mid-IR transient.

    uv run python -I hunts/H-0012/reviews/ngc3239-check-2026-11-01/hst_diff.py <scratch work dir>

Inputs: <work>/registered.npz from hst_register.py (all images on the 2021 F606W grid, uJy/px).
Outputs (here): hst_diff.json, hst_peaks_<diff>.csv, hst_stamps.png, hst_cutouts.npz (6"x6" stamps of every image).
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from astropy.io import fits
from astropy.wcs import WCS
from scipy import ndimage

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hst_lib as L  # noqa: E402

W_ = Path(sys.argv[1])
Z = np.load(W_ / "registered.npz")
wcs = WCS(fits.Header.fromstring(str(Z["ref_wcs"])))
WISE = (156.29118, 17.16387)  # wise_lc.py weighted position; 1-sigma ~0.2-0.3" per axis (see report)
CLAIM = (156.2910, 17.1639)
REFEREE_HST = (156.2912155590566, 17.163771631433413)
PIX = 0.04


def img(tag):
    return Z[tag].astype(float), Z[tag + "__ivar"].astype(float)


def combine2(a, ia, b, ib, k=5.0):
    """Two-exposure combination with cosmic-ray rejection: where they disagree by > k sigma take the lower."""
    va, vb = np.where(ia > 0, 1 / np.maximum(ia, 1e-30), np.inf), np.where(ib > 0, 1 / np.maximum(ib, 1e-30), np.inf)
    m = (a * ib + b * ia) / np.maximum(ia + ib, 1e-30)
    bad = np.abs(a - b) > k * np.sqrt(va + vb)
    out = np.where(bad, np.minimum(a, b), m)
    iv = np.where(bad, np.where(a < b, ia, ib), ia + ib)
    return out, iv, bad


images = {}
images["F606W_2021"] = img("16179_08_wfc3_uvis_f606w_ieb308")
images["F606W_2021_hc"] = img("16179_08_wfc3_uvis_f606w_ieb308hc")
images["F606W_2021_hg"] = img("16179_08_wfc3_uvis_f606w_ieb308hg")
images["F814W_2021"] = img("16179_08_wfc3_uvis_f814w_ieb308")
images["F814W_2021_hb"] = img("16179_08_wfc3_uvis_f814w_ieb308hb")
images["F814W_2021_he"] = img("16179_08_wfc3_uvis_f814w_ieb308he")
images["ACS_F606W_2022"] = img("15446_76_acs_wfc_f606w_jdrz76")
images["ACS_F606W_2022_le"] = img("15446_76_acs_wfc_f606w_jdrz76le")
images["ACS_F606W_2022_lf"] = img("15446_76_acs_wfc_f606w_jdrz76lf")
for f, (e1, e2) in {"F814W": ("u8", "uk"), "F555W": ("ui", "uu"), "F438W": ("ua", "un")}.items():
    a, ia = img(f"17502_14_wfc3_uvis_{f.lower()}_ifab14{e1}")
    b, ib = img(f"17502_14_wfc3_uvis_{f.lower()}_ifab14{e2}")
    c, ic, bad = combine2(a, ia, b, ib)
    images[f"{f}_2025"] = (c, ic)
    images[f"{f}_2025_{e1}"] = (a, ia)
    images[f"{f}_2025_{e2}"] = (b, ib)
images["F336W_2025"] = img("17502_14_wfc3_uvis_f336w_ifab14")
images["F275W_2025"] = img("17502_14_wfc3_uvis_f275w_ifab14")
images["F657N_2025"] = img("17502_51_wfc3_uvis_f657n_ifab51")

R = images["F606W_2021"][0]
ny, nx = R.shape
wx, wy = wcs.all_world2pix([WISE], 0)[0]
cx_, cy_ = wcs.all_world2pix([CLAIM], 0)[0]
rx, ry = wcs.all_world2pix([REFEREE_HST], 0)[0]
yy, xx = np.mgrid[:ny, :nx]

# PSF stars from the reference (compact, isolated, bright, unsaturated)
xs, ys, snr, _ = L.find_peaks(R, nsig=20)
st = []
for x, y in zip(xs, ys):
    f = L.gauss2d_fit(R, x, y, box=4)
    if f and 0.7 < f[3] < 1.4 and f[2] > 0:
        st.append(f[:3])
st = np.array(st)
dd = np.hypot(st[:, 0][:, None] - st[:, 0][None], st[:, 1][:, None] - st[:, 1][None])
np.fill_diagonal(dd, 99)
st = st[(dd.min(1) > 10)]
psfs = {}
for k, (im, iv) in images.items():
    try:
        psfs[k], npsf = L.build_psf(im, st[:, 0], st[:, 1], size=15)
    except ValueError:
        psfs[k] = None


def noise_scale(D, V, mask):
    z = (D / np.sqrt(V))[mask & np.isfinite(D) & np.isfinite(V) & (V > 0)]
    return 1.4826 * np.median(np.abs(z - np.median(z)))


def snr_map(D, V, psf):
    """Matched-filter S/N for a point source: sum(P d / v) / sqrt(sum(P^2 / v))."""
    Dn = np.nan_to_num(D)
    iv = np.where(np.isfinite(V) & (V > 0), 1 / V, 0)
    num = ndimage.correlate(Dn * iv, psf, mode="constant")
    den = ndimage.correlate(iv, psf ** 2, mode="constant")
    return np.where(den > 0, num / np.sqrt(np.maximum(den, 1e-30)), np.nan), np.where(den > 0, num / np.maximum(den, 1e-30), np.nan)


central = np.hypot(xx - wx, yy - wy) * PIX < 1.5
valid_core = (xx > 30) & (xx < nx - 30) & (yy > 30) & (yy < ny - 30)
diffs = {
    "F606W21-ACSF606W22": ("F606W_2021", "ACS_F606W_2022"),
    "F814W21-F814W25": ("F814W_2021", "F814W_2025"),
    "F606W21-F555W25": ("F606W_2021", "F555W_2025"),
    "ACSF606W22-F555W25": ("ACS_F606W_2022", "F555W_2025"),
    "F606W21hc-F606W21hg": ("F606W_2021_hc", "F606W_2021_hg"),
    "F814W21hb-F814W21he": ("F814W_2021_hb", "F814W_2021_he"),
    "F606W21hc-ACSF606W22": ("F606W_2021_hc", "ACS_F606W_2022"),
    "F606W21hg-ACSF606W22": ("F606W_2021_hg", "ACS_F606W_2022"),
    "F814W21hb-F814W25": ("F814W_2021_hb", "F814W_2025"),
    "F814W21he-F814W25": ("F814W_2021_he", "F814W_2025"),
}
out = dict(wise_pos=WISE, claim_pos=CLAIM, referee_hst_pos=REFEREE_HST, wise_pix=[float(wx), float(wy)], diffs={})
D_store = {}
for name, (a, b) in diffs.items():
    A, iA = images[a]
    B, iB = images[b]
    fitmask = valid_core & ~central & np.isfinite(A) & np.isfinite(B) & (iA > 0) & (iB > 0)
    # fit on a 20" box only (the kernel varies over the field)
    fitmask &= (np.abs(xx - wx) * PIX < 10) & (np.abs(yy - wy) * PIX < 10)
    conv, K, bk = L.fit_kernel(A, B, fitmask, half=5)
    D = A - conv
    VA = np.where(iA > 0, 1 / np.maximum(iA, 1e-30), np.nan)
    VB = np.where(iB > 0, 1 / np.maximum(iB, 1e-30), np.nan)
    VBc = ndimage.convolve(np.nan_to_num(VB), (K ** 2)[::-1, ::-1], mode="constant")
    V = VA + VBc
    # empirical rescaling (drizzle-correlated noise, source Poisson noise): robust std of D/sigma within 10"
    box = (np.abs(xx - wx) * PIX < 10) & (np.abs(yy - wy) * PIX < 10) & ~central & valid_core
    s = noise_scale(D, V, box)
    V = V * s ** 2
    psf = psfs[a]
    S, F = snr_map(D, V, psf)
    s2 = noise_scale(S, np.ones_like(S), box)  # matched-filter S/N rescale (pixel-correlated noise)
    S = S / s2
    D_store[name] = (D, V, S, F)
    # peaks in the 20" box
    reg = (np.abs(xx - wx) * PIX < 10) & (np.abs(yy - wy) * PIX < 10) & valid_core
    peaks = []
    for sign in (1, -1):
        Ss = sign * np.nan_to_num(S)
        pk = (Ss == ndimage.maximum_filter(Ss, 5)) & (Ss > 4.0) & reg
        for y, x in zip(*np.nonzero(pk)):
            peaks.append(dict(x=int(x), y=int(y), snr=float(S[y, x]), sep_wise=float(np.hypot(x - wx, y - wy) * PIX),
                              sep_refhst=float(np.hypot(x - rx, y - ry) * PIX), flux_uJy=float(F[y, x])))
    pk = pd.DataFrame(peaks)
    pk.to_csv(HERE / f"hst_peaks_{name}.csv", index=False)
    area = reg.sum() * PIX ** 2
    near = pk[pk.sep_wise < 1.5].sort_values("snr", ascending=False)
    out["diffs"][name] = dict(noise_scale_pix=float(s), noise_scale_mf=float(s2), kernel_sum=float(K.sum()), area_arcsec2=float(area),
                              n_pos_gt5=int((pk.snr > 5).sum()), n_neg_gt5=int((pk.snr < -5).sum()),
                              n_pos_gt8=int((pk.snr > 8).sum()), n_neg_gt8=int((pk.snr < -8).sum()),
                              near_wise=near.head(8).to_dict("records"))
    print(name, json.dumps({k: v for k, v in out["diffs"][name].items() if k != "near_wise"}), flush=True)
    print(near.head(6).to_string(), flush=True)

# --- the residual nearest the referee's position, in the main difference ---
D, V, S, F = D_store["F606W21-ACSF606W22"]
sub = (np.hypot(xx - rx, yy - ry) < 6)
iy, ix = np.unravel_index(np.nanargmax(np.where(sub, S, -np.inf)), S.shape)
fit = L.psf_phot(D, V, psfs["F606W_2021"], ix, iy, free=True, rad=3.5)
sx, sy = fit["x"], fit["y"]
sra, sdec = wcs.all_pix2world([[sx, sy]], 0)[0]
out["source"] = dict(pix=[sx, sy], ra=float(sra), dec=float(sdec), snr_mf=float(S[iy, ix]),
                     sep_wise_arcsec=float(np.hypot(sx - wx, sy - wy) * PIX), sep_claim_arcsec=float(np.hypot(sx - cx_, sy - cy_) * PIX),
                     sep_refhst_arcsec=float(np.hypot(sx - rx, sy - ry) * PIX),
                     dRA_arcsec_from_wise=float(-(sx - wx) * PIX), dDec_arcsec_from_wise=float((sy - wy) * PIX), fit_diff=fit)
# position error from the fit: centroid scatter by bootstrapping noise
rng = np.random.default_rng(1)
pos = []
P0 = psfs["F606W_2021"]
for _ in range(200):
    Dn = D + rng.normal(0, 1, D.shape) * 0  # placeholder (no-op)
    break
# injection-recovery for position and flux error at this flux into nearby blank-ish difference pixels
inj = []
h = P0.shape[0] // 2
for _ in range(400):
    x0 = rng.uniform(sx - 125, sx + 125); y0 = rng.uniform(sy - 125, sy + 125)
    if np.hypot(x0 - sx, y0 - sy) < 10 or not (40 < x0 < nx - 40 and 40 < y0 < ny - 40):
        continue
    xi, yi = int(round(x0)), int(round(y0))
    Dt = D.copy()
    Dt[yi - h:yi + h + 1, xi - h:xi + h + 1] += ndimage.shift(P0, (y0 - yi, x0 - xi), order=3) * fit["flux"]
    r = L.psf_phot(Dt, V, P0, x0 + rng.normal(0, 0.5), y0 + rng.normal(0, 0.5), free=True, rad=3.5)
    if r is None or not np.isfinite(r["flux"]):
        continue
    inj.append((r["x"] - x0, r["y"] - y0, r["flux"] - fit["flux"]))
inj = np.array(inj)
inj = inj[(np.abs(inj[:, :2]) < 3).all(1)]
rob = lambda v: float(1.4826 * np.median(np.abs(v - np.median(v))))
out["source"]["inj_pos_err_mas"] = [rob(inj[:, 0]) * 40, rob(inj[:, 1]) * 40]
out["source"]["inj_flux_err_uJy"] = rob(inj[:, 2])
out["source"]["mag_AB_diff"] = float(L.ab(fit["flux"]))

# --- forced PSF photometry at the source position on every image and difference ---
phot = {}
for k, (im, iv) in images.items():
    if psfs.get(k) is None:
        continue
    var = np.where(iv > 0, 1 / np.maximum(iv, 1e-30), np.nan)
    # empirical noise scale on the direct image is not meaningful (crowding); use local background scatter
    r = L.psf_phot(im, var, psfs[k], sx, sy, free=False, rad=3.5)
    rf = L.psf_phot(im, var, psfs[k], sx, sy, free=True, rad=3.5)
    # local crowding error: scatter of PSF fluxes at 200 random positions within 1.5" (excluding 0.2" of the source)
    loc = []
    for _ in range(300):
        x0 = sx + rng.uniform(-37, 37); y0 = sy + rng.uniform(-37, 37)
        if np.hypot(x0 - sx, y0 - sy) < 5:
            continue
        q = L.psf_phot(im, var, psfs[k], x0, y0, free=False, rad=3.5)
        if q and np.isfinite(q["flux"]):
            loc.append(q["flux"])
    loc = np.array(loc)
    phot[k] = dict(flux_uJy=r["flux"], err_stat=r["err"], err_local=rob(loc), local_median=float(np.median(loc)),
                   mag_AB=float(L.ab(r["flux"])), free_fit=dict(x=rf["x"], y=rf["y"], flux=rf["flux"], shift_mas=float(np.hypot(rf["x"] - sx, rf["y"] - sy) * 40)),
                   five_sigma_lim_AB=float(L.ab(5 * max(rob(loc), r["err"]))))
for name, (D, V, S, F) in D_store.items():
    a = diffs[name][0]
    r = L.psf_phot(D, V, psfs[a], sx, sy, free=False, rad=3.5)
    phot["DIFF " + name] = dict(flux_uJy=r["flux"], err=r["err"], snr=r["flux"] / r["err"], mag_AB=float(L.ab(r["flux"])),
                                snr_mf_at_pix=float(S[int(round(sy)), int(round(sx))]))
out["phot"] = phot
for k, v in phot.items():
    print(f"{k:32s}", {kk: (round(vv, 3) if isinstance(vv, float) else vv) for kk, vv in v.items() if kk != "free_fit"})
print(json.dumps(out["source"], indent=1, default=float))

# --- stamps ---
H = 50  # 4" boxes
show = ["F606W_2021", "F606W_2021_hc", "F606W_2021_hg", "ACS_F606W_2022", "F555W_2025", "F814W_2021", "F814W_2021_hb", "F814W_2021_he",
        "F814W_2025", "F438W_2025", "F336W_2025", "F657N_2025"]
dshow = ["F606W21-ACSF606W22", "F606W21hc-ACSF606W22", "F606W21hg-ACSF606W22", "F606W21-F555W25", "F814W21-F814W25",
         "F814W21hb-F814W25", "F814W21he-F814W25", "ACSF606W22-F555W25", "F606W21hc-F606W21hg", "F814W21hb-F814W21he"]
ix0, iy0 = int(round(sx)), int(round(sy))
fig, axs = plt.subplots(4, 6, figsize=(15, 10.5))
axs = axs.ravel()
stamps = {}
for i, k in enumerate(show):
    c = images[k][0][iy0 - H:iy0 + H + 1, ix0 - H:ix0 + H + 1]
    stamps[k] = c.astype(np.float32)
    v0, v1 = np.nanpercentile(c, [5, 99.5])
    axs[i].imshow(c, origin="lower", cmap="gray_r", vmin=v0, vmax=v1)
    axs[i].set_title(k, fontsize=7)
for j, k in enumerate(dshow):
    S = D_store[k][2]
    c = S[iy0 - H:iy0 + H + 1, ix0 - H:ix0 + H + 1]
    stamps["SNR " + k] = c.astype(np.float32)
    axs[len(show) + j].imshow(c, origin="lower", cmap="RdBu_r", vmin=-8, vmax=8)
    axs[len(show) + j].set_title("S/N " + k, fontsize=7)
for a in axs[:len(show) + len(dshow)]:
    a.plot(wx - ix0 + H, wy - iy0 + H, "+", color="lime", ms=12, mew=1.5)
    a.add_patch(plt.Circle((wx - ix0 + H, wy - iy0 + H), 0.3 / PIX, fill=False, color="lime", lw=0.8))
    a.add_patch(plt.Circle((wx - ix0 + H, wy - iy0 + H), 0.6 / PIX, fill=False, color="lime", lw=0.5, ls="--"))
    a.plot(sx - ix0 + H, sy - iy0 + H, "o", mfc="none", mec="orange", ms=10)
    a.set_xticks([]); a.set_yticks([])
for a in axs[len(show) + len(dshow):]:
    a.axis("off")
fig.suptitle("NGC 3239: 4\" boxes on the 2021-only residual (orange). WISE position (green +, 0.3\" and 0.6\" circles). N up, E left", fontsize=9)
fig.tight_layout()
fig.savefig(HERE / "hst_stamps.png", dpi=95)
np.savez_compressed(HERE / "hst_cutouts.npz", **stamps)
json.dump(out, open(HERE / "hst_diff.json", "w"), indent=1, default=float)
