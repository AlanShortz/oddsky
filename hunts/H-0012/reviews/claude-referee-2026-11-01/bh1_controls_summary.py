"""Summarise bh1_step_test.json: the 2010 -> NEOWISE statistic on control sources and positions.

    uv run python hunts/H-0012/reviews/claude-referee-2026-11-01/bh1_controls_summary.py
"""
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
F0 = {1: 309.54, 2: 171.787}


def rstd(x):
    return 1.4826 * np.median(np.abs(x - np.median(x)))


d = json.loads((HERE / "bh1_step_test.json").read_text())
print("BH1 environment:", d["bh1_env"])
for b in (1, 2):
    S = d["sources"][f"W{b}"]
    ref = np.array([s["ref"] for s in S]); dn = np.array([s["dneo"] for s in S])
    sg = np.array([s["dneo_sig"] for s in S]); dl = np.array([s["dlate_sig"] for s in S])
    print(f"\nW{b}: {len(S)} reference sources; dneo_sig median {np.median(sg):+.2f}, robust std {rstd(sg):.2f}, "
          f"n(<-5) {np.sum(sg < -5)}, n(>5) {np.sum(sg > 5)}, min {sg.min():.1f}; dlate_sig rstd {rstd(dl):.2f}, n(<-5) {np.sum(dl < -5)}")
    for lo, hi in [(-1e9, 10), (10, 30), (30, 100), (100, 300), (300, 1000), (1000, 3000), (3000, 1e9)]:
        m = (ref >= lo) & (ref < hi)
        if m.sum() < 3:
            continue
        frac = dn[m] / np.maximum(ref[m], 1)
        print(f"   ref {lo:>7.0f}-{hi:<7.0f} n={m.sum():3d}  dneo median {np.median(dn[m]):+7.2f} nmgy "
              f"({1e3 * np.median(dn[m]) * F0[b] * 1e-6:+6.2f} uJy)  dneo_sig median {np.median(sg[m]):+5.2f} "
              f"rstd {rstd(sg[m]):.2f} min {sg[m].min():+5.1f}  median dneo/ref {np.median(frac):+.4f}")
    for k in np.argsort(sg)[:6]:
        print("     most negative:", {kk: (round(S[k][kk], 4) if isinstance(S[k][kk], float) else S[k][kk])
                                     for kk in ("ra", "dec", "ref", "dneo", "dneo_sig", "dlate_sig", "rell")})
    G = d["grid"][f"W{b}"]
    hp = np.array([g["hp"] for g in G]); gs = np.array([g["dneo_sig"] for g in G])
    r = np.hypot([g["dx"] for g in G], [g["dy"] for g in G])
    print(f"   grid: {len(G)} positions within 2.5' of BH1: dneo_sig median {np.median(gs):+.2f} rstd {rstd(gs):.2f} "
          f"min {gs.min():.1f} n(<-5) {np.sum(gs < -5)}")
    for q in (50, 75, 90, 97):
        thr = np.percentile(hp, q); m = hp >= thr
        print(f"     high-pass >= p{q} ({thr:.2f} nmgy/px): n={m.sum()} median {np.median(gs[m]):+.2f} rstd {rstd(gs[m]):.2f} "
              f"min {gs[m].min():+.1f} n(<-5) {np.sum(gs[m] < -5)}")
    m = (r <= 6)
    print("     grid points 3-6 px from BH1 (sharing its PSF):", sorted(np.round(gs[m], 1).tolist()))
    far = r > 6
    print(f"     grid beyond 6 px: n={far.sum()} min {gs[far].min():.1f}, n(<-5) {np.sum(gs[far] < -5)}, n(<-4) {np.sum(gs[far] < -4)}")
