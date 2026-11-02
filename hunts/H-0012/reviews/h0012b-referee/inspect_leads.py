"""Referee (h0012b): light curves, cutouts and neighbours for the new v2 leads.

    uv run python hunts/H-0012/reviews/h0012b-referee/inspect_leads.py

Reads hunts/H-0012/work/triage_h0012b.csv and ~/oddsky-runs/h0012b/<tile>/<galaxy>/. Writes lead_<label>.png,
leads_lc.csv and leads.json next to this script.
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
RUN = Path("~/oddsky-runs/h0012b").expanduser()
TRI = pd.read_csv(ROOT / "hunts/H-0012/work/triage_h0012b.csv", dtype={"gaia_id": str})
PIX = 2.75

LEADS = [  # label, rank column, rank
    ("NGC55_fsn7", "rank_fsn", 7), ("NGC55_fsn13", "rank_fsn", 13), ("M81_fsn24", "rank_fsn", 24),
    ("NGC925_obs37", "rank_obs", 37), ("NGC2403_obs50", "rank_obs", 50), ("NGC2903_obs75", "rank_obs", 75),
    ("Circinus_fsn72", "rank_fsn", 72), ("NGC5128_obs22_AT2020nqq", "rank_obs", 22),
    ("NGC55_obs184", "rank_obs", 184), ("NGC55_obs299", "rank_obs", 299), ("NGC55_obs187", "rank_obs", 187),
    ("NGC55_fsn64", "rank_fsn", 64), ("NGC55_fsn90", "rank_fsn", 90), ("NGC55_fsn111", "rank_fsn", 111),
    ("ESO274-001_fsn51", "rank_fsn", 51), ("NGC6946_fsn71", "rank_fsn", 71), ("HIZSS012_obs123", "rank_obs", 123),
    ("IC3104_obs259", "rank_obs", 259), ("IC3104_obs283", "rank_obs", 283), ("M31_obs302", "rank_obs", 302),
    ("M33_fsn304", "rank_fsn", 304), ("M33_obs754", "rank_obs", 754),
]


def yr(mjd):
    return 2000 + (np.asarray(mjd) - 51544.5) / 365.25


def aligned(lc, b):
    lb = lc[lc.band == b].sort_values("mjd")
    g = (np.isfinite(lb.flux) & np.isfinite(lb.err) & (lb.err > 0)).to_numpy()
    rf = lb.groupby("season").ref_flux.first().to_dict()
    f = metrics.align_seasons(lb.flux.to_numpy(), lb.season.to_numpy(), rf)
    out = pd.DataFrame(dict(mjd=lb.mjd.to_numpy(), epoch=lb.epoch.to_numpy(), season=lb.season.to_numpy(), f=f,
                            fraw=lb.flux.to_numpy(), e=lb.err.to_numpy(), ref=lb.ref_flux.to_numpy()))[g]
    early = out.mjd < metrics.EARLY_MJD
    w = 1 / out.e**2
    base = np.sum(w[early] * out.f[early]) / np.sum(w[early]) if early.any() else 0.0
    k = F0_JY[b] * 1e-3  # nanomaggy -> uJy
    out["df_ujy"] = (out.f - base) * k
    out["e_ujy"] = out.e * k
    out["raw_ujy"] = out.fraw * k
    out["ref_ujy"] = out.ref * k
    return out.reset_index(drop=True)


def season_stack(cube, seasons, mjd, sel_a, sel_b):
    """Season-matched mean(D[a]) - mean(D[b]), averaged over the seasons that have both."""
    ims = []
    for s in np.unique(seasons):
        a = sel_a & (seasons == s)
        b = sel_b & (seasons == s)
        if a.any() and b.any():
            ims.append(np.nanmean(cube[a], 0) - np.nanmean(cube[b], 0))
    return np.nanmean(ims, 0) if ims else None


def main():
    rows, lcs = [], []
    for lab, col, rk in LEADS:
        sel = TRI[TRI[col] == rk]
        if len(sel) != 1:
            print(lab, "not found", len(sel))
            continue
        r = sel.iloc[0]
        gal, tile, gid = r.uid.split("|")
        gid = int(gid)
        gdir = RUN / tile / gal
        lc_all = pd.read_parquet(gdir / "lightcurves.parquet")
        lc = lc_all[lc_all.group == gid]
        cands = pd.read_csv(gdir / "candidates.csv")
        a1, a2 = aligned(lc, 1), aligned(lc, 2)
        for b, a in ((1, a1), (2, a2)):
            lcs.append(a.assign(lead=lab, band=b))
        z = np.load(gdir / "cutouts.npz")
        # neighbours: other candidates within 60"
        d = np.hypot((cands.ra - r.ra) * np.cos(np.radians(r.dec)), cands.dec - r.dec) * 3600
        nb = cands[(d < 60) & (cands.group != gid)].assign(sep=d[(d < 60) & (cands.group != gid)])
        fig = plt.figure(figsize=(17, 7.2))
        gs = fig.add_gridspec(2, 6, width_ratios=[3.2, 1, 1, 1, 1, 1.4])
        ax = fig.add_subplot(gs[0, 0])
        for b, a, c in ((1, a1, "C0"), (2, a2, "C3")):
            for s, mk in ((0, "o"), (1, "s")):
                m = a.season == s
                ax.errorbar(yr(a.mjd[m]), a.df_ujy[m], a.e_ujy[m], fmt=mk, ms=3.5, color=c, mfc=c if s == 0 else "white",
                            label=f"W{b} season {s}")
        ax.axhline(0, color="k", lw=0.5)
        ax.set_ylabel("change since 2010-11 (uJy)")
        ax.legend(fontsize=6, ncol=2)
        ax.set_title(f"{lab}  {gal} {r.ra:.5f} {r.dec:+.5f}  cls {r.cls} (W1 {r.cls_w1} / W2 {r.cls_w2})  "
                     f"var_sig {r.var_sig:.1f}  chan {r.channel}", fontsize=8)
        # raw (unaligned) per-season fluxes: season offsets show PSF/blend systematics
        ax2 = fig.add_subplot(gs[1, 0])
        for b, a, c in ((1, a1, "C0"), (2, a2, "C3")):
            for s, mk in ((0, "o"), (1, "s")):
                m = a.season == s
                ax2.errorbar(yr(a.mjd[m]), a.raw_ujy[m], a.e_ujy[m], fmt=mk, ms=3.5, color=c, mfc=c if s == 0 else "white")
        ax2.axhline(0, color="k", lw=0.5)
        ref1 = a1.groupby("season").ref_ujy.first().round(0).to_dict()
        ref2 = a2.groupby("season").ref_ujy.first().round(0).to_dict()
        ax2.set_title(f"raw difference flux per season (not aligned).  ref W1 {ref1}  W2 {ref2} uJy", fontsize=7)
        ax2.set_xlabel("year")
        # event epoch: largest |change| in the gate band
        gb = a1 if r.gate_band == 1 or str(r.gate_band) == "1" else a2
        iev = int(np.nanargmax(np.abs(gb.df_ujy.to_numpy())))
        ev_epoch = int(gb.epoch.iloc[iev])
        info = dict(lead=lab, uid=r.uid, galaxy=gal, ra=float(r.ra), dec=float(r.dec), cls=r.cls, var_sig=float(r.var_sig),
                    ev_epoch=ev_epoch, ev_year=float(yr(gb.mjd.iloc[iev])),
                    refW1_ujy=ref1, refW2_ujy=ref2, n_neighbours_60=int(len(nb)),
                    neighbours=nb[["group", "ra", "dec", "sep", "cls", "var_sig", "channel"]].round(5).to_dict("records"))
        for bi, b in enumerate((1, 2)):
            kr, kd = f"{gid}_w{b}_ref", f"{gid}_w{b}_diff"
            axr = fig.add_subplot(gs[bi, 1])
            axl = fig.add_subplot(gs[bi, 2])
            axe = fig.add_subplot(gs[bi, 3])
            axn = fig.add_subplot(gs[bi, 4])
            for x in (axr, axl, axe, axn):
                x.set_xticks([]); x.set_yticks([])
            if kr not in z:
                axr.set_title("no cutout", fontsize=7)
                continue
            ref = z[kr]
            cube = z[kd]
            lb = lc[lc.band == b].sort_values("epoch")
            seas = lb.season.to_numpy()
            mjd = lb.mjd.to_numpy()
            if len(seas) != cube.shape[0]:
                print(lab, "epoch/cube mismatch", len(seas), cube.shape)
                continue
            v0, v1 = np.nanpercentile(ref, [5, 99.7])
            axr.imshow(np.arcsinh((ref - v0) / max(v1 - v0, 1e-3) * 10), origin="lower", cmap="gray")
            axr.set_title(f"W{b} ref (113\")", fontsize=7)
            early = mjd < metrics.EARLY_MJD
            late = mjd >= mjd.max() - 550
            neo = mjd > 56600
            le = season_stack(cube, seas, mjd, late, early)
            ne = season_stack(cube, seas, mjd, neo, early)
            ev = cube[int(np.where(lb.epoch.to_numpy() == ev_epoch)[0][0])] if ev_epoch in set(lb.epoch) else None
            # one colour scale per band from the NEO-early stack's outer region noise
            def show(axx, im, title):
                if im is None:
                    axx.set_title(title + " n/a", fontsize=7)
                    return
                v = max(np.nanpercentile(np.abs(im), 99.5), 1e-3)
                axx.imshow(im, origin="lower", cmap="RdBu_r", vmin=-v, vmax=v)
                axx.set_title(title, fontsize=7)
            show(axl, le, f"W{b} late-early")
            show(axn, ne, f"W{b} NEO-early")
            show(axe, ev, f"W{b} D @ {yr(mjd[lb.epoch.to_numpy() == ev_epoch][0]):.1f}" if ev is not None else "")
            for x in (axr, axl, axe, axn):
                x.plot(20, 20, "+", color="lime", ms=10, mew=0.8)
                for _, n in nb.iterrows():
                    dx = (n.ra - r.ra) * np.cos(np.radians(r.dec)) * 3600 / PIX
                    dy = (n.dec - r.dec) * 3600 / PIX
                    x.plot(20 - dx, 20 + dy, "x", color="orange", ms=5, mew=0.8)  # RA increases to the left (east)
            # quantify: PSF-like central residual vs ring scatter in NEO-early
            if ne is not None:
                yy, xx = np.mgrid[:41, :41]
                rr = np.hypot(xx - 20, yy - 20)
                cen = np.nanmean(ne[rr <= 1.5])
                ring = ne[(rr > 6) & (rr < 18)]
                info[f"w{b}_neo_early_centre"] = float(cen)
                info[f"w{b}_neo_early_ring_rms"] = float(np.nanstd(ring))
                info[f"w{b}_neo_early_ring_min"] = float(np.nanmin(ring))
                info[f"w{b}_neo_early_ring_max"] = float(np.nanmax(ring))
                info[f"w{b}_ref_peak_ratio"] = float(ref[20, 20] / np.nanmax(ref))
        axt = fig.add_subplot(gs[:, 5]); axt.axis("off")
        txt = (f"fsn#{r.rank_fsn} obs#{r.rank_obs}\nmask {r.mask_code} lowconf {r.low_confidence}\n"
               f"r_norm {r.r_norm:.2f} edge {r.edge_px:.0f}px\n"
               f"dneo W1 {r.w1_delta_neo_sig:.1f} W2 {r.w2_delta_neo_sig:.1f}\n"
               f"dlate W1 {r.w1_delta_late_sig:.1f} W2 {r.w2_delta_late_sig:.1f}\n"
               f"rough {r.rough_max:.2f} dipole_dchi2 {r.dipole_dchi2}\n"
               f"Lup W1 {r.L_up_w1:.2g} Lfade W1 {r.L_fade_w1:.2g}\ncol_up {r.colour_up:.2f}\n"
               f"Gaia {r.gaia_id}\n sep {r.gaia_sep} G {r.gaia_G} BP-RP {r.gaia_bp_rp}\n"
               f"AllWISE sep {r.allwise_sep} W1 {r.allwise_w1mpro}\n W1-W2 {r.allwise_w1w2}\n"
               f"SIMBAD {r.simbad_all}\nTNS {r.tns_name} {r.tns_sep}\n"
               f"neighbours<60\": {len(nb)} (orange x)\n" +
               "\n".join(f" {n.sep:4.0f}\" {n.cls} vs{n.var_sig:.1f}" for _, n in nb.sort_values('sep').head(8).iterrows()))
        axt.text(0, 0.98, txt, fontsize=6.5, va="top", family="monospace")
        fig.tight_layout()
        fig.savefig(HERE / f"lead_{lab}.png", dpi=85)
        plt.close(fig)
        rows.append(info)
        print(lab, "ok", r.uid, "event", info["ev_year"], "nb", len(nb))
    pd.concat(lcs).to_csv(HERE / "leads_lc.csv", index=False)
    (HERE / "leads.json").write_text(json.dumps(rows, indent=1, default=str))


if __name__ == "__main__":
    main()
