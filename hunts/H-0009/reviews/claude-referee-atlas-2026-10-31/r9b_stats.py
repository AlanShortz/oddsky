"""r9b: statistics of the artifact diagnostics (data/r9_metrics.csv): known lenses (118, of which 58 new to the relaxed pass)
against strong unexplained events (122, of which 56 not in H-0008's clean list). Candidate cuts and their cost in known lenses.
Indicators:
  flag-dominated   share of event frames flagged h/d >= 0.5, or nb>1 >= 0.5, or saturated >= 0.5 (frame level, r_allwise<2 frames)
  hd_excess        survey table: hdfrac_event > hdfrac_other + 0.3        nb_excess: nbfrac_event > nbfrac_other + 0.3
  off_target       event centroid misses the shift predicted for the matched Gaia star by > 0.3" and > 5 sigma
  r2_drop          share of the star's associated detections passing r_allwise < 2 falls by > 0.25 at the event
  merged           >= 30% of event frames have fewer detections within 6" than the quiet median (a neighbour not extracted)
  clean_contra     >= 2 clean event frames and they show less than half the brightening (d_clean > 0.5 d_all)
  incoherent       event-frame scatter > 3x the quiet-visit scatter
  replic           my visit median differs from the survey's dW1 by > 0.3 mag (the survey's number is not reproduced)"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA  # noqa: E402

pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 300)
m = pd.read_csv(os.path.join(DATA, "r9_metrics.csv"))
m["flagdom_hd"] = m.frac_hd_ev >= 0.5
m["flagdom_nb"] = m.frac_nb_ev >= 0.5
m["flagdom_sat"] = m.frac_sat_ev >= 0.5
m["flagdom"] = m.flagdom_hd | m.flagdom_nb | m.flagdom_sat
m["hd_excess"] = m.hdfrac_event > m.hdfrac_other + 0.3
m["nb_excess"] = m.nbfrac_event > m.nbfrac_other + 0.3
m["off_target"] = (m.miss > 0.3) & (m.miss_sig > 5)
m["r2_drop"] = m.pass_r2_ev < m.pass_r2_q - 0.25
m["merged"] = (m.frac_merged_ev >= 0.3) & (m.frac_merged_ev > m.frac_merged_q + 0.2)
m["clean_contra"] = (m.n_ev_clean >= 2) & (m.d_clean > 0.5 * m.d_all)
m["incoherent"] = m.scat > 3
m["replic"] = (m.d_all - m.dw1).abs() > 0.3
m["frame_artifact"] = m.r2_drop | m.merged | m.clean_contra | m.replic
IND = ["flagdom_hd", "flagdom_nb", "flagdom_sat", "flagdom", "hd_excess", "nb_excess", "off_target", "r2_drop", "merged",
       "clean_contra", "incoherent", "replic", "frame_artifact"]
groups = {"known (all)": m.grp == "known", "known, new in H-0009": (m.grp == "known") & m.new, "strong (all)": m.grp == "strong",
          "strong, new in H-0009": (m.grp == "strong") & m.new, "strong, also in H-0008": (m.grp == "strong") & ~m.new}
rows = []
for g, sel in groups.items():
    x = m[sel]
    rows.append({"group": g, "n": len(x), **{i: f"{int(x[i].sum())} ({100 * x[i].mean():.0f}%)" for i in IND}})
print(pd.DataFrame(rows).set_index("group").T.to_string())

print("\nMedian diagnostics per group:")
print(m.groupby(["grp", "new"])[["frac_hd_ev", "frac_nb_ev", "frac_sat_ev", "frac_clean_ev", "shift", "miss", "scat", "R_ap"]]
      .median().round(2).to_string())

# cuts and their cost
print("\nCandidate cuts (events rejected):")
CUTS = {
    "A hdfrac_event > hdfrac_other + 0.3 (table)": m.hd_excess,
    "B nbfrac_event > nbfrac_other + 0.3 (table)": m.nb_excess,
    "C A or B": m.hd_excess | m.nb_excess,
    "D event frames >= 50% hd/nb/sat (flag-dominated)": m.flagdom,
    "E off-target centroid": m.off_target,
    "F r_allwise<2 pass share drops > 0.25": m.r2_drop,
    "G merged-neighbour frames": m.merged,
    "H clean frames contradict": m.clean_contra,
    "I survey dW1 not reproduced (> 0.3 mag)": m.replic,
    "J F or G or H or I (frame-level artifact)": m.frame_artifact,
    "K J or E": m.frame_artifact | m.off_target,
    "L J or (E and flag-dominated)": m.frame_artifact | (m.off_target & m.flagdom),
}
cr = []
for name, rej in CUTS.items():
    k, s, sn = rej[m.grp == "known"], rej[m.grp == "strong"], rej[(m.grp == "strong") & m.new]
    kn = rej[(m.grp == "known") & m.new]
    cr.append((name, f"{int(k.sum())}/{len(k)} ({100 * k.mean():.0f}%)", f"{int(kn.sum())}/{len(kn)}",
               f"{int(s.sum())}/{len(s)} ({100 * s.mean():.0f}%)", f"{int(sn.sum())}/{len(sn)} ({100 * sn.mean():.0f}%)"))
print(pd.DataFrame(cr, columns=["cut", "known lenses lost", "of the 58 new known", "strong rejected", "new strong rejected"]).to_string(index=False))

print("\nStrong events flagged by the frame-level tests (J/E):")
x = m[(m.grp == "strong") & (m.frame_artifact | m.off_target)].sort_values("dw1")
print(x[["designation", "new", "nblock", "dw1", "d_all", "d_clean", "n_ev", "n_ev_clean", "frac_hd_ev", "frac_nb_ev", "frac_sat_ev",
         "pass_r2_ev", "pass_r2_q", "frac_merged_ev", "shift", "miss", "miss_sig", "scat"] + [c for c in IND if c in ("off_target", "r2_drop", "merged", "clean_contra", "replic")]]
      .round(2).to_string(index=False))
print("\nKnown lenses flagged by the frame-level tests:")
x = m[(m.grp == "known") & (m.frame_artifact | m.off_target)].sort_values("dw1")
print(x[["designation", "new", "dw1", "d_all", "d_clean", "frac_hd_ev", "frac_nb_ev", "pass_r2_ev", "pass_r2_q", "frac_merged_ev", "shift",
         "miss", "miss_sig", "scat", "off_target", "r2_drop", "merged", "clean_contra", "replic"]].round(2).to_string(index=False))
m.to_csv(os.path.join(DATA, "r9b_flags.csv"), index=False)
