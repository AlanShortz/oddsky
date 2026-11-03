"""H-0016 step 2: triage the AllWISE-vs-NEOWISE step candidates with the AllWISE catalogue flags and 2MASS as a third epoch.
usage: steps_triage.py STEPS_RAW_CSV ALLWISE_CSV OUT_CSV
Columns added:
  flag_cc    any W1/W2 artifact flag in AllWISE (cc_flags[0:2] != '00')
  flag_nb    AllWISE profile fit used > 1 component (blend)
  flag_ext   AllWISE extended-source flag > 0
  flag_sat   AllWISE saturated pixels in W1 or W2
  flag_chi   AllWISE W1 reduced chi-square > 3 (confused or extended)
  flag_det   AllWISE detected the source in < 70% of its frames in W1 (w1nm/w1m): faint or variable inside 2010-11
  kw1_aw, kw1_neo   2MASS K minus W1 at the AllWISE and NEOWISE epochs; a bare photosphere has K - W1 ~ 0.0-0.2
  epoch3     which WISE epoch 2MASS agrees with: 'allwise' (the star changed after 2010), 'neowise' (2010 was the odd state),
             'neither' (red or dusty at both, or K off), 'no2mass'
"""
import sys

import numpy as np
import pandas as pd

s = pd.read_csv(sys.argv[1])
a = pd.read_csv(sys.argv[2])
s["allwise_cntr"] = s.allwise_cntr.astype("int64")
a["cntr"] = a.cntr.astype("int64")
x = s.merge(a, left_on="allwise_cntr", right_on="cntr", how="left", suffixes=("", "_aw"))
cc = x.cc_flags.fillna("0000").astype(str).str.zfill(4)
x["flag_cc"] = (cc.str[0] != "0") | (cc.str[1] != "0")
x["flag_nb"] = x.nb.fillna(1) > 1
x["flag_ext"] = x.ext_flg.fillna(0) > 0
x["flag_sat"] = (x.w1sat.fillna(0) > 0) | (x.w2sat.fillna(0) > 0)
x["flag_chi"] = x.w1rchi2.fillna(1) > 3
x["flag_det"] = (x.w1nm / x.w1m.replace(0, np.nan)).fillna(1) < 0.7
x["nflags"] = x[["flag_cc", "flag_nb", "flag_ext", "flag_sat", "flag_chi", "flag_det"]].sum(axis=1)
x["kw1_aw"] = x.k_m_2mass - x.w1mpro_allwise
x["kw1_neo"] = x.k_m_2mass - x.w1_base
x["kw2_aw"] = x.k_m_2mass - x.w2mpro_allwise
x["kw2_neo"] = x.k_m_2mass - x.w2_base
ok_aw = x.kw1_aw.between(-0.35, 0.45)
ok_neo = x.kw1_neo.between(-0.35, 0.45)
x["epoch3"] = np.select([x.k_m_2mass.isna(), ok_aw & ~ok_neo, ok_neo & ~ok_aw, ok_aw & ok_neo], ["no2mass", "allwise", "neowise", "both"], "neither")
x["direction"] = np.where(x.d1 > 0, "fainter_now", "brighter_now")
x["step"] = (x.d1 + x.d2) / 2
x = x.sort_values("step")
x.to_csv(sys.argv[3], index=False)
print(len(x), "candidates;", "with AllWISE row:", int(x.cntr.notna().sum()))
print(pd.crosstab(x.direction, x.nflags))
clean = x[x.nflags == 0]
print("\nclean (no AllWISE flag):", len(clean))
print(pd.crosstab(clean.direction, clean.epoch3))
for d in ("fainter_now", "brighter_now"):
    c = clean[clean.direction == d]
    print(f"\n{d}: clean {len(c)}; |step|>0.7: {int((c.step.abs() > 0.7).sum())}; >1.0: {int((c.step.abs() > 1).sum())}")
    print(c[["designation", "w1mpro_allwise", "w1_base", "d1", "d2", "k_m_2mass", "kw1_aw", "kw1_neo", "epoch3", "w1_ptp", "w2_ptp", "w1mjdmean"]]
          .sort_values("d1", key=abs, ascending=False).head(25).to_string())
