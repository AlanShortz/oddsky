"""PSF photometry check: the same two-visit statistic from ANGST DOLPHOT catalogues (Dalcanton+2009), where ANGST reduced
both visits of a field. Two measurements per galaxy:

  same stars   the stars of the Hubble Source Catalog measurement (work/pairs), with their change re-measured by DOLPHOT
  psf only     every DOLPHOT star matched between the two visits, boxes rebuilt from DOLPHOT magnitudes and colours

Catalogues are the "gst" (good star) files; F814W is MAG2_ACS (Vega). Each pair of fields is tied with an affine fit
before matching at 0.07 arcsec, and a shifted-position chance rate is recorded. Writes work/psf.csv, work/psf_stars.parquet.
"""
import io, sys, pathlib, itertools
import numpy as np, pandas as pd, httpx
from astropy.io import fits
from scipy.spatial import cKDTree
from oddsky.analysis import twopoint

RUN = pathlib.Path.home() / "oddsky-runs/h0019/angst"; RUN.mkdir(exist_ok=True)
HERE = pathlib.Path(__file__).resolve().parents[1]
BASE = "https://archive.stsci.edu/hlsps/angst/acs/hlsp_angst_hst_acs-wfc_{}_v1_gst.fits"
# red cut in the Vega colour of each filter pair (the AB cuts of 04_measure.py moved to Vega), and E(colour)/E(B-V)
RED = {"f606w-f814w": (0.79, 1.0), "f555w-f814w": (1.05, 1.3), "f475w-f814w": (1.60, 2.1)}
GAL = {
    "NGC0300": (["9492-ngc300-%d_f555w-f814w" % i for i in range(1, 7)], ["10915-ngc0300-wide%d_f606w-f814w" % i for i in (1, 2, 3)]),
    "GARLAND": (["9381-ngc3077-phoenix_f555w-f814w"], ["10915-ngc3077-wide1_f606w-f814w"]),
    "KKH37": (["9771-kkh37_f606w-f814w"], ["10915-kkh37_f475w-f814w"]),
    "NGC4163": (["9771-ngc4163_f606w-f814w"], ["10915-ngc4163_f606w-f814w"]),
    "IC2574": (["9755-ic2574-sgs_f555w-f814w"], ["10605-ic-2574-1-copy_f555w-f814w", "10605-ic-2574-2_f555w-f814w"]),
    "MESSIER081": (["10584-m81-field-%d_f606w-f814w" % i for i in (1, 2, 27, 28, 29)], ["10915-m81-deep_f606w-f814w", "10523-ngc3031-halo-1_f606w-f814w", "10523-ngc3031-halo-2_f606w-f814w"]),
    "NGC0253": (["10523-ngc0253-halo-11_f606w-f814w"], ["10915-ngc0253-wide%d_f606w-f814w" % i for i in range(1, 6)]),
    "NGC2403": (["10182-sn-ngc2403-pr_f606w-f814w"], ["10523-ngc2403-halo-1_f606w-f814w", "10523-ngc2403-halo-6_f606w-f814w"]),
}
meas = pd.read_csv(HERE / "work/measure.csv").set_index("name")
# galaxies not in the HSC measurement: predicted tip, 5 log d - 4.05 + 0.42 A_B + 0.68 (Karachentsev+2013: M81 3.63 Mpc, A_B 0.35)
TIP_PRED_AB = {"MESSIER081": 27.80 - 4.05 + 0.15 + 0.68}


def load(tag, maglim):
    f = RUN / f"{tag}.parquet"
    if not f.exists():
        r = httpx.get(BASE.format(tag), timeout=600, follow_redirects=True); r.raise_for_status()
        t = fits.open(io.BytesIO(r.content))[1].data
        df = pd.DataFrame({k.lower(): np.asarray(t[k]).astype("f8") for k in ("RA", "DEC", "MAG1_ACS", "MAG2_ACS", "MAG2_ERR", "CROWD2", "SHARP2", "SNR2")})
        df[df.mag2_acs < 27].to_parquet(f)
    df = pd.read_parquet(f)
    return df[df.mag2_acs < maglim].reset_index(drop=True).assign(colkind=tag.split("_", 1)[1])


def tie(a, b, cd):
    """Affine fit of a's positions onto b's (arcsec, tangent plane about b's median). Returns matched index pairs, the
    rms of the fit, and the chance-match count for positions shifted by 3 arcsec."""
    ra0, dec0 = b.ra.median(), b.dec.median()
    xy = lambda d: np.c_[(d.ra.values - ra0) * cd * 3600, (d.dec.values - dec0) * 3600]
    A, B = xy(a), xy(b)
    if np.hypot(*(np.median(A, 0) - np.median(B, 0))) > 260:
        return None
    tb = cKDTree(B)
    bright_a = np.argsort(a.mag2_acs.values)[:6000]
    # coarse offset by histogram of all pair offsets within 3 arcsec among bright stars
    nb = tb.query_ball_point(A[bright_a], 3.0)
    off = np.array([B[j] - A[i] for i, js in zip(bright_a, nb) for j in js])
    if len(off) < 50:
        return None
    h, xe, ye = np.histogram2d(off[:, 0], off[:, 1], bins=60, range=[[-3, 3], [-3, 3]])
    ix, iy = np.unravel_index(h.argmax(), h.shape); shift = np.array([(xe[ix] + xe[ix + 1]) / 2, (ye[iy] + ye[iy + 1]) / 2])
    M = np.eye(2); t = shift
    for rad in (0.3, 0.12, 0.07, 0.07):
        A2 = A @ M.T + t
        d, j = tb.query(A2, distance_upper_bound=rad); ok = np.isfinite(d)
        if ok.sum() < 30:
            return None
        X = np.c_[A[ok], np.ones(ok.sum())]; sol, *_ = np.linalg.lstsq(X, B[j[ok]], rcond=None)
        M, t = sol[:2].T, sol[2]
    A2 = A @ M.T + t
    d, j = tb.query(A2, distance_upper_bound=0.07); ok = np.isfinite(d)
    dc, _ = tb.query(A2 + [3.0, 0.0], distance_upper_bound=0.07)
    return np.where(ok)[0], j[ok], float(np.sqrt(np.mean(d[ok] ** 2))), int(np.isfinite(dc).sum())


rows, stars = [], []
for gal, (e1, e2) in GAL.items():
    if len(sys.argv) > 1 and gal not in sys.argv[1:]:
        continue
    key = gal
    tip_ab = float(meas.tip[gal]) if gal in meas.index and meas.tip[gal] == meas.tip[gal] else TIP_PRED_AB.get(gal)
    if tip_ab is None:
        print(gal, "no tip"); continue
    tip = tip_ab - 0.68                       # AB aperture magnitude to Vega total, as in 03_fetch.py
    try:
        E1 = [load(t, tip + 1.2) for t in e1]; E2 = [load(t, tip + 1.2) for t in e2]
    except Exception as e:  # noqa: BLE001
        print(gal, "download failed", repr(e)[:100]); continue
    allred = pd.concat(E1)
    edge, sig = twopoint.tip_edge(allred.mag2_acs.values[(allred.mag1_acs - allred.mag2_acs).values > 0.8], tip, half_window=0.3)
    if sig >= 4:
        tip = edge
    cd = np.cos(np.radians(E1[0].dec.median())); parts = []
    for (ia, a), (ib, b) in itertools.product(enumerate(E1), enumerate(E2)):
        r = tie(a, b, cd)
        if r is None or len(r[0]) < 200:
            continue
        i, j, rms, chance = r
        m = pd.DataFrame({"ra": b.ra.values[j], "dec": b.dec.values[j], "m1": a.mag2_acs.values[i], "m2": b.mag2_acs.values[j],
                          "col": (a.mag1_acs - a.mag2_acs).values[i], "colkind": a.colkind.values[i], "crowd": np.maximum(a.crowd2.values[i], b.crowd2.values[j]),
                          "pair": f"{e1[ia]}+{e2[ib]}"})
        m["d"] = (m.m2 - m.m1) - np.median(m.m2 - m.m1); m["rms"], m["chance"] = rms, chance
        parts.append(m); print(f"  {gal}: {e1[ia]} + {e2[ib]}: {len(m)} matched, rms {rms*1000:.0f} mas, chance {chance}", flush=True)
    if not parts:
        print(gal, "no overlapping fields"); continue
    P = pd.concat(parts, ignore_index=True)
    ebv = 0.0
    P["mag"] = (P.m1 + P.m2) / 2; P["rel"] = P.mag - tip
    cut = P.colkind.map(lambda k: RED[k][0])
    P["red"] = P.col > cut
    P["box"] = np.select([P.red & (P.rel >= -1) & (P.rel < 0), P.red & (P.rel > 0) & (P.rel <= 0.5)], ["agb", "rgb"], "other")
    P["gal"] = gal
    # the Hubble Source Catalog stars of this galaxy, same stars re-measured
    row = dict(gal=gal, tip_vega=round(tip, 2), n_matched=len(P), chance=int(P.groupby("pair").chance.first().sum()))
    e = twopoint.excess(P.d[P.box == "agb"].values, P.d[P.box == "rgb"].values, 0.3)
    row.update(psf_n_agb=e["n_target"], psf_n_rgb=e["n_control"], psf_f_agb=round(e.get("f_target", np.nan), 4), psf_f_rgb=round(e.get("f_control", np.nan), 4),
               psf_E03=round(e["E"], 4), psf_se=round(e["se"], 4), psf_sd_rgb=round(1.4826 * float(np.median(np.abs(P.d[P.box == "rgb"]))), 4) if (P.box == "rgb").any() else None)
    lo = P[P.crowd < 0.1]
    e = twopoint.excess(lo.d[lo.box == "agb"].values, lo.d[lo.box == "rgb"].values, 0.3)
    row.update(uncrowded_n_agb=e["n_target"], uncrowded_E03=round(e["E"], 4), uncrowded_se=round(e["se"], 4))
    hp = HERE / f"work/pairs/{key}.parquet"
    if hp.exists():
        H = pd.read_parquet(hp); H = H[(H.kind == "long") & H.box.isin(["agb", "rgb"])]
        t = cKDTree(np.c_[P.ra.values * cd * 3600, P.dec.values * 3600])
        best = None
        for dx, dy in itertools.product(np.arange(-1.0, 1.01, 0.1), repeat=2):     # catalogue offset: grid search, then match at 0.1"
            dd, _ = t.query(np.c_[H.MatchRA.values * cd * 3600 + dx, H.MatchDec.values * 3600 + dy], distance_upper_bound=0.1)
            n = int(np.isfinite(dd).sum())
            if best is None or n > best[0]:
                best = (n, dx, dy)
        n, dx, dy = best
        dd, jj = t.query(np.c_[H.MatchRA.values * cd * 3600 + dx, H.MatchDec.values * 3600 + dy], distance_upper_bound=0.1); ok = np.isfinite(dd)
        S = H[ok].assign(d_psf=P.d.values[jj[ok]], crowd=P.crowd.values[jj[ok]], gal=gal)
        stars.append(S[["gal", "MatchID", "box", "rel", "d", "d_psf", "crowd"]])
        eh = twopoint.excess(S.d[S.box == "agb"].values, S.d[S.box == "rgb"].values, 0.3); ep = twopoint.excess(S.d_psf[S.box == "agb"].values, S.d_psf[S.box == "rgb"].values, 0.3)
        big = (S.d.abs() > 0.3) & (S.box == "agb")
        row.update(same_n_agb=eh["n_target"], same_n_rgb=eh["n_control"], same_offset=f"{dx:+.1f},{dy:+.1f}", same_hsc_E03=round(eh["E"], 4), same_hsc_se=round(eh["se"], 4),
                   same_psf_E03=round(ep["E"], 4), same_psf_se=round(ep["se"], 4), hsc_big=int(big.sum()), hsc_big_confirmed=int((S.d_psf.abs()[big] > 0.3).sum()),
                   rms_diff=round(float(1.4826 * np.median(np.abs(S.d - S.d_psf))), 4))
    rows.append(row); print(row, flush=True)
df = pd.DataFrame(rows); df.to_csv(HERE / "work/psf.csv", index=False)
if stars:
    pd.concat(stars).to_parquet(HERE / "work/psf_stars.parquet")
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40); print(df.to_string(index=False))
