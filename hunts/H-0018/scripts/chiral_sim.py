"""Forward model: for random orbits and their mirror images (same sky ellipse, opposite sense), sample with the real Gaia
scan law, compute a single-star fit and the 12-parameter Fisher matrix of an orbit fit (P, T and e free), apply the published
DR3 cuts (Halbwachs+ 2023), and record which of the two survives. No noise fit is run: errors come from the Fisher matrix.

The only inputs from Gaia's astrometric-orbit catalogue are positions, G and parallax of its development stars (or of the
a random Gaia field sample with --parent field: G < 17, parallax > 0.1 mas); no handedness information enters.
"""
import argparse
import sys

import numpy as np
import pandas as pd
from astropy.coordinates import get_body_barycentric
from astropy.time import Time
from scipy.spatial import cKDTree

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import handedness as hd  # noqa: E402

G_TAB = [4, 5, 6, 7, 8.2, 8.4, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
SIG_TAB = [0.4, 0.35, 0.15, 0.17, 0.23, 0.13, 0.13, 0.135, 0.125, 0.13, 0.15, 0.23, 0.36, 0.63, 1.05, 2.05, 4.1]  # Lindegren+21 via El-Badry+24
T0_JD = 2455197.5
KEYS = ["pass_ruwe", "pass_a0", "pass_plx", "pass_e", "s_plx", "plx", "ruwe", "s_a0", "a0h", "s_e"]


def unit(ra, dec):
    ra, dec = np.radians(ra), np.radians(dec)
    return np.column_stack([np.cos(dec) * np.cos(ra), np.cos(dec) * np.sin(ra), np.sin(dec)])


class Scan:
    def __init__(self, path=f"{hd.RUNS}/data/scanlaw/scan30s.npz"):
        z = np.load(path)
        self.t, self.ra, self.dec, self.psi, self.fov = z["t"], z["ra"], z["dec"], z["psi"], z["fov"]
        self.tree = cKDTree(unit(self.ra, self.dec))

    def transits(self, ra, dec, tmax=None):
        chord = 2 * np.sin(np.radians(0.75) / 2)
        idx = np.array(self.tree.query_ball_point(unit(np.array([ra]), np.array([dec]))[0], chord))
        if len(idx) == 0:
            return np.array([]), np.array([])
        idx = idx[np.lexsort((self.t[idx], self.fov[idx]))]
        t, r, d, p, f = self.t[idx], self.ra[idx], self.dec[idx], self.psi[idx], self.fov[idx]
        new = np.r_[True, (np.diff(t) > 0.01) | (np.diff(f) != 0)]
        groups = np.cumsum(new) - 1
        out_t, out_p = [], []
        for g in range(groups[-1] + 1):
            m = groups == g
            dE = ((ra - r[m] + 180) % 360 - 180) * np.cos(np.radians(dec))
            dN = dec - d[m]
            s, c = np.sin(np.radians(p[m])), np.cos(np.radians(p[m]))
            al, ac = dE * s + dN * c, dE * c - dN * s
            k = np.argmin(np.abs(al))
            if abs(ac[k]) < 0.36:
                out_t.append(t[m][k] + al[k] / (60 / 3600 * 86400) * 0)  # the sub-minute timing does not matter here
                out_p.append(p[m][k])
        return np.array(out_t), np.array(out_p)


def kepler(M, e):
    E = M + e * np.sin(M)
    for _ in range(8):
        E = E - (E - e * np.sin(E) - M) / (1 - e * np.cos(E))
    return E


def simulate(args):
    rng = np.random.default_rng(args.seed)
    if args.parent == "nss":
        p = pd.read_csv(hd.NSS_CSV, usecols=["source_id", "ra", "dec", "parallax", "phot_g_mean_mag"], dtype={"source_id": "int64"})
        p = p[hd.is_dev(p.source_id.values)].dropna()
        p = p.rename(columns={"phot_g_mean_mag": "G"})
    else:
        p = pd.read_csv(f"{hd.RUNS}/data/nss/field_parent.csv").rename(columns={"phot_g_mean_mag": "G"})
    p = p.sample(args.stars, random_state=args.seed, replace=len(p) < args.stars)
    scan = Scan()
    if args.standin_test:
        # Test of the DR4 stand-in on DR3 itself: the first year of the real law, repeated at +1 and +2 yr, in place of the truth
        t0 = scan.t.min()
        keep = scan.t < t0 + 365.25
        parts = [(scan.t[keep] + k * 365.25, scan.ra[keep], scan.dec[keep], scan.psi[keep], scan.fov[keep]) for k in range(3)]
        scan.t, scan.ra, scan.dec, scan.psi, scan.fov = [np.concatenate(x) for x in zip(*parts)]
        scan.tree = cKDTree(unit(scan.ra, scan.dec))
        args.tmax = t0 + 1038
    if args.dr4:
        # DR4 spans 66 months and its commanded scan law is not public. Stand-in: repeat the real law three years later, which
        # keeps the solar phase; the spin-axis phase is then not the true one.
        scan.t = np.concatenate([scan.t, scan.t + 3 * 365.25])
        for name in ("ra", "dec", "psi", "fov"):
            setattr(scan, name, np.concatenate([getattr(scan, name)] * 2))
        scan.tree = cKDTree(unit(scan.ra, scan.dec))
        args.tmax = 1666.44 + 2006
    tmax = args.tmax if args.tmax else scan.t.max()
    tc = 0.5 * (scan.t.min() + tmax)
    from astropy.coordinates import BarycentricMeanEcliptic, SkyCoord
    from astropy import units as u
    rows = []
    ncount = []
    for n, s in enumerate(p.itertuples()):
        t, psi = scan.transits(s.ra, s.dec)
        if args.tmax:
            m = t < args.tmax
            t, psi = t[m], psi[m]
        if len(t) < 12:
            continue
        if args.thin:  # drop transits at random: the model has 1.21 times the matched transits of real sources
            m = rng.random(len(t)) > args.thin
            t, psi = t[m], psi[m]
        ncount.append(len(t))
        sp, cp = np.sin(np.radians(psi)), np.cos(np.radians(psi))
        e_pos = get_body_barycentric("earth", Time(t + T0_JD, format="jd", scale="tdb")).xyz.to_value("au")
        a, d = np.radians(s.ra), np.radians(s.dec)
        pa = e_pos[0] * np.sin(a) - e_pos[1] * np.cos(a)
        pd_ = e_pos[0] * np.cos(a) * np.sin(d) + e_pos[1] * np.sin(a) * np.sin(d) - e_pos[2] * np.cos(d)
        fpl = pa * sp + pd_ * cp
        tau = (t - tc) / 365.25
        D5 = np.column_stack([sp, cp, fpl, tau * sp, tau * cp])
        Q5, _ = np.linalg.qr(D5)
        sig_ccd = np.interp(s.G, G_TAB, SIG_TAB)
        sig_t = sig_ccd / np.sqrt(8)
        sb = float(SkyCoord(ra=s.ra * u.deg, dec=s.dec * u.deg).transform_to(BarycentricMeanEcliptic()).lat.deg)
        M = args.draws
        P = 10 ** rng.uniform(np.log10(30), np.log10(3000), M)
        ecc = rng.uniform(0, 0.9, M) if args.ecc == "uniform" else (np.sqrt(rng.uniform(0, 0.81, M)) if args.ecc == "thermal" else rng.beta(1.2, 3, M) * 0.9)
        phase0 = rng.uniform(0, 2 * np.pi, M)
        q = rng.uniform(0.05, 1, M) if args.q == "flat" else np.clip(rng.lognormal(np.log(0.3), 0.7, M), 0.02, 1)
        l_ = q**3.5
        a_rel = (args.m1 + q * args.m1) ** (1 / 3) * (P / 365.25) ** (2 / 3)
        a0 = a_rel * np.abs(q / (1 + q) - l_ / (1 + l_)) * s.parallax
        cosi = rng.uniform(-1, 1, M)
        sini = np.sqrt(1 - cosi**2)
        om, Om = rng.uniform(0, 2 * np.pi, (2, M))
        A = a0 * (np.cos(om) * np.cos(Om) - np.sin(om) * np.sin(Om) * cosi)
        B = a0 * (np.cos(om) * np.sin(Om) + np.sin(om) * np.cos(Om) * cosi)
        F = a0 * (-np.sin(om) * np.cos(Om) - np.cos(om) * np.sin(Om) * cosi)
        G = a0 * (-np.sin(om) * np.sin(Om) + np.cos(om) * np.cos(Om) * cosi)
        # Orbit as seen along-scan, for each draw (M x Nt)
        anom = kepler(((2 * np.pi * (t[None, :] - tc) / P[:, None] + phase0[:, None]) % (2 * np.pi)), ecc[:, None])
        X = np.cos(anom) - ecc[:, None]
        Y = np.sqrt(1 - ecc[:, None] ** 2) * np.sin(anom)
        snE, csE = np.sin(anom), np.cos(anom)
        sq = np.sqrt(1 - ecc[:, None] ** 2)
        dE_dM = 1 / (1 - ecc[:, None] * csE)
        dX_dM, dY_dM = -snE * dE_dM, sq * csE * dE_dM
        dE_de = snE * dE_dM
        dX_de, dY_de = -snE * dE_de - 1, -ecc[:, None] / sq * snE + sq * csE * dE_de
        tt = 2 * np.pi * (t[None, :] - tc) / 365.25  # d(M)/d(frequency in cycles per yr)
        z1, z2, z3 = rng.normal(size=(3, M))
        res = {}
        for sign_name, s_y in [("orig", 1.0), ("mirror", -1.0)]:
            Fs, Gs = s_y * F, s_y * G
            sig = (cp * (A[:, None] * X + Fs[:, None] * Y)) + (sp * (B[:, None] * X + Gs[:, None] * Y))
            # Single-star residual, in signal only: RUWE^2 = 1 + mean(r^2) / sig_ccd^2
            r_ss = sig - (sig @ Q5) @ Q5.T
            ruwe = np.sqrt(1 + np.mean(r_ss**2, axis=1) / sig_ccd**2)
            # Fisher matrix with P, T and e free: the three non-linear columns carry the signed constants
            Dfull = np.zeros((M, len(t), 12))
            Dfull[:, :, :5] = D5
            Dfull[:, :, 5] = cp * X
            Dfull[:, :, 6] = sp * X
            Dfull[:, :, 7] = cp * Y
            Dfull[:, :, 8] = sp * Y
            dsig_dM = (cp * (A[:, None] * dX_dM + Fs[:, None] * dY_dM)) + (sp * (B[:, None] * dX_dM + Gs[:, None] * dY_dM))
            Dfull[:, :, 9] = dsig_dM
            Dfull[:, :, 10] = dsig_dM * tt
            Dfull[:, :, 11] = (cp * (A[:, None] * dX_de + Fs[:, None] * dY_de)) + (sp * (B[:, None] * dX_de + Gs[:, None] * dY_de))
            if args.fix:  # hold orbital elements fixed, to see which one carries the sense into the parallax error
                gone = {"T": 9, "P": 10, "e": 11}
                Dfull[:, :, [gone[x] for x in args.fix.split(",")]] = 0
                for x in args.fix.split(","):
                    Dfull[:, :, gone[x]] = 1e-9 * rng.normal(size=len(t))
            NtN = np.einsum("mti,mtj->mij", Dfull, Dfull)
            scale = np.sqrt(np.einsum("mii->mi", NtN))
            cond = NtN / (scale[:, :, None] * scale[:, None, :])
            good = np.linalg.cond(cond) < 1e10
            cov = np.full_like(NtN, np.nan)
            cov[good] = np.linalg.inv(cond[good]) / (scale[good][:, :, None] * scale[good][:, None, :]) * sig_t**2
            s_plx = np.sqrt(cov[:, 2, 2])
            s_e = np.sqrt(cov[:, 11, 11])
            plx = s.parallax + s_plx * z1
            grad = np.zeros((M, 4))
            base = np.column_stack([A, B, Fs, Gs])
            u0 = (base**2).sum(axis=1) / 2
            v0 = base[:, 0] * base[:, 3] - base[:, 1] * base[:, 2]
            a0t = np.sqrt(u0 + np.sqrt(np.maximum((u0 + v0) * (u0 - v0), 0)))
            h = 1e-3 * np.maximum(a0t, 1e-3)
            for j in range(4):
                b2 = base.copy()
                b2[:, j] += h
                u2 = (b2**2).sum(axis=1) / 2
                v2 = b2[:, 0] * b2[:, 3] - b2[:, 1] * b2[:, 2]
                grad[:, j] = (np.sqrt(u2 + np.sqrt(np.maximum((u2 + v2) * (u2 - v2), 0))) - a0t) / h
            s_a0 = np.sqrt(np.einsum("mi,mij,mj->m", grad, cov[:, 5:9, 5:9], grad))
            a0h = a0t + s_a0 * z2
            res[sign_name] = dict(
                ruwe=ruwe, plx=plx, s_plx=s_plx, a0h=a0h, s_a0=s_a0, s_e=s_e,
                pass_ruwe=ruwe > 1.4,
                pass_a0=(a0h / s_a0 > 158 / np.sqrt(P)) & (a0h / s_a0 > 5),
                pass_plx=plx / s_plx > 20000 / P,
                pass_e=s_e < 0.079 * np.log(P) - 0.244,
            )
        # 'orig' has true y = sign(-cos i) in sky terms
        y_true = np.sign(B * F - A * G)
        rows.append(pd.DataFrame(dict(
            P=P, ecc=ecc, cosi=cosi, a0=a0, plx=s.parallax, G=s.G, beta=sb, ytrue=y_true, nt=len(t), q=q,
            **{f"{k}_{nm}": res[nm][k] for nm in res for k in KEYS},
        )))
        if n % 200 == 0:
            print(n, len(t), flush=True)
    d = pd.concat(rows, ignore_index=True)
    # Translate to 'plus' = L has a component along +NEP on this line of sight, for original or its mirror
    is_plus_orig = d.ytrue * np.sign(d.beta) > 0
    for k in KEYS:
        d[f"{k}_plus"] = np.where(is_plus_orig, d[f"{k}_orig"], d[f"{k}_mirror"])
        d[f"{k}_minus"] = np.where(is_plus_orig, d[f"{k}_mirror"], d[f"{k}_orig"])
        d = d.drop(columns=[f"{k}_orig", f"{k}_mirror"])
    d["acc_plus"] = d.pass_ruwe_plus & d.pass_a0_plus & d.pass_plx_plus & d.pass_e_plus
    d["acc_minus"] = d.pass_ruwe_minus & d.pass_a0_minus & d.pass_plx_minus & d.pass_e_minus
    print("median transits", np.median(ncount), "draws", len(d))
    d.to_parquet(args.out)
    return d


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stars", type=int, default=3000)
    ap.add_argument("--draws", type=int, default=100)
    ap.add_argument("--parent", default="nss")
    ap.add_argument("--seed", type=int, default=18)
    ap.add_argument("--tmax", type=float, default=None)
    ap.add_argument("--dr4", action="store_true")
    ap.add_argument("--standin-test", action="store_true")
    ap.add_argument("--thin", type=float, default=0.0)
    ap.add_argument("--ecc", default="uniform", help="uniform, thermal or low")
    ap.add_argument("--q", default="flat", help="flat or low")
    ap.add_argument("--m1", type=float, default=1.0)
    ap.add_argument("--fix", default="", help="comma list of T,P,e to hold fixed in the Fisher matrix")
    ap.add_argument("--out", default=f"{hd.RUNS}/sim_nss.parquet")
    d = simulate(ap.parse_args())
    print("accept: plus", d.acc_plus.sum(), "minus", d.acc_minus.sum(), "A", (d.acc_plus.sum() - d.acc_minus.sum()) / (d.acc_plus.sum() + d.acc_minus.sum()))
