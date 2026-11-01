"""H-0011 pilot, step 6: figures for the README.

figures/population.png    drift-corrected W1 change 2014-15 -> 2023-24 vs W1 brightness, MC and Galactic RSGs,
                          with the per-bin 5-sigma band and the 0.4 mag floor of flag B
figures/drift.png         the NEOWISE saturation drift (median W1 change per brightness bin)
figures/calibrators.png   WOH G64 and LBV/dusty calibrators
figures/candidates.png    every MC/Galactic star with a flag
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plotlib as P  # noqa: E402

W = P.WORK


def population():
    mc, gal = pd.read_csv(W / "stats_mc.csv"), pd.read_csv(W / "stats_gal.csv")
    dt = pd.read_csv(W / "saturation_drift.csv")
    dt = dt[dt.band == "W1"]
    fig, ax = P.plt.subplots(figsize=(7.2, 4.2))
    ax.scatter(gal.W1_med, gal.W1_dc, s=9, color=P.C["W2"], alpha=0.55, lw=0, label=f"Galactic RSGs (n={gal.W1_dc.notna().sum()})")
    ax.scatter(mc.W1_med, mc.W1_dc, s=9, color=P.C["W1"], alpha=0.7, lw=0, label=f"LMC+SMC RSGs (n={mc.W1_dc.notna().sum()})")
    x = np.r_[dt.lo.clip(lower=1).to_numpy(), dt.hi.clip(upper=11).to_numpy()[-1]]
    thr = np.maximum(5 * dt.mad.to_numpy(), 0.4)
    ax.stairs(thr, x, color=P.C["muted"], lw=1.2, ls="--", label="flag B threshold (max of 5 x scatter, 0.4 mag)")
    ax.stairs(-thr, x, color=P.C["muted"], lw=1.2, ls="--")
    for d, c in ((mc, P.C["W1"]), (gal, P.C["W2"])):
        f = d[d.n_flags > 0]
        for r in f.itertuples():
            ax.annotate(r.main_id.replace("SV* ", "").replace("V* ", ""), (r.W1_med, r.W1_dc), fontsize=7,
                        xytext=(4, 4), textcoords="offset points", color=P.C["ink"])
            ax.plot(r.W1_med, r.W1_dc, "o", ms=7, mfc="none", mec=P.C["ink"], mew=0.8)
    ax.axvspan(0, 8, color="#f2f2ef", zorder=0)
    ax.text(1.15, -1.35, "W1 < 8: saturated in NEOWISE", fontsize=7, color=P.C["muted"])
    ax.set_xlim(1, 11)
    ax.set_ylim(-1.5, 1.5)
    ax.invert_yaxis()
    ax.set_xlabel("median NEOWISE W1 (mag)")
    ax.set_ylabel("W1 change 2014-15 -> 2023-24, drift-corrected (mag)\n(down = fainter)")
    ax.legend(fontsize=7, loc="lower right")
    ax.set_title("Ten-year W1 change of every sample RSG: a failed SN (DS1-like) ends 1-4 mag down", loc="left", fontsize=9)
    fig.savefig(P.FIG / "population.png", dpi=130, bbox_inches="tight")
    P.plt.close(fig)

    fig, ax = P.plt.subplots(figsize=(5.5, 3.2))
    pop = pd.concat([mc, gal])
    ax.scatter(pop.W1_med, pop.W1_delta, s=6, color=P.C["muted"], alpha=0.35, lw=0, label="each star (raw)")
    mid = (dt.lo.clip(lower=1.5) + dt.hi.clip(upper=10.5)) / 2
    ax.plot(mid, dt.med, "o-", color=P.C["W1"], ms=5, lw=1.8, label="bin median (the drift)")
    ax.axhline(0, color="#999", lw=0.8)
    ax.set_xlim(1, 11)
    ax.set_ylim(-1.2, 0.8)
    ax.invert_yaxis()
    ax.set_xlabel("median NEOWISE W1 (mag)")
    ax.set_ylabel("raw W1 late - early (mag)")
    ax.set_title("NEOWISE saturation drift: saturated RSGs 'brighten' 0.1-0.5 mag", loc="left", fontsize=9)
    ax.legend(fontsize=7)
    fig.savefig(P.FIG / "drift.png", dpi=130, bbox_inches="tight")
    P.plt.close(fig)


def lcs(which: str, names: list[str] | None, out: str, flagged: bool = False):
    st = pd.read_csv(W / f"stats_{which}.csv", dtype={"source_id": "Int64", "gaia_dr3": "Int64"})
    v = pd.read_parquet(W / f"neowise_visits_{which}.parquet")
    ep = pd.read_parquet(W / f"gaia_epoch_{which}.parquet") if (W / f"gaia_epoch_{which}.parquet").exists() else None
    sel = st[st.n_flags > 0] if flagged else st[st.main_id.isin(names)]
    if names and not flagged:
        sel = sel.set_index("main_id").loc[[n for n in names if n in set(sel.main_id)]].reset_index()
    rows = []
    for r in sel.itertuples():
        flags = [c.split("_")[0] for c in ("A_optfade_irholds", "B_ir_oneway", "C_gaia_deficit", "D_failedSN_shape")
                 if getattr(r, c, False) is True]
        lab = getattr(r, "note", "") if which == "cal" else (getattr(r, "sp_type", "") or "")
        lab = lab if isinstance(lab, str) else ""
        title = f"{r.main_id}  {lab[:38]}" + (f"  [flag {','.join(flags)}]" if flags else "")
        rows.append(dict(sid=r.oid, source_id=getattr(r, "source_id", None) if pd.notna(getattr(r, "source_id", None)) else None, title=title))
    if rows:
        P.grid(rows, v, ep, P.FIG / out)


def main():
    population()
    lcs("cal", ["WOH G  64", "HD 269006", "HD 269858", "V* S Dor", "SV* HV   888", "HD 269582"], "calibrators.png")
    for w in ("mc", "gal"):
        lcs(w, None, f"candidates_{w}.png", flagged=True)


if __name__ == "__main__":
    main()
