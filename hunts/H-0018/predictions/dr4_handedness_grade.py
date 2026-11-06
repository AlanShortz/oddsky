"""Grade the H-0018 DR4 forecasts from a CSV of astrometric orbit solutions.

    uv run python hunts/H-0018/predictions/dr4_handedness_grade.py DR4_ORBITS.csv
    uv run python hunts/H-0018/predictions/dr4_handedness_grade.py --self-test DR3_ORBITS.csv

Needed columns: nss_solution_type, period, eccentricity, parallax_error, phot_g_mean_mag, ecl_lat, a/b/f/g_thiele_innes.
"""
import argparse

import numpy as np
import pandas as pd

BINS = [(340, 390), (600, 700), (700, 800), (800, 900), (1100, 1600)]
TYPES = ["Orbital", "AstroSpectroSB1"]


def prepare(df):
    df = df[df.nss_solution_type.isin(TYPES)].copy()
    y = np.sign(df.b_thiele_innes * df.f_thiele_innes - df.a_thiele_innes * df.g_thiele_innes)
    df["sense"] = y * np.sign(df.ecl_lat)
    return df


def ratio(df, lo, hi, emin=0.0, emax=1.0):
    """N-weighted mean, over unit G bins in 12 <= G < 16, of median parallax_error (+NEP) / (-NEP), Orbital only."""
    o = df[(df.nss_solution_type == "Orbital") & (df.period >= lo) & (df.period < hi) & (df.eccentricity >= emin) & (df.eccentricity < emax)]
    vals, wts = [], []
    for g in range(12, 16):
        s = o[(o.phot_g_mean_mag >= g) & (o.phot_g_mean_mag < g + 1)]
        p, m = s[s.sense > 0], s[s.sense < 0]
        if min(len(p), len(m)) >= 10:
            vals.append(np.median(p.parallax_error) / np.median(m.parallax_error))
            wts.append(len(p) + len(m))
    return float(np.average(vals, weights=wts)) if vals else float("nan")


def asym(df, lo, hi):
    s = df[(df.period >= lo) & (df.period < hi)]
    m = s.sense.mean()
    return float(m), float(np.sqrt((1 - m**2) / max(len(s), 1))), len(s)


def grade(df):
    r = {f"ratio_{lo}_{hi}": ratio(df, lo, hi) for lo, hi in BINS}
    contrast = r["ratio_700_800"] - 0.5 * (r["ratio_600_700"] + r["ratio_800_900"])
    low_e, high_e = ratio(df, 700, 800, 0, 0.2), ratio(df, 700, 800, 0.4, 1.0)
    circular = ratio(df, 600, 900, 0, 5e-4)
    a, e, n = asym(df, 340, 390)
    a_two, a_long = asym(df, 600, 900)[0], asym(df, 1100, 3000)[0]
    verdict = {
        "F1 one-year inflation persists: ratio 340-390 d > 1.05": r["ratio_340_390"] > 1.05,
        "F2 two-year peak stands out: contrast against 600-700 and 800-900 d > 0.05": contrast > 0.05,
        "F3 shoulders collapse: ratio 600-700 d and 800-900 d both < 1.10": r["ratio_600_700"] < 1.10 and r["ratio_800_900"] < 1.10,
        "F4 long periods collapse: ratio 1100-1600 d < 1.08": r["ratio_1100_1600"] < 1.08,
        "F5 Earth-sense deficit at one year: A(340-390 d) < 0 at 3 sigma": a < -3 * e,
        "F6 peak falls with e: ratio 700-800 d, e < 0.2 minus e >= 0.4, > 0.10": low_e - high_e > 0.10,
        "F7 e and T fixed removes it: e < 5e-4, 600-900 d, |ratio - 1| < 0.10": abs(circular - 1) < 0.10,
        "F8 asymmetry fades at two years: A(600-900 d) > -0.05": a_two > -0.05,
        "F9 asymmetry fades at long periods: A(1100-3000 d) > -0.03": a_long > -0.03,
    }
    print(r)
    print(f"contrast {contrast:.3f}; 700-800 d by e: {low_e:.3f}, {high_e:.3f}; e < 5e-4, 600-900 d: {circular:.3f}")
    print(f"A(340-390 d) = {a:+.3f} +/- {e:.3f}, N = {n}; A(600-900 d) = {a_two:+.3f}; A(1100-3000 d) = {a_long:+.3f}")
    for k, v in verdict.items():
        print(("TRUE " if v else "FALSE"), k)
    return verdict


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("orbits")
    ap.add_argument("--self-test", action="store_true", help="run on DR3: only F3, F4, F8 and F9 should be FALSE")
    args = ap.parse_args()
    out = grade(prepare(pd.read_csv(args.orbits, dtype={"source_id": "int64"})))
    if args.self_test:
        false = [k for k, v in out.items() if not v]
        assert [k[:2] for k in false] == ["F3", "F4", "F8", "F9"], false
        print("self-test passed")
