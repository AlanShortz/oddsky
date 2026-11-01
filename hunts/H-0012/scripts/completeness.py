"""H-0012 candidate-level completeness: inject fake variable point sources into the RAW epoch images
(before references, kernels, subtraction, masks and noise calibration), run the full detection
(both channels, both bands) and the candidate rule, and count recoveries.

    uv run python hunts/H-0012/scripts/completeness.py M31
    uv run python hunts/H-0012/scripts/completeness.py NGC6946

Light-curve shapes (flux A in mJy, the same in W1 and W2, i.e. W1-W2 = 0.64 Vega):
  vanish      A until 2016.6, then 0 (a star that disappears)
  early_only  A in the 2010-11 WISE epochs only (an N6946-BH1-like remnant that fades by 2014)
  appear      0 until 2017.0, then A (a new mid-IR source)
  ds1         De et al.'s DS1 shape: quiescent A, +50% by 2017.0, then exponential fade to ~0
Positions: a 30-px grid in each test region, minus masked pixels and minus anything within 8" of a
candidate found without injection. Recovered = a candidate within 4" (the grouping length).
Writes work/completeness_<galaxy>.json and figures/<galaxy>_completeness.png.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from oddsky.imaging import fetch, mjy_to_flux
from oddsky.imaging.galaxies import GALAXIES
from oddsky.imaging.pipeline import Config, analyse_stack, candidates_from, tile_dir
from oddsky.imaging.psf import shifted
from oddsky.imaging.stack import load_stack
from oddsky.imaging.tiles import primary_tile, wcs_for

HERE = Path(__file__).resolve().parents[1]
F0 = {1: 309.54, 2: 171.787}
W1C, W2C, INK, MUTED = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e"

REGIONS = {  # (label, ra, dec, half-size px)
    "M31": [("mid-disk r=0.45", 11.270, 41.832, 256), ("outer r=1.05", 11.243, 40.941, 256)],
    "NGC6946": [("disk (whole window)", 308.718015, 60.153915, 200)],
}
SHAPES = ("vanish", "early_only", "appear", "ds1")


def curve(shape: str, mjd: np.ndarray) -> np.ndarray:
    if shape == "vanish":
        return (mjd < 57600).astype(float)
    if shape == "early_only":
        return (mjd < 55700).astype(float)
    if shape == "appear":
        return (mjd >= 57750).astype(float)
    y = np.ones_like(mjd, float)
    rise = (mjd >= 56650) & (mjd < 57750)
    y[rise] = 1 + 0.5 * (mjd[rise] - 56650) / 1100
    fade = mjd >= 57750
    y[fade] = 1.5 * np.exp(-(mjd[fade] - 57750) / 500)
    return y


def mag_to_mjy(m_w1: float) -> float:
    return F0[1] * 10 ** (-m_w1 / 2.5) * 1e3


def run_region(galaxy, label, ra, dec, half, mags, cfg):
    gal = GALAXIES[galaxy]
    tile = primary_tile(ra, dec)
    x0, y0 = wcs_for(tile).all_world2pix([[ra, dec]], 0)[0]
    win = (int(max(0, y0 - half)), int(min(2048, y0 + half)), int(max(0, x0 - half)), int(min(2048, x0 + half)))
    stacks = {b: load_stack(tile, b, window=win) for b in (1, 2)}
    psfs = {b: {s: np.load(tile_dir(fetch.cache_root() / "work" / galaxy, tile, b) / f"psf_s{s}.npy") for s in (0, 1)}
            for b in (1, 2)}

    def detect_all(injector=None):
        dets = []
        masks = {}
        for b, st0 in stacks.items():
            st = type(st0)(**{**st0.__dict__, "img": st0.img.copy()})
            d, prod = analyse_stack(st, gal, cfg, inject=(lambda s, b=b: injector(s, b)) if injector else None)
            dets.append(d)
            masks[b] = prod["det_mask"]
        return candidates_from(pd.concat(dets, ignore_index=True), cfg), masks

    base, masks = detect_all()
    st1 = stacks[1]
    ny, nx = st1.img.shape[1:]
    gy, gx = np.mgrid[20:ny - 20:30, 20:nx - 20:30]
    gx, gy = gx.ravel() + 0.3, gy.ravel() + 0.4
    ok = ~(masks[1][gy.astype(int), gx.astype(int)] | masks[2][gy.astype(int), gx.astype(int)])
    pra, pdec = st1.wcs.all_pix2world(gx, gy, 0)
    if len(base):
        for cra, cdec in zip(base.ra, base.dec, strict=True):
            ok &= np.hypot((pra - cra) * np.cos(np.radians(cdec)), pdec - cdec) * 3600 > 8
    gx, gy, pra, pdec = gx[ok], gy[ok], pra[ok], pdec[ok]
    res = {}
    for shape in SHAPES:
        for m in mags:
            amp = mag_to_mjy(m)

            def injector(st, b, shape=shape, amp=amp):
                h = psfs[b][0].shape[0] // 2
                lc = curve(shape, st.mjd) * mjy_to_flux(amp, b)
                for i in range(st.n):
                    if lc[i] == 0:
                        continue
                    p = psfs[b][int(st.season[i])]
                    for x, y in zip(gx, gy, strict=True):
                        xi, yi = int(round(x)), int(round(y))
                        st.img[i, yi - h: yi + h + 1, xi - h: xi + h + 1] += lc[i] * shifted(p, x - xi, y - yi)

            t0 = time.time()
            c, _ = detect_all(injector)
            hit = {"epoch": 0, "stack": 0, "union": 0}
            for a, d in zip(pra, pdec, strict=True):
                if not len(c):
                    break
                sep = np.hypot((c.ra - a) * np.cos(np.radians(d)), c.dec - d) * 3600
                j = sep < 4.0
                if j.any():
                    chans = set(c.channel[j])
                    hit["union"] += 1
                    hit["epoch"] += bool(chans & {"epoch", "both"})
                    hit["stack"] += bool(chans & {"stack", "both"})
            res[(shape, m)] = {k: v / len(gx) for k, v in hit.items()}
            print(f"  {label} {shape:10s} W1={m:5.2f} ({amp * 1e3:7.1f} uJy): epoch {res[(shape, m)]['epoch']:.2f} "
                  f"stack {res[(shape, m)]['stack']:.2f} union {res[(shape, m)]['union']:.2f}  [{time.time() - t0:.0f}s]", flush=True)
    return dict(tile=tile, window=win, n_positions=int(len(gx)), n_baseline_candidates=int(len(base)),
                recovery={f"{s}|{m}": v for (s, m), v in res.items()})


def main(galaxy: str):
    cfg = Config()
    mags = np.arange(13.0, 18.51, 0.5) if galaxy == "M31" else np.arange(14.0, 19.01, 0.5)
    out = dict(galaxy=galaxy, mags_w1=mags.tolist(), uJy=[mag_to_mjy(m) * 1e3 for m in mags], regions={})
    for label, ra, dec, half in REGIONS[galaxy]:
        print(galaxy, label, flush=True)
        out["regions"][label] = run_region(galaxy, label, ra, dec, half, mags, cfg)
    (HERE / "work" / f"completeness_{galaxy}.json").write_text(json.dumps(out, indent=1))
    figure(out, HERE / "figures" / f"{galaxy}_completeness.png")


def figure(out, path):
    regs = out["regions"]
    fig, axs = plt.subplots(len(regs), len(SHAPES), figsize=(13, 3.0 * len(regs)), squeeze=False, sharey=True, facecolor="#fcfcfb")
    uj = np.array(out["uJy"])
    for r, (label, reg) in enumerate(regs.items()):
        for k, shape in enumerate(SHAPES):
            ax = axs[r, k]
            for chan, col, ls in (("union", INK, "-"), ("epoch", W1C, "--"), ("stack", W2C, ":")):
                y = [reg["recovery"][f"{shape}|{m}"][chan] for m in out["mags_w1"]]
                ax.plot(uj, y, ls, color=col, lw=2, marker="o", ms=4, label=chan if (r == 0 and k == 0) else None)
            ax.set_xscale("log")
            ax.set_ylim(-0.03, 1.03)
            ax.grid(alpha=0.25, lw=0.5)
            ax.spines[["top", "right"]].set_visible(False)
            ax.set_title(f"{label}: {shape}", fontsize=9, color=INK)
            if r == len(regs) - 1:
                ax.set_xlabel("injected amplitude A (µJy, both bands)", fontsize=8, color=INK)
    axs[0, 0].set_ylabel("candidate recovery", color=INK)
    axs[0, 0].legend(frameon=False, fontsize=8)
    fig.suptitle(f"{out['galaxy']}: completeness of the candidate rule (injected into raw epoch images)", fontsize=10, color=INK)
    fig.tight_layout()
    fig.savefig(path, dpi=130, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main(sys.argv[1])
