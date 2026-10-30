"""r14: claim 4 (the 432 unclassified are mostly crowded-plane variability). Local tests on the sky3lens light curves:
  * chromaticity in units of its own noise: |dW1 - dW2| / sqrt(sw1^2 + sw2^2);
  * sub-threshold repeats: other visits brighter by > 0.1 mag in W1 AND W2 (the pipeline allows up to 0.15 / 4 sigma);
  * baseline excess scatter: chi2/dof of the non-event visits about the median, using the per-visit errors;
  * ZTF at the NEOWISE visit (the investigators' ztf_dr): optical brightening vs the W1 brightening.
Compared across classes; the known lenses are the control for 'what a real lens looks like in this pipeline'."""
import os
import numpy as np, pandas as pd
from scipy.stats import ks_2samp, mannwhitneyu
HERE = os.path.dirname(os.path.abspath(__file__))
x = pd.read_csv(f"{HERE}/../../work/sky3_classified.csv", dtype={"g_source_id": str})
LC = os.path.expanduser("~/oddsky-runs/h0008/lightcurves")
rows = []
for pix, grp in x.groupby("pixel"):
    lc = pd.read_parquet(f"{LC}/pixel={pix}.parquet")
    for r in grp.itertuples():
        s = lc[lc.allwise_cntr == r.allwise_cntr].sort_values("t")
        ev = (s.t - r.t).abs() < 1
        d1 = s.w1 - s.w1.median(); d2 = s.w2 - s.w2.median()
        o = ~ev
        # neighbours of the event visit (the 1-3 hit visits) are excluded from 'repeats'
        k = np.where(ev.values)[0]
        near = np.zeros(len(s), bool)
        if len(k):
            for j in range(max(k[0] - 3, 0), min(k[0] + 4, len(s))):
                near[j] = True
        far = o.values & ~near
        rep = int(((d1 < -0.1) & (d2 < -0.1)).values[far].sum())
        chi = float(np.sum((d1[o] / np.hypot(s.w1_err[o], 0.01)) ** 2) / max(o.sum() - 1, 1))
        rows.append({"allwise_cntr": r.allwise_cntr, "repeats": rep, "base_chi2dof": chi})
x = x.merge(pd.DataFrame(rows), on="allwise_cntr", how="left")
x["ach_sig"] = (x.dw1 - x.dw2).abs() / np.hypot(x.sw1, x.sw2)
x["ztf_ratio"] = x.ztf_dr / x.dw1
x.to_csv(f"{HERE}/r14_unclassified.csv", index=False)
cls = ["microlensing (known)", "unclassified", "other variable", "young star", "dwarf nova / CV"]
t = x.groupby("class").agg(n=("t", "size"), ach_sig_med=("ach_sig", "median"), ach_sig_lt1=("ach_sig", lambda s: (s < 1).mean()),
                           repeats_any=("repeats", lambda s: (s > 0).mean()), base_chi2_med=("base_chi2dof", "median"),
                           dw1_med=("dw1", "median"), abs_b_lt5=("b", lambda s: (s.abs() < 5).mean())).loc[cls].round(3)
print(t.T.to_string())
L, U, V = (x[x["class"] == c] for c in ("microlensing (known)", "unclassified", "other variable"))
for col in ("ach_sig", "base_chi2dof", "dw1"):
    print(f"{col}: KS unclassified vs known lenses p={ks_2samp(U[col], L[col]).pvalue:.2g}; vs other variables p={ks_2samp(U[col], V[col]).pvalue:.2g}")
# Mixture estimate: unclassified achromaticity distribution as f*lens + (1-f)*other-variable (binned least squares)
bins = np.r_[0, 0.25, 0.5, 1, 1.5, 2, 3, 5, 100]
hl, hv, hu = (np.histogram(d.ach_sig, bins)[0] / len(d) for d in (L, V, U))
fs = np.linspace(0, 1, 101)
cost = [np.sum((hu - (f * hl + (1 - f) * hv)) ** 2) for f in fs]
f_best = fs[int(np.argmin(cost))]
boot = []
rng = np.random.default_rng(1)
for _ in range(500):
    lb, vb, ub = (d.sample(len(d), replace=True, random_state=int(rng.integers(1e9))) for d in (L, V, U))
    hl_, hv_, hu_ = (np.histogram(d.ach_sig, bins)[0] / len(d) for d in (lb, vb, ub))
    boot.append(fs[int(np.argmin([np.sum((hu_ - (f * hl_ + (1 - f) * hv_)) ** 2) for f in fs]))])
print(f"lens-like fraction of the unclassified from achromaticity mixture: {f_best:.2f} (bootstrap 68%: {np.percentile(boot, 16):.2f}-{np.percentile(boot, 84):.2f}; 95% upper {np.percentile(boot, 95):.2f})")
z = U[U.ztf_dr.notna()]
print(f"unclassified with ZTF in the +-10 d window: {len(z)}; ZTF/W1 amplitude ratio (mag/mag) median {z.ztf_ratio.median():.2f};"
      f" ZTF brighter by < 1/3 of the W1 brightening: {int((z.ztf_ratio < 1/3).sum())}; >= 2/3: {int((z.ztf_ratio >= 2/3).sum())}")
print(z.sort_values("ztf_dr")[["designation", "t", "dw1", "dw2", "ztf_dr", "ztf_n_window", "ach_sig", "repeats", "b"]].head(30).round(3).to_string(index=False))
