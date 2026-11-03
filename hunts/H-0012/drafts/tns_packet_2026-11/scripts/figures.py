"""TNS packet 2026-11: one summary figure per ready candidate, for the TNS related-file upload (PNG < 1 MB).

Top: unWISE W1/W2 difference light curve (flux vs the pre-event leave-one-out reference; numbers.json) with the
last non-detection and discovery epochs marked, plus Spitzer/IRAC difference photometry where available (M81: the
H-0013 Spitzer extension, hunts/H-0013/work/spitzer/MESSIER081_1507p696_6.json; NGC 4945: spitzer_ngc4945.py).
Bottom: 69" x 69" unWISE stamps, north up, east left: the pre-event W1 reference, then W1 and W2 difference images
at the last non-detection, the discovery and the W1 peak (each stamp scaled to max(4 x its robust noise,
0.9 x its central peak)); a circle of 5" radius marks the transient centroid.

    uv run python hunts/H-0012/drafts/tns_packet_2026-11/scripts/figures.py
Output: hunts/H-0012/drafts/tns_packet_2026-11/<label>_summary.png
"""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import sys

sys.path.insert(0, str(Path(__file__).parent))
from lc_screen import centroid_fit  # noqa: E402

PK = Path(__file__).resolve().parents[1]
REPO = PK.parents[3]
S = Path.home() / "oddsky-runs/imaging/scratch/tns-packet-2026-11"
RUNS = Path.home() / "oddsky-runs/h0012b"
NUM = json.loads((PK / "numbers.json").read_text())
CEN = json.loads((S / "lc/centroids.json").read_text())

CFG = {
    "NGC4945_obs3": dict(rank=3, uid="NGC4945|1974m500|14", title="Oddsky H0012-NGC4945-1: mid-infrared transient in NGC 4945",
                         spitzer=S / "spitzer/discovery.json", internal="Oddsky H0012-NGC4945-1"),
    "M81_OS-0035": dict(rank=8, uid="MESSIER081|1507p696|6", title="Oddsky OS-0035: mid-infrared eruption in M81 (NGC 3031)",
                        spitzer=REPO / "hunts/H-0013/work/spitzer/MESSIER081_1507p696_6.json", internal="Oddsky OS-0035"),
}
C1, C2, CI1, CI2 = "#1f5fa8", "#c0392b", "#7fb2e5", "#f1948a"


def yr(mjd):
    return 2000 + (np.asarray(mjd, float) - 51544.5) / 365.25


def spitzer_points(lab, path):
    if not path.exists():
        return {}
    d = json.loads(path.read_text())
    out = {}
    if lab == "M81_OS-0035":
        sp = d["spitzer"]
        for b in ("I1", "I2"):
            if b in sp and sp[b]:
                m = np.array(sp[b]["mjd"])
                f = np.array(sp[b]["dflux"])
                e = np.array(sp[b]["err"])
                y = yr(m)
                q = (y > 2003.5) & (y < 2005.5)  # put the zero at the quiescent 2003.8-2005.0 level
                f = f - (np.median(f[q]) if q.any() else 0.0)
                out[b] = (y, f, e)
    else:
        for b in ("I1", "I2"):  # spitzer_discovery.py: LOO vs flat 2013-2016, aperture-corrected
            lc = pd.DataFrame([r for r in d["lc"][b] if "uJy" in r])
            out[b] = (lc.year.to_numpy(), lc.uJy.to_numpy(), lc.e_uJy.to_numpy())
    return out


def stamp(ax, img, title, vm, pos_px=(20, 20)):
    # per-stamp scale: noise-dominated stamps look like noise, detections are not saturated
    st = img[8:33, 8:33]
    noise = 1.4826 * np.median(np.abs(st - np.median(st)))
    peak = np.max(img[18:23, 18:23])
    vm = max(4 * noise, 0.9 * peak)
    ax.imshow(img[8:33, 8:33], origin="lower", cmap="gray_r", vmin=-vm, vmax=vm, interpolation="nearest")
    ax.add_patch(plt.Circle((pos_px[0] - 8, pos_px[1] - 8), 5 / 2.75, fill=False, color="#e67e22", lw=1.0))
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(title, fontsize=7.5)


for lab, cfg in CFG.items():
    n = NUM[lab]
    L = pd.DataFrame(n["light_curve"])
    fig = plt.figure(figsize=(10.5, 6.3))
    ax = fig.add_axes([0.075, 0.45, 0.9, 0.44])
    sp = spitzer_points(lab, cfg["spitzer"])
    if "I1" in sp:
        ax.errorbar(sp["I1"][0], sp["I1"][1], sp["I1"][2], fmt="s", ms=3, color=CI1, label="Spitzer [3.6]", zorder=1)
    if "I2" in sp:
        ax.errorbar(sp["I2"][0], sp["I2"][1], sp["I2"][2], fmt="s", ms=3, color=CI2, label="Spitzer [4.5]", zorder=1)
    for b, c in ((1, C1), (2, C2)):
        x = L[L.band == b]
        ax.errorbar(x.year, x.flux, x.err, fmt="o", ms=4.5, color=c, label=f"unWISE W{b}", zorder=3)
    if lab == "NGC4945_obs3":  # discovery = Spitzer [3.6] 2018-06-02; last non-detection = IRAC 2017-10-03
        dd, ll = n["discovery"]["phot"][0], n["last_nondetection"]["phot"][0]
        td, tl = yr(dd["mjd_mid"]), yr(ll["mjd_mid"])
        dlab, llab = f" discovery (IRAC)\n {dd['utc_mid'][:10]}", f" last non-det.\n (IRAC) {ll['utc_mid'][:10]}"
        wd, wl = n["wise_first_detection"]["time"], n["wise_last_nondetection"]["time"]
    else:
        td = yr(n["discovery"]["time"]["mjd_mean"])
        tl = yr(n["last_nondetection"]["time"]["mjd_mean"])
        dlab = f" discovery\n {n['discovery']['time']['utc_mean'][:10]}"
        llab = f" last non-det.\n {n['last_nondetection']['time']['utc_mean'][:10]}"
        wd, wl = n["discovery"]["time"], n["last_nondetection"]["time"]
    ax.axvline(tl, color="0.5", ls=":", lw=1)
    ax.axvline(td, color="k", ls="--", lw=1)
    ymax = np.nanmax(L.flux) * 1.12
    ax.text(tl, ymax * 0.97, llab, fontsize=7.5, ha="right", va="top", color="0.35")
    ax.text(td, ymax * 0.97, dlab, fontsize=7.5, ha="left", va="top")
    ax.axhline(0, color="k", lw=0.5)
    ax.set_ylim(min(-80, np.nanmin(L.flux) - 60), ymax)
    ax.set_xlim(2003.3 if "I1" in sp and sp["I1"][0].min() < 2006 else 2006.5, 2025.0)
    ax.set_ylabel("flux change vs pre-event reference (µJy)")
    ax.set_xlabel("year")
    ax.legend(loc="upper left", fontsize=7.5, ncol=2, frameon=False)
    p = n["position"]
    ax.set_title(f"{cfg['title']}\nRA, Dec = {p['ra_hms']} {p['dec_dms']} (±{p['err_arcsec_quoted']}\", {'Spitzer/IRAC centroid' if 'source' in p else 'Gaia-tied WISE centroid'})",
                 fontsize=10)
    # stamps
    gal, tile, gid = cfg["uid"].split("|")
    z = np.load(RUNS / tile / gal / "cutouts.npz")
    ref = z[f"{gid}_w1_ref"]
    rank = cfg["rank"]
    cubes = {b: np.load(S / f"lc/cube_{rank}_w{b}.npy") for b in (1, 2)}
    eps = {b: sorted(L[L.band == b].epoch) for b in (1, 2)}
    if lab == "NGC4945_obs3":
        cols = [("WISE non-det.", wl), ("1st WISE det.", wd), ("W1 peak", n["peak_W1"]["time"])]
    else:
        cols = [("last non-det.", wl), ("discovery", wd), ("W1 peak", n["peak_W1"]["time"])]
    vm = {b: 0.6 * np.nanpercentile(np.abs(cubes[b][eps[b].index(n["peak_W1"]["time"]["epoch"])][12:29, 12:29]), 99.5) for b in (1, 2)}
    stk = np.nan_to_num(np.load(S / f"lc/stack_{rank}.npy"))
    cx, cy, _ = centroid_fit(stk, 20.0, 20.0, 2.27)
    w = 0.13
    a0 = fig.add_axes([0.04, 0.06, w, w * 10.5 / 6.3])
    rv = np.nanpercentile(ref, 99)
    a0.imshow(ref[8:33, 8:33], origin="lower", cmap="gray_r", vmin=np.nanpercentile(ref, 5), vmax=rv)
    a0.add_patch(plt.Circle((cx - 8, cy - 8), 5 / 2.75, fill=False, color="#e67e22", lw=1.0))
    a0.set_xticks([]); a0.set_yticks([])
    a0.set_title("W1 reference (pre-event)", fontsize=7.5)
    a0.text(0.03, 0.03, "N up, E left\n69\" x 69\"", transform=a0.transAxes, fontsize=6, color="k",
            bbox=dict(fc="w", ec="none", alpha=0.7, pad=1))
    for j, (name, t) in enumerate(cols):
        for k, b in enumerate((1, 2)):
            axs = fig.add_axes([0.2 + (2 * j + k) * 0.13, 0.06, w, w * 10.5 / 6.3])
            i = eps[b].index(t["epoch"])
            stamp(axs, np.nan_to_num(cubes[b][i]), f"W{b} diff, {name}\n{t['utc_mean'][:10]}", vm[b], (cx, cy))
    fig.text(0.04, 0.012, "Data: unWISE time-resolved coadds (NEO11 version, courtesy A. Meisner; Meisner, Lang & Schlegel 2018); "
             "WISE/NEOWISE (NASA/JPL/IPAC); Spitzer Heritage Archive (IRSA). Oddsky (oddsky.ai).", fontsize=6.5, color="0.3")
    out = PK / f"{lab}_summary.png"
    fig.savefig(out, dpi=110)
    plt.close(fig)
    print(out, out.stat().st_size // 1024, "kB")
