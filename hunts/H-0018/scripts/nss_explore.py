"""Exploratory, development split only: how does the ecliptic handedness of Gaia astrometric orbits behave?"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import handedness as hd  # noqa: E402

df = pd.read_csv(hd.NSS_CSV, dtype={"source_id": "int64"})
ex = pd.read_csv(f"{hd.RUNS}/data/nss/nss_extra.csv", dtype={"source_id": "int64"})
df = df.merge(ex, on="source_id", how="left")
df = df[hd.is_dev(df.source_id.values) & df.nss_solution_type.isin(["Orbital", "AstroSpectroSB1"])].copy()
A, B, F, G = df.a_thiele_innes, df.b_thiele_innes, df.f_thiele_innes, df.g_thiele_innes
df["y"] = np.sign(B * F - A * G)
u_ = (A**2 + B**2 + F**2 + G**2) / 2
v_ = A * G - B * F
df["a0"] = np.sqrt(u_ + np.sqrt((u_ + v_) * (u_ - v_)))
df["cosi"] = np.clip(v_ / df.a0**2, -1, 1)
df["sinbeta"] = np.sin(np.radians(df.ecl_lat))
df["e_y"] = df.y * np.sign(df.sinbeta)  # +1: L has a component along +NEP on this line of sight
df["a0_au"] = df.a0 / df.parallax
df["sig"] = df.significance


def asym(sub):
    f = sub.e_y.mean()
    return len(sub), f, np.sqrt((1 - f**2) / max(len(sub), 1))


def table(name, col, edges, sub=None):
    sub = df if sub is None else sub
    print(f"\nA = <y sign(beta)> by {name}")
    for lo, hi in zip(edges[:-1], edges[1:]):
        s = sub[(sub[col] >= lo) & (sub[col] < hi)]
        if len(s) < 30:
            continue
        n, a, e = asym(s)
        print(f"  {lo:>10.3g} to {hi:<10.3g} N={n:6d}  A={a:+.3f} ± {e:.3f} ({a / e:+.1f}s)")


print("overall", asym(df))
table("period (d)", "period", [10, 50, 100, 150, 200, 250, 300, 340, 390, 450, 500, 600, 700, 800, 900, 1000, 1100, 1300, 1600, 3000])
table("|sin beta|", "absb", np.linspace(0, 1, 11), df.assign(absb=np.abs(df.sinbeta)))
table("|b|", "absgb", [0, 3, 6, 10, 15, 20, 30, 45, 60, 90], df.assign(absgb=np.abs(df.b)))
table("significance", "sig", [0, 5, 7, 10, 15, 20, 30, 50, 100, 300, 1e5])
table("G", "phot_g_mean_mag", [0, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 22])
table("parallax (mas)", "parallax", [0, 0.5, 1, 1.5, 2, 3, 5, 10, 20, 50, 1000])
table("a0 (mas)", "a0", [0, 0.1, 0.2, 0.3, 0.5, 1, 2, 5, 10, 100])
table("a0 / parallax (au)", "a0_au", [0, 0.05, 0.1, 0.2, 0.3, 0.5, 1, 2, 5, 100])
table("eccentricity", "eccentricity", [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1])
table("|cos i|", "acosi", np.linspace(0, 1, 11), df.assign(acosi=np.abs(df.cosi)))
table("goodness_of_fit", "goodness_of_fit", [-10, -2, 0, 2, 5, 10, 20, 50, 1000])
table("efficiency", "efficiency", [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.01])
table("ipd_frac_multi_peak", "ipd_frac_multi_peak", [0, 1, 2, 5, 10, 20, 50, 101])
table("ipd_gof_harmonic_amplitude", "ipd_gof_harmonic_amplitude", [0, 0.02, 0.05, 0.1, 0.2, 0.5, 5])
table("RUWE", "ruwe", [0, 1.2, 1.4, 2, 3, 5, 10, 100])
table("visibility periods", "visibility_periods_used", [0, 12, 16, 20, 24, 28, 32, 36, 40, 60])
table("BP-RP", "bp_rp", [-1, 0, 0.5, 0.8, 1, 1.2, 1.5, 2, 3, 6])
for ty in ["Orbital", "AstroSpectroSB1"]:
    table(f"period, {ty}", "period", [10, 100, 200, 300, 400, 500, 700, 900, 1100, 3000], df[df.nss_solution_type == ty])
