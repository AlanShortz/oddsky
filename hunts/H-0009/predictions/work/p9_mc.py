"""p9: candidate DR4 predictions through a Monte Carlo of the Oddsky grader (gaialib.grade = oddsky.tools.evaluate:
points in [start, end]; < 3 points = unresolvable; brightest = min nightly median (floor(MJD) bins); baseline median
subtracted). Observed series per realisation: GOST transits (barycentric MJD) in the DR4 span, 10% lost at random
(DR3 delivered 93-100% of the GOST forecast, p4), per-transit noise sigma_G(G at that transit), 2% outliers of
+-0.2..1.0 mag. Pessimistic branch (3% weight): every transit > 0.5 mag above the series median dropped, as if flagged
rejected_by_photometry (p7 found 0 such flags on 918 DR3 microlensing transits, so this is a tail risk).

Scenario weights (P of each scenario for the Gaia star) are stated per target below; P(true) is the weighted mixture.
Probability to stake = P(true | resolved) = P(true) / (1 - P(unresolvable)). Also printed: the same with 20% loss.
Writes work/p9_results.json."""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gaialib import gost, grade, simulate  # noqa: E402
from models import atlas_draws, scenario_draws  # noqa: E402
from targets import HERE, T  # noqa: E402

rng = np.random.default_rng(20261030)
N_MODEL, N_NOISE = 600, 4
FLAG_W = 0.03

# Dates: MJD. 56863.5 = 2014-07-25, 57570 = 2016-06-30, 57935 = 2017-06-30, 58868 = 2020-01-20.
BASE_EARLY = (56863.5, 57570.0)
PRIORS = {  # P(scenario): L lens on the Gaia star, R real non-lens on the Gaia star, F short outburst, N Gaia sees nothing
    "J163539": dict(ATLAS=0.97, N=0.03),  # DR3 CCD deficit (p6) says Gaia saw the 2017 rise
    "J173150": dict(ATLAS=0.95, N=0.05),
    "J124517": dict(L=0.35, R=0.15, F=0.15, N=0.35),
    "J160706": dict(L=0.55, R=0.20, F=0.00, N=0.25),  # mild DR3 CCD deficit (p6, 12th pct, ~4 transits)
    "J131026": dict(L=0.50, R=0.20, F=0.05, N=0.25),  # DR3 CCD deficit 1.4th pct (~9 transits), scatter 95th pct
    "J154239": dict(L=0.30, R=0.10, F=0.15, N=0.45),
}


def C(start, end, statistic, op, value, baseline=None):
    return dict(start=start, end=end, statistic=statistic, op=op, value=value, baseline=baseline)


CANDS = {
    "J163539": {
        "A peak median": C(57949.0, 58042.0, "median", "<", -1.0, BASE_EARLY),
        "A' peak median -1.2": C(57949.0, 58042.0, "median", "<", -1.2, BASE_EARLY),
        "B rise wing": C(57770.0, 57840.0, "median", "<", -0.10, BASE_EARLY),
        "C decline wing": C(58140.0, 58215.0, "median", "<", -0.07, BASE_EARLY),
    },
    "J173150": {
        "A peak brightest": C(58330.0, 58400.0, "brightest", "<", -1.0, (56863.5, 57935.0)),
        "A3 Feb-Oct brightest": C(58150.0, 58400.0, "brightest", "<", -1.0, (56863.5, 57935.0)),
        "A2 Feb-Oct median": C(58150.0, 58400.0, "median", "<", -0.2, (56863.5, 57935.0)),
        "B rise wing": C(58150.0, 58215.0, "median", "<", -0.10, (56863.5, 57935.0)),
        "C 2019 back to baseline": C(58500.0, 58868.0, "median", ">", -0.10, (56863.5, 57935.0)),
    },
    "J124517": {
        "A brightest -58..+27": C(58255.0, 58340.0, "brightest", "<", -0.3, (56863.5, 57935.0)),
        "A' brightest -33..+57": C(58280.0, 58370.0, "brightest", "<", -0.3, (56863.5, 57935.0)),
        "B median -58..+27": C(58255.0, 58340.0, "median", "<", -0.15, (56863.5, 57935.0)),
        "B' median -58..+87": C(58255.0, 58400.0, "median", "<", -0.10, (56863.5, 57935.0)),
    },
    "J160706": {
        "A median -35..+45": C(57945.0, 58025.0, "median", "<", -0.5, BASE_EARLY),
        "A' median -35..+45 (-1.0)": C(57945.0, 58025.0, "median", "<", -1.0, BASE_EARLY),
        "B brightest -35..+45 < -1.5": C(57945.0, 58025.0, "brightest", "<", -1.5, BASE_EARLY),
        "C rise+peak median": C(57770.0, 58025.0, "median", "<", -0.5, BASE_EARLY),
        "D decline wing": C(58140.0, 58215.0, "median", "<", -0.05, BASE_EARLY),
    },
    "J131026": {
        "A median -51..+64": C(57185.0, 57300.0, "median", "<", -0.3, (57600.0, 58868.0)),
        "A' median -51..+64 (-0.2)": C(57185.0, 57300.0, "median", "<", -0.2, (57600.0, 58868.0)),
        "B brightest -51..+64 < -0.6": C(57185.0, 57300.0, "brightest", "<", -0.6, (57600.0, 58868.0)),
        "B' brightest -51..+64 < -0.4": C(57185.0, 57300.0, "brightest", "<", -0.4, (57600.0, 58868.0)),
        "C wide median -115..+130": C(57120.0, 57366.0, "median", "<", -0.15, (57600.0, 58868.0)),
    },
    "J154239": {
        "A brightest -33..+42": C(57945.0, 58020.0, "brightest", "<", -0.4, (56863.5, 57630.0)),
        "A' brightest -33..+42 (-0.25)": C(57945.0, 58020.0, "brightest", "<", -0.25, (56863.5, 57630.0)),
        "B median -33..+42": C(57945.0, 58020.0, "median", "<", -0.3, (56863.5, 57630.0)),
        "B' median -33..+42 (-0.15)": C(57945.0, 58020.0, "median", "<", -0.15, (56863.5, 57630.0)),
        "C Oct-Nov 2017 (+60..+110)": C(58040.0, 58090.0, "median", "<", -0.1, (56863.5, 57630.0)),
    },
}


def run(t_all, G, dms, cands, loss):
    """Per candidate: (P true, P unresolvable) over model draws x noise draws, with the flag branch mixed in."""
    out = {}
    for flag in (None, -0.5):
        res = {c: [] for c in cands}
        for dm in dms:
            for _ in range(N_NOISE):
                t, m = simulate(t_all, dm, G, rng, loss=loss, flag_bright=flag)
                for c, chk in cands.items():
                    res[c].append(grade(t, m, chk))
        for c in cands:
            r = np.array(res[c])
            out.setdefault(c, []).append(((r == "true").mean(), (r == "unresolvable").mean()))
    return {c: tuple((1 - FLAG_W) * np.array(v[0]) + FLAG_W * np.array(v[1])) for c, v in out.items()}


results = {}
for k, cands in CANDS.items():
    tg = T[k]
    t_all = gost(k)
    if k in ("J163539", "J173150"):
        dms, _ = atlas_draws(k, t_all, rng, N_MODEL)
        scen = {"ATLAS": dms}
    else:
        sd = scenario_draws(k, t_all, rng, N_MODEL)
        post = sd["post"]
        S = sd["S"]
        print(f"== {k}: lens posterior ESS {post['ess']:.0f}, chi2min {post['chi2min']:.1f} ({post['nvis']} visits), t0 window "
              f"{post['lo']:.0f}..{post['hi']:.0f}; tE median {np.median(S['te']):.0f} (16-84: {np.percentile(S['te'], 16):.0f}-"
              f"{np.percentile(S['te'], 84):.0f}); t0-tvis 16/50/84: {np.percentile(S['t0'] - tg['t_nw'], [16, 50, 84]).round(0)}; "
              f"fs_W1 median {np.median(S['fs']):.2f}; tE2 (fall) median {np.median(S['te2']):.0f}; F draws {len(sd['F'])}")
        scen = {"L": sd["L"], "R": sd["R"], "F": sd["F"]}
    scen["N"] = [np.zeros_like(t_all)] * max(N_MODEL // 3, 50)
    pri = PRIORS[k]
    results[k] = {}
    for loss in (0.10, 0.20):
        per = {s: run(t_all, tg["G"], dms_s, cands, loss) for s, dms_s in scen.items() if pri.get(s, 0) > 0 and len(dms_s)}
        if loss == 0.10:
            print(f"== {k} (G {tg['G']}), priors {pri}")
        for c in cands:
            pt = sum(pri[s] * per[s][c][0] for s in per)
            pu = sum(pri[s] * per[s][c][1] for s in per)
            stake = pt / (1 - pu) if pu < 1 else float("nan")
            sc = "  ".join(f"{s}: {per[s][c][0]:.2f}/{per[s][c][1]:.2f}" for s in per)
            if loss == 0.10:
                print(f"   {c:34s} P(true) {pt:.3f} P(unres) {pu:.3f} -> stake {stake:.3f}   [true/unres per scenario: {sc}]")
                results[k][c] = dict(check=cands[c], p_true=pt, p_unres=pu, stake=stake,
                                     per_scenario={s: dict(p_true=per[s][c][0], p_unres=per[s][c][1]) for s in per})
            else:
                print(f"   {c:34s} (20% loss) P(true) {pt:.3f} P(unres) {pu:.3f} -> stake {stake:.3f}")
                results[k][c]["loss20"] = dict(p_true=pt, p_unres=pu, stake=stake)
json.dump(results, open(os.path.join(HERE, "p9_results.json"), "w"), indent=1)
