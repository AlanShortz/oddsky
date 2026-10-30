"""r5: Gaia Science Alerts per-transit BP/RP low-resolution spectra (from the alert pages, data/gsa_<alert>.html) for Gaia21atr
(J191120) and Gaia23boj (J174440). The spectra carry no dates, so the event transits are identified by their integrated flux
(bright transits = event), matched to the alert light curve by rank. Achromaticity test: the event spectrum divided by the
median quiescent spectrum should be flat (a lens multiplies every wavelength by the same A); a nova / CV / YSO / Be outburst
adds a bluer continuum and/or H-alpha emission (RP pixel ~ 656 nm).
"""
import json
import os
import re
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA, HERE  # noqa: E402

fig, axes = plt.subplots(2, 2, figsize=(11, 7))
for row, a in enumerate(["Gaia21atr", "Gaia23boj"]):
    h = open(os.path.join(DATA, f"gsa_{a}.html")).read()
    s = json.loads(re.search(r"var spectra = (\[.*?\]);\s*\n", h, re.S).group(1))
    det = json.loads(re.search(r"var detections = (\[.*?\]);", h, re.S).group(1))
    bp = np.array([x["bp"] for x in s], float)
    rp = np.array([x["rp"] for x in s], float)
    tot = bp.sum(1) + rp.sum(1)
    q = np.median(tot)
    rel = tot / q
    mags = np.array([d[1] for d in det])
    gq = np.median(mags)
    # expected flux ratios of the brightest detections
    exp_ratio = np.sort(10 ** (-0.4 * (mags - gq)))[::-1][:12]
    order = np.argsort(rel)[::-1]
    print(f"== {a}: {len(s)} spectra, {len(det)} light-curve detections")
    print("  brightest spectra (integrated BP+RP / median):", np.round(rel[order[:12]], 2))
    print("  brightest light-curve transits (flux / median):", np.round(exp_ratio, 2))
    quiet = (rel > 0.9) & (rel < 1.1)
    bq, rq = np.median(bp[quiet], 0), np.median(rp[quiet], 0)
    sbq = 1.4826 * np.median(np.abs(bp[quiet] - bq), 0)
    srq = 1.4826 * np.median(np.abs(rp[quiet] - rq), 0)
    ev = order[:8] if a == "Gaia21atr" else order[:4]
    ev = [i for i in ev if rel[i] > 1.2]
    print(f"  quiescent spectra: {quiet.sum()}; event spectra used: {len(ev)} (flux ratios {np.round(rel[ev], 2)})")
    # ratio spectrum where the quiescent signal is significant
    for i in ev:
        okb = bq > 5 * sbq / np.sqrt(quiet.sum()) + 3
        okr = rq > 5 * srq / np.sqrt(quiet.sum()) + 3
        rb = bp[i][okb].sum() / bq[okb].sum()
        rr = rp[i][okr].sum() / rq[okr].sum()
        # within RP: blue half vs red half, and the H-alpha region (RP samples ~ 8-14 of 60 lie near 640-680 nm)
        half = len(rq) // 2
        r_lo = rp[i][:half][okr[:half]].sum() / rq[:half][okr[:half]].sum()
        r_hi = rp[i][half:][okr[half:]].sum() / rq[half:][okr[half:]].sum()
        print(f"   spectrum #{i}: total x{rel[i]:.2f}; BP x{rb:.2f}, RP x{rr:.2f} (BP/RP ratio change {rb / rr:.2f}); "
              f"RP blue half x{r_lo:.2f}, red half x{r_hi:.2f}")
    ax = axes[row, 0]
    x = np.arange(60)
    ax.plot(x, bq, c="b", lw=2, label="BP quiescent median")
    ax.plot(x + 62, rq, c="r", lw=2, label="RP quiescent median")
    for i in ev:
        ax.plot(x, bp[i] / rel[i], c="b", lw=0.6, alpha=0.6)
        ax.plot(x + 62, rp[i] / rel[i], c="r", lw=0.6, alpha=0.6)
    ax.set_title(f"{a}: event spectra scaled by their total flux (thin) vs quiescent", fontsize=8)
    ax.legend(fontsize=7)
    ax = axes[row, 1]
    for i in ev:
        with np.errstate(divide="ignore", invalid="ignore"):
            rb = np.where(bq > 10, bp[i] / bq, np.nan)
            rr = np.where(rq > 10, rp[i] / rq, np.nan)
        ax.plot(x, rb, "b.-", lw=0.5, ms=2)
        ax.plot(x + 62, rr, "r.-", lw=0.5, ms=2)
    ax.set_title(f"{a}: event / quiescent per sample (flat = achromatic)", fontsize=8)
    ax.set_xlabel("BP samples 0-59 | RP samples 62-121 (blue to red within each)", fontsize=7)
fig.tight_layout()
fig.savefig(os.path.join(HERE, "r5_gaia_spectra.png"), dpi=110)
