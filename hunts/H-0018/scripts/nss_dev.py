"""NSS dipole on the 30% development split (or held-out with --heldout, once the method is frozen)."""
import argparse
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import handedness as hd  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--heldout", action="store_true")
args = ap.parse_args()

df = pd.read_csv(hd.NSS_CSV, dtype={"source_id": "int64"})
dev = hd.is_dev(df.source_id.values)
print(f"rows {len(df)}, dev fraction {dev.mean():.4f}")
df = df[~dev if args.heldout else dev].copy()
print("split:", "HELD-OUT" if args.heldout else "dev", len(df))

df["cross"] = df.b_thiele_innes * df.f_thiele_innes - df.a_thiele_innes * df.g_thiele_innes
df["y"] = np.sign(df.cross)
print("y == 0 or NaN:", int((df.y == 0).sum() + df.y.isna().sum()))
n = hd.gal_vectors(df.ra.values, df.dec.values)
df[["nx", "ny", "nz"]] = n
core = df[df.nss_solution_type.isin(["Orbital", "AstroSpectroSB1"])]


def run(label, sub):
    if len(sub) < 200:
        return
    print(hd.fmt(label, hd.fit_dipole(sub.y.values, sub[["nx", "ny", "nz"]].values)))


run("Orbital + AstroSpectroSB1", core)
run("Orbital", core[core.nss_solution_type == "Orbital"])
run("AstroSpectroSB1", core[core.nss_solution_type == "AstroSpectroSB1"])
run("All astrometric types", df)
for lo, hi in [(0, 100), (100, 300), (300, 450), (450, 800), (800, 1e9)]:
    run(f"P in [{lo},{hi:.0f}) d", core[(core.period >= lo) & (core.period < hi)])
print("\n1 yr zoom")
for lo, hi in [(200, 300), (300, 340), (340, 390), (390, 450), (450, 550)]:
    run(f"P in [{lo},{hi}) d", core[(core.period >= lo) & (core.period < hi)])

X = core
print("\nSplits for the sample overall")
run("north b>0", X[X.nz > 0])
run("south b<0", X[X.nz < 0])
run("G<median", X[X.phot_g_mean_mag < X.phot_g_mean_mag.median()])
run("G>median", X[X.phot_g_mean_mag >= X.phot_g_mean_mag.median()])
run("plx>median", X[X.parallax > X.parallax.median()])
run("plx<median", X[X.parallax <= X.parallax.median()])

# Period counts of both senses in the frame of the parallactic ellipse
v = core.nx * hd.NEP_GAL[0] + core.ny * hd.NEP_GAL[1] + core.nz * hd.NEP_GAL[2]
core = core.assign(sense=core.y * np.sign(v))
print("\nFraction with L.n sign matching L along +NEP, by period (bins of 40 d near 1 yr)")
for lo in range(200, 560, 40):
    s = core[(core.period >= lo) & (core.period < lo + 40) & (np.abs(v) > 0.3)]
    f = (s.sense > 0).mean()
    print(f"  {lo}-{lo + 40} d  N={len(s):6d}  f={f:.3f} ± {np.sqrt(f * (1 - f) / len(s)):.3f}")

# Full 3D mean of L-hat from AstroSpectroSB1
s3 = df[df.nss_solution_type == "AstroSpectroSB1"].dropna(subset=["c_thiele_innes", "h_thiele_innes"])
P = np.column_stack([s3.b_thiele_innes, s3.a_thiele_innes, s3.c_thiele_innes])
Q = np.column_stack([s3.g_thiele_innes, s3.f_thiele_innes, s3.h_thiele_innes])
L = np.cross(P, Q)  # in (east, north, outward)
L /= np.linalg.norm(L, axis=1, keepdims=True)
print(f"\nAstroSpectroSB1 N={len(s3)}  mean(cos L,n)={L[:, 2].mean():+.4f} ± {L[:, 2].std() / np.sqrt(len(L)):.4f}")
