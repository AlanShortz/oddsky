"""(e): Fisher-matrix test with a nominal Gaia-like scanning law.

Everything is simulated from isotropic orbits and works in the local ecliptic
(east, north) tangent basis; sign(BF-AG) is invariant under a tangent-plane rotation.
Question 1: does the formal parallax error differ between a mirrored pair of orbits
            (same Omega, omega, i vs 180-i) at the same sky position and epochs?
Question 2: for noise-only Thiele-Innes draws, does sign(BF-AG) have a preference
            correlated with ecliptic hemisphere?
Spin-axis precession direction is unknown here from memory, so both signs are run.
"""
import numpy as np

rng = np.random.default_rng(1802)
T = 1038.0
XI = np.radians(45.0)
DAY = np.arange(-T / 2, T / 2, 0.05)
LAM = 2 * np.pi * DAY / 365.25 + 1.3
NU0 = 2 * np.pi * DAY * 5.8 / 365.25

def scan_events(lon, lat, sign_nu):
    uvec = np.array([np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)])
    nu = sign_nu * NU0 + 0.7
    s = np.stack([np.cos(LAM), np.sin(LAM), 0 * LAM], 1)
    y_ = np.stack([-np.sin(LAM), np.cos(LAM), 0 * LAM], 1)
    z_ = np.array([0, 0, 1.0])
    z = np.cos(XI) * s + np.sin(XI) * (np.cos(nu)[:, None] * y_ + np.sin(nu)[:, None] * z_)
    dp = z @ uvec
    idx = np.where(np.sign(dp[:-1]) != np.sign(dp[1:]))[0]
    t = DAY[idx]
    w = np.cross(z[idx], uvec)
    w /= np.linalg.norm(w, axis=1, keepdims=True)
    e = np.array([-np.sin(lon), np.cos(lon), 0.0])
    n = np.array([-np.sin(lat) * np.cos(lon), -np.sin(lat) * np.sin(lon), np.cos(lat)])
    we, wn = w @ e, w @ n
    # parallax factor projected on the scan: star shifts along +s_perp
    pf = we * (s[idx] @ e) + wn * (s[idx] @ n)
    return t, we, wn, pf

def kep(t, P, ecc, tau):
    M = 2 * np.pi * (t - tau) / P
    M = np.mod(M + np.pi, 2 * np.pi) - np.pi
    E = M + ecc * np.sin(M)
    for _ in range(12):
        E = E - (E - ecc * np.sin(E) - M) / (1 - ecc * np.cos(E))
    return np.cos(E) - ecc, np.sqrt(1 - ecc**2) * np.sin(E)

def ti(inc, om, Om):
    return (np.cos(om) * np.cos(Om) - np.sin(om) * np.sin(Om) * np.cos(inc),
            np.cos(om) * np.sin(Om) + np.sin(om) * np.cos(Om) * np.cos(inc),
            -np.sin(om) * np.cos(Om) - np.cos(om) * np.sin(Om) * np.cos(inc),
            -np.sin(om) * np.sin(Om) + np.cos(om) * np.cos(Om) * np.cos(inc))

def fisher_cov(t, we, wn, pf, P, ecc, tau, abfg, full=True):
    X, Y = kep(t, P, ecc, tau)
    tA, tB, tF, tG = abfg
    cols = [we, wn, we * t, wn * t, pf, wn * X, we * X, wn * Y, we * Y]
    if full:
        def model(P_, e_, tau_):
            x, y = kep(t, P_, e_, tau_)
            return we * (tB * x + tG * y) + wn * (tA * x + tF * y)
        dP, de, dt = P * 1e-4, 1e-4, P * 1e-4
        cols += [(model(P + dP, ecc, tau) - model(P - dP, ecc, tau)) / (2 * dP),
                 (model(P, ecc + de, tau) - model(P, ecc - de, tau)) / (2 * de),
                 (model(P, ecc, tau + dt) - model(P, ecc, tau - dt)) / (2 * dt)]
    M = np.column_stack(cols)
    scale = np.linalg.norm(M, axis=0)
    Mn = M / scale
    # pinv with a modest rcond: a singular design is treated as weakly constrained, not infinite
    C = np.linalg.pinv(Mn.T @ Mn, rcond=1e-10, hermitian=True)
    return C / np.outer(scale, scale)

PS = [120, 182.6, 250, 320, 365.25, 420, 550, 650, 730, 850, 1000, 1300]
NSKY = 250
print("P  | sign_nu | med sigma_plx(s=+sense)/sigma_plx(s=-sense) mirrored pairs (full fit incl P,e,T) | a0-sig ratio | noise-only mean(s*sign beta) +- | linear-only ratio")
for sign_nu in (+1, -1):
    for P in PS:
        lr, lr_a, lr_lin, nsense = [], [], [], []
        for _ in range(NSKY):
            lon = rng.uniform(0, 2 * np.pi)
            lat = np.arcsin(rng.uniform(-1, 1))
            t, we, wn, pf = scan_events(lon, lat, sign_nu)
            if len(t) < 14:
                continue
            ecc = rng.uniform(0.05, 0.6)
            tau = rng.uniform(-P / 2, P / 2)
            inc = np.arccos(rng.uniform(0.02, 1))   # prograde-like cos i>0, mirror below
            om, Om = rng.uniform(0, 2 * np.pi, 2)
            sb = np.sign(lat)
            # s = -sign(cos i); sense = s*sign(beta)
            res = {}
            for cosi_sign in (+1, -1):
                abfg = ti(inc if cosi_sign > 0 else np.pi - inc, om, Om)
                C = fisher_cov(t, we, wn, pf, P, ecc, tau, abfg)
                sense = -cosi_sign * sb
                a2 = np.sum(np.array(abfg) ** 2)
                # sigma on a0: isotropic proxy from TI block
                tiC = np.array([C[5, 5], C[6, 6], C[7, 7], C[8, 8]])
                res[sense] = (C[4, 4], tiC.mean())
            lr.append(0.5 * np.log(res[1][0] / res[-1][0]))
            lr_a.append(0.5 * np.log(res[1][1] / res[-1][1]))
            # Noise only: draws from TI block of the linear fit, s = sign(BF-AG)
            C0 = fisher_cov(t, we, wn, pf, P, ecc, tau, ti(inc, om, Om), full=False)
            TI = C0[5:9, 5:9]  # order A,B,F,G
            if np.all(np.linalg.eigvalsh(TI) > 0):
                dr = rng.multivariate_normal(np.zeros(4), TI, 400)
                nsense.append(np.mean(np.sign(dr[:, 1] * dr[:, 2] - dr[:, 0] * dr[:, 3])) * sb)
        lr, lr_a, nsense = np.array(lr), np.array(lr_a), np.array(nsense)
        print(f"P={P:7.1f} nu={sign_nu:+d} N={len(lr):3d} sigma_plx ratio +/-: median {np.exp(np.median(lr)):.4f} mean {np.exp(lr.mean()):.4f} +-{lr.std()/np.sqrt(len(lr)):.4f}"
              f" | TI-sig ratio {np.exp(np.median(lr_a)):.4f} | noise-only mean sense {nsense.mean():+.4f} +-{nsense.std()/np.sqrt(len(nsense)):.4f}")
