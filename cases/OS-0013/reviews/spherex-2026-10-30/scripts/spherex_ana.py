"""Calibrate SPHEREx forced photometry of OS-0013 against the 27 NEOWISE-flat field stars of claim C1.
ratio = SPHEREx flux / photospheric reference at the image's wavelength at the star, where the reference is a
log-log interpolation through 2MASS J,H,Ks and the 2014-17 (pre-step) NEOWISE W1,W2 visit medians (AllWISE
2010 for the neighbours). Per (release, window) the field stars' per-star median ratios give the calibration C;
ratios are divided by C, so a field star scatters around 1 and the target's value - 1 is its excess over its
pre-2018 photosphere. Uncertainty = star-to-star robust scatter of the field stars (a single star's systematic)
combined with the target's own standard error. Usage: spherex_ana.py <phot.csv> [flux column]"""
import sys, numpy as np, pandas as pd
phot = pd.read_csv(sys.argv[1]); col = sys.argv[2] if len(sys.argv) > 2 else "f_psf"
srcs = pd.read_csv(sys.argv[1].replace(".csv", "_sources.csv"))
ZP = {"J": (1.235, 1594.0), "H": (1.662, 1024.0), "K": (2.159, 666.7), "W1": (3.353, 309.54), "W2": (4.603, 171.787)}
TARGET = "J144351.92-761145.9"
NB = set(srcs.allwise[srcs.neighbour])
s = srcs.set_index("allwise")
pd.set_option("display.width", 250)

def ref(row, lam, post=False):
    m = [row.J, row.H, row.K, 11.020 if post else row.pre_w1, 10.899 if post else row.pre_w2]
    x = np.log([ZP[b][0] for b in ZP]); y = np.log([ZP[b][1] * 1e3 * 10 ** (-0.4 * mm) for b, mm in zip(ZP, m)])
    l = np.log(lam); i = np.clip(np.searchsorted(x, l) - 1, 0, len(x) - 2)
    return np.exp(y[i] + (y[i + 1] - y[i]) / (x[i + 1] - x[i]) * (l - x[i]))

phot["ref"] = [ref(s.loc[a], l) for a, l in zip(phot.allwise, phot.lam)]
phot["ratio"] = phot[col] / phot.ref
q = phot[(phot.nbad_core == 0) & np.isfinite(phot.ratio) & (phot.ratio > 0)].copy()
WIN = {"J 1.10-1.40": (1.10, 1.40), "H 1.50-1.80": (1.50, 1.80), "K 2.00-2.40": (2.00, 2.40),
       "W1-like 3.00-3.80": (3.00, 3.80), "D5 3.80-4.40": (3.80, 4.40), "W2-like 4.40-5.00": (4.40, 5.00)}
q["win"] = None
for wn, (a, b) in WIN.items():
    q.loc[(q.lam >= a) & (q.lam < b), "win"] = wn
q = q[q.win.notna()]
comp_mask = ~q.allwise.isin([TARGET] + list(NB))
# calibration per release and window
C = (q[comp_mask].groupby(["release", "win", "allwise"]).ratio.median().groupby(["release", "win"]).median())
q["nr"] = q.ratio / [C.loc[(r, w)] for r, w in zip(q.release, q.win)]

# expected excess if the NEOWISE post-step state persists: 1045 K blackbody through the NEOWISE W1/W2 excesses
def bb(lam, T=1045.0): return lam ** -3 / np.expm1(14387.77 / (lam * T))
t = s.loc[TARGET]
ex1 = ZP["W1"][1] * 1e3 * (10 ** (-0.4 * 11.020) - 10 ** (-0.4 * 11.188))
ex2 = ZP["W2"][1] * 1e3 * (10 ** (-0.4 * 10.899) - 10 ** (-0.4 * 11.259))
amp = np.mean([ex1 / bb(3.353), ex2 / bb(4.603)])

out, nbrows = [], []
for wn in WIN:
    w = q[q.win == wn]
    per = w.groupby("allwise").agg(n=("nr", "size"), med=("nr", "median"),
                                   mad=("nr", lambda r: 1.4826 * np.median(np.abs(r - np.median(r)))))
    per["sem"] = 1.253 * per["mad"] / np.sqrt(per["n"])
    comps = per.drop([TARGET] + list(NB), errors="ignore"); comps = comps[comps["n"] >= 3]
    cm = comps["med"].median(); sc = 1.4826 * np.median(np.abs(comps["med"] - cm))
    for nb in NB & set(per.index):
        nbrows.append(dict(window=wn, allwise=nb, val=round(per.loc[nb, "med"] / cm - 1, 3)))
    tt = per.loc[TARGET]; wt = w[w.allwise == TARGET]
    lam_t = wt.lam.median()
    pred = amp * bb(lam_t) / ref(t, lam_t)
    out.append(dict(window=wn, n_img=int(tt["n"]), lam=round(lam_t, 3), f_target_mJy=round(wt[col].median(), 3),
                    photosphere_mJy=round(ref(t, lam_t), 3), n_comp=len(comps), comp_sd=round(sc / cm, 3),
                    target_sem=round(tt["sem"] / cm, 3), excess=round(tt["med"] / cm - 1, 3),
                    err=round(np.hypot(sc / cm, tt["sem"] / cm), 3), expected_if_present=round(pred, 3),
                    comps_above_target=f"{int((comps['med'] > tt['med']).sum())}/{len(comps)}",
                    comp_max=round(comps["med"].max() / cm - 1, 3)))
res = pd.DataFrame(out)
print(f"flux column: {col};  calibration C per release/window:\n{C.unstack(0).round(3).to_string()}\n")
print(res.to_string(index=False))
res.to_csv(sys.argv[1].replace(".csv", f"_summary_{col}.csv"), index=False)
print("\nneighbours: SPHEREx / (2MASS+AllWISE 2010 reference), field-calibrated, minus 1:")
print(pd.DataFrame(nbrows).pivot(index="allwise", columns="window", values="val").to_string())

print("\ncolour tests (independent of each star's absolute normalisation):")
pm = q.groupby(["win", "allwise"]).nr.median().unstack(0)
for wa, wb in (("W2-like 4.40-5.00", "K 2.00-2.40"), ("W2-like 4.40-5.00", "H 1.50-1.80"),
               ("W1-like 3.00-3.80", "K 2.00-2.40"), ("W2-like 4.40-5.00", "W1-like 3.00-3.80")):
    cr = (pm[wa] / pm[wb]).dropna(); cc = cr.drop([TARGET] + list(NB), errors="ignore")
    lam_a = q[(q.win == wa) & (q.allwise == TARGET)].lam.median(); lam_b = q[(q.win == wb) & (q.allwise == TARGET)].lam.median()
    pred = (1 + amp * bb(lam_a) / ref(t, lam_a)) / (1 + amp * bb(lam_b) / ref(t, lam_b)) - 1
    print(f"  {wa} / {wb}: target {cr[TARGET] / cc.median() - 1:+.3f} relative to field median "
          f"(field robust sd {1.4826 * np.median(np.abs(cc - cc.median())) / cc.median():.3f}, field max {cc.max() / cc.median() - 1:+.3f}, "
          f"n={len(cc)}); expected if excess persists {pred:+.3f}")

print("\ntarget per season (field-calibrated excess, median of images):")
q["season"] = pd.cut(q.mjd, [60800, 61000, 61200, 61400], labels=["2025 Aug-Sep", "2026 Feb-Apr", "2026 Aug-Oct"])
cm_all = q[comp_mask].groupby(["win", "allwise"]).nr.median().groupby("win").median()
g = q[q.allwise == TARGET].groupby(["win", "season"], observed=True).nr.agg(["size", "median"])
g["excess"] = g["median"] / cm_all.reindex(g.index.get_level_values(0)).values - 1
print(g[["size", "excess"]].round(3).to_string())
# field-star per-season scatter (how stable is the calibration between seasons?)
fs = q[comp_mask].groupby(["win", "season", "allwise"], observed=True).nr.median().groupby(["win", "season"], observed=True).median()
print("\nfield median per season (should be ~1):"); print(fs.unstack(1).round(3).to_string())
