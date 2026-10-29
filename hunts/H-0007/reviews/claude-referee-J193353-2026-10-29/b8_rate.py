"""b8: microlensing optical depth and rate toward (l, b) = (17.95, -18.56) for Ds = 6-9 kpc, with the same crude disc + bulge model as the
first referee (a6.py), plus a stellar halo (rho ~ r^-3.5). Own model, outside the Oddsky tools."""
import numpy as np

K = 4 * np.pi * 4.30091e-3 / (2.99792458e5 ** 2)  # pc / Msun
R0, zs = 8200.0, 20.0


def rho(D, l, b, halo=True):
    l, b = np.radians(l), np.radians(b)
    x = R0 - D * np.cos(b) * np.cos(l)
    y = D * np.cos(b) * np.sin(l)
    z = zs + D * np.sin(b)
    R = np.hypot(x, y)
    thin = 0.043 * np.exp(-(R - R0) / 2600) * np.exp(-np.abs(z) / 300)
    thick = 0.043 * 0.12 * np.exp(-(R - R0) / 2000) * np.exp(-np.abs(z) / 900)
    r = np.sqrt(x ** 2 + y ** 2 + (z / 0.6) ** 2)
    bul = 1.5 * np.exp(-0.5 * (r / 700) ** 2)
    rs = np.sqrt(x ** 2 + y ** 2 + (z / 0.7) ** 2)
    hal = 1.0e-4 * (np.maximum(rs, 500) / R0) ** -3.5 if halo else 0  # ~1e-4 Msun/pc3 locally (stellar halo)
    return thin + thick + bul + hal


def tau(l, b, Ds):
    D = np.linspace(1, Ds - 1, 6000)
    return K * np.trapezoid(rho(D, l, b) * D * (Ds - D) / Ds, D)


for lab, l, b, Ds in [("J193353 Ds=6 kpc", 17.95, -18.56, 6000), ("J193353 Ds=8.4 kpc", 17.95, -18.56, 8400), ("J193353 Ds=10 kpc", 17.95, -18.56, 10000),
                      ("J040025 (3.0 kpc)", 162.8, -15.3, 3000), ("OGLE bulge (1,-3), 8 kpc", 1.0, -3.0, 8000)]:
    t = tau(l, b, Ds)
    for tE in [40, 80]:
        G = 2 / np.pi * t / tE * 365.25
        print(f"{lab:28s} tau={t:.2e}  tE={tE}d: rate={G:.1e}/yr/star; P(A>=1.96 in one snapshot, u<0.575)={t*0.575**2:.1e}")
# expected number in pass 3 that a single NEOWISE visit catches with A >= 1.45 (u < 0.85) given selection on |dW| >= 0.4 swing
for ntot, taubar in [(64.45e6, 3e-8), (64.45e6, 1e-7)]:
    print(f"N={ntot:.2e} stars x 20 visits x u^2(A>=1.96)={0.575**2:.3f} x tau={taubar:.0e}: expected A>=1.96 snapshots = {ntot*20*0.575**2*taubar:.2f}")
