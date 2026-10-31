"""s7: what the missing VARIABLE flags say about the strong events as a population. Known lenses recovered blind by H-0009 inside
the DR3 span, and not selected through Gaia (s5), set P(a VARIABLE Gaia DR3 source within 4" | lens). Compared with the fraction
among the in-span strong events that have a Gaia source within 4", restricted alike by Gaia G of the brightest source within 2"
and by GOST transits within +-30 d. Prints only; the numbers go into the report."""
import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import beta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA, H9  # noqa: E402

gost = pd.read_csv(os.path.join(DATA, "gost_transits.csv"))
k = pd.read_csv(os.path.join(DATA, "calib_known.csv"))
kc = pd.read_csv(os.path.join(H9, "work", "sky4_classified.csv"), usecols=["designation", "t"]).drop_duplicates("designation")
s = pd.read_csv(os.path.join(H9, "work", "gaia_dr3_sweep.csv"), dtype={"gaia_source_id": str})


def n30(d, t):
    g = gost[gost.designation == d]
    return int((np.abs(g.mjd - t) <= 30).sum())


k["gost_n30"] = [n30(r.designation, r.t) for r in k.itertuples()]
ku = k[~k.gaia_selected]
ss = s[s.in_dr3_span & (s.n_gaia_4as > 0)]


def ci(x, n):
    return beta.ppf(0.025, x, n - x + 1) if x else 0.0, beta.ppf(0.975, x + 1, n - x) if x < n else 1.0


def show(name, n, x):
    lo, hi = ci(x, n)
    print(f"  {name}: {x}/{n} = {x / n:.2f} (95% {lo:.2f}-{hi:.2f})")


print("P(VARIABLE source within 4\"):")
show("known lenses, not Gaia-selected", len(ku), int((ku.var4 > 0).sum()))
show("strong events in the DR3 span with a Gaia source within 4\"", len(ss), int((ss.n_variable_4as > 0).sum()))
print("\nGaia G of the matched star: known (unbiased) median %.2f, strong (chosen source) median %.2f" % (ku.G.median(), ss.G.median()))
print("GOST transits within +-30 d: known median %d (min %d), strong median %d (min %d)" % (
    ku.gost_n30.median(), ku.gost_n30.min(), ss.gost_n30.median(), ss.gost_n30.min()))
for lo, hi in ((0, 17.0), (17.0, 22)):
    a = ku[(ku.G >= lo) & (ku.G < hi)]
    b = ss[(ss.G >= lo) & (ss.G < hi)]
    print(f"\nG {lo}-{hi}:")
    show("known", len(a), int((a.var4 > 0).sum()))
    show("strong", len(b), int((b.n_variable_4as > 0).sum()))
a = ku[ku.gost_n30 >= 2]
b = ss[ss.gost_n30 >= 2]
print("\n>= 2 GOST transits within +-30 d:")
show("known", len(a), int((a.var4 > 0).sum()))
show("strong", len(b), int((b.n_variable_4as > 0).sum()))
# lens fraction among the strong events: f * p_lens + (1 - f) * p_bg = observed
p = (ku.var4 > 0).mean()
obs = (ss.n_variable_4as > 0).mean()
print(f"\nimplied lens fraction among in-span strong events with a Gaia source (background VARIABLE rate ~0): {obs / p:.2f}")
rng = np.random.default_rng(1)
pk = rng.beta((ku.var4 > 0).sum() + 1, (ku.var4 == 0).sum() + 1, 100000)
po = rng.beta((ss.n_variable_4as > 0).sum() + 1, (ss.n_variable_4as == 0).sum() + 1, 100000)
f = np.clip(po / pk, 0, 1)
print(f"  Monte Carlo (flat priors): median {np.median(f):.2f}, 95% {np.percentile(f, 2.5):.2f}-{np.percentile(f, 97.5):.2f}")
print(f"  per event: absence of a VARIABLE flag multiplies the lens odds by ~{1 - p:.2f} (P(no flag | lens) / P(no flag | no optical event ~ 1))")
print("\nknown lenses without a VARIABLE source (unbiased set):")
print(ku[ku.var4 == 0][["designation", "t", "dw1", "G", "gost_n30", "known"]].to_string(index=False))
