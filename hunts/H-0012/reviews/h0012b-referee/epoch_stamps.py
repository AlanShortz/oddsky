"""Per-epoch W1/W2 difference stamps (25x25 px = 69") at the h0012b leads, from the runner's cutouts.npz. Leads without
their own cutout (var_sig < 5, single-epoch channel) are cut from a neighbouring candidate's 41x41 cube that covers them.

    uv run python hunts/H-0012/reviews/h0012b-referee/epoch_stamps.py
Writes epochs_<lead>.png and stamps.json (central PSF-weighted flux vs annulus scatter per epoch) next to this script.
"""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
RUN = Path("~/oddsky-runs/h0012b").expanduser()
TRI = pd.read_csv(HERE.parents[1] / "work/triage_h0012b.csv", dtype={"gaia_id": str})
L = {d["lead"]: d for d in json.loads((HERE / "leads.json").read_text())}
SEL = ["NGC55_fsn7", "NGC55_fsn13", "NGC55_obs184", "NGC55_obs299", "M81_fsn24", "NGC925_obs37", "NGC2403_obs50",
       "NGC2903_obs75", "NGC5128_obs22_AT2020nqq", "Circinus_fsn72"]
PIX = 2.75
H = 12


def find_cube(gal_dir, gid, ra, dec, cands):
    z = np.load(gal_dir / "cutouts.npz")
    if f"{gid}_w1_diff" in z:
        return z, gid, 0, 0
    d = np.hypot((cands.ra - ra) * np.cos(np.radians(dec)), cands.dec - dec) * 3600
    for k in np.argsort(d.to_numpy()):
        g = int(cands.group.iloc[k])
        if f"{g}_w1_diff" not in z:
            continue
        dx = -(ra - cands.ra.iloc[k]) * np.cos(np.radians(dec)) * 3600 / PIX  # +x = west? tiles have RA increasing to -x
        dy = (dec - cands.dec.iloc[k]) * 3600 / PIX
        if max(abs(dx), abs(dy)) <= 20 - 5:  # at least an 11x11 stamp
            return z, g, int(round(dx)), int(round(dy))
    return z, None, 0, 0


def gauss_psf(fwhm_px, H):
    s = fwhm_px / 2.355
    yy, xx = np.mgrid[-H:H + 1, -H:H + 1]
    p = np.exp(-(xx**2 + yy**2) / (2 * s**2))
    return p / p.sum()


res = {}
for lab in SEL:
    d = L[lab]
    gal, tile, gid = d["uid"].split("|")
    gdir = RUN / tile / gal
    cands = pd.read_csv(gdir / "candidates.csv", low_memory=False)
    lc = pd.read_parquet(gdir / "lightcurves.parquet")
    z, g, ox, oy = find_cube(gdir, int(gid), d["ra"], d["dec"], cands)
    H = min(12, 20 - max(abs(ox), abs(oy)))
    if g is None:
        print(lab, "no covering cube")
        continue
    lc1 = lc[(lc.group == int(gid)) & (lc.band == 1)].sort_values("epoch")
    n = z[f"{g}_w1_diff"].shape[0]
    fig, ax = plt.subplots(3, n, figsize=(1.05 * n, 3.6))
    rows = {}
    for b in (1, 2):
        cube = z[f"{g}_w{b}_diff"]
        ref = z[f"{g}_w{b}_ref"]
        cy, cx = 20 + oy, 20 + ox
        st = cube[:, cy - H:cy + H + 1, cx - H:cx + H + 1]
        v = np.nanpercentile(np.abs(st), 99.0)
        psf = gauss_psf(6.1 / PIX if b == 1 else 6.8 / PIX, H)
        yy, xx = np.mgrid[-H:H + 1, -H:H + 1]
        rr = np.hypot(xx, yy)
        fl = []
        for i in range(n):
            im = st[i]
            f = np.nansum(im * psf) / np.nansum(psf**2)  # PSF-weighted amplitude (nanomaggy, Gaussian approx)
            # same statistic at 16 offset positions in the annulus: an empirical local error
            offs = []
            for ang in np.linspace(0, 2 * np.pi, 16, endpoint=False):
                ddx, ddy = int(round(min(8, 20 - H - max(abs(ox), abs(oy))) * np.cos(ang))), int(round(min(8, 20 - H - max(abs(ox), abs(oy))) * np.sin(ang)))
                sub = cube[i, cy - H + ddy:cy + H + 1 + ddy, cx - H + ddx:cx + H + 1 + ddx]
                if sub.shape == psf.shape:
                    offs.append(np.nansum(sub * psf) / np.nansum(psf**2))
            fl.append((float(f), float(np.nanstd(offs))))
            if b == 1:
                ax[0, i].imshow(im, origin="lower", cmap="RdBu_r", vmin=-v, vmax=v)
                if i < len(lc1):
                    ax[0, i].set_title(f"{2000 + (lc1.mjd.iloc[i] - 51544.5) / 365.25:.1f}", fontsize=6)
            else:
                ax[1, i].imshow(im, origin="lower", cmap="RdBu_r", vmin=-v, vmax=v)
        rows[f"w{b}"] = fl
        r0 = ref[cy - H:cy + H + 1, cx - H:cx + H + 1]
        v0, v1 = np.nanpercentile(r0, [5, 99.7])
        ax[2, b - 1].imshow(np.arcsinh((r0 - v0) / max(v1 - v0, 1e-3) * 10), origin="lower", cmap="gray")
        ax[2, b - 1].set_title(f"W{b} ref", fontsize=6)
    for a in ax.ravel():
        a.set_xticks([]); a.set_yticks([])
        if a.images:
            a.plot(H, H, "+", color="lime", ms=6, mew=0.6)
    for a in ax[2, 2:]:
        a.axis("off")
    fig.suptitle(f"{lab}: W1 (row 1) / W2 (row 2) difference per epoch vs full-season reference, {2*H+1} px square, "
                 f"cube of group {g} offset ({ox},{oy}) px", fontsize=7)
    fig.tight_layout()
    fig.savefig(HERE / f"epochs_{lab}.png", dpi=90)
    plt.close(fig)
    res[lab] = dict(cube_group=g, offset_px=[ox, oy], mjd=lc1.mjd.round(1).tolist(), **rows)
    print(lab, "ok", g, ox, oy)
(HERE / "stamps.json").write_text(json.dumps(res, indent=1))
