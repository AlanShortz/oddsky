"""Do radial velocities confirm astrometric orbits equally for both senses? Development split unless --heldout."""
import argparse
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import handedness as hd  # noqa: E402


def load(heldout=False):
    df = pd.read_csv(hd.NSS_CSV, dtype={"source_id": "int64"})
    df = df.merge(pd.read_csv(f"{hd.RUNS}/data/nss/nss_extra.csv", dtype={"source_id": "int64"}), on="source_id", how="left")
    rv = pd.read_csv(f"{hd.RUNS}/data/nss/nss_rv.csv", dtype={"source_id": "int64"})
    df = df.merge(rv[["source_id"] + [c for c in rv.columns if c not in df.columns]], on="source_id", how="left")
    dev = hd.is_dev(df.source_id.values)
    df = df[~dev if heldout else dev].copy()
    A, B, F, G = df.a_thiele_innes, df.b_thiele_innes, df.f_thiele_innes, df.g_thiele_innes
    df["y"] = np.sign(B * F - A * G)
    df["sense"] = df.y * np.sign(df.ecl_lat)  # +1 means L has a component along +NEP on this line of sight
    u_ = (A**2 + B**2 + F**2 + G**2) / 2
    v_ = A * G - B * F
    df["a0"] = np.sqrt(u_ + np.sqrt(np.maximum((u_ + v_) * (u_ - v_), 0)))
    df["cosi"] = np.clip(v_ / df.a0**2, -1, 1)
    df["sini"] = np.sqrt(1 - df.cosi**2)
    df["a0_au"] = df.a0 / df.parallax
    df["mf"] = df.a0_au**3 / (df.period / 365.25) ** 2  # photocentre mass function, Msun
    df["kpred"] = 4.74047 * 2 * np.pi * df.a0_au * df.sini / ((df.period / 365.25) * np.sqrt(1 - df.eccentricity**2))  # km/s
    return df


def binom(x):
    f = x.mean()
    return f, np.sqrt(f * (1 - f) / max(len(x), 1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--heldout", action="store_true")
    args = ap.parse_args()
    d = load(args.heldout)
    d = d[d.nss_solution_type.isin(["Orbital", "AstroSpectroSB1"])]
    print("split", "HELD-OUT" if args.heldout else "dev", len(d))
    orb = d[d.nss_solution_type == "Orbital"]
    has_rv = orb[orb.rv_chisq_pvalue.notna() & (orb.rv_nb_transits >= 8)]
    print("Orbital", len(orb), "with rv_chisq_pvalue & >=8 transits", len(has_rv))
    print("\nRV-variable rate (p<0.001) for Orbital stars with predicted K > 5 km/s")
    rows = []
    for lo, hi in [(50, 200), (200, 300), (300, 450), (450, 600), (600, 900), (900, 1200), (1200, 3000)]:
        s = has_rv[(has_rv.period >= lo) & (has_rv.period < hi) & (has_rv.kpred > 5)]
        for name, sub in [("+NEP", s[s.sense > 0]), ("-NEP", s[s.sense < 0])]:
            f, e = binom(sub.rv_chisq_pvalue < 0.001)
            print(f"  P {lo}-{hi}  {name}  N={len(sub):5d}  rate={f:.3f} ± {e:.3f}")
    print("\nAsymmetry and physical plausibility (Orbital + AstroSpectroSB1), by period zone")
    for lo, hi in [(50, 300), (300, 450), (450, 600), (600, 900), (900, 3000)]:
        s = d[(d.period >= lo) & (d.period < hi)]
        print(f"P {lo}-{hi}: N={len(s)}")
        for name, c, edges in [
            ("mass function (Msun)", "mf", [0, 0.01, 0.03, 0.1, 0.2, 0.3, 0.5, 1, 100]),
            ("parallax", "parallax", [0, 0.7, 1, 1.5, 2, 3, 5, 1000]),
        ]:
            line = [f"   {name}:"]
            for a, b in zip(edges[:-1], edges[1:]):
                x = s[(s[c] >= a) & (s[c] < b)]
                if len(x) < 40:
                    continue
                m, se = x.sense.mean(), np.sqrt((1 - x.sense.mean() ** 2) / len(x))
                line.append(f"[{a:g},{b:g}) {m:+.3f}±{se:.3f} n={len(x)};")
            print(" ".join(line))
