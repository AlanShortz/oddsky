"""e4: the ensemble forecast. Run from the repo root:  uv run python -I hunts/H-0009/predictions/work/ensemble/e4_ensemble.py

Merges the per-event scenario pass probabilities (e3) into dr4_ensemble_sample.csv together with the per-event evidence (below),
runs dr4_ensemble_grade.ensemble_mc (the same code the grader uses) and writes work/ensemble/forecast.json and the log.

Per-event evidence, all fixed here before DR4:
  lr_onstar  the H-0009 referee's centroid test. The on-star scenarios (L, R, F) are multiplied by 0.48 when the event-frame
             centroid moved away from the tested star (off_target True) and by 1.16 when it did not (False); 1 for the four
             H-0008-only events, which have no test. From P(off | event on the star) <= 13/117 (known lenses) and
             P(off | strong event) = 22/112 once the frame artifacts (9 of them off-target) are removed: with ~30% of strong
             events on the star, P(off | not on the star) = 0.233, so LR = 0.111/0.233 and 0.889/0.767.
  in_dr3_span  inside 2014-07-25..2017-05-28 and not flagged VARIABLE in DR3 (all 25 such events): ensemble_mc multiplies each
             scenario by (1 - DR3 flag efficiency) and lowers its DR4 pass probability (a lens DR3 did not flag is more likely one
             whose transits caught little of it).
  w_*        fixed scenario weights for events with optical follow-up (ATLAS referees); they replace the population fractions.
  lr_*_extra event-specific evidence: J131026 (OS-0024) DR3 CCD-level G scatter at the 95th percentile of its field with ~9
             missing transits (the earlier proposal's p5/p6): L and R x7, the likelihood ratio the sealed-case referee
             calibrated for that deficit on 47 DR3 lenses (dr4_referee.md section 3.3). J173349: OGLE observed the field in 2015 without an
             alert: L x0.5.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
PRED = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, PRED)
from dr4_ensemble_grade import ensemble_mc, falsification_thresholds, nuisance_bounds, pct  # noqa: E402

smp = pd.read_csv(os.path.join(PRED, "dr4_ensemble_sample.csv"), dtype={"source_id": str, "alt_source_id": str})
smp = smp[[c for c in smp.columns if not c.startswith(("q_", "a_", "u_", "w_", "p_", "lr_", "ess_", "chi2min_", "L_best"))]]
sp = pd.read_csv(os.path.join(HERE, "scenario_pass.csv"))
smp = smp.merge(sp, on="designation", how="left")

LR_OFF, LR_ON = 0.48, 1.16
smp["lr_onstar"] = smp.off_target.map({"True": LR_OFF, "False": LR_ON, True: LR_OFF, False: LR_ON}).fillna(1.0)
smp["lr_L_extra"] = 1.0
smp["lr_R_extra"] = 1.0
k7 = smp.designation.str[:7]
smp.loc[k7 == "J131026", ["lr_L_extra", "lr_R_extra"]] = 7.0
smp.loc[k7 == "J173349", "lr_L_extra"] = 0.5
FIXED = {  # L, R, F, N
    "J163539": (0.80, 0.17, 0.00, 0.03),  # ATLAS x6-9, achromatic, smooth, at the NEOWISE time
    "J173150": (0.60, 0.35, 0.00, 0.05),  # ATLAS x7.7 for months; rise mildly chromatic
    "J075219": (0.35, 0.35, 0.15, 0.15),  # ATLAS: real month-long brightening, unclassified; ATLAS baselines 0.3x Gaia's flux
    "J185846": (0.00, 0.03, 0.00, 0.97),  # the matched Gaia star (2.8") is not the variable
    "J182120": (0.03, 0.30, 0.02, 0.65),  # IR variable / YSO candidate; ATLAS 2016 unusable, so an optical rise is possible
    "J170153": (0.02, 0.05, 0.00, 0.93),  # ATLAS flat at +9 and +21 d where a lens needs x2
    "J185035": (0.01, 0.04, 0.00, 0.95),  # IR-only; IR source far too red for the Gaia star
}
for c in ("w_L", "w_R", "w_F", "w_N"):
    smp[c] = np.nan
for k, w in FIXED.items():
    smp.loc[k7 == k, ["w_L", "w_R", "w_F", "w_N"]] = w

test = smp[smp.status == "testable"].reset_index(drop=True)
assert len(test) == 47 and test.q_L.notna().all()
core = test.blind_core.astype(bool).to_numpy()
inspan = test.in_dr3_span.astype(bool).to_numpy()
N = 40000


def summ(r, label):
    x = r["npass"]
    d = dict(label=label, m=int(r["m"]), mean=round(float(x.mean()), 2), median=pct(x, 50), p10=pct(x, 10), p90=pct(x, 90),
             p5=pct(x, 5), p95=pct(x, 95), mean_resolved=round(float(r["nres"].mean()), 1),
             mean_lens_passes=round(float(r["nlens_pass"].mean()), 2),
             mean_achromatic=round(float(r["nach"].mean()), 2), mean_chromatic=round(float(r["nchro"].mean()), 2),
             mean_undetermined=round(float(r["nund"].mean()), 2), ach_p10=pct(r["nach"], 10), ach_p90=pct(r["nach"], 90),
             ach_p5=pct(r["nach"], 5), ach_p95=pct(r["nach"], 95))
    det = r["nach"] + r["nchro"]
    fr = r["nach"][det > 0] / det[det > 0]
    d["ach_frac_of_determined_mean"] = round(float(fr.mean()), 3)
    d["ach_frac_of_determined_p10_p90"] = [round(pct(fr, 10), 3), round(pct(fr, 90), 3)]
    d["P_no_determined_colour"] = round(float(np.mean(det == 0)), 3)
    pa = r["npass"] > 0
    d["und_frac_of_passes_mean"] = round(float((r["nund"][pa] / r["npass"][pa]).mean()), 3)
    return d


out = {}
main = ensemble_mc(test, n=N)
out["main"] = summ(main, "all 47 testable, lens fraction from the DR3 posterior")
out["main"]["f_L_draws_median_p10_p90"] = [round(pct(main["f_L"], 50), 3), round(pct(main["f_L"], 10), 3), round(pct(main["f_L"], 90), 3)]
f20 = ensemble_mc(test, n=N, fL=0.20)
out["fL_0.20"] = summ(f20, "all 47, lens fraction held at 0.20")
out["grid"] = {}
for g in (0.0, 0.05, 0.10, 0.20, 0.30, 0.40, 0.50, 0.70):
    out["grid"][f"{g:.2f}"] = summ(ensemble_mc(test, n=20000, fL=g, seed=11), f"fL={g}")
out["core"] = summ(ensemble_mc(test, n=N, use=core), "blind core (no optical information)")
out["core_fL_0.20"] = summ(ensemble_mc(test, n=N, use=core, fL=0.20), "blind core, fL=0.20")
out["inspan"] = summ(ensemble_mc(test, n=N, use=inspan), "in the DR3 span (unflagged)")
out["post"] = summ(ensemble_mc(test, n=N, use=~inspan), "after the DR3 span")
out["followed"] = summ(ensemble_mc(test, n=N, use=~core), "events with optical follow-up")
# sensitivity
sens = {}
t2 = test.copy()
t2["in_dr3_span"] = False
sens["no DR3-nonflag conditioning"] = summ(ensemble_mc(t2, n=20000), "")
t3 = test.copy()
t3["lr_onstar"] = 1.0
sens["no centroid evidence"] = summ(ensemble_mc(t3, n=20000), "")
sens["rho 0-1 (DR3 flag and DR4 pass less correlated)"] = summ(ensemble_mc(test, n=20000, rho_range=(0.0, 1.0)), "")
sens["f_R mean 0.15, f_F mean 0.10"] = summ(ensemble_mc(test, n=20000, fR_ab=(3, 17), fF_ab=(2, 18)), "")
sens["f_R, f_F = 0"] = summ(ensemble_mc(test, n=20000, fR_ab=(1e-3, 1e3), fF_ab=(1e-3, 1e3)), "")
t4 = test.copy()
for k in "LRF":
    t4[f"q_{k}"] = t4[f"q_{k}"] * 0.85
sens["on-star pass probabilities x0.85"] = summ(ensemble_mc(t4, n=20000), "")
out["sensitivity"] = {k: {kk: v[kk] for kk in ("mean", "p10", "p90", "p5", "p95", "mean_achromatic")} for k, v in sens.items()}

m = out["main"]
out["headline"] = (f"{m['mean']:.1f} passes expected of 47 (median {m['median']:.0f}, 80% {m['p10']:.0f}-{m['p90']:.0f}, "
                   f"90% {m['p5']:.0f}-{m['p95']:.0f})")
f = out["fL_0.20"]
klo, khi = falsification_thresholds(f20["npass"])
out["falsification"] = dict(rule="with the lens fraction held at 0.20, a pass count k with P(count <= k) < 0.05 or P(count >= k) < "
                            "0.05 falsifies '~20% lenses' (recomputed by the grader for the events that resolve)",
                            falsified_if_at_most=klo, falsified_if_at_least=khi,
                            P_le=float(np.mean(f20["npass"] <= klo)), P_ge=float(np.mean(f20["npass"] >= khi)),
                            achromatic=dict(zip(("falsified_if_at_most", "falsified_if_at_least"), falsification_thresholds(f20["nach"]), strict=True)))
# firm thresholds (nuisance bounds), at the expected resolution and with all 47 resolved; power; two-tail false alarm
allres = np.ones(len(test), bool)
f20r = ensemble_mc(test, n=N, fL=0.20, resolved_known=True)
a_lo, a_hi = falsification_thresholds(f20r["npass"])
r_lo, r_hi = nuisance_bounds(test, n=N, resolved_known=False)
c_lo, c_hi = falsification_thresholds(r_lo["npass"])[0], falsification_thresholds(r_hi["npass"])[1]
r_lo2, r_hi2 = nuisance_bounds(test, n=N, resolved_known=True)
c_lo2, c_hi2 = falsification_thresholds(r_lo2["npass"])[0], falsification_thresholds(r_hi2["npass"])[1]
ach_lo2, ach_hi2 = falsification_thresholds(f20r["nach"])
pw = {}
for g_ in (0.0, 0.4):
    # truth drawn under the stated priors at f_L = g_; regions: as written (a) and firm (c, nuisance bounds); all 47 resolved
    rr = ensemble_mc(test, n=N, fL=g_, resolved_known=True, seed=99)
    pw[f"{g_:.1f}"] = dict(P_too_few=float(np.mean(rr["npass"] <= a_lo)), P_too_many=float(np.mean(rr["npass"] >= a_hi)),
                           P_too_few_firm=float(np.mean(rr["npass"] <= c_lo2)), P_too_many_firm=float(np.mean(rr["npass"] >= c_hi2)))
out["falsification"].update(all_resolved=dict(falsified_if_at_most=a_lo, falsified_if_at_least=a_hi,
                                               achromatic=[ach_lo2, ach_hi2], firm=[c_lo2, c_hi2],
                                               false_alarm_two_tails=float(np.mean(f20r["npass"] <= a_lo) + np.mean(f20r["npass"] >= a_hi))),
                            firm_expected_resolution=[c_lo, c_hi], power=pw)
t5 = test.copy()
t5["q_N"] = t5.q_N + 0.02
out["flat_star_3pct_delta"] = round(float(ensemble_mc(t5, n=N)["npass"].mean() - main["npass"].mean()), 2)
bc = ensemble_mc(test, n=N)["p_event"]
out["blind_core_per_event"] = dict(inspan=round(float(bc[core & inspan].mean()), 3), after=round(float(bc[core & ~inspan].mean()), 3))
out["all_per_event"] = dict(inspan=round(float(bc[inspan].mean()), 3), after=round(float(bc[~inspan].mean()), 3))

# which lens fractions each pass count would allow (flat prior on a grid; the grader's fL_posterior)
from dr4_ensemble_grade import fL_posterior  # noqa: E402

out["fL_given_count"] = {}
for kk in (3, 5, 7, 10, 13, 16, 20):
    pp = fL_posterior(test, np.ones(len(test), bool), kk, n=3000)
    out["fL_given_count"][str(kk)] = dict(median=round(pp["median"], 3), lo90=round(pp["lo90"], 3), hi90=round(pp["hi90"], 3))

# per-event marginals into the sample CSV
test["p_pass_forecast"] = np.round(main["p_event"], 3)
test["p_pass_fL20"] = np.round(f20["p_event"], 3)
test["p_lens_onstar"] = np.round(main["p_lens_event"], 3)
cols = [c for c in test.columns]
full = smp.merge(test[["designation", "p_pass_forecast", "p_pass_fL20", "p_lens_onstar"]], on="designation", how="left")
full.to_csv(os.path.join(PRED, "dr4_ensemble_sample.csv"), index=False)
json.dump(out, open(os.path.join(HERE, "forecast.json"), "w"), indent=1, default=float)

pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 100)
print(out["headline"])
for k in ("main", "fL_0.20", "core", "core_fL_0.20", "inspan", "post", "followed"):
    v = out[k]
    print(f"{v['label']:58s} m {v['m']:2d}  mean {v['mean']:5.2f}  median {v['median']:4.0f}  80% {v['p10']:.0f}-{v['p90']:.0f}  "
          f"90% {v['p5']:.0f}-{v['p95']:.0f}  resolved {v['mean_resolved']}  lens passes {v['mean_lens_passes']}  "
          f"achromatic {v['mean_achromatic']} (80% {v['ach_p10']:.0f}-{v['ach_p90']:.0f})  chromatic {v['mean_chromatic']}  "
          f"undetermined {v['mean_undetermined']}  ach/determined {v['ach_frac_of_determined_mean']} {v['ach_frac_of_determined_p10_p90']}"
          f"  P(no determined colour) {v['P_no_determined_colour']}")
print("\nlens fraction grid (all 47):")
for g, v in out["grid"].items():
    print(f"  fL {g}: mean {v['mean']:5.2f}  80% {v['p10']:.0f}-{v['p90']:.0f}  90% {v['p5']:.0f}-{v['p95']:.0f}  "
          f"achromatic mean {v['mean_achromatic']:.2f} (90% {v['ach_p5']:.0f}-{v['ach_p95']:.0f})")
print("\nfalsification:", out["falsification"])
print("lens fraction implied by a pass count (all 47 resolved; median, 90%):", out["fL_given_count"])
print("flat-star pass rate +2% adds", out["flat_star_3pct_delta"], "passes; per-event pass rate in-span/after:",
      out["all_per_event"], "blind core:", out["blind_core_per_event"])
print("\nsensitivity:")
for k, v in out["sensitivity"].items():
    print(f"  {k:50s} mean {v['mean']:5.2f}  80% {v['p10']:.0f}-{v['p90']:.0f}  90% {v['p5']:.0f}-{v['p95']:.0f}  ach {v['mean_achromatic']}")
print("\nper event:")
print(test[["designation", "case", "in_dr3_span", "off_target", "gost_n_fov_30", "p_res", "q_L", "q_R", "q_F", "q_N",
            "p_lens_onstar", "p_pass_forecast", "p_pass_fL20", "blind_core"]].to_string(index=False))
