"""H-0016 section 4c: the AllWISE profile-fit failure list as a product.
Input: IRSA pull of clean AllWISE sources (8 <= W1 <= 14.5, cc_flags 0000, nb 1, ext_flg 0, |b| > 10) with
|w1mag - w1mpro| > 0.4 OR w1snr < 20 (IRSA async job 27150356). Applies the four catalogue tests of oddsky.data.allwise.diagnose
(aperture - profile, SNR for the magnitude, frame-detection fraction; the Gaia offset needs a cross-match and is left to the
sample stage) and uses 2MASS K as the arbiter of which magnitude is the star's. Writes:
  work/allwise_profile_fit_failures.csv   tier A: K agrees with the aperture (|K - w1mag| < 0.4) and not the profile; tier B: no K
                                          or ambiguous but >= 3 catalogue tests fail
usage: allwise_product.py IN_CSV OUT_CSV"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "src")
from oddsky.data.allwise import expected_w1snr  # noqa: E402

x = pd.read_csv(sys.argv[1])
x["ap_pro"] = x.w1mag - x.w1mpro
x["snr_exp"] = x.w1mpro.apply(expected_w1snr)
x["t_appro"] = x.ap_pro.abs() > 0.3
x["t_snr"] = x.w1snr < 0.5 * x.snr_exp
x["t_frames"] = (x.w1nm / x.w1m.replace(0, np.nan)).fillna(1) < 0.6
x["n_tests"] = x[["t_appro", "t_snr", "t_frames"]].sum(axis=1)
dk_ap = (x.k_m_2mass - x.w1mag).abs()
dk_pro = (x.k_m_2mass - x.w1mpro).abs()
x["k_says"] = np.select([x.k_m_2mass.isna(), (dk_ap < 0.4) & (dk_pro > 0.4), (dk_pro < 0.4) & (dk_ap > 0.4)], ["no_2mass", "aperture", "profile"], "ambiguous")
x["tier"] = np.select([(x.k_says == "aperture") & (x.n_tests >= 2), (x.k_says != "profile") & (x.n_tests >= 3)], ["A", "B"], "")
print(len(x), "sources in the pull")
print(pd.crosstab(x.k_says, x.n_tests))
print("tier A:", int((x.tier == "A").sum()), " tier B:", int((x.tier == "B").sum()))
out = x[x.tier != ""].sort_values(["tier", "ap_pro"])
cols = ["tier", "cntr", "designation", "ra", "dec", "glon", "glat", "w1mpro", "w1mag", "w1snr", "snr_exp", "w1nm", "w1m", "w2mpro", "w2mag", "k_m_2mass", "r_2mass", "sigra", "pmra", "pmdec", "ap_pro", "k_says", "n_tests"]
out[cols].to_csv(sys.argv[2], index=False)
print("written", len(out), "->", sys.argv[2])
for h, g in x.assign(hemi=np.where(x.glat > 0, "north", "south")).groupby("hemi"):
    print(h, "tier A", int((g.tier == "A").sum()), "tier B", int((g.tier == "B").sum()))
