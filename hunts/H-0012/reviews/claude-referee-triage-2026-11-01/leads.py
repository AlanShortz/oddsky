"""Referee (triage round): light curves + cutouts + numbers for the H-0012a leads.

    uv run python hunts/H-0012/reviews/claude-referee-triage-2026-11-01/leads.py

Reads hunts/H-0012/work/triage_h0012a.csv and the per-tile run outputs in ~/oddsky-runs/h0012a.
Writes leads.png, leads_lc.csv and leads.json next to this script.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from oddsky.imaging import F0_JY, metrics

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
RUN = Path("~/oddsky-runs/h0012a").expanduser()
TRI = pd.read_csv(ROOT / "hunts/H-0012/work/triage_h0012a.csv", dtype={"gaia_id": str})

LEADS = [  # label, ra, dec (as briefed / from the triage table)
    ("NGC4945 obs#3", 196.4697, -49.4162),
    ("M81 obs#9", 148.739, 69.1468),
    ("NGC55 obs#14", 3.75575, -39.2033),
    ("M101 obs#19", 210.729, 54.374),
    ("IC342 fsn#1", 56.2762, 68.0725),
    ("NGC2976 fsn#5", 146.765, 67.935),
    ("M31 fsn#4", 10.0712, 40.4525),
    ("M33 fsn#10", 23.376, 30.6566),
    ("M33 fsn#12", 23.8551, 31.0109),
    ("M33 fsn#13", 23.7019, 30.8149),
    ("M33 fsn#14", 23.293, 30.6337),
    ("M31 fsn#3", 11.4583, 40.0859),
    ("M31 fsn#7", 11.273, 42.7306),
    ("M31 fsn#9", 9.71953, 40.3182),
    ("M31 fsn#11", 11.9763, 42.0834),
    ("NGC4945 obs#22", 196.416, -49.42),
    ("NGC4945 obs#45", 196.438, -49.4275),
    ("IC342 obs#26", 56.5658, 68.1491),
    ("HolmII obs#21", 124.803, 70.7187),
    ("M31 obs#27", 10.8769, 41.7422),
    ("UGCA127 obs#30", 95.2591, -8.4826),
    ("NGC3239 obs#33", 156.291, 17.1639),
    ("NGC1744 obs#32", 74.9977, -26.0432),
    ("IC342 fsn#59", 56.5002, 68.0429),
    ("BH1 fsn#65", 308.865, 60.1357),
    ("DS1 fsn#2", 11.3062, 41.5426),
    ("M31 GAPO209 fsn#27", 10.14482, 40.74984),
    ("NGC3109 fsn#143", 150.72496, -26.25587),
    ("IC342 fsn#70", 56.35968, 68.05055),
    ("NGC5128 fsn#49", 201.30782, -43.12396),
]


def sep(r1, d1, r2, d2):
    return np.hypot((np.asarray(r1) - r2) * np.cos(np.radians(d2)), np.asarray(d1) - d2) * 3600


def row_for(ra, dec):
    s = sep(TRI.ra, TRI.dec, ra, dec)
    k = int(np.argmin(s))
    return TRI.iloc[k], s[k]


def lc_for(r):
    gal, tile, gid = r.uid.split("|")
    gal_dir = RUN / tile / gal
    lc = pd.read_parquet(gal_dir / "lightcurves.parquet")
    lc = lc[lc.group == int(gid)].copy()
    return lc, gal_dir, int(gid)


def aligned(lc, b):
    lb = lc[lc.band == b].sort_values("mjd")
    g = (np.isfinite(lb.flux) & np.isfinite(lb.err) & (lb.err > 0)).to_numpy()
    rf = lb.groupby("season").ref_flux.first().to_dict()
    f = metrics.align_seasons(lb.flux.to_numpy(), lb.season.to_numpy(), rf)
    out = pd.DataFrame(dict(mjd=lb.mjd.to_numpy(), epoch=lb.epoch.to_numpy(), season=lb.season.to_numpy(),
                            f=f, e=lb.err.to_numpy(), ref=lb.ref_flux.to_numpy()))[g]
    early = out.mjd < metrics.EARLY_MJD
    w = 1 / out.e**2
    base = np.sum(w[early] * out.f[early]) / np.sum(w[early]) if early.any() else 0.0
    out["df_ujy"] = (out.f - base) * F0_JY[b] * 1e-3  # change since 2010-11, uJy
    out["e_ujy"] = out.e * F0_JY[b] * 1e-3
    out["tot_ujy"] = (out.f - base + np.nanmean(list(rf.values())) + base) * F0_JY[b] * 1e-3
    return out


def main():
    rows, lcs = [], []
    PER = 4
    figs = []
    for i, (lab, ra, dec) in enumerate(LEADS):
        if i % PER == 0:
            fig, axes_p = plt.subplots(PER, 5, figsize=(17, 3.2 * PER), gridspec_kw=dict(width_ratios=[3, 1, 1, 1, 1]))
            figs.append(fig)
        axes = {(i, k): axes_p[i % PER, k] for k in range(5)}
        class _A(dict):
            def __getitem__(self, ij):
                return dict.__getitem__(self, ij)
        axes = _A(axes)
        r, s = row_for(ra, dec)
        lc, gal_dir, gid = lc_for(r)
        a1, a2 = aligned(lc, 1), aligned(lc, 2)
        for b, a in ((1, a1), (2, a2)):
            lcs.append(a.assign(lead=lab, band=b))
        ax = axes[i, 0]
        for b, a, c in ((1, a1, "C0"), (2, a2, "C3")):
            yr = 2000 + (a.mjd - 51544.5) / 365.25
            ax.errorbar(yr, a.df_ujy, a.e_ujy, fmt="o", ms=3, color=c, label=f"W{b}")
        ax.axhline(0, color="k", lw=0.5)
        ax.set_title(f"{lab}  {r.galaxy} {r.ra:.4f} {r.dec:+.4f}  cls {r.cls} (W1 {r.cls_w1}/W2 {r.cls_w2})  "
                     f"refW1 {np.nanmean(a1.ref) * F0_JY[1] * 1e-3:.0f} uJy  sep {s:.1f}\"", fontsize=8)
        ax.set_ylabel("dF since 2010-11 (uJy)", fontsize=7)
        ax.legend(fontsize=6)
        z = np.load(gal_dir / "cutouts.npz")
        for j, key in enumerate([f"{gid}_w1_ref", f"{gid}_w1_diff", f"{gid}_w2_diff"]):
            axj = axes[i, 1 + j]
            axj.set_xticks([]); axj.set_yticks([])
            if key not in z:
                axj.set_title("no cutout", fontsize=6)
                continue
            im = z[key]
            if im.ndim == 3:  # difference stack: show late mean minus early mean
                mjd = lc[lc.band == 1].sort_values("epoch").mjd.to_numpy()
                ev = (a1.df_ujy.abs()).idxmax() if len(a1) else None
                late = np.arange(im.shape[0]) >= im.shape[0] - 4
                early = np.arange(im.shape[0]) < 2
                im = np.nanmean(im[late], 0) - np.nanmean(im[early], 0)
                v = np.nanpercentile(np.abs(im), 99)
                axj.imshow(im, origin="lower", cmap="RdBu_r", vmin=-v, vmax=v)
                axj.set_title(key.split("_", 1)[1] + " late-early", fontsize=6)
            else:
                v0, v1 = np.nanpercentile(im, [5, 99.5])
                axj.imshow(np.arcsinh((im - v0) / max(v1 - v0, 1e-3) * 10), origin="lower", cmap="gray")
                axj.set_title(key.split("_", 1)[1], fontsize=6)
        axes[i, 4].axis("off")
        txt = (f"fsn#{r.rank_fsn} obs#{r.rank_obs}\nLpre {r.Lbol_pre_est:.2g}  Lpk {r.L_peak:.2g}\n"
               f"col_up {r.colour_up:.2f} col_fade {r.colour_fade:.2f}\nAllWISE W1-W2 {r.allwise_w1w2}\n"
               f"Gaia {r.gaia_id} G {r.gaia_G}\nSIMBAD {r.simbad_otype} {r.simbad_id}\nr_norm {r.r_norm:.2f} edge {r.edge_px:.0f}px")
        axes[i, 4].text(0, 0.5, txt, fontsize=6, va="center")
        rows.append(dict(lead=lab, uid=r.uid, sep=float(s), galaxy=r.galaxy, ra=float(r.ra), dec=float(r.dec),
                         cls=r.cls, cls_w1=r.cls_w1, cls_w2=r.cls_w2, rank_fsn=r.rank_fsn, rank_obs=r.rank_obs,
                         r_norm=float(r.r_norm), edge_px=float(r.edge_px), dist=float(r.dist_mpc),
                         refW1_ujy=float(np.nanmean(a1.ref) * F0_JY[1] * 1e-3) if len(a1) else None,
                         refW2_ujy=float(np.nanmean(a2.ref) * F0_JY[2] * 1e-3) if len(a2) else None,
                         gaia_id=r.gaia_id, allwise=r.allwise_designation, allwise_w1w2=r.allwise_w1w2))
    for k, f in enumerate(figs):
        f.tight_layout()
        f.savefig(HERE / f"leads_{k}.png", dpi=70)
    pd.concat(lcs).to_csv(HERE / "leads_lc.csv", index=False)
    (HERE / "leads.json").write_text(json.dumps(rows, indent=1, default=str))
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
