"""Blind pipeline test. Mirror pairs of orbits are sampled with the real scan law, then fitted by gaiamock's full astrometric cascade
(El-Badry+ 2024: 5-par, 9-par, 7-par, then a period search and 12-par orbit) with no knowledge of the truth. Needs gaiamock's source,
compiled against GSL, in ~/oddsky-runs/h0018/gaiamock_src. Run: uv run --with healpy --with joblib python -I gm_run.py --out FILE
"""
import argparse
import os
import sys
import warnings

import numpy as np
import pandas as pd
from astropy.coordinates import BarycentricMeanEcliptic, SkyCoord, get_body_barycentric
from astropy import units as u
from astropy.time import Time
from joblib import Parallel, delayed
from scipy.spatial import cKDTree

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import chiral_sim as cs  # noqa: E402
import handedness as hd  # noqa: E402

sys.path.insert(0, os.path.expanduser("~/oddsky-runs/h0018/gaiamock_src"))
warnings.filterwarnings("ignore")
T0, SPAN_DR4 = 1666.44, 2006.0


def extend_for_dr4(scan):
    """The real law repeated three years later, with the last 188 d reflected in the ecliptic plane for reversed precession."""
    nep = SkyCoord(lon=0 * u.deg, lat=90 * u.deg, frame="barycentricmeanecliptic").icrs.cartesian.xyz.value
    t = np.concatenate([scan.t, scan.t + 3 * 365.25])
    ra, dec, psi, fov = [np.concatenate([x] * 2) for x in (scan.ra, scan.dec, scan.psi, scan.fov)]
    m = t >= T0 + SPAN_DR4 - 188
    v = cs.unit(ra[m], dec[m])
    a_, d_, p = np.radians(ra[m]), np.radians(dec[m]), np.radians(psi[m])
    e = np.column_stack([-np.sin(a_), np.cos(a_), 0 * a_])
    n = np.column_stack([-np.sin(d_) * np.cos(a_), -np.sin(d_) * np.sin(a_), np.cos(d_)])
    dv = np.sin(p)[:, None] * e + np.cos(p)[:, None] * n
    v2, dv2 = v - 2 * (v @ nep)[:, None] * nep, dv - 2 * (dv @ nep)[:, None] * nep
    ra2, dec2 = np.degrees(np.arctan2(v2[:, 1], v2[:, 0])) % 360, np.degrees(np.arcsin(v2[:, 2]))
    a2, d2 = np.radians(ra2), np.radians(dec2)
    e2 = np.column_stack([-np.sin(a2), np.cos(a2), 0 * a2])
    n2 = np.column_stack([-np.sin(d2) * np.cos(a2), -np.sin(d2) * np.sin(a2), np.cos(d2)])
    ra[m], dec[m], psi[m] = ra2, dec2, np.degrees(np.arctan2((dv2 * e2).sum(1), (dv2 * n2).sum(1))) % 360
    scan.t, scan.ra, scan.dec, scan.psi, scan.fov = t, ra, dec, psi, fov
    scan.tree = cKDTree(cs.unit(ra, dec))
    return scan


def geometry(stars, dr4):
    scan = cs.Scan()
    if dr4:
        scan = extend_for_dr4(scan)
    tmax = T0 + SPAN_DR4 if dr4 else scan.t.max()
    tref = T0 + 0.5 * (tmax - T0)
    out = []
    for s in stars.itertuples():
        t, psi = scan.transits(s.ra, s.dec)
        m = t < tmax
        t, psi = t[m], np.radians(psi[m])
        if len(t) < 13:
            continue
        ep = get_body_barycentric("earth", Time(t + cs.T0_JD, format="jd", scale="tdb")).xyz.to_value("au")
        a, d = np.radians(s.ra), np.radians(s.dec)
        f = (ep[0] * np.sin(a) - ep[1] * np.cos(a)) * np.sin(psi) + (ep[0] * np.cos(a) * np.sin(d) + ep[1] * np.sin(a) * np.sin(d) - ep[2] * np.cos(d)) * np.cos(psi)
        beta = SkyCoord(ra=s.ra * u.deg, dec=s.dec * u.deg).transform_to(BarycentricMeanEcliptic()).lat.deg
        out.append(dict(ra=s.ra, dec=s.dec, G=s.G, plx=s.parallax, beta=float(beta), t=t, psi=psi, f=f, tref=tref))
    return out


def one_star(g, draws, seed, pmin=30.0, pmax=3000.0):
    import gaiamock as gm

    c = gm.read_in_C_functions()
    rng = np.random.default_rng(seed)
    sig = np.interp(g["G"], cs.G_TAB, cs.SIG_TAB) / np.sqrt(8)
    t, psi, f = g["t"], g["psi"], g["f"]
    tyr = (t - g["tref"]) / 365.25
    sp, cp = np.sin(psi), np.cos(psi)
    rows = []
    for _ in range(draws):
        P = 10 ** rng.uniform(np.log10(pmin), np.log10(pmax))
        ecc = rng.uniform(0, 0.9)
        q = rng.uniform(0.05, 1)
        l_ = q**3.5
        a0 = (1 + q) ** (1 / 3) * (P / 365.25) ** (2 / 3) * abs(q / (1 + q) - l_ / (1 + l_)) * g["plx"]
        cosi, om, Om, ph = rng.uniform(-1, 1), *rng.uniform(0, 2 * np.pi, 3)
        A = a0 * (np.cos(om) * np.cos(Om) - np.sin(om) * np.sin(Om) * cosi)
        B = a0 * (np.cos(om) * np.sin(Om) + np.sin(om) * np.cos(Om) * cosi)
        F = a0 * (-np.sin(om) * np.cos(Om) - np.cos(om) * np.sin(Om) * cosi)
        G = a0 * (-np.sin(om) * np.sin(Om) + np.cos(om) * np.cos(Om) * cosi)
        E = cs.kepler((2 * np.pi * (t - g["tref"]) / P + ph) % (2 * np.pi), ecc)
        X, Y = np.cos(E) - ecc, np.sqrt(1 - ecc**2) * np.sin(E)
        noise = rng.normal(0, sig, len(t))
        pm = rng.normal(0, 5, 2)
        for flip in (1, -1):
            Fs, Gs = flip * F, flip * G
            obs = cp * (A * X + Fs * Y) + sp * (B * X + Gs * Y) + g["plx"] * f + tyr * (pm[0] * sp + pm[1] * cp) + noise
            r = gm.fit_full_astrometric_cascade(tyr, psi, f, obs, np.full(len(t), sig), c, binned=True)
            sense_true = int(np.sign(B * Fs - A * Gs) * np.sign(g["beta"]))
            row = dict(P=P, ecc=ecc, cosi=cosi, a0=a0, q=q, G_mag=g["G"], plx_true=g["plx"], beta=g["beta"], sense_true=sense_true, nt=len(t), kind=int(r[0]) if r[0] in (0, -1, -7, -9) else 12)
            if row["kind"] == 12:
                plx, s_plx, Ah, _, Bh, _, Fh, _, Gh, _, Ph, sP, _, _, eh, s_e, _, a0h, s_a0, _, _, F2, ruwe = r
                row.update(plx=plx, s_plx=s_plx, P_fit=Ph, s_P=sP, e_fit=eh, s_e=s_e, a0_fit=a0h, s_a0=s_a0, F2=F2, ruwe=ruwe, sense_fit=int(np.sign(Bh * Fh - Ah * Gh) * np.sign(g["beta"])))
            elif row["kind"] == -1:
                row.update(ruwe=r[1])
            elif row["kind"] in (-7, -9):
                row.update(plx=r[2], s_plx=r[3])
            rows.append(row)
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stars", type=int, default=1500)
    ap.add_argument("--draws", type=int, default=20)
    ap.add_argument("--seed", type=int, default=41)
    ap.add_argument("--dr4", action="store_true")
    ap.add_argument("--pmin", type=float, default=30.0)
    ap.add_argument("--pmax", type=float, default=3000.0)
    ap.add_argument("--plxmin", type=float, default=0.3)
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    p = pd.read_csv(f"{hd.RUNS}/data/nss/field_parent.csv").rename(columns={"phot_g_mean_mag": "G"})
    p = p[(p.parallax > args.plxmin)].sample(args.stars, random_state=args.seed)
    # Resumable: geometry is cached and each batch of stars is written out, so a killed run loses at most one batch
    parts = args.out + ".parts"
    os.makedirs(parts, exist_ok=True)
    cache = f"{parts}/geometry.pkl"
    if os.path.exists(cache):
        geo = pd.read_pickle(cache)
    else:
        geo = geometry(p, args.dr4)
        pd.to_pickle(geo, cache)
    print("stars with geometry", len(geo), "median transits", np.median([len(g["t"]) for g in geo]), flush=True)
    size = 300
    for b in range(0, len(geo), size):
        f = f"{parts}/batch_{b:06d}.parquet"
        if os.path.exists(f):
            continue
        res = Parallel(n_jobs=args.jobs)(delayed(one_star)(g, args.draws, args.seed + b + i, args.pmin, args.pmax) for i, g in enumerate(geo[b : b + size]))
        pd.DataFrame([r for rr in res for r in rr]).to_parquet(f + ".tmp", index=False)
        os.replace(f + ".tmp", f)
        print("batch", b, flush=True)
    d = pd.concat([pd.read_parquet(f"{parts}/batch_{b:06d}.parquet") for b in range(0, len(geo), size)], ignore_index=True)
    d.to_parquet(args.out)
    print(d.kind.value_counts().to_dict())
