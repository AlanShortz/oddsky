"""r11: what tE and the piE range imply. theta_E = kappa M pi_rel (kappa = 8.144 mas/Msun), pi_E = pi_rel / theta_E,
tE = theta_E / mu_rel. Without theta_E (no finite-source effect, no astrometry) the mass follows only through an assumed mu_rel:
M = mu_rel tE / (kappa pi_E). Source distance: J180624 parallax -0.32 +- 0.13 mas (Gaia DR3; RUWE 1.29) -> take pi_s = 0.15 mas
(~6.5 kpc); J183040 parallax 0.04 +- 0.02 -> pi_s = 0.12 (bulge giant, ~8 kpc)."""
import numpy as np

K = 8.144
for k, tE, pis, piEs in (("J180624", 130.0, 0.15, (0.03, 0.1, 0.18, 0.27, 0.35)), ("J183040 (fs>=0.9 fit)", 101.0, 0.12, (0.1, 0.3, 0.49, 0.7)),
                          ("J183040 (free-fs fit)", 220.0, 0.12, (0.05, 0.13, 0.3))):
    print("==", k, f"tE {tE} d, pi_s {pis} mas")
    for piE in piEs:
        row = []
        for mu in (2.0, 4.0, 7.0):
            th = mu * tE / 365.25
            M = th / (K * piE)
            pirel = piE * th
            DL = 1 / (pirel + pis)
            row.append(f"mu {mu:.0f}: thE {th:.2f} M {M:5.2f} DL {DL:4.1f}")
        print(f"  piE {piE:.2f} | " + " | ".join(row))
# Luminous-lens check for J180624: a main-sequence lens of mass M at DL contributes to the blend; fs(ATLAS o) ~0.75-0.9 allows
# 10-25% of the o flux (G ~ 17.0 -> blend G >~ 18.5-19.5)
for M, MG in ((0.3, 10.3), (0.5, 8.9), (0.8, 6.0), (1.0, 4.7), (1.5, 3.0)):
    for DL in (1.0, 2.0, 3.0):
        AG = 3.56 * min(DL / 4.0, 1.0)  # crude: extinction grows ~linearly to the source's A_G 3.56 by 4 kpc
        G = MG + 5 * np.log10(DL * 100) + AG
        print(f"  J180624 MS lens M {M} Msun at {DL} kpc: G ~ {G:.1f} (vs source 17.0; blend share {10 ** (-0.4 * (G - 17.0)) / (1 + 10 ** (-0.4 * (G - 17.0))):.2f})")
