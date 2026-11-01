"""s6: diagnostic sheets for the 67 (for the verdicts, not the README figure). Per source, two panels:
  left: Gaia DR3 G, BP, RP flux ratios with the static and parallax lens models (G band);
  right: NEOWISE W1, W2 visit medians ("long" cuts) 2014-2024, as magnitude offsets from the median, Gaia span shaded.
Run from the repo root: uv run python -I hunts/H-0010/scripts/s6_diag.py
Writes hunts/H-0010/data/diag_<k>.png (12 sources per sheet)."""
import json
import os
import sys

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import CASES, DATA, DR3_END, DR3_START, NW, epoch, targets  # noqa: E402
from s3_lightcurves import ratio_series  # noqa: E402

COL = {"G": "k", "BP": "tab:blue", "RP": "tab:red", "W1": "tab:orange", "W2": "tab:purple"}


def main():
    T = targets().sort_values("best_class_score", ascending=False).reset_index(drop=True)
    lc = pd.read_csv(os.path.join(DATA, "lc_metrics.csv"), dtype={"source_id": str}).set_index("source_id")
    per = 12
    for k in range(0, len(T), per):
        sub = T.iloc[k:k + per]
        fig, axes = plt.subplots(len(sub), 2, figsize=(18, 2.6 * len(sub)), gridspec_kw={"width_ratios": [1.6, 1]})
        axes = np.atleast_2d(axes)
        for i, r in enumerate(sub.itertuples()):
            a, b = axes[i]
            d, _ = epoch(r.source_id)
            df, _ = ratio_series(d)
            for band in ("BP", "RP", "G"):
                x = df[df.g == band]
                a.errorbar(x.t, x.f, x.e, fmt=".", color=COL[band], ms=4, alpha=0.8, lw=0.6, label=band)
                v = x[x.flag == "rejected_by_variability"]
                a.plot(v.t, v.f, "o", mfc="none", mec=COL[band], ms=7, lw=0.5)
            fj = json.load(open(os.path.join(DATA, "fits", f"{r.source_id}.json")))
            for lab, ls in (("static", "-"), ("parallax", "--")):
                m = fj["models"][lab]
                a.plot(m["t"], m["G"], ls, color="green", lw=1)
            m = lc.loc[r.source_id]
            ymax = max(float(df[df.g == "G"].f.max()) * 1.15, 1.3)
            a.set_ylim(0.6, ymax)
            a.set_xlim(DR3_START - 20, DR3_END + 20)
            a.set_title(f"{r.source_id} {CASES.get(r.source_id, '')} score {r.best_class_score:.2f} G {r.phot_g_mean_mag:.1f} "
                        f"BP-RP {r.bp_rp:.2f} l {r.l:.1f} b {r.b:.1f} | eps {m.bright_eps} | fades {m.fade_eps if isinstance(m.fade_eps, str) else ''}\n"
                        f"static tE {m.static_tE} chi2 {m.static_chi2} | par {m.par_chi2} | pv7 {m.pv7_chi2} asym {m.pv7_asym_chi2} "
                        f"fred {m.fred_chi2} | n {m.n_fit} | k {m.get('k_bp_rp')}±{m.get('k_err')}", fontsize=7.5, loc="left")
            if i == 0:
                a.legend(fontsize=7, ncol=3)
            vp = os.path.join(NW, f"{r.source_id}_visits.csv")
            if os.path.exists(vp) and os.path.getsize(vp) > 5:
                v = pd.read_csv(vp)
                v = v[v["mode"] == "long"] if len(v) else v
                for band in ("W1", "W2"):
                    x = v[v.band == band]
                    if len(x):
                        b.errorbar(x.t, x.mag - x.mag.median(), x.err, fmt="o-", color=COL[band], ms=3, lw=0.6)
                b.invert_yaxis()
            b.axvspan(DR3_START, DR3_END, color="0.9")
            b.set_xlim(56600, 60600)
            b.set_title("NEOWISE W1/W2 (mag offset)", fontsize=7)
        plt.tight_layout()
        plt.savefig(os.path.join(DATA, f"diag_{k // per}.png"), dpi=60)
        plt.close()


if __name__ == "__main__":
    main()
