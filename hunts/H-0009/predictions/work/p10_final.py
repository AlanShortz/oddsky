"""p10: the proposed predictions. Reads p9_results.json (grader Monte Carlo), prints the GOST transits inside every window
and baseline, the noise-free G model at the window transits (targets 3-6: lens-posterior median and 16-84% range, fs_G
drawn as in models.L), and writes ../dr4_proposal.json. probability = the stake: P(true | resolved) from p9, shaded down
for targets 1-2 by 0.04-0.07 for model systematics the Monte Carlo does not hold (G vs ATLAS-o passband for a blend, Gaia
processing of DR4 unknown)."""
import json
import os
import sys

import numpy as np
from astropy.time import Time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gaialib import gost  # noqa: E402
from models import lens_dm, lens_posterior, sample  # noqa: E402
from targets import HERE, T  # noqa: E402

R = json.load(open(os.path.join(HERE, "p9_results.json")))
rng = np.random.default_rng(7)


def iso(m):
    return Time(m, format="mjd").iso[:10]


# (target, candidate key in p9, stake, scenario tested, statement)
CHOSEN = [
    ("J163539", "A' peak median -1.2", 0.93, "lens (ATLAS model) vs Gaia sees nothing; amplitude fs_G >= 0.65 x ATLAS ratio",
     "Gaia G in 2017 Jul 15 - Oct 16 (6 transits on Jul 29, Aug 20, Sep 19 2017) has a median at least 1.2 mag brighter than the 2014-07..2016-06 baseline (model: 1.6-2.1 mag)."),
    ("J163539", "B rise wing", 0.90, "slow lens rise seen in G months before peak (vs a short outburst or an ATLAS-only artefact)",
     "Gaia G in 2017 Jan 17 - Mar 28 (5 transits) has a median at least 0.10 mag brighter than the 2014-07..2016-06 baseline (model: 0.18-0.37 mag)."),
    ("J163539", "C decline wing", 0.90, "slow lens decline in G 5-7 months after peak",
     "Gaia G in 2018 Jan 22 - Apr 7 (5 transits) has a median at least 0.07 mag brighter than the 2014-07..2016-06 baseline (model: 0.10-0.30 mag)."),
    ("J173150", "A3 Feb-Oct brightest", 0.90, "lens (ATLAS parallax model) vs Gaia sees nothing; G amplitude at +27 d",
     "The brightest Gaia night in 2018 Feb 1 - Oct 9 is at least 1.0 mag brighter than the 2014-07..2017-06 baseline (model: 1.4-1.85 mag on 2018 Aug 9)."),
    ("J173150", "B rise wing", 0.92, "slow lens rise in G (NEOWISE saw W1 -0.35 on 2018 Mar 15)",
     "Gaia G in 2018 Feb 1 - Apr 7 (6 transits) has a median at least 0.10 mag brighter than the 2014-07..2017-06 baseline (model: 0.19-0.30 mag)."),
    ("J124517", "A brightest -58..+27", 0.57, "real brightening of the Gaia star (lens or outburst lasting >~ weeks) vs artifact / other star",
     "The brightest Gaia night in 2018 May 17 - Aug 10 (6 transits on 3 nights: May 26, Jun 19, Jul 27) is at least 0.3 mag brighter than the 2014-07..2017-06 baseline."),
    ("J124517", "B median -58..+27", 0.50, "a weeks-to-months event on the Gaia star (lens, tE >~ 40 d) vs a short outburst or artifact",
     "Gaia G in 2018 May 17 - Aug 10 (6 transits) has a median at least 0.15 mag brighter than the 2014-07..2017-06 baseline."),
    ("J160706", "A median -35..+45", 0.74, "real slow event on the Gaia star vs artifact / event on another star in the WISE beam",
     "Gaia G in 2017 Jul 11 - Sep 29 (5 transits on Jul 23, Aug 17, Sep 16) has a median at least 0.5 mag brighter than the 2014-07..2016-06 baseline."),
    ("J160706", "B brightest -35..+45 < -1.5", 0.71, "achromatic lens with fs_G >= fs_W1 (G amplitude >= W1's x8 visit) vs a weaker, chromatic G response",
     "The brightest Gaia night in 2017 Jul 11 - Sep 29 is at least 1.5 mag brighter than the 2014-07..2016-06 baseline (NEOWISE W1 was 2.3 mag up on Aug 15)."),
    ("J131026", "A' median -51..+64 (-0.2)", 0.70, "real months-long event on the Gaia star (lens) vs artifact / days-long flare",
     "Gaia G in 2015 Jun 12 - Oct 5 (6 transits on 4 nights) has a median at least 0.2 mag brighter than the 2016-08..2020-01 baseline."),
    ("J131026", "B brightest -51..+64 < -0.6", 0.69, "achromatic lens with fs_G >= fs_W1 (W1 was 1.0 mag up on 2015 Aug 1)",
     "The brightest Gaia night in 2015 Jun 12 - Oct 5 is at least 0.6 mag brighter than the 2016-08..2020-01 baseline."),
    ("J154239", "A brightest -33..+42", 0.48, "real brightening of the Gaia star vs artifact / event on the G 17.6 neighbour at 3.2\"",
     "The brightest Gaia night in 2017 Jul 11 - Sep 24 (5 transits on Jul 21, Aug 17, Sep 15) is at least 0.4 mag brighter than the 2014-07..2016-08 baseline."),
    ("J154239", "B' median -33..+42 (-0.15)", 0.45, "event on the Gaia star lasting >~ 2 weeks (lens) vs short outburst / artifact",
     "Gaia G in 2017 Jul 11 - Sep 24 (5 transits) has a median at least 0.15 mag brighter than the 2014-07..2016-08 baseline."),
]

out = []
post_cache = {}
for k, ck, stake, scen, stmt in CHOSEN:
    r = R[k][ck]
    c = r["check"]
    t = gost(k)
    w = t[(t >= c["start"]) & (t <= c["end"])]
    b = t[(t >= c["baseline"][0]) & (t <= c["baseline"][1])]
    line = (f"{k} | {ck}: window {iso(c['start'])}..{iso(c['end'])} {len(w)} transits / {len(np.unique(np.floor(w)))} nights "
            f"({', '.join(sorted({iso(x) for x in w}))}); baseline {iso(c['baseline'][0])}..{iso(c['baseline'][1])} {len(b)} transits; "
            f"MC P(true|resolved) {r['stake']:.3f} (20% loss {r['loss20']['stake']:.3f}), P(unres) {r['p_unres']:.3f} "
            f"(20% loss {r['loss20']['p_unres']:.3f}); stake {stake}")
    print(line)
    if k not in ("J163539", "J173150"):
        if k not in post_cache:
            post_cache[k] = sample(lens_posterior(k, rng), rng, 500)
        S = post_cache[k]
        dms = []
        for i in range(500):
            d = {kk: S[kk][i] for kk in S}
            dms.append(lens_dm(w, d, d["fs"] + (1 - d["fs"]) * rng.uniform()))
        dms = np.array(dms)
        print("    lens model dG at window transits (median [16-84]): " + "; ".join(
            f"{iso(x)} {np.median(dms[:, j]):+.2f} [{np.percentile(dms[:, j], 16):+.2f},{np.percentile(dms[:, j], 84):+.2f}]"
            for j, x in enumerate(w)))
    out.append(dict(case_target=T[k]["name"], gaia_id=T[k]["gaia"], statement=stmt, probability=stake, series="GAIA:G",
                    start=c["start"], end=c["end"], statistic=c["statistic"], baseline_start=c["baseline"][0],
                    baseline_end=c["baseline"][1], op=c["op"], value=c["value"], p_unresolvable=round(r["p_unres"], 3),
                    scenario=scen, mc_p_true_given_resolved=round(r["stake"], 3),
                    mc_per_scenario={s: round(v["p_true"], 3) for s, v in r["per_scenario"].items()}))
json.dump(out, open(os.path.join(HERE, "..", "dr4_proposal.json"), "w"), indent=1)
print(f"wrote {len(out)} predictions")
