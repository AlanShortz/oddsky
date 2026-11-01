"""s10: figures/candidates.png, the best new lens candidates (work/verdicts.csv, verdict 'new lens candidate', highest
P(lens) first, up to 8). Per candidate, left: Gaia DR3 G, BP, RP flux ratios to the quiet baseline around the event, with the
lens model preferred by BIC (G band), and NEOWISE W1/W2 visit ratios when NEOWISE resolves the star; right: NEOWISE
2014-2024 (W1, W2), Gaia DR3 span shaded, or a note when NEOWISE has no source on the star.
Colours: G ink, BP blue, RP red, W1 aqua squares, W2 yellow diamonds (validated with the dataviz palette checker; marker
shape is the secondary encoding).
Run from the repo root: uv run python -I hunts/H-0010/scripts/s10_figure.py"""
import json
import os
import sys

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from astropy.time import Time  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA, DR3_END, DR3_START, FIG, NW, WORK, epoch  # noqa: E402
from s3_lightcurves import ratio_series  # noqa: E402

INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e6e5e1"
COL = {"G": INK, "BP": "#2a78d6", "RP": "#e34948", "W1": "#1baf7a", "W2": "#eda100"}
MK = {"G": "o", "BP": "o", "RP": "o", "W1": "s", "W2": "D"}


def yr(m):
    return Time(np.asarray(m, float), format="mjd").decimalyear


def neowise_visits(sid):
    p = os.path.join(NW, f"{sid}_visits.csv")
    if not os.path.exists(p) or os.path.getsize(p) < 5:
        return None
    v = pd.read_csv(p)
    v = v[v["mode"] == "long"]
    return v


def main():
    tab = pd.read_csv(os.path.join(WORK, "gaia_ml_unpub.csv"), dtype={"source_id": str})
    c = tab[tab.verdict == "new lens candidate"].sort_values(["p_lens", "A_obs_G"], ascending=False).head(8)
    n = len(c)
    fig, axes = plt.subplots(n, 2, figsize=(12, 2.35 * n), gridspec_kw={"width_ratios": [1.5, 1]})
    axes = np.atleast_2d(axes)
    for i, r in enumerate(c.itertuples()):
        a, b = axes[i]
        d, _ = epoch(r.source_id)
        df, _ = ratio_series(d)
        fj = json.load(open(os.path.join(DATA, "fits", f"{r.source_id}.json")))
        lab = "parallax" if fj["fit"]["parallax"]["bic"] < fj["fit"]["static"]["bic"] else "static"
        t0 = fj["fit"][lab]["t0"]
        tp = r.t_peak if np.isfinite(r.t_peak) else t0
        lo, hi = tp - 260, tp + 260
        tg = df[df.g == "G"].t
        for mlab, ls in (("static", "-"), ("parallax", "--")):
            m = fj["models"][mlab]
            mt = np.array(m["t"])
            sel = (mt > max(lo, tg.min() - 20)) & (mt < min(hi, tg.max() + 20))
            a.plot(yr(mt[sel]), np.array(m["G"])[sel], ls, color=MUTED, lw=1.1, label=f"point lens, {mlab} (G)")
        for band in ("BP", "RP", "G"):
            x = df[(df.g == band) & (df.t > lo) & (df.t < hi)]
            a.errorbar(yr(x.t), x.f, x.e, fmt=MK[band], color=COL[band], ms=4 if band == "G" else 3.2, lw=0.7,
                       elinewidth=0.7, alpha=1 if band == "G" else 0.8, label=f"Gaia {band}", zorder=3 if band == "G" else 2)
        v = neowise_visits(r.source_id)
        nw_ok = isinstance(r.nw_status, str) and r.nw_status == "ok" and v is not None
        if nw_ok:
            win = (np.abs(v.t - t0) > max(2 * min(fj["fit"]["static"]["tE"], 750), 100))
            for band in ("W1", "W2"):
                x = v[v.band == band]
                base = np.median(x.mag[win[x.index]]) if win[x.index].sum() >= 4 else np.median(x.mag)
                xr = x[(x.t > lo) & (x.t < hi)]
                f = 10 ** (-0.4 * (xr.mag - base))
                a.errorbar(yr(xr.t), f, f * 0.921 * xr.err, fmt=MK[band], color=COL[band], ms=6, mfc="white", mew=1.5,
                           lw=0.8, label=f"NEOWISE {band}", zorder=4)
                xa = x
                fa = 10 ** (-0.4 * (xa.mag - base))
                b.plot(yr(xa.t), fa, MK[band] + "-", color=COL[band], ms=4.5, mfc="white", mew=1.2, lw=0.8, label=band)
            b.axhline(1, color=GRID, lw=1, zorder=0)
            b.set_ylabel("flux / baseline", fontsize=8, color=MUTED)
        else:
            b.text(0.5, 0.5, "NEOWISE: no source on the star\n(crowded field)", transform=b.transAxes, ha="center",
                   va="center", fontsize=8, color=MUTED)
            b.set_yticks([])
        b.axvspan(yr(DR3_START), yr(DR3_END), color="#f0efec", zorder=-1)
        b.set_xlim(2013.9, 2024.7)
        a.axhline(1, color=GRID, lw=1, zorder=0)
        ymax = max(float(df[(df.g == "G") & (df.t > lo) & (df.t < hi)].f.max()), 1.2)
        if nw_ok:
            ymax = max(ymax, float(np.nanmax(10 ** (-0.4 * (v.mag - v.groupby("band").mag.transform("median"))))))
        a.set_ylim(0.7, ymax * 1.18)
        a.set_xlim(yr(lo), yr(hi))
        a.set_ylabel("flux / baseline", fontsize=8, color=MUTED)
        title = (f"{r.name}  Gaia DR3 {r.source_id}  (l {r.l:.1f}, b {r.b:+.1f}, G {r.phot_g_mean_mag:.1f})  "
                 f"P(lens) {r.p_lens:.2f}")
        a.set_title(title, fontsize=8.5, loc="left", color=INK)
        b.set_title(f"peak {r.t0_robust.split(' (')[0]}; tE {r.tE_range.split(' (')[0]}; Gaia ≥ ×{r.peak_amp}",
                    fontsize=8, loc="left", color=MUTED)
        for ax in (a, b):
            ax.tick_params(labelsize=7.5, colors=MUTED)
            for s in ("top", "right"):
                ax.spines[s].set_visible(False)
            for s in ("left", "bottom"):
                ax.spines[s].set_color(GRID)
        if i == 0:
            h, lab_ = a.get_legend_handles_labels()
            hb, lb = b.get_legend_handles_labels()
            seen = {}
            for hh, ll in zip(h + hb, lab_ + [f"NEOWISE {x}" for x in lb], strict=True):
                seen.setdefault(ll, hh)
            fig.legend(list(seen.values()), list(seen.keys()), loc="upper center", ncol=7, fontsize=8, frameon=False,
                       bbox_to_anchor=(0.5, 1.0))
    axes[-1, 0].set_xlabel("year", fontsize=8, color=MUTED)
    axes[-1, 1].set_xlabel("year (NEOWISE 2014-2024; Gaia DR3 span shaded)", fontsize=8, color=MUTED)
    plt.tight_layout(rect=(0, 0, 1, 0.975))
    os.makedirs(FIG, exist_ok=True)
    out = os.path.join(FIG, "candidates.png")
    plt.savefig(out, dpi=150)
    print("wrote", out, n, "candidates")


if __name__ == "__main__":
    main()
