"""H-0013: recurrent dust-formation outbursts in the H-0012 forced light curves.

    uv run python hunts/H-0013/scripts/h0013.py scan  [--galaxies NGC2403 ...]   # every merged H-0012 source
    uv run python hunts/H-0013/scripts/h0013.py nulls [--n 500]                  # per-source nulls for the shortlist
    uv run python hunts/H-0013/scripts/h0013.py rank                             # vetoes, verdicts, ranking

Input: the H-0012 v2 run (~/oddsky-runs/h0012b/<tile>/<galaxy>/lightcurves.parquet) and its merged table
(~/oddsky-runs/h0012-xmatch/merged_h0012b.parquet: one row per source after the cross-tile merge, with the
H-0012 classes, triage flags and cross-matches). Every source with a light curve is scanned, whatever its
H-0012 class (most periodic dust makers would have been demoted as 'lpv-like' or 'irregular' there).

Outputs (big ones under ~/oddsky-runs/h0013/, small ones in hunts/H-0013/work/):
- scan.parquet: oddsky.imaging.recurrence.analyse for every source, plus one within-season shuffle and one
  phase-randomised surrogate per source (F_shuf1, F_phase1: the population nulls used to set F_MIN).
- nulls.parquet: p_shuffle (n shuffles) and p_phase (n/2 phase surrogates) for the shortlist.
- work/candidates_h0013.csv: the shortlist with context flags, verdicts and ranks.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd

from oddsky.imaging import metrics
from oddsky.imaging import recurrence as rc

log = logging.getLogger("h0013")
HERE = Path(__file__).resolve().parents[1]
WORK = HERE / "work"
RUN = Path(os.environ.get("ODDSKY_H0012_RUN", "~/oddsky-runs/h0012b")).expanduser()
MERGED = Path(os.environ.get("ODDSKY_H0012_MERGED", "~/oddsky-runs/h0012-xmatch/merged_h0012b.parquet")).expanduser()
OUT = Path(os.environ.get("ODDSKY_H0013", "~/oddsky-runs/h0013")).expanduser()

KEEP_COLS = ["uid", "galaxy", "phot_galaxy", "tile", "group", "ra", "dec", "cls", "var_sig", "r_norm", "dist_mpc",
             "dipole", "dipole_cutout", "mask_code", "w1_ref_flux", "w2_ref_flux", "triage_class", "what", "known_name",
             "gaia_foreground", "gaia_quasar", "agn_colour", "simbad_agn", "simbad_otype", "simbad_id", "simbad_sep",
             "gaia_id", "gaia_sep", "gaia_G", "gaia_bp_rp", "allwise_w1w2", "edge_px", "n_tiles"]

SCALAR_KEYS = ["P_yr", "t0", "tau_r", "tau_d", "F", "dchi2", "chi2_fit", "dof", "chi2r_fit", "chi2r_null", "n",
               "amp_w1", "amp_w2", "n_cycles_det", "n_cycles_covered", "n_cycles_missing", "cycle_snr2",
               "alpha_s0", "snr_s0", "alpha_s1", "snr_s1", "dchi2_single", "t_single", "taud_single", "dchi2_sine",
               "P_sine_d", "R", "S", "asym", "duty", "colour", "dchi2_short", "P_short_d", "A", "Z"]


def load_merged() -> pd.DataFrame:
    m = pd.read_parquet(MERGED)
    cols = [c for c in KEEP_COLS if c in m]
    return m.loc[m.get("has_lc", True).astype(bool), cols].reset_index(drop=True)


def iter_lightcurves(m: pd.DataFrame, galaxies=None):
    """(row, LightCurve) for every merged source, one H-0012 tile-galaxy light-curve file at a time."""
    if galaxies:
        m = m[m.galaxy.isin(galaxies) | m.phot_galaxy.isin(galaxies)]
    for (tile, gal), g in m.groupby(["tile", "phot_galaxy"], sort=True):
        p = RUN / tile / gal / "lightcurves.parquet"
        if not p.exists():
            log.warning("no light curves: %s", p)
            continue
        lcs = pd.read_parquet(p)
        lcs = lcs[lcs.group.isin(set(g.group))]
        by = dict(tuple(lcs.groupby("group")))
        for _, r in g.iterrows():
            lc = by.get(r.group)
            if lc is None:
                continue
            L = rc.from_long(lc, metrics.align_seasons)
            if L is None or L.n_good() < 20:
                continue
            yield r, L


def analyse_row(r, L, seed: int) -> dict:
    a = rc.analyse(L)
    out = {k: a.get(k, np.nan) for k in SCALAR_KEYS}
    out["peaks_det"] = json.dumps(a.get("peaks_det", []))
    out["cycles"] = json.dumps([{k: (round(v, 4) if isinstance(v, float) else v) for k, v in c.items()} for c in a.get("cycles", [])])
    out["light_verdict"], why = rc.light_verdict(a)
    out["light_why"] = ",".join(why)
    bank = rc.periodic_bank(L.t)
    out["F_shuf1"] = float(rc.shuffle_null(L, 1, seed=seed, bank=bank)[0])
    out["F_phase1"] = float(rc.phase_null(L, 1, seed=seed, bank=bank)[0])
    out["t_first"], out["t_last"], out["n_epochs"] = float(L.t.min()), float(L.t.max()), int(L.t.size)
    out["med_err_w1"], out["med_err_w2"] = float(np.nanmedian(L.e[0])), float(np.nanmedian(L.e[1]))
    return out


def cmd_scan(a):
    OUT.mkdir(parents=True, exist_ok=True)
    m = load_merged()
    t0 = time.time()
    rows = []
    for i, (r, L) in enumerate(iter_lightcurves(m, a.galaxies)):
        try:
            res = analyse_row(r, L, seed=int(r.name) + 1)
        except Exception as e:  # noqa: BLE001  (record, never silently drop)
            log.warning("failed %s: %s", r.uid, e)
            res = {"error": str(e)[:200]}
        rows.append({**r.to_dict(), **res})
        if (i + 1) % 2000 == 0:
            log.info("%d sources, %.0f s", i + 1, time.time() - t0)
    df = pd.DataFrame(rows)
    name = a.name or ("scan" if not a.galaxies else "scan_" + "_".join(a.galaxies))
    df.to_parquet(OUT / f"{name}.parquet")
    log.info("scan: %d sources in %.0f s -> %s", len(df), time.time() - t0, OUT / f"{name}.parquet")


# ----------------------------------------------------------------------------------------------
# context flags (image / catalogue level)

CORE_RNORM = 0.03


def _b(v) -> bool:
    if v is None or v is pd.NA or (isinstance(v, float) and np.isnan(v)):
        return False
    return str(v).lower() == "true" if isinstance(v, str) else bool(v)


def context_flags(df: pd.DataFrame, scan: pd.DataFrame | None = None) -> list[list[str]]:
    """Per row: moving (dipole / cutout dipole / SIMBAD PM*), foreground-star (Gaia parallax/PM), agn
    (Gaia quasar, AGN colour, SIMBAD AGN; soft), core (within CORE_RNORM of the galaxy centre or a
    nucleus/saturation mask code), empty-sky (reference flux <= 0 in both bands), lpv-known (SIMBAD
    AGB/LPV type; soft) and neighbour (a source within 12" whose recurrence fit at the same period is
    stronger and whose light curve correlates: this one is its PSF wing)."""
    from oddsky.imaging import masks

    out = []
    for _, r in df.iterrows():
        f = []
        if _b(r.get("dipole")) or _b(r.get("dipole_cutout")) or "moving" in str(r.get("what", "")):
            f.append("moving")
        if _b(r.get("gaia_foreground")):
            f.append("foreground-star")
        if _b(r.get("gaia_quasar")) or _b(r.get("agn_colour")) or _b(r.get("simbad_agn")):
            f.append("agn")
        mc = int(r.get("mask_code", 0) or 0)
        if np.nan_to_num(r.get("r_norm", 1.0), nan=1.0) < CORE_RNORM or (mc != 255 and mc & (masks.MB_NUCLEUS | masks.MB_SATURATED)):
            f.append("core")
        if np.nan_to_num(r.get("w1_ref_flux", 1.0), nan=1.0) <= 0 and np.nan_to_num(r.get("w2_ref_flux", 1.0), nan=1.0) <= 0:
            f.append("empty-sky")
        if str(r.get("simbad_otype", "")) in ("AB*", "LP*", "Mi*", "C*", "OH*", "S*", "sr*", "LP?", "Mi?", "AB?"):
            f.append("lpv-known")
        out.append(f)
    return out


def neighbour_flags(short: pd.DataFrame, scan: pd.DataFrame, r_arcsec: float = 12.0) -> dict:
    """uid -> neighbour uid, when a scanned source within r_arcsec has a larger dchi2 and its best period is
    within 10% (the same variable seen through the PSF wing)."""
    from scipy.spatial import cKDTree

    xyz = lambda ra, dec: np.c_[np.cos(np.radians(dec)) * np.cos(np.radians(ra)),  # noqa: E731
                                np.cos(np.radians(dec)) * np.sin(np.radians(ra)), np.sin(np.radians(dec))]
    tree = cKDTree(xyz(scan.ra.to_numpy(), scan.dec.to_numpy()))
    rad = 2 * np.sin(np.radians(r_arcsec / 3600) / 2)
    out = {}
    for _, r in short.iterrows():
        for j in tree.query_ball_point(xyz(np.r_[r.ra], np.r_[r.dec])[0], rad):
            o = scan.iloc[j]
            if o.uid == r.uid:
                continue
            if o.dchi2 > r.dchi2 and abs(o.P_yr / r.P_yr - 1) < 0.1:
                out[r.uid] = o.uid
                break
    return out


def tile_systematic(short: pd.DataFrame, scan: pd.DataFrame, k_min: int = 3) -> dict:
    """uid -> n: a recurrent source whose period (within 5%) and phase (within 0.1 P) are shared by >= k_min other
    recurrent sources more than 12" away in the same tile: a coherent pattern across a tile is a calibration
    (build / zero-point) systematic, not a star."""
    rec = scan[scan.light_verdict == "recurrent"]
    out = {}
    for _, r in short.iterrows():
        o = rec[(rec.tile == r.tile) & (rec.uid != r.uid)]
        if o.empty:
            continue
        far = np.hypot((o.ra - r.ra) * np.cos(np.radians(r.dec)), o.dec - r.dec) * 3600 > 12
        sameP = np.abs(o.P_yr / r.P_yr - 1) < 0.05
        dph = np.abs(((o.t0 - r.t0) / r.P_yr + 0.5) % 1 - 0.5)
        n = int((far & sameP & (dph < 0.1)).sum())
        if n >= k_min:
            out[r.uid] = n
    return out


def cmd_nulls(a):
    scan = pd.read_parquet(OUT / "scan.parquet")
    short = shortlist(scan, a.f_pre)
    log.info("nulls for %d shortlisted sources (F >= %.0f, >= 2 cycles)", len(short), a.f_pre)
    m = load_merged()
    want = set(short.uid)
    rows = []
    t0 = time.time()
    for r, L in iter_lightcurves(m[m.uid.isin(want)]):
        bank = rc.periodic_bank(L.t)
        F = rc.scan(L, bank)["F"]
        ns = rc.shuffle_null(L, a.n, seed=7, bank=bank)
        nph = rc.phase_null(L, a.n // 2, seed=8, bank=bank)
        rows.append(dict(uid=r.uid, F_check=F, p_shuffle=rc.p_value(ns, F), p_phase=rc.p_value(nph, F),
                         F_shuf_med=float(np.median(ns)), F_shuf_99=float(np.percentile(ns, 99)),
                         F_phase_med=float(np.median(nph)), n_shuffle=a.n, n_phase=a.n // 2))
    pd.DataFrame(rows).to_parquet(OUT / "nulls.parquet")
    log.info("nulls: %d sources in %.0f s", len(rows), time.time() - t0)


def shortlist(scan: pd.DataFrame, f_pre: float) -> pd.DataFrame:
    """Sources that pass the light-curve decision (recurrent: F >= F_MIN, >= 2 cycles, both seasons, not a Mira
    alias or short-period sinusoid)
    f_pre is an extra floor on F."""
    s = scan[(scan.light_verdict == "recurrent") & (scan.F >= f_pre)].copy()
    s["L_w2"] = nu_lnu(s.amp_w2.to_numpy(float), 2, s.dist_mpc.to_numpy(float))
    return s


def nu_lnu(amp_nmgy, band, dist_mpc):
    """nu L_nu (L_sun) of an amplitude in Vega nanomaggies at dist_mpc (Jarrett et al. 2011 zero points)."""
    from oddsky.imaging import F0_JY

    lam = {1: 3.368, 2: 4.618}[band]
    ujy = np.asarray(amp_nmgy, float) * F0_JY[band] * 1e-3
    return 4 * np.pi * (np.asarray(dist_mpc, float) * 3.0856775814913673e22) ** 2 * (2.99792458e14 / lam) * ujy * 1e-32 / 3.828e26


def cmd_rank(a):
    scan = pd.read_parquet(OUT / "scan.parquet")
    nulls = pd.read_parquet(OUT / "nulls.parquet")
    short = shortlist(scan, a.f_pre).merge(nulls, on="uid", how="left")
    short["flags"] = [",".join(f) for f in context_flags(short)]
    nb = neighbour_flags(short, scan)
    short["neighbour_of"] = short.uid.map(nb).fillna("")
    ts = tile_systematic(short, scan)
    short["n_tile_coherent"] = short.uid.map(ts).fillna(0).astype(int)
    vs, whys = [], []
    for _, r in short.iterrows():
        fl = [x for x in r["flags"].split(",") if x]
        if r.neighbour_of:
            fl.append("neighbour")
        if r.n_tile_coherent:
            fl.append("tile-systematic")
        pk = json.loads(r.peaks_det)
        if sum(r.t_first - 0.25 <= x <= r.t_last + 0.25 for x in pk) < 2:
            fl.append("edge-cycle")  # a detected cycle peaks outside the data: seen only as a tail or a final rise
        ana = r.to_dict()
        v, why = rc.verdict(ana, r.p_shuffle if np.isfinite(r.p_shuffle) else None, fl, f_min=a.f_min)
        vs.append(v)
        whys.append(",".join(why))
    short["verdict"], short["why"] = vs, whys
    # dust-maker priority (light curve and luminosity only; no catalogue identities): log10 F plus 0.5 for each of
    # P >= P_AGB_MAX (beyond AGB pulsation periods), Z >= 10 (flat-minimum outbursts clearly preferred over a
    # sinusoid), L_W2 >= 3e4 L_sun (more luminous than ordinary dusty AGB amplitudes), p_phase <= 0.01 (beats the
    # red-noise null)
    crit = np.c_[short.P_yr >= rc.P_AGB_MAX, short.Z >= 10, short.L_w2 >= 3e4, short.p_phase <= 0.01]
    short["n_crit"] = crit.sum(1)
    short["priority"] = np.log10(short.F.clip(lower=1)) + 0.5 * short.n_crit
    order = {"candidate": 0, "flagged": 1, "rejected": 2}
    short["_o"] = short.verdict.map(order)
    short["rank_F"] = short.F.rank(ascending=False, method="first").astype(int)
    ok = short.verdict != "rejected"
    short.loc[ok, "rank_F_ok"] = short.loc[ok, "F"].rank(ascending=False, method="first")
    short = short.sort_values(["_o", "priority"], ascending=[True, False]).reset_index(drop=True)
    # one list for the non-rejected (candidate and flagged together, by priority), then the rejected
    short["_ok"] = (short.verdict != "rejected").astype(int)
    short = short.sort_values(["_ok", "priority"], ascending=[False, False]).drop(columns=["_o", "_ok"]).reset_index(drop=True)
    short["rank"] = np.arange(1, len(short) + 1)
    WORK.mkdir(parents=True, exist_ok=True)
    cols = ["rank", "priority", "n_crit", "rank_F_ok", "verdict", "why", "uid", "galaxy", "ra", "dec", "dist_mpc", "r_norm", "cls", "var_sig", "P_yr", "t0",
            "tau_r", "tau_d", "F", "p_shuffle", "p_phase", "n_cycles_det", "n_cycles_covered", "n_cycles_missing",
            "peaks_det", "cycle_snr2", "snr_s0", "snr_s1", "R", "S", "Z", "A", "P_short_d", "P_sine_d", "asym", "duty", "colour",
            "amp_w1", "amp_w2", "L_w2", "n_tile_coherent", "t_first", "t_last",
            "chi2r_fit", "flags", "neighbour_of", "what", "known_name", "simbad_id", "simbad_otype", "gaia_G", "gaia_bp_rp",
            "allwise_w1w2", "cycles"]
    short[[c for c in cols if c in short]].to_csv(WORK / "candidates_h0013.csv", index=False)
    log.info("rank: %s", short.verdict.value_counts().to_dict())


# ----------------------------------------------------------------------------------------------
# image-level check and gallery


def hump_stamp(r, L: rc.LightCurve | None = None, band: int = 2):
    """Mean difference cutout of the outburst epochs (template >= 0.5 of peak) minus the mean of the quiescent
    epochs (template <= 0.1), from the H-0012 41x41 cutouts. Returns (stamp, ref, (dx, dy) centroid offset in px,
    peak S/N against the stamp's robust scatter)."""
    p = RUN / r.tile / r.phot_galaxy / "cutouts.npz"
    if not p.exists():
        return None
    z = np.load(p)
    k = f"{r.group}_w{band}_diff"
    if k not in z.files:
        return None
    cube = np.asarray(z[k], float)
    ref = np.asarray(z[f"{r.group}_w{band}_ref"], float)
    lcs = pd.read_parquet(RUN / r.tile / r.phot_galaxy / "lightcurves.parquet", filters=[("group", "==", int(r.group))])
    lb = lcs[lcs.band == band].sort_values("epoch")
    t = rc.mjd_to_year(lb.mjd.to_numpy())
    h = rc.periodic_template(t, r.P_yr, r.t0, r.tau_r, r.tau_d)
    h = h / h.max() if h.max() > 0 else h
    hi, lo = h >= 0.5, h <= 0.1
    if hi.sum() == 0 or lo.sum() == 0 or cube.shape[0] != t.size:
        return None
    st = np.nanmean(cube[hi], 0) - np.nanmean(cube[lo], 0)
    c = st.shape[0] // 2
    from scipy import ndimage

    sm = ndimage.gaussian_filter(np.nan_to_num(st), 1.0)
    win = sm[c - 4:c + 5, c - 4:c + 5]
    jy, jx = np.unravel_index(np.argmax(win), win.shape)
    mad = 1.4826 * np.nanmedian(np.abs(sm - np.nanmedian(sm)))
    return st, ref, (float(jx - 4), float(jy - 4)), float(win.max() / mad) if mad > 0 else np.nan


def cmd_figures(a):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    cands = pd.read_csv(WORK / "candidates_h0013.csv")
    sel = cands[cands.verdict.isin(a.verdicts.split(","))].head(a.top)
    m = load_merged().set_index("uid")
    n = len(sel)
    fig = plt.figure(figsize=(14, 2.3 * n))
    gs = fig.add_gridspec(n, 4, width_ratios=[4, 1, 1, 1])
    for i, (_, c) in enumerate(sel.iterrows()):
        r = m.loc[c.uid]
        lcs = pd.read_parquet(RUN / r.tile / r.phot_galaxy / "lightcurves.parquet", filters=[("group", "==", int(r.group))])
        L = rc.from_long(lcs, metrics.align_seasons)
        ax = fig.add_subplot(gs[i, 0])
        tt = np.linspace(L.t.min() - 0.3, L.t.max() + 0.3, 800)
        h = rc.periodic_template(tt, c.P_yr, c.t0, c.tau_r, c.tau_d)
        hd = rc.periodic_template(L.t, c.P_yr, c.t0, c.tau_r, c.tau_d)
        for b, col, scale, amp in ((0, "#1f5fa8", 0.30954, c.amp_w1), (1, "#d1495b", 0.171787, c.amp_w2)):
            y = L.y[b].copy()
            for ss in (0, 1):  # season offsets relative to the model, removed for display
                mm = (L.season == ss) & np.isfinite(y)
                w = 1 / L.e[b, mm] ** 2
                y[mm] -= np.sum(w * (y[mm] - amp * hd[mm])) / w.sum()
            for ss, mk in ((0, "o"), (1, "s")):
                mm = L.season == ss
                ax.errorbar(L.t[mm], y[mm] * scale, L.e[b, mm] * scale, fmt=mk, ms=3.2, lw=0.6, color=col,
                            label=f"W{b + 1} season {ss}" if i == 0 else None)
            ax.plot(tt, amp * h * scale, color=col, lw=0.8, alpha=0.6)
        for pk in json.loads(c.peaks_det):
            ax.axvline(pk, color="k", lw=0.5, ls=":")
        ax.axhline(0, color="0.85", lw=0.5)
        ax.set_ylabel("uJy", fontsize=8)
        ax.set_title(f"#{c['rank']} {c.verdict} {c.galaxy} {c.uid.split('|')[-1]} ({c.ra:.5f} {c.dec:+.5f}) | P={c.P_yr:.2f} yr "
                     f"F={c.F:.0f} p_sh={c.p_shuffle:.3f} cyc={c.n_cycles_det} S={c.S:.0f} col={c.colour:.2f} | "
                     f"H-0012 {c.cls} | {c.why if isinstance(c.why, str) else ''}", fontsize=7.5)
        if i == 0:
            ax.legend(fontsize=6, frameon=False, ncol=4, loc="upper left")
        hs = hump_stamp(r.rename(c.uid).combine_first(c))
        if hs is not None:
            st, ref, (dx, dy), snr = hs
            ax2 = fig.add_subplot(gs[i, 1])
            v0, v1 = np.nanpercentile(ref, [5, 99.5])
            ax2.imshow(np.arcsinh((ref - v0) / max(v1 - v0, 1e-6) * 10), origin="lower", cmap="gray")
            ax2.set_title("W2 reference (113\")", fontsize=7)
            ax3 = fig.add_subplot(gs[i, 2])
            v = np.nanpercentile(np.abs(st), 99.5)
            ax3.imshow(st, origin="lower", cmap="RdBu_r", vmin=-v, vmax=v)
            ax3.set_title(f"W2 outburst - quiescent (S/N {snr:.0f})", fontsize=7)
            for axx in (ax2, ax3):
                axx.plot(20, 20, "+", color="lime", ms=8)
                axx.set_xticks([])
                axx.set_yticks([])
        ax4 = fig.add_subplot(gs[i, 3])
        for b, col in ((0, "#1f5fa8"), (1, "#d1495b")):
            ph = ((L.t - c.t0) / c.P_yr) % 1
            yy = L.y[b] - np.nanmedian(L.y[b])
            ax4.plot(ph, yy / np.nanmax(np.abs(yy)), ".", color=col, ms=4)
        ax4.set_xlabel("phase", fontsize=7)
        ax4.set_yticks([])
    fig.tight_layout()
    out = HERE / "figures" / f"{a.name}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=90)
    log.info("wrote %s", out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan")
    s.add_argument("--galaxies", nargs="*")
    s.add_argument("--name")
    n = sub.add_parser("nulls")
    n.add_argument("--n", type=int, default=300)
    n.add_argument("--f-pre", type=float, default=rc.F_MIN)
    k = sub.add_parser("rank")
    k.add_argument("--f-pre", type=float, default=rc.F_MIN)
    k.add_argument("--f-min", type=float, default=rc.F_MIN)
    f = sub.add_parser("figures")
    f.add_argument("--top", type=int, default=12)
    f.add_argument("--verdicts", default="candidate,flagged")
    f.add_argument("--name", default="top_candidates")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    {"scan": cmd_scan, "nulls": cmd_nulls, "rank": cmd_rank, "figures": cmd_figures}[a.cmd](a)


if __name__ == "__main__":
    main()
