"""H-0015 s6: figures for the README (hunts/H-0015/figures/).

  acceptance.png   detection probability (left) and median mass precision of detections (right) vs source G, one line per
                   lens mass (ordinal: one blue ramp, light = light lens), nominal errors; pessimistic errors dashed (left)
  ranked.png       the top 20 ranked targets: P(detect) if the lens were a dark 1, 5, 10 Msun object, and for the Galactic
                   model's lens population (the mass DR4 would actually measure)
  ob110462.png     OGLE-2011-BLG-0462's expected Gaia deflection: as it happened (peak 2011) and peaking mid-DR4, against
                   DR4's span and the per-transit along-scan error at its Gaia G
Run: uv run python -I hunts/H-0015/scripts/s6_figures.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA, DR4_END, DR4_START, FIG, RUNS  # noqa: E402

from oddsky.analysis import astrolens as al  # noqa: E402
from oddsky.analysis import lensing  # noqa: E402

RAMP = ["#b7d3f6", "#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#0d366b"]   # one blue ramp, ordinal masses
INK, MUTED, GRID = "#1f1f1e", "#6b6a63", "#e6e5e0"
ACCENT = "#eb6834"


def style(ax):
    ax.grid(True, color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.xaxis.label.set_color(INK)
    ax.yaxis.label.set_color(INK)


def acceptance():
    d = pd.read_csv(RUNS / "acceptance/acceptance_full.csv")
    d["det"] = d.dchi2 >= 25
    inj = d[d.kind == "inject"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 3.8))
    for i, M in enumerate(sorted(inj.M.unique())):
        for prec, ls in (("edr3", "-"), ("rybicki18", "--")):
            g = inj[(inj.M == M) & (inj.precision == prec)].groupby("G").det.mean()
            a1.plot(g.index, g.values, ls, color=RAMP[i], lw=2, marker="o" if ls == "-" else None, ms=4,
                    label=f"{M:g} Msun" if prec == "edr3" else None)
        dd = inj[(inj.M == M) & (inj.precision == "edr3") & inj.det & inj.M_best.notna()]
        grp = ((dd.M_hi68 - dd.M_lo68) / (2 * dd.M_best)).groupby(dd.G)
        rs = grp.median()[grp.size() >= 5]          # cells with at least 5 detections
        a2.plot(rs.index, rs.values, "-", color=RAMP[i], lw=2, marker="o", ms=4)
    a1.set_xlabel("source G (baseline)")
    a1.set_ylabel("P(Delta chi^2 >= 25)")
    a1.set_title("Detection probability (solid: EDR3 errors; dashed: 1.7-2x worse)", fontsize=9, color=INK, loc="left")
    a1.legend(fontsize=7, frameon=False, title="dark lens", title_fontsize=7)
    a2.set_xlabel("source G (baseline)")
    a2.set_ylabel("median sigma(M)/M of detections")
    a2.set_yscale("log")
    a2.set_title("Mass precision of detections (>= 5 per point; Gaia G photometry only)", fontsize=9, color=INK, loc="left")
    for a in (a1, a2):
        style(a)
    fig.tight_layout()
    fig.savefig(FIG / "acceptance.png", dpi=130)
    plt.close(fig)


def ranked():
    R = pd.read_csv(DATA / "ranked_targets.csv", dtype={"source_id": str})
    R = R[R.score >= 0].sort_values("rank").head(20).iloc[::-1]
    lab = [f"{(c + ' ') if isinstance(c, str) and c else ''}{n}  G {g:.1f}  P(lens) {p:.2f}"
           for c, n, g, p in zip(R.case, R.name, R.G, R.p_lens, strict=True)]
    y = np.arange(len(R))
    fig, ax = plt.subplots(figsize=(9, 6.2))
    for j, (col, name, c, mk) in enumerate((("pdet_1", "1 Msun", RAMP[1], "o"), ("pdet_5", "5 Msun", RAMP[3], "o"),
                                            ("pdet_10", "10 Msun", RAMP[5], "o"),
                                            ("pdet_pop", "Galactic-model lens", ACCENT, "D"))):
        note = f"note_{col.split('_')[1]}"
        v = R[col].where(R[note].isna()) if note in R else R[col]     # no lens of that mass fits the photometry: no point
        ax.scatter(v, y + (j - 1.5) * 0.15, s=34 if mk == "o" else 30, color=c, marker=mk, label=name,
                   edgecolor="white", linewidth=0.8, zorder=3)
    ax.set_yticks(y)
    ax.set_yticklabels(lab, fontsize=7)
    ax.set_xlabel("P(DR4 detects the deflection | lens)")
    ax.set_xlim(-0.03, 1.03)
    ax.set_title("Top 20 targets (rank by P(lens) x max(P_det pop, P_det 5 Msun))", fontsize=9, color=INK, loc="left")
    ax.legend(fontsize=7, frameon=False, loc="lower right")
    style(ax)
    fig.tight_layout()
    fig.savefig(FIG / "ranked.png", dpi=130)
    plt.close(fig)


def ob110462():
    ra, dec = 267.917458, -29.890639
    t = np.linspace(55000, 59200, 3000)
    fig, ax = plt.subplots(figsize=(9, 3.6))
    for t0, lab, c in ((55762.83, "as it happened (peak 2011 Jul)", RAMP[5]), (57813.0, "if it had peaked 2017 Mar", RAMP[2])):
        q = np.array([t0, 239.7, 0.00263, 0.073, -0.050])
        dn_s, de_s = lensing.sun_offsets(t, ra, dec, round(t0))
        tau = (t - q[0]) / q[1] + q[3] * dn_s + q[4] * de_s
        beta = q[2] + (-q[3] * de_s + q[4] * dn_s)
        un, ue = al.trajectory(tau, beta, q[3], q[4])
        for fs, ls in ((1.0, "-"), (0.048, ":")):
            dn, de = al.centroid_shift(un, ue, fs)
            ax.plot(t, 5.68 * np.hypot(dn, de), ls, color=c, lw=2,
                    label=f"{lab}, {'unblended' if fs == 1 else 'blended as observed (fs 0.05)'}")
    ax.axvspan(DR4_START, DR4_END, color=GRID, alpha=0.7, lw=0)
    ax.text(DR4_START + 30, 2.05, "Gaia DR4 span", fontsize=8, color=MUTED)
    s = float(al.sigma_al_fov(17.93))
    ax.axhline(s, color=MUTED, lw=1, ls="--")
    ax.text(55050, s + 0.04, f"one-transit AL error at G 17.9 ({s:.2f} mas)", fontsize=7, color=MUTED)
    ax.set_ylim(0, 2.3)
    ax.set_xlabel("MJD")
    ax.set_ylabel("centroid shift (mas)")
    ax.set_title("OGLE-2011-BLG-0462 (Mroz et al. 2022 parameters: theta_E 5.68 mas, M 7.9 Msun)", fontsize=9, color=INK, loc="left")
    ax.legend(fontsize=7, frameon=False, loc="upper right")
    style(ax)
    fig.tight_layout()
    fig.savefig(FIG / "ob110462.png", dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    FIG.mkdir(parents=True, exist_ok=True)
    acceptance()
    ranked()
    ob110462()
    print("figures ->", FIG)
