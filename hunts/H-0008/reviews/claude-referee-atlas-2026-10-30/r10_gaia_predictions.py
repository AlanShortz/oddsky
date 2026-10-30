"""r10: the proposed Sky Ledger predictions against Gaia's actual scanning (GOST forecast, gaia.esac.esa.int/gost, fetched
2026-10-30 into data/gost_<k>.csv; predicted times good to ~6 h; dead time not modelled) and a Monte Carlo of the grader
(oddsky.tools.evaluate: flagged points dropped, nightly medians for extremes, <3 points = unresolvable).

Event models: the referee's main-reduction parallax fits (r3/r7). Gaia G sees the Gaia target only; the flux ratio in G is
fs_G*A + 1 - fs_G. J180624: fs_G 0.8-1.0 (Gaia-resolved neighbours give 0.93 of ATLAS flux). J183040: two cases, (i) the free-fs
fit's observed ratio curve (blend unresolved by Gaia, so G sees the same ratio as ATLAS), (ii) fs >= 0.9 parallax fit.
Noise: per-transit G error 0.010 mag (J180624, G 17.0) / 0.006 (J183040, G 14.3); outliers 2% of transits, +-0.2-1.0 mag either
sign; 10% of transits lost at random; the grader's variability-flag rejection is ignored here (see report)."""
import os
import sys

import numpy as np
import pandas as pd
from astropy.time import Time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import HERE, TARGETS  # noqa: E402

from oddsky.analysis.lensing import Problem  # noqa: E402

rng = np.random.default_rng(1)


def mjd(s):
    return Time(s).mjd


def gost(k):
    g = pd.read_csv(os.path.join(HERE, "data", f"gost_{k}.csv"), skipinitialspace=True)
    t = Time(list(g["ObservationTimeAtGaia[UTC]"].str.replace("T", " ")), scale="utc").mjd
    return np.sort(t)


def lens_ratio(k, t, p, fs):
    T = TARGETS[k]
    q = Problem(t, np.ones_like(t), np.ones_like(t), np.array(["G"] * len(t)), ra=T["ra"], dec=T["dec"], parallax=True, blend=True, t0par=T["tpk"])
    return q.model(np.r_[p, fs])


MODELS = {  # t0, tE, u0, piE_N, piE_E (parallax, t0par = tpk) from r7/r7b
    "J180624": {"fit fs~0.8 (main)": ([59841.6, 130.1, -0.167, -0.273, -0.018], [0.8, 0.93, 1.0])},
    "J183040": {"free fs (ratio as observed)": ([59812.4, 220.6, 0.189, -0.129, -0.037], [0.15]),
                "fs>=0.9": ([59802.6, 101.5, 0.711, -0.469, -0.149], [0.95])},
}
SIG = {"J180624": 0.010, "J183040": 0.006}

PRED = {
    "J180624": [
        ("a  DR4 brightest night - DR4 median > -0.3", dict(win=("2014-07-25", "2020-01-20"), stat="brightest", base=("2014-07-25", "2020-01-20"), op=">", v=-0.3)),
        ("a' DR4 brightest night - DR4 median > -0.5", dict(win=("2014-07-25", "2020-01-20"), stat="brightest", base=("2014-07-25", "2020-01-20"), op=">", v=-0.5)),
        ("b  DR4 median(2014-07-25..2016-06-30) - median(2018-01-01..2020-01-20) < 0.1", dict(win=("2014-07-25", "2016-06-30"), stat="median", base=("2018-01-01", "2020-01-20"), op="<", v=0.1)),
        ("c  DR5 median(2022-08-25..2022-10-15) - median(2015-2021) < -1.0", dict(win=("2022-08-25", "2022-10-15"), stat="median", base=("2015-01-01", "2021-12-31"), op="<", v=-1.0)),
        ("c' DR5 brightest(2022-08-01..2022-11-15) - median(2015-2021) < -1.0", dict(win=("2022-08-01", "2022-11-15"), stat="brightest", base=("2015-01-01", "2021-12-31"), op="<", v=-1.0)),
        ("c'' DR5 median(2022-07-15..2022-11-30) - median(2015-2021) < -0.5", dict(win=("2022-07-15", "2022-11-30"), stat="median", base=("2015-01-01", "2021-12-31"), op="<", v=-0.5)),
    ],
    "J183040": [
        ("d1 DR4 brightest night - DR4 median > -0.3", dict(win=("2014-07-25", "2020-01-20"), stat="brightest", base=("2014-07-25", "2020-01-20"), op=">", v=-0.3)),
        ("d1' DR4 brightest night - DR4 median > -0.2", dict(win=("2014-07-25", "2020-01-20"), stat="brightest", base=("2014-07-25", "2020-01-20"), op=">", v=-0.2)),
        ("d2 DR5 median(2022-08-01..2022-09-30) - median(2015-2021) < -0.3", dict(win=("2022-08-01", "2022-09-30"), stat="median", base=("2015-01-01", "2021-12-31"), op="<", v=-0.3)),
        ("d2' DR5 brightest(2022-07-01..2022-10-31) - median(2015-2021) < -0.3", dict(win=("2022-07-01", "2022-10-31"), stat="brightest", base=("2015-01-01", "2021-12-31"), op="<", v=-0.3)),
        ("d2'' DR5 median(2022-07-01..2022-10-31) - median(2015-2021) < -0.2", dict(win=("2022-07-01", "2022-10-31"), stat="median", base=("2015-01-01", "2021-12-31"), op="<", v=-0.2)),
    ],
}


def grade(t, m, P):
    w0, w1 = mjd(P["win"][0]), mjd(P["win"][1]) + 1
    sel = (t >= w0) & (t <= w1)
    if sel.sum() < 3:
        return "unresolvable"
    tw, mw = t[sel], m[sel]
    night = np.floor(tw)
    nm = pd.Series(mw).groupby(night).median().values
    val = {"median": np.median(mw), "brightest": nm.min()}[P["stat"]]
    b0, b1 = mjd(P["base"][0]), mjd(P["base"][1]) + 1
    bs = (t >= b0) & (t <= b1)
    if bs.sum() < 3:
        return "unresolvable"
    val -= np.median(m[bs])
    return str(val > P["v"] if P["op"] == ">" else val < P["v"])


for k, T in TARGETS.items():
    t_all = gost(k)
    print(f"== {k}: {len(t_all)} GOST transits 2014-07-26..2025-01-15; in the DR3 window (to 2017-05-28): {(t_all < mjd('2017-05-28')).sum()}; "
          f"DR4 window (to 2020-01-20): {(t_all < mjd('2020-01-20')).sum()}")
    for lab, P in PRED[k]:
        w0, w1 = mjd(P["win"][0]), mjd(P["win"][1]) + 1
        tw = t_all[(t_all >= w0) & (t_all <= w1)]
        print(f"  {lab}\n     window transits {len(tw)} on {len(np.unique(np.floor(tw)))} nights: {[Time(x, format='mjd').iso[:10] for x in np.unique(np.floor(tw))][:12]}")
    for mname, (p, fss) in MODELS[k].items():
        for fs in fss:
            r = lens_ratio(k, t_all, p, fs)
            dm = -2.5 * np.log10(r)
            ev = (t_all > mjd("2022-06-01")) & (t_all < mjd("2022-12-31"))
            print(f"  model {mname}, fs_G {fs}: noise-free dG at the 2022 transits: "
                  + ", ".join(f"{Time(x, format='mjd').iso[:10]} {d:+.2f}" for x, d in zip(t_all[ev], dm[ev], strict=True)))
            res = {lab: [] for lab, _ in PRED[k]}
            for _ in range(2000):
                keep = rng.random(len(t_all)) > 0.10
                t = t_all[keep] + rng.normal(0, 0.15, keep.sum())
                m = dm[keep] + rng.normal(0, SIG[k], keep.sum())
                out = rng.random(len(t)) < 0.02
                m[out] += rng.choice([-1, 1], out.sum()) * rng.uniform(0.2, 1.0, out.sum())
                for lab, P in PRED[k]:
                    res[lab].append(grade(t, m, P))
            for lab, _ in PRED[k]:
                v = pd.Series(res[lab]).value_counts(normalize=True)
                print(f"     P(true) {v.get('True', 0):.2f}  P(unresolvable) {v.get('unresolvable', 0):.2f}  | {lab}")
