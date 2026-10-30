"""r10c: the referee's proposed replacement predictions, through the same grader Monte Carlo as r10 (also with a 20%
transit-loss rate, and with a scenario where Gaia's variability cleaning flags every transit brighter than 0.5 mag, which the
Oddsky grader then drops)."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from r10_gaia_predictions import MODELS, SIG, gost, grade, lens_ratio  # noqa: E402

rng = np.random.default_rng(2)
NEW = {
    "J180624": [
        ("A  DR4 brightest - DR4 median > -0.5", dict(win=("2014-07-25", "2020-01-20"), stat="brightest", base=("2014-07-25", "2020-01-20"), op=">", v=-0.5)),
        ("B  DR4 median(2014-07-25..2016-06-30) - median(2018-01-01..2020-01-20) < 0.1", dict(win=("2014-07-25", "2016-06-30"), stat="median", base=("2018-01-01", "2020-01-20"), op="<", v=0.1)),
        ("B' same, > -0.1", dict(win=("2014-07-25", "2016-06-30"), stat="median", base=("2018-01-01", "2020-01-20"), op=">", v=-0.1)),
        ("C  DR5 brightest(2022-02-01..2023-05-31) - median(2015-2021) < -1.2", dict(win=("2022-02-01", "2023-05-31"), stat="brightest", base=("2015-01-01", "2021-12-31"), op="<", v=-1.2)),
        ("C2 DR5 median(2022-02-01..2022-04-30) - median(2015-2021) < -0.1 (rising wing)", dict(win=("2022-02-01", "2022-04-30"), stat="median", base=("2015-01-01", "2021-12-31"), op="<", v=-0.1)),
        ("C3 DR5 median(2023-03-01..2023-04-30) - median(2015-2021) < -0.1 (falling wing)", dict(win=("2023-03-01", "2023-04-30"), stat="median", base=("2015-01-01", "2021-12-31"), op="<", v=-0.1)),
    ],
    "J183040": [
        ("D1 DR4 brightest - DR4 median > -0.3", dict(win=("2014-07-25", "2020-01-20"), stat="brightest", base=("2014-07-25", "2020-01-20"), op=">", v=-0.3)),
        ("D2 DR5 brightest(2022-02-01..2023-05-31) - median(2015-2021) < -0.3", dict(win=("2022-02-01", "2023-05-31"), stat="brightest", base=("2015-01-01", "2021-12-31"), op="<", v=-0.3)),
    ],
}
for k in NEW:
    t_all = gost(k)
    for mname, (p, fss) in MODELS[k].items():
        fs = fss[0] if k == "J183040" else 0.8  # the least favourable J180624 case
        dm = -2.5 * np.log10(lens_ratio(k, t_all, p, fs))
        for loss in (0.10, 0.20):
            for flagged in (False, True):
                res = {lab: [] for lab, _ in NEW[k]}
                for _ in range(2000):
                    keep = rng.random(len(t_all)) > loss
                    t = t_all[keep] + rng.normal(0, 0.15, keep.sum())
                    m = dm[keep] + rng.normal(0, SIG[k], keep.sum())
                    out = rng.random(len(t)) < 0.02
                    m[out] += rng.choice([-1, 1], out.sum()) * rng.uniform(0.2, 1.0, out.sum())
                    if flagged:
                        ok = m - np.median(m) > -0.5
                        t, m = t[ok], m[ok]
                    for lab, P in NEW[k]:
                        res[lab].append(grade(t, m, P))
                print(f"{k} model '{mname}' fs {fs} loss {loss:.0%} {'event transits flagged+dropped' if flagged else ''}")
                for lab, _ in NEW[k]:
                    v = pd.Series(res[lab]).value_counts(normalize=True)
                    print(f"   P(true) {v.get('True', 0):.2f} P(unres) {v.get('unresolvable', 0):.2f} | {lab}")
