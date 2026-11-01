"""Shared plotting for the H-0011 pilot (static PNGs for the README).

Colours: reference categorical slots 1-3 (blue W1, orange W2, aqua Gaia G / optical). One magnitude axis per panel.
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
WORK, FIG = ROOT / "work", ROOT / "figures"
C = {"W1": "#2a78d6", "W2": "#eb6834", "G": "#1baf7a", "ATLAS_o": "#6250d6", "ink": "#0b0b0b", "muted": "#52514e"}
MJD2000 = 51544.5

plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": "#888",
                     "axes.labelcolor": C["ink"], "xtick.color": C["muted"], "ytick.color": C["muted"],
                     "axes.grid": True, "grid.color": "#e6e6e3", "grid.linewidth": 0.6, "legend.frameon": False})


def yr(mjd):
    return 2000.0 + (np.asarray(mjd, float) - MJD2000) / 365.25


def lc_panel(ax_ir, ax_opt, sid, visits: pd.DataFrame, gaia_ep: pd.DataFrame | None, source_id, title: str,
             extra_opt: pd.DataFrame | None = None):
    v = visits[visits.sid == sid]
    for band in ("W1", "W2"):
        b = v[v.band == band].sort_values("t_mjd")
        if b.empty:
            continue
        neo = b[b.survey == "NEOWISE"]
        ref = np.median(neo.mag.to_numpy()[:4]) if len(neo) else np.median(b.mag)
        sat = neo.flag.fillna("").str.contains("saturated")
        ax_ir.errorbar(yr(neo.t_mjd), neo.mag - ref, neo.err, fmt="o-", ms=4, lw=1.2, color=C[band], label=f"{band}",
                       mfc=C[band], mec="white", mew=0.6)
        if sat.any():
            ax_ir.plot(yr(neo.t_mjd[sat]), (neo.mag - ref)[sat], "o", ms=8, mfc="none", mec=C[band], mew=0.8)
        mep = b[b.survey == "WISE_MEP"]
        if len(mep):
            ax_ir.errorbar(yr(mep.t_mjd), mep.mag - ref, mep.err, fmt="s", ms=4, color=C[band], mfc="white")
    ax_ir.invert_yaxis()
    ax_ir.set_ylabel("Δmag vs 2014-15")
    ax_ir.set_title(title, fontsize=9, loc="left", color=C["ink"])
    ax_ir.legend(loc="best", fontsize=8)
    have = False
    if gaia_ep is not None and source_id is not None and np.isfinite(source_id):
        g = gaia_ep[(gaia_ep.source_id == int(source_id)) & (gaia_ep.band == "G") & np.isfinite(gaia_ep.mag)]
        g = g[g.flag.fillna("") != "rejected_by_photometry"]
        if len(g):
            ax_opt.plot(yr(g.t_mjd), g.mag, "o", ms=3.5, color=C["G"], label="Gaia DR3 G")
            have = True
    if extra_opt is not None and len(extra_opt):
        for band, d in extra_opt.groupby("band"):
            ax_opt.plot(yr(d.t_mjd), d.mag, ".", ms=2, color=C.get(band, C["muted"]), label=band)
        have = True
    if have:
        ax_opt.invert_yaxis()
        ax_opt.legend(loc="best", fontsize=8)
    else:
        ax_opt.text(0.5, 0.5, "no optical epoch photometry", transform=ax_opt.transAxes, ha="center", va="center",
                    color=C["muted"])
    ax_opt.set_ylabel("mag")
    for ax in (ax_ir, ax_opt):
        ax.set_xlim(2009.5, 2025)


def grid(rows: list[dict], visits, gaia_ep, out: Path, ncol: int = 2):
    n = len(rows)
    nr = int(np.ceil(n / ncol))
    fig = plt.figure(figsize=(5.2 * ncol, 3.6 * nr))
    gs = fig.add_gridspec(nr * 3, ncol, hspace=0.9, wspace=0.25)
    for i, r in enumerate(rows):
        rr, cc = divmod(i, ncol)
        a1 = fig.add_subplot(gs[rr * 3:rr * 3 + 2, cc])
        a2 = fig.add_subplot(gs[rr * 3 + 2, cc], sharex=a1)
        lc_panel(a1, a2, r["sid"], visits, gaia_ep, r.get("source_id"), r["title"], r.get("extra_opt"))
    fig.savefig(out, dpi=130, bbox_inches="tight")
    plt.close(fig)
