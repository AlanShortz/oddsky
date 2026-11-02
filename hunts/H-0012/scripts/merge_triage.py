"""H-0012 merge and triage: from per-tile runner outputs to a ranked review table.

    uv run python hunts/H-0012/scripts/merge_triage.py run ~/oddsky-runs/h0012p [--top 8] [--tns fetch|cache]
    uv run python hunts/H-0012/scripts/merge_triage.py tns-prefetch          # all target galaxies, paced

Input: a run directory laid out by infra/gcp/imaging_tile.py,
<run>/<tile>/{report.json, <galaxy>/candidates.csv, lightcurves.parquet, detections.parquet, cutouts.npz}.

1. **Merge.** Every galaxy is processed tile by tile, so a source in a tile overlap (or inside two
   galaxies' windows) appears more than once. Rows within 4" of each other that come from a different
   tile or a different galaxy are the same source. The row kept is the one with photometry from the
   tile where the source is furthest from the tile edge (pipeline.photometer's rule). The source goes
   to the galaxy whose centre is nearest in units of its radius (a26/2). Distances come from the
   UNGC target list, overridden by the TRGB/Cepheid distances in oddsky.imaging.galaxies where a
   galaxy is listed there (NGC 6946: 7.72 Mpc, not UNGC's 5.89).
2. **Luminosities.** The variable component's amplitude in each band (the peak above the 2010-11
   level for brightenings, the fade below it for fades and steps), unWISE Vega nanomaggies -> uJy
   -> nu L_nu in L_sun at the galaxy's distance (Jarrett et al. 2011 zero points and wavelengths).
   The pre-event level is the reference PSF flux plus the 2010-11 difference flux: in a crowded disk
   that includes blended neighbours, so it is an upper limit and the fade depth a lower limit.
3. **Triage.** (Rows of class 'no-photometry' -- a source outside its tile's photometry window -- normally
   merge with the neighbouring tile's measured row; any left over are counted as 'no-photometry'.)
   By the gate band's class: failed-SN-like (rise-then-fade, step-down, fading; a fade
   with no recovery is labelled fade-no-recovery), obscured transients (transient, brightening), and
   step-ups survive; lpv-like, irregular and season-locked are demoted; not-variable / no-data are
   quiet.
4. **Cross-matches** for survivors: Gaia DR3 within 2" (parallax / proper motion -> foreground star,
   DSC quasar probability, source_id kept as a string), AllWISE W1-W2 within 3" (IRSA TAP upload;
   W1-W2 >= 0.8 outside the galaxy (D25 ellipse where known, else a26/2) -> AGN colour), SIMBAD within 4" (simbad.harvard.edu TAP
   upload), and TNS. TNS is queried per galaxy (one cone over the galaxy, or over a few neighbouring
   galaxies at once) through the public search CSV, at most one request per 45 s across processes
   (a file lock), and an HTTP 429 or an HTML page is an ERROR, never "nothing found". TNS includes
   the historical (IAU CBAT) supernovae, e.g. SN 2008S and SN 1980K. A small local list adds the
   known failed-SN candidates (N6946-BH1, M31-2014-DS1). Every service records a status per
   candidate: a failed lookup reads "ERR ...", not "none".
5. **Scores** (both are products of factors, documented in fsn_score / obs_score):
   failed-SN score = fade significance x RSG luminosity window x fade depth x IR excess of the
   variable component x both-bands bonus x contaminant penalties; obscured-transient score = rise
   significance x peak luminosity x redness x no-optical-counterpart bonus x contaminant penalties.
   Known objects are flagged, not penalised, so they show where real events land.

v2 (2026-11-01; referee report reviews/claude-referee-triage-2026-11-01.md, section 4). The failed-SN score
is fsn_score (v2); the h0012a score is kept as fsn_score_v1 / rank_fsn_v1 for comparison. v2 adds a floor
on the lost W1 luminosity (a vanishing >= 3e4 L_sun photosphere loses >= ~4e3 L_sun in W1), a roughness
(zig-zag) penalty, drops the redness bonus and penalises a static AGN / dusty-AGB AllWISE colour anywhere,
and penalises SIMBAD high-proper-motion stars and a cutout-level moving-star dipole (oddsky.imaging.detect.
dipole_test). These were designed AFTER seeing BH1 at #65, so `inject` measures them honestly: synthetic
DS1-like and BH1-like fades injected into real light curves across galaxies, ranked against the real
failed-SN-like population under both scores. `known-list` writes the forced-photometry position list for
the runner (--known), and `run` reports the recall of every known transient from those forced light
curves (work/triage_<run>_recall.csv).

    uv run python hunts/H-0012/scripts/merge_triage.py known-list            # work/known_positions.csv (TNS cache)
    uv run python hunts/H-0012/scripts/merge_triage.py inject ~/oddsky-runs/h0012a --name h0012a_v2 [--n 400]

Outputs: hunts/H-0012/work/triage_<run>.csv (survivors, ranked), work/triage_<run>_summary.json
(counts by class, known objects and their ranks), work/triage_<run>_benchmarks.csv (every TNS SN / LRN /
ILRT / LBV / nova of 2009.5-2024.5 in a searched galaxy: found or not, class, rank), figures/triage_<run>_top.png (top N by each
score: W1 reference, W1/W2 difference at the event, W1/W2 light curves), and the merged table of all
candidates in <cache>/merged_<run>.parquet. Cross-match caches live in ~/oddsky-runs/h0012-xmatch
(override with ODDSKY_H0012_XMATCH).
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import io
import json
import logging
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd

from oddsky.imaging import F0_JY, crossmatch, detect, metrics
from oddsky.imaging.galaxies import GALAXIES, UNGC_NAMES

log = logging.getLogger("h0012.triage")
HERE = Path(__file__).resolve().parents[1]
TARGETS = HERE / "work" / "targets_10mpc.csv"
CACHE = Path(os.environ.get("ODDSKY_H0012_XMATCH", "~/oddsky-runs/h0012-xmatch")).expanduser()
UA = "oddsky/0.1 (+https://github.com/oddsky; open-source astronomy)"

MERGE_ARCSEC = 4.0
GAIA_ARCSEC = 2.0
ALLWISE_ARCSEC = 3.0
SIMBAD_ARCSEC = 4.0
KNOWN_ARCSEC = 4.0
TNS_PACE_S = 45.0
TNS_PAGE = 500

# Jarrett et al. 2011: isophotal wavelengths; F0 (Jy) in oddsky.imaging.F0_JY
LAMBDA_UM = {1: 3.368, 2: 4.618}
C_UM_HZ = 2.99792458e14
LSUN_W = 3.828e26
MPC_M = 3.0856775814913673e22
# nu L_nu(W1) / L_bol for a ~3500 K photosphere (blackbody); a crude red-supergiant bolometric
# correction (factor ~2), used only to place a source in the RSG luminosity window.
W1_TO_BOL = 1 / 0.14
RSG_LBOL = (1e4, 1e6)

# v2 score constants (referee report section 4)
L_FADE_FLOOR = 4e3  # L_sun: 0.14 x 3e4 L_sun, the least W1 light a vanishing RSG photosphere loses
L_FADE_DEX = 0.25
ROUGH_REF = 1.5  # sqrt(chi2_nu) about the 5-point running median; above it the light curve zig-zags (LPV)
# roughness error floor, as a fraction of the light curve's excursion. Chosen from {0 (the referee's), 0.05, 0.1}
# on the h0012a injection set (best overall top-30 recovery); validated on an independent draw (seed 13)
ROUGH_AMP_FLOOR = 0.05
AGN_STATIC_W1W2 = 0.8
PM_ARCSEC = 3.0
SIMBAD_PM_OTYPES = {"PM*", "HPM", "HPM*"}

FSN_CLASSES = ("rise-then-fade", "step-down", "fading")
OBS_CLASSES = ("transient", "brightening")
STEPUP_CLASSES = ("step-up",)
DEMOTED = ("lpv-like", "irregular", "season-locked")

# Known failed-SN candidates (not in TNS). Positions as in scripts/acceptance.py.
LOCAL_KNOWN = [
    ("N6946-BH1", 308.864833, 60.135636, "failed-SN candidate (Gerke+2015, Adams+2017)"),
    ("M31-2014-DS1", 11.306125, 41.542539, "failed-SN candidate (De+2024)"),
]
SIMBAD_TRANSIENT_OTYPES = {"SN*", "SN", "SN?", "ev", "No*", "No?", "LRN", "ILRT"}
# Mira / LPV / AGB / carbon / OH-IR / S stars, with SIMBAD's candidate spellings (red supergiants, s*r, are
# NOT here: they are what a failed supernova looks like beforehand)
SIMBAD_LPV_OTYPES = {"Mi*", "Mi?", "LP*", "LP?", "AB*", "AB?", "C*", "C?*", "C*?", "OH*", "OH?", "S*", "S?*", "S*?", "pA*", "pA?"}
SIMBAD_AGN_OTYPES = {"AGN", "AG?", "QSO", "Q?", "Sy1", "Sy2", "SyG", "Bla", "BLL", "Bz?", "LIN"}
SIMBAD_URL = "https://simbad.harvard.edu/simbad/sim-tap/sync"
IRSA_URL = "https://irsa.ipac.caltech.edu/TAP/sync"
TNS_URL = "https://www.wis-tns.org/search"


# ----------------------------------------------------------------------------------------------
# units


def nmgy_to_ujy(f, band: int):
    """unWISE Vega nanomaggies -> microjansky."""
    return np.asarray(f, float) * F0_JY[band] * 1e-3


def nu_lnu_lsun(ujy, band: int, dist_mpc):
    """nu L_nu in L_sun of a flux density (uJy) at dist_mpc."""
    nu = C_UM_HZ / LAMBDA_UM[band]
    d = np.asarray(dist_mpc, float) * MPC_M
    return 4 * np.pi * d**2 * nu * np.asarray(ujy, float) * 1e-32 / LSUN_W


def vega_colour(f1_nmgy, f2_nmgy):
    """W1 - W2 (Vega) of two Vega-nanomaggie fluxes; NaN unless both are positive."""
    f1, f2 = np.asarray(f1_nmgy, float), np.asarray(f2_nmgy, float)
    with np.errstate(all="ignore"):
        return np.where((f1 > 0) & (f2 > 0), -2.5 * np.log10(f1 / f2), np.nan)


def sep_arcsec(ra1, dec1, ra2, dec2):
    ra1, dec1, ra2, dec2 = map(lambda v: np.radians(np.asarray(v, float)), (ra1, dec1, ra2, dec2))
    s = np.sin((dec2 - dec1) / 2) ** 2 + np.cos(dec1) * np.cos(dec2) * np.sin((ra2 - ra1) / 2) ** 2
    return np.degrees(2 * np.arcsin(np.sqrt(np.clip(s, 0, 1)))) * 3600


def _xyz(ra, dec):
    ra, dec = np.radians(np.asarray(ra, float)), np.radians(np.asarray(dec, float))
    return np.c_[np.cos(dec) * np.cos(ra), np.cos(dec) * np.sin(ra), np.sin(dec)]


def pairs_within(ra, dec, r_arcsec):
    from scipy.spatial import cKDTree

    if len(ra) < 2:
        return np.zeros((0, 2), int)
    return cKDTree(_xyz(ra, dec)).query_pairs(2 * np.sin(np.radians(r_arcsec / 3600) / 2), output_type="ndarray")


# ----------------------------------------------------------------------------------------------
# targets


def load_targets(path: Path = TARGETS) -> pd.DataFrame:
    t = pd.read_csv(path)
    t = t[~t.separate_project.astype(bool)].copy()
    t["dist_mpc"] = t.Dist.astype(float)
    t["dist_source"] = "UNGC " + t.f_Dist.astype(str)
    for key, g in GALAXIES.items():  # TRGB/Cepheid distances adopted in the acceptance tests
        k = np.nonzero(t.Name.to_numpy() == UNGC_NAMES.get(key, ""))[0]
        if not k.size:
            s = sep_arcsec(t.ra, t.dec, g.ra, g.dec)
            k = [int(np.argmin(s))] if s.min() < 180 else []
        for kk in k:
            t.iloc[kk, t.columns.get_loc("dist_mpc")] = g.dist_mpc
            t.iloc[kk, t.columns.get_loc("dist_source")] = f"oddsky.imaging.galaxies ({g.name})"
    t["r_arcmin"] = t.a26.astype(float) / 2
    # the radius used for r_norm (galaxy assignment, the 'outside the galaxy' AGN-colour test): UNGC gives no
    # position angle, so a circle of radius a26/2; galaxies in oddsky.imaging.galaxies get their D25 ellipse
    # (M31's circle would otherwise take in a huge area off its b/a = 0.32 disk)
    t["ell_a"], t["ell_ba"], t["ell_pa"] = t.r_arcmin, 1.0, 0.0
    for key, g in GALAXIES.items():
        k = np.nonzero(t.Name.to_numpy() == UNGC_NAMES.get(key, ""))[0]
        if not k.size:
            s = sep_arcsec(t.ra, t.dec, g.ra, g.dec)
            k = [int(np.argmin(s))] if s.min() < 180 else []
        for kk in k:
            for c, v in (("ell_a", g.d25_arcmin / 2), ("ell_ba", g.ba), ("ell_pa", g.pa_deg)):
                t.iloc[kk, t.columns.get_loc(c)] = v
    t.index = pd.Index(t.Name.to_numpy())
    return t


# ----------------------------------------------------------------------------------------------
# loading and merging


def r_norm(ra, dec, tg: pd.DataFrame) -> np.ndarray:
    """Elliptical radius in units of the semi-major axis (ell_a, ell_ba, ell_pa per row of tg)."""
    ra, dec = np.asarray(ra, float), np.asarray(dec, float)
    dx = (((ra - tg.ra.to_numpy() + 180) % 360) - 180) * np.cos(np.radians(tg.dec.to_numpy())) * 60
    dy = (dec - tg.dec.to_numpy()) * 60
    pa = np.radians(tg.ell_pa.to_numpy(float))
    major = dx * np.sin(pa) + dy * np.cos(pa)
    minor = dx * np.cos(pa) - dy * np.sin(pa)
    a = tg.ell_a.to_numpy(float)
    return np.hypot(major / a, minor / (a * tg.ell_ba.to_numpy(float)))


def load_run(run_dir: Path) -> tuple[pd.DataFrame, dict]:
    """All candidates of all tiles and galaxies, with tile-edge distances. Returns (df, reports)."""
    from oddsky.imaging import tiles

    rows, reports = [], {}
    for rp in sorted(run_dir.glob("*/report.json")):
        tile = rp.parent.name
        rep = json.loads(rp.read_text())
        reports[tile] = rep
        w = None
        for gal in rep.get("galaxies", {}):
            p = rp.parent / gal / "candidates.csv"
            if not p.exists() or p.stat().st_size == 0:
                continue
            try:
                c = pd.read_csv(p)
            except pd.errors.EmptyDataError:
                continue
            if c.empty:
                continue
            w = w or tiles.wcs_for(tile)
            x, y = w.all_world2pix(c.ra.to_numpy(), c.dec.to_numpy(), 0)
            c.insert(0, "galaxy", gal)
            c.insert(1, "tile", tile)
            c.insert(0, "uid", [f"{gal}|{tile}|{g}" for g in c.group])
            c["edge_px"] = np.minimum.reduce([x, y, tiles.NPIX - 1 - x, tiles.NPIX - 1 - y])
            c["has_lc"] = c.get("w1_n", pd.Series(np.nan, index=c.index)).fillna(0) > 0
            rows.append(c)
    df = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    return df, reports


def merge_candidates(df: pd.DataFrame, targets: pd.DataFrame, r_arcsec: float = MERGE_ARCSEC) -> pd.DataFrame:
    """Same source = within r_arcsec AND from a different tile or a different galaxy (within one
    tile-galaxy the pipeline has already grouped at 4"). Keep the row with photometry from the tile
    where the source is furthest from the edge; assign the galaxy whose centre is nearest in units
    of its radius. Adds n_tiles, tiles_all, merged_uids, also_in, r_norm, dist_mpc."""
    if df.empty:
        return df
    df = df.reset_index(drop=True).copy()
    tg = targets.reindex(df.galaxy)
    df["r_norm"] = r_norm(df.ra, df.dec, tg)
    parent = np.arange(len(df))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    tile, gal = df.tile.to_numpy(), df.galaxy.to_numpy()
    for i, j in pairs_within(df.ra.to_numpy(), df.dec.to_numpy(), r_arcsec):
        if tile[i] != tile[j] or gal[i] != gal[j]:
            a, b = find(i), find(j)
            if a != b:
                parent[b] = a
    root = np.array([find(i) for i in range(len(df))])
    df["_root"] = root
    size = df.groupby("_root")._root.transform("size")
    keep = list(df.index[size == 1])
    extra = {}
    for _, g in df[size > 1].groupby("_root"):
        best_tile = g.sort_values(["has_lc", "edge_px"], ascending=False).tile.iloc[0]
        home_gal = g.sort_values("r_norm").galaxy.iloc[0]
        # within the best tile prefer the row from the home galaxy (same pixels, its window)
        cand = g[g.tile == best_tile]
        cand = cand.assign(_home=(cand.galaxy == home_gal)).sort_values(["_home", "has_lc"], ascending=False)
        k = cand.index[0]
        keep.append(k)
        others = g.drop(index=k)
        extra[k] = dict(n_tiles=g.tile.nunique(), tiles_all=",".join(sorted(set(g.tile))),
                        merged_uids=";".join(others.uid), assigned_galaxy=home_gal,
                        also_in=",".join(sorted(set(g.galaxy) - {home_gal})))
    out = df.loc[keep].copy()
    out["n_tiles"] = 1
    out["tiles_all"] = out.tile
    out["merged_uids"] = ""
    out["also_in"] = ""
    for k, e in extra.items():
        for c, v in e.items():
            if c == "assigned_galaxy":
                out.loc[k, "phot_galaxy"] = out.loc[k, "galaxy"]
                out.loc[k, "galaxy"] = v
            else:
                out.loc[k, c] = v
    out["phot_galaxy"] = out.get("phot_galaxy", pd.Series(index=out.index, dtype=object)).fillna(out.galaxy)
    tg = targets.reindex(out.galaxy)
    out["r_norm"] = r_norm(out.ra, out.dec, tg)
    out["dist_mpc"] = tg.dist_mpc.to_numpy()
    out["dist_source"] = tg.dist_source.to_numpy()
    return out.drop(columns="_root").reset_index(drop=True)


# ----------------------------------------------------------------------------------------------
# light-curve features and luminosities


def lc_features(lc: pd.DataFrame) -> dict:
    """Per band, from the season-aligned difference light curve (as pipeline.score aligns it):
    2010-11 baseline, peak above it, the final level, recovery after the minimum, the pre-event
    total flux (reference PSF flux + baseline), and the epoch of the largest excursion. nmgy."""
    out = {}
    for b in (1, 2):
        lb = lc[lc.band == b].sort_values("mjd")
        g = np.isfinite(lb.flux) & np.isfinite(lb.err) & (lb.err > 0)
        if g.sum() < 5:
            continue
        rf = lb.groupby("season").ref_flux.first().to_dict()
        f = metrics.align_seasons(lb.flux.to_numpy(), lb.season.to_numpy(), rf)[g.to_numpy()]
        e = lb.err.to_numpy()[g.to_numpy()]
        t = lb.mjd.to_numpy()[g.to_numpy()]
        ep = lb.epoch.to_numpy()[g.to_numpy()]
        w = 1 / e**2
        early = t < metrics.EARLY_MJD
        if early.sum() == 0:
            early = np.arange(f.size) < 2
        base = np.sum(w[early] * f[early]) / np.sum(w[early])
        sm = metrics.running_median(f, 3)
        late = np.arange(f.size) >= f.size - 3
        final = np.sum(w[late] * f[late]) / np.sum(w[late]) - base
        ipk, ilo = int(np.argmax(sm)), int(np.argmin(sm))
        fade = base - sm[ilo]
        ref_vals = [v for v in rf.values() if np.isfinite(v)]
        pre = (np.mean(ref_vals) if ref_vals else np.nan) + base
        iev = int(np.argmax(np.abs(sm - base)))
        med = float(np.median(f))
        # roughness: sqrt(chi2_nu) about the light curve's own 5-point running median (an LPV / AGB star
        # zig-zags about any smooth trend; DS1 and BH1 do not). Needs >= 8 epochs. The error gets a floor of
        # ROUGH_AMP_FLOOR x the light curve's excursion (range of its 3-point running median): an LPV's
        # season-to-season swings are a large fraction of its amplitude, a failed SN's wiggles a small one.
        # Without the floor the statistic grows with S/N: injected DS1-shaped fades at M31 scored 4-20 from
        # DS1's own ~5% wiggles (found by `inject`; the referee's version had no floor).
        amp = float(np.max(sm) - np.min(sm))
        e_r = np.hypot(e, ROUGH_AMP_FLOOR * amp)
        rough = float(np.sqrt(np.mean(((f - metrics.running_median(f, 5)) / e_r) ** 2))) if f.size >= 8 else np.nan
        out[b] = dict(base=base, rough=rough, peak_up=sm[ipk] - base, burst_up=sm[ipk] - med,
                      burst_sig=(sm[ipk] - med) / float(np.median(e)), t_peak=t[ipk], fade=fade, t_min=t[ilo], final=final,
                      recovery=(sm[-1] - sm[ilo]) / fade if fade > 0 and ilo < f.size - 1 else 0.0,
                      pre=pre, ev_epoch=int(ep[iev]), med_err=float(np.median(e)))
    return out


def add_features(df: pd.DataFrame, run_dir: Path, reclassify: bool = False) -> pd.DataFrame:
    """Light-curve features, amplitudes (uJy) and luminosities (L_sun) for every merged row. With
    `reclassify`, the classes are recomputed from the light curves with the current classifier (v2: the
    2011-13 gap-fade rule), as pipeline.score would; the runner's classes are kept as cls_run."""
    feats, classes = {}, {}
    for (tile, gal), g in df.groupby(["tile", "phot_galaxy"]):
        p = run_dir / tile / gal / "lightcurves.parquet"
        if not p.exists():
            continue
        lcs = pd.read_parquet(p)
        lcs = lcs[lcs.group.isin(set(g.group))]
        for gid, lc in lcs.groupby("group"):
            feats[(tile, gal, gid)] = lc_features(lc)
            if reclassify:
                rec = rescore_lc(None, lc)
                classes[(tile, gal, gid)] = {k: rec[k] for k in CLASS_KEYS}
    if reclassify:
        df["cls_run"] = df.cls
        for i, r in df.iterrows():
            c = classes.get((r.tile, r.phot_galaxy, r.group))
            if c:
                for k, v in c.items():
                    df.at[i, k] = v
        log.info("reclassified: %d of %d rows changed class", int((df.cls != df.cls_run).sum()), len(df))
    return amplitudes(assign_lc_features(df, {i: feats.get((r.tile, r.phot_galaxy, r.group), {}) for i, r in df.iterrows()}))


LC_KEYS = ("base", "rough", "peak_up", "burst_up", "burst_sig", "fade", "final", "recovery", "pre", "ev_epoch", "t_peak")


def assign_lc_features(df: pd.DataFrame, feats: dict) -> pd.DataFrame:
    """{row index: lc_features(...)} -> lc_w{b}_* columns."""
    cols = {f"lc_w{b}_{k}": {} for b in (1, 2) for k in LC_KEYS}
    for i in df.index:
        f = feats.get(i, {})
        for b in (1, 2):
            fb = f.get(b, {})
            for k in LC_KEYS:
                cols[f"lc_w{b}_{k}"][i] = fb.get(k, np.nan)
    for c, v in cols.items():
        df[c] = pd.Series(v, dtype=float)
    return df


def amplitudes(df: pd.DataFrame) -> pd.DataFrame:
    """Amplitudes (uJy), luminosities (L_sun), depths and colours from the metric and lc_* columns."""
    d = df.dist_mpc.to_numpy()
    for b in (1, 2):
        dl, dn = _col(df, f"w{b}_delta_late"), _col(df, f"w{b}_delta_neo")
        fade_nm = np.fmax(0, np.fmax(-np.asarray(dl, float), -np.asarray(dn, float)))  # robust (weighted means)
        # the brightening: above the 2010-11 level, or (a burst at any time, e.g. one already under way
        # in 2010) above the light curve's median
        up_nm = np.fmax(0, np.fmax(np.fmax(df[f"lc_w{b}_peak_up"].to_numpy(float), df[f"lc_w{b}_burst_up"].to_numpy(float)),
                                   np.fmax(np.asarray(dl, float), np.asarray(dn, float))))
        pre_nm = np.fmax(df[f"lc_w{b}_pre"].to_numpy(float), fade_nm)  # a star cannot lose more than it had
        df[f"fade_w{b}_nmgy"], df[f"up_w{b}_nmgy"], df[f"pre_w{b}_nmgy"] = fade_nm, up_nm, pre_nm
        df[f"fade_w{b}_ujy"] = nmgy_to_ujy(fade_nm, b)
        df[f"up_w{b}_ujy"] = nmgy_to_ujy(up_nm, b)
        df[f"L_fade_w{b}"] = nu_lnu_lsun(df[f"fade_w{b}_ujy"], b, d)
        df[f"L_up_w{b}"] = nu_lnu_lsun(df[f"up_w{b}_ujy"], b, d)
        df[f"L_pre_w{b}"] = nu_lnu_lsun(nmgy_to_ujy(pre_nm, b), b, d)
        with np.errstate(all="ignore"):
            df[f"depth_w{b}"] = np.where(pre_nm > 0, fade_nm / pre_nm, np.nan)
    df["Lbol_pre_est"] = df.L_pre_w1 * W1_TO_BOL
    df["colour_fade"] = vega_colour(df.fade_w1_nmgy, df.fade_w2_nmgy)
    df["colour_up"] = vega_colour(df.up_w1_nmgy, df.up_w2_nmgy)
    df["L_peak"] = np.fmax(df.L_up_w1, df.L_up_w2)
    df["rough_max"] = np.fmax(df.lc_w1_rough.to_numpy(float), df.lc_w2_rough.to_numpy(float))
    return df


# ----------------------------------------------------------------------------------------------
# triage classes


def triage_class(row) -> str:
    c = row.cls
    if c in FSN_CLASSES:
        return "failed-SN-like"
    if c in OBS_CLASSES:
        return "obscured-transient"
    if c in STEPUP_CLASSES:
        return "step-up"
    if c in DEMOTED:
        return "demoted"
    if c == "no-photometry":  # outside this tile's photometry window and not merged with a neighbouring tile's row
        return "no-photometry"
    return "quiet"


def fsn_shape(row) -> str:
    """Sub-label for failed-SN-like rows: a 'fading' source with < 30% recovery from its minimum
    in the gate band is a long monotonic fade with no recovery."""
    if row.cls != "fading":
        return row.cls if row.cls in FSN_CLASSES else ""
    rec = row.get(f"lc_w{int(row.gate_band)}_recovery", np.nan) if pd.notna(row.get("gate_band")) else np.nan
    return "fade-no-recovery" if np.nan_to_num(rec, nan=0.0) < 0.3 else "fading-recovering"


# ----------------------------------------------------------------------------------------------
# scores


def _lum_window(lbol, lo=RSG_LBOL[0], hi=RSG_LBOL[1], width_dex=0.5):
    """1 inside [lo, hi]; Gaussian fall-off in log L outside (sigma width_dex)."""
    with np.errstate(all="ignore"):
        ll = np.log10(np.asarray(lbol, float))
    dist = np.where(ll < np.log10(lo), np.log10(lo) - ll, np.where(ll > np.log10(hi), ll - np.log10(hi), 0.0))
    return np.where(np.isfinite(ll), np.exp(-0.5 * (dist / width_dex) ** 2), 0.0)


def _to_bool(s: pd.Series) -> pd.Series:
    """bool / 'True' / 'False' / NA (as stored in the caches) -> bool, NA -> False."""
    m = {True: True, False: False, "True": True, "False": False, "true": True, "false": False}
    return s.map(lambda v: m.get(v, False) if not (isinstance(v, float) and np.isnan(v)) and v is not pd.NA else False).astype(bool)


def _col(df: pd.DataFrame, col: str) -> np.ndarray:
    """A numeric column as float; missing -> NaN."""
    if col not in df:
        return np.full(len(df), np.nan)
    return pd.to_numeric(df[col], errors="coerce").to_numpy(float)


def _flag(df: pd.DataFrame, col: str) -> np.ndarray:
    """A boolean column as a numpy array; missing column or NA -> False."""
    if col not in df:
        return np.zeros(len(df), bool)
    return _to_bool(df[col]).to_numpy(bool)


def simbad_pm_near(df: pd.DataFrame, r_arcsec: float = PM_ARCSEC) -> np.ndarray:
    """A SIMBAD high-proper-motion star (PM*) within r_arcsec: the nearest object, or any listed in
    simbad_all ('MAIN_ID [otype] sep"; ...'), so a PM* that is not the nearest SIMBAD entry still counts."""
    import re

    out = np.zeros(len(df), bool)
    ot = df.simbad_otype.map(_str).to_numpy() if "simbad_otype" in df else np.full(len(df), "")
    sep = _col(df, "simbad_sep")
    allc = df.simbad_all.map(_str).to_numpy() if "simbad_all" in df else np.full(len(df), "")
    for i in range(len(df)):
        if ot[i] in SIMBAD_PM_OTYPES and np.nan_to_num(sep[i], nan=99) < r_arcsec:
            out[i] = True
            continue
        for o, d in re.findall(r"\[([^\]]*)\]\s*([0-9.]+)\"", allc[i]):
            if o in SIMBAD_PM_OTYPES and float(d) < r_arcsec:
                out[i] = True
                break
    return out


def contaminant_factor(df: pd.DataFrame, v2: bool = True) -> np.ndarray:
    f = np.ones(len(df))
    f *= np.where(_flag(df, "dipole"), 0.1, 1)
    f *= np.where(_flag(df, "gaia_foreground"), 0.02, 1)
    f *= np.where(_flag(df, "gaia_quasar"), 0.1, 1)
    f *= np.where(_flag(df, "agn_colour"), 0.1, 1)
    f *= np.where(_flag(df, "simbad_agn"), 0.1, 1)
    if "simbad_otype" in df:  # a catalogued AGB/carbon star: dust-cycle fades and brightenings are expected
        f *= np.where(df.simbad_otype.map(_str).isin(SIMBAD_LPV_OTYPES).to_numpy(), 0.3, 1)
    if v2:
        f *= np.where(simbad_pm_near(df), 0.02, 1)  # a moving foreground star the 2" Gaia match missed
        f *= np.where(_flag(df, "dipole_cutout") & ~_flag(df, "dipole"), 0.1, 1)  # the cutout-level dipole test
    return f


def _fsn_parts(df: pd.DataFrame):
    sig = []
    for b in (1, 2):
        dl = -_col(df, f"w{b}_delta_late_sig")
        dn = -_col(df, f"w{b}_delta_neo_sig")
        rtf = np.fmin(_col(df, f"w{b}_rise_sig"), _col(df, f"w{b}_fade_sig"))
        rtf = np.where(df.cls == "rise-then-fade", rtf, np.nan)
        sig.append(np.nanmax(np.c_[dl, dn, rtf], axis=1))
    S = np.clip(np.nan_to_num(np.nanmax(np.c_[sig[0], sig[1]], axis=1)), 0, 50)
    f_L = _lum_window(df.Lbol_pre_est)
    depth = np.nan_to_num(np.fmax(df.depth_w1.to_numpy(float), df.depth_w2.to_numpy(float)))
    f_depth = 0.3 + 0.7 * np.clip(depth / 0.5, 0, 1)
    both = (np.nan_to_num(sig[0]) >= 3) & (np.nan_to_num(sig[1]) >= 3)
    f_both = np.where(both, 1.5, 1.0)
    f_shape = np.where(df.fsn_shape == "fading-recovering", 0.5, 1.0)
    return S, f_L, f_depth, f_both, f_shape


def fsn_score_v1(df: pd.DataFrame) -> np.ndarray:
    """The h0012a failed-SN score (kept for comparison):

    S/5 x f_L x f_depth x f_IR x f_both x f_shape x contaminants, where
      S        largest fade significance in either band: -delta_late_sig, -delta_neo_sig, and for
               rise-then-fade min(rise_sig, fade_sig); capped at 50
      f_L      1 when the estimated pre-event L_bol (nu L_nu(W1) / 0.14) is in 1e4-1e6 L_sun,
               Gaussian in log L outside (sigma 0.5 dex)
      f_depth  0.3 + 0.7 min(depth / 0.5, 1): depth = fade / pre-event flux (best band); a fade to
               half the pre-event level or deeper gets full weight (depth is a lower limit in crowding)
      f_IR     1 + min(max(W1-W2 of the variable component, 0) / 0.5, 1): dust makes the
               changing light red (the rise for rise-then-fade, the lost light for fades)
      f_both   1.5 if both bands fade at >= 3 sigma (delta_late or delta_neo)
      f_shape  0.5 for a 'fading' source that recovers (>= 30% back from its minimum)
      contaminants: dipole 0.1, Gaia foreground 0.02, Gaia quasar 0.1, AGN colour 0.1, SIMBAD AGN 0.1,
               SIMBAD AGB/LPV/carbon star 0.3
    """
    S, f_L, f_depth, f_both, f_shape = _fsn_parts(df)
    col = np.where(df.cls == "rise-then-fade", df.colour_up, df.colour_fade)
    f_ir = 1 + np.clip(np.nan_to_num(col) / 0.5, 0, 1)
    s = S / 5 * f_L * f_depth * f_ir * f_both * f_shape * contaminant_factor(df, v2=False)
    return np.where(df.triage_class == "failed-SN-like", s, 0.0)


def soft_above(x, thr, dex=L_FADE_DEX):
    """Logistic in log10 x: 0.5 at thr, ~0.9 at +0.4 dex, ~0.1 at -0.4 dex."""
    with np.errstate(all="ignore"):
        z = (np.log10(np.asarray(x, float)) - np.log10(thr)) / dex
    return np.where(np.isfinite(z), 1 / (1 + np.exp(-2.2 * z)), 0.0)


def fsn_factors_v2(df: pd.DataFrame) -> dict:
    """The v2 factors that differ from v1 (each in [0, 1])."""
    f_lfade = soft_above(np.fmax(_col(df, "L_fade_w1"), 1e-3), L_FADE_FLOOR)
    rough = _col(df, "rough_max")
    f_rough = np.where(np.isfinite(rough), np.clip((ROUGH_REF / np.fmax(rough, 1e-3)) ** 2, 0, 1), 1.0)
    aw = _col(df, "allwise_w1w2")
    f_colour = np.where(aw >= AGN_STATIC_W1W2, 0.3, 1.0)
    return dict(f_lfade=f_lfade, f_rough=f_rough, f_colour=f_colour)


def fsn_score(df: pd.DataFrame) -> np.ndarray:
    """Failed-SN score v2, for failed-SN-like rows (0 otherwise):

    S/5 x f_L x f_depth x f_both x f_shape x f_Lfade x f_rough x f_colour x contaminants(v2), where S, f_L,
    f_depth, f_both, f_shape are as in fsn_score_v1 (no f_IR redness bonus: AGB stars and AGN are red too) and
      f_Lfade  logistic(log10 L_fade(W1); 4e3 L_sun, 0.25 dex): the lost W1 light must be what a >= 3e4
               L_sun photosphere emits there (0.14 x 3e4); at 0.8 Mpc a 2e3 L_sun AGB wobble is a 7 sigma fade
      f_rough  min(1, (1.5 / roughness)^2), roughness = sqrt(chi2_nu) about the 5-point running median in the
               rougher band, errors floored at 5% of the light curve's excursion: LPV zig-zag during and
               after the fade
      f_colour 0.3 if the static AllWISE W1-W2 >= 0.8 (AGN or dusty AGB colour), anywhere
      contaminants(v2) = v1's plus SIMBAD PM* within 3" (x 0.02) and the cutout dipole test (x 0.1)
    """
    S, f_L, f_depth, f_both, f_shape = _fsn_parts(df)
    v2 = fsn_factors_v2(df)
    s = S / 5 * f_L * f_depth * f_both * f_shape * v2["f_lfade"] * v2["f_rough"] * v2["f_colour"] * contaminant_factor(df)
    return np.where(df.triage_class == "failed-SN-like", s, 0.0)


def obs_score(df: pd.DataFrame) -> np.ndarray:
    """Obscured-transient score, for transient / brightening / rise-then-fade / step-up rows:

    S/5 x f_L x f_red x f_opt x contaminants, where
      S      largest brightening significance in either band: rise_sig, delta_late_sig,
             delta_neo_sig, burst_sig (peak of the smoothed light curve above its median, in median
             errors; this catches a burst already under way in 2010); capped at 100
      f_L    min(max((log10 L_peak - 3.5) / 2.5, 0.05), 1): L_peak = nu L_nu of the brightening,
             larger band; 1e6 L_sun or more gets full weight
      f_red  1 + min(max(W1-W2 of the rising light, 0) / 0.5, 1)
      f_opt  1.5 if there is no Gaia DR3 source within 2" and no known transient (the 'not in
             optical catalogues' case), else 1
      contaminants as in fsn_score
    """
    sig = []
    for b in (1, 2):
        cand = [_col(df, f"w{b}_{k}") for k in ("rise_sig", "delta_late_sig", "delta_neo_sig")]
        cand.append(df[f"lc_w{b}_burst_sig"].astype(float))
        s = np.nanmax(np.c_[tuple(cand)], axis=1)
        s = np.where(np.isfinite(s), s, _col(df, f"w{b}_amp_sig"))
        sig.append(s)
    S = np.clip(np.nan_to_num(np.nanmax(np.c_[sig[0], sig[1]], axis=1)), 0, 100)
    with np.errstate(all="ignore"):
        ll = np.log10(df.L_peak.to_numpy(float))
    f_L = np.clip(np.nan_to_num((ll - 3.5) / 2.5, nan=0.05), 0.05, 1)
    f_red = 1 + np.clip(np.nan_to_num(df.colour_up.to_numpy(float)) / 0.5, 0, 1)
    gst = df["gaia_status"] if "gaia_status" in df else pd.Series("", index=df.index)
    gid = df["gaia_id"] if "gaia_id" in df else pd.Series(pd.NA, index=df.index)
    no_gaia = (gst.astype(str) == "ok").to_numpy() & gid.isna().to_numpy()
    f_opt = np.where(no_gaia & ~_flag(df, "known"), 1.5, 1.0)
    s = S / 5 * f_L * f_red * f_opt * contaminant_factor(df)
    ok = df.triage_class.isin(["obscured-transient", "step-up"]) | (df.cls == "rise-then-fade")
    return np.where(ok, s, 0.0)


# ----------------------------------------------------------------------------------------------
# TNS (per galaxy cones, paced across processes)


def tns_cones(targets: pd.DataFrame, max_join_arcmin: float = 60.0, pad_arcmin: float = 0.5) -> list[dict]:
    """Group galaxies into TNS cones: a cone is centred on its largest galaxy and absorbs neighbours
    that fit wholly inside max(own radius, max_join_arcmin). Deterministic, so prefetch and triage
    share cache keys."""
    t = targets.assign(rr=targets.search_diam_arcmin.astype(float) / 2 + pad_arcmin).sort_values(
        ["rr", "Name"], ascending=[False, True])
    left = list(t.Name)
    cones = []
    while left:
        seed = t.loc[left[0]]
        lim = max(seed.rr, max_join_arcmin)
        s = sep_arcsec(seed.ra, seed.dec, t.loc[left].ra, t.loc[left].dec) / 60
        reach = s + t.loc[left].rr.to_numpy()
        mem = [n for n, ok in zip(left, reach <= lim, strict=True) if ok] or [seed.Name]
        r = float(max(seed.rr, max(rv for n, rv in zip(left, reach, strict=True) if n in mem)))
        cones.append(dict(key=f"tns_{seed.Name}", ra=float(seed.ra), dec=float(seed.dec), r_arcmin=round(r, 2),
                          members=mem))
        left = [n for n in left if n not in mem]
    return cones


@contextlib.contextmanager
def _tns_slot():
    """Hold the cross-process TNS lock and wait until TNS_PACE_S has passed since the last request."""
    d = CACHE / "tns"
    d.mkdir(parents=True, exist_ok=True)
    with open(d / ".lock", "a+") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            last_p = d / ".last"
            last = float(last_p.read_text()) if last_p.exists() else 0.0
            wait = last + TNS_PACE_S - time.time()
            if wait > 0:
                time.sleep(wait)
            yield
        finally:
            (d / ".last").write_text(str(time.time()))
            fcntl.flock(fh, fcntl.LOCK_UN)


def parse_tns_csv(text: str) -> pd.DataFrame:
    """Parse a TNS search CSV; RA/DEC sexagesimal -> degrees. Raises ValueError on HTML."""
    s = text.strip()
    if s.startswith("<"):
        raise ValueError("html response")
    if not s:
        return pd.DataFrame(columns=["Name", "ra", "dec", "Obj. Type", "Discovery Date (UT)"])
    d = pd.read_csv(io.StringIO(text), dtype=str).fillna("")
    if "Name" not in d or "RA" not in d:
        raise ValueError(f"unexpected TNS columns: {list(d.columns)[:5]}")
    import astropy.units as u
    from astropy.coordinates import SkyCoord

    if len(d):
        c = SkyCoord(d.RA.to_list(), d.DEC.to_list(), unit=(u.hourangle, u.deg))
        d["ra"], d["dec"] = c.ra.deg, c.dec.deg
    else:
        d["ra"], d["dec"] = [], []
    d["Name"] = d.Name.str.strip()
    return d


def tns_get(params: dict, get=None, max_429: int = 4) -> tuple[str | None, str]:
    """One paced TNS search request: (text, 'ok') or (None, 'ERR ...'). HTTP 429 waits Retry-After
    (>= 120 s) and retries; if it persists it is an error, never an empty result."""
    import httpx

    get = get or (lambda p: httpx.get(TNS_URL, params=p, headers={"User-Agent": UA}, timeout=90, follow_redirects=True))
    status = "ERR not tried"
    for _ in range(max_429 + 1):
        with _tns_slot():
            try:
                r = get(params)
            except Exception as e:  # noqa: BLE001
                status = f"ERR {type(e).__name__}: {str(e)[:80]}"
                continue
        if r.status_code == 429:
            status = "ERR HTTP 429"
            time.sleep(max(120.0, float(r.headers.get("Retry-After", 120) or 120)))
            continue
        if r.status_code != 200:
            return None, f"ERR HTTP {r.status_code}"
        if r.text.strip().startswith("<"):
            return None, "ERR html response"
        return r.text, "ok"
    return None, status


def tns_cone(cone: dict, fetch: bool = True, get=None) -> tuple[pd.DataFrame, str]:
    """All TNS objects in a cone (cached; paginated). Status 'ok', 'ERR ...' or 'not queried'."""
    d = CACHE / "tns"
    d.mkdir(parents=True, exist_ok=True)
    meta_p, csv_p = d / f"{cone['key']}.json", d / f"{cone['key']}.csv"

    def cached():
        if meta_p.exists():
            m = json.loads(meta_p.read_text())
            if m.get("status") == "ok" and csv_p.exists():
                return pd.read_csv(csv_p, dtype={"Name": str}), "ok"
        return None

    c = cached()
    if c is not None or not fetch:
        return c if c is not None else (pd.DataFrame(), "not queried")
    frames, status = [], "ok"
    for page in range(20):
        params = dict(ra=cone["ra"], decl=cone["dec"], radius=cone["r_arcmin"], coords_unit="arcmin", format="csv",
                      num_page=TNS_PAGE, page=page)
        text, st = tns_get(params, get=get)
        if st != "ok":
            status = st
            break
        try:
            p = parse_tns_csv(text)
        except ValueError as e:
            status = f"ERR {e}"
            break
        frames.append(p)
        if len(p) < TNS_PAGE:
            break
    else:
        status = "ERR too many pages"
    meta = dict(cone, status=status, fetched=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), url=TNS_URL)
    if status == "ok":
        out = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        keep = [c for c in ("ID", "Name", "ra", "dec", "Obj. Type", "Host Name", "Discovery Date (UT)",
                            "Discovery Mag/Flux", "Remarks") if c in out]
        out = out[keep] if len(out) else pd.DataFrame(columns=["Name", "ra", "dec"])
        out.to_csv(csv_p, index=False)
        meta["n"] = len(out)
        meta_p.write_text(json.dumps(meta, indent=1))
        return out, "ok"
    meta_p.write_text(json.dumps(meta, indent=1))
    return pd.DataFrame(), status


def tns_for_galaxies(galaxies, targets, fetch=True) -> dict:
    """{galaxy: (objects DataFrame, status)} using the shared cone layout."""
    cones = tns_cones(targets)
    by_gal = {g: c for c in cones for g in c["members"]}
    out, done = {}, {}
    for g in galaxies:
        c = by_gal.get(g)
        if c is None:
            out[g] = (pd.DataFrame(), "ERR galaxy not in target list")
            continue
        if c["key"] not in done:
            done[c["key"]] = tns_cone(c, fetch=fetch)
            log.info("TNS %s (%.1f'): %s, %d objects", c["key"], c["r_arcmin"], done[c["key"]][1], len(done[c["key"]][0]))
        out[g] = done[c["key"]]
    return out


def match_known(df: pd.DataFrame, tns: dict) -> pd.DataFrame:
    """TNS objects and the local known list within KNOWN_ARCSEC (nearest), per candidate."""
    names, seps, types, dates, status = [], [], [], [], []
    for _, r in df.iterrows():
        objs, st = tns.get(r.galaxy, (pd.DataFrame(), "not queried"))
        status.append(st)
        if st == "ok" and len(objs):
            s = sep_arcsec(r.ra, r.dec, objs.ra, objs.dec)
            k = int(np.argmin(s))
            if s[k] < KNOWN_ARCSEC:
                o = objs.iloc[k]
                names.append(str(o.Name))
                seps.append(float(s[k]))
                types.append(str(o.get("Obj. Type", "")))
                dates.append(str(o.get("Discovery Date (UT)", ""))[:10])
                continue
        names.append("")
        seps.append(np.nan)
        types.append("")
        dates.append("")
    df["tns_status"], df["tns_name"], df["tns_sep"], df["tns_type"], df["tns_disc"] = status, names, seps, types, dates
    loc = []
    for _, r in df.iterrows():
        hit = [n for n, a, d, _ in LOCAL_KNOWN if sep_arcsec(r.ra, r.dec, a, d) < KNOWN_ARCSEC]
        loc.append(hit[0] if hit else "")
    df["local_known"] = loc
    return df


# ----------------------------------------------------------------------------------------------
# Gaia, AllWISE, SIMBAD (cached per position)


def _pos_key(ra, dec) -> list[str]:
    return [f"{a:.5f}{d:+.5f}" for a, d in zip(ra, dec, strict=True)]


def _cached_service(name: str, df: pd.DataFrame, query, chunk: int) -> pd.DataFrame:
    """Run `query(sub_df) -> DataFrame[key, ...]` for positions not yet answered 'ok'; cache in
    CACHE/<name>.parquet. A failed chunk is recorded with status 'ERR ...'."""
    p = CACHE / f"{name}.parquet"
    cache = pd.read_parquet(p) if p.exists() else pd.DataFrame(columns=["key", "status"])
    keys = pd.Series(_pos_key(df.ra, df.dec), index=df.index)
    have = set(cache.key[cache.status == "ok"])
    todo = df[~keys.isin(have)].assign(key=keys[~keys.isin(have)]).drop_duplicates("key")
    new = []
    for i in range(0, len(todo), chunk):
        sub = todo.iloc[i:i + chunk]
        try:
            res = query(sub)
            res = sub[["key"]].merge(res, on="key", how="left").assign(status="ok")
        except Exception as e:  # noqa: BLE001
            log.warning("%s chunk %d failed: %s", name, i // chunk, e)
            res = sub[["key"]].assign(status=f"ERR {type(e).__name__}: {str(e)[:100]}")
        new.append(res)
        log.info("%s: %d/%d", name, min(i + chunk, len(todo)), len(todo))
    if new:
        cache = pd.concat([cache[~cache.key.isin(todo.key)]] + new, ignore_index=True)
        for c in cache.columns:
            if cache[c].dtype == object:
                cache[c] = cache[c].astype("string")
        CACHE.mkdir(parents=True, exist_ok=True)
        cache.to_parquet(p)
    out = pd.DataFrame({"key": keys}).merge(cache.drop_duplicates("key", keep="last"), on="key", how="left")
    out.index = df.index
    out["status"] = out.status.fillna("not queried")
    return out


def _gaia_query(sub: pd.DataFrame) -> pd.DataFrame:
    g = crossmatch.gaia_batch(sub.ra.to_numpy(), sub.dec.to_numpy(), r_arcsec=GAIA_ARCSEC)
    near = crossmatch.nearest(sub.assign(group=sub.key), g, r_arcsec=GAIA_ARCSEC).rename(columns={"group": "key"})
    near["n_gaia"] = near["n_gaia"].astype(int)
    if "gaia_id" in near:
        near["gaia_id"] = near.gaia_id.astype("string")
    return near


def _votable(sub: pd.DataFrame) -> bytes:
    """Upload table (cid, ra, dec); "key" is an ADQL reserved word."""
    rows = "".join(f"<TR><TD>{k}</TD><TD>{a:.7f}</TD><TD>{d:.7f}</TD></TR>"
                   for k, a, d in zip(sub.key, sub.ra, sub.dec, strict=True))
    return ('<?xml version="1.0"?><VOTABLE version="1.3" xmlns="http://www.ivoa.net/xml/VOTable/v1.3"><RESOURCE><TABLE>'
            '<FIELD name="cid" datatype="char" arraysize="*"/><FIELD name="ra" datatype="double"/>'
            '<FIELD name="dec" datatype="double"/><DATA><TABLEDATA>' + rows +
            "</TABLEDATA></DATA></TABLE></RESOURCE></VOTABLE>").encode()


def _tap_upload(url: str, query: str, sub: pd.DataFrame, upload_name: str = "t") -> pd.DataFrame:
    import httpx

    last = None
    for attempt in range(3):
        try:
            r = httpx.post(url, data=dict(REQUEST="doQuery", LANG="ADQL", FORMAT="csv", QUERY=query,
                                          UPLOAD=f"{upload_name},param:{upload_name}"),
                           files={upload_name: ("t.xml", _votable(sub), "application/x-votable+xml")},
                           headers={"User-Agent": UA}, timeout=300)
            if r.status_code != 200 or r.text.lstrip().startswith("<"):
                raise RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
            return pd.read_csv(io.StringIO(r.text), dtype={"cid": str}).rename(columns={"cid": "key"})
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(10 * (attempt + 1))
    raise RuntimeError(str(last)[:200])


def _allwise_query(sub: pd.DataFrame) -> pd.DataFrame:
    q = ("SELECT u.cid, a.designation, a.ra, a.dec, a.w1mpro, a.w2mpro, a.w1sigmpro, a.w2sigmpro, a.cc_flags, a.ext_flg "
         "FROM allwise_p3as_psd a, TAP_UPLOAD.t u "
         f"WHERE CONTAINS(POINT('ICRS', a.ra, a.dec), CIRCLE('ICRS', u.ra, u.dec, {ALLWISE_ARCSEC / 3600:.6f})) = 1")
    r = _tap_upload(IRSA_URL, q, sub)
    if r.empty:
        return pd.DataFrame(columns=["key"])
    pos = sub.set_index("key")
    r["sep"] = sep_arcsec(r.ra, r.dec, pos.loc[r.key].ra.to_numpy(), pos.loc[r.key].dec.to_numpy())
    r = r.sort_values("sep").drop_duplicates("key")
    r["w1w2"] = r.w1mpro - r.w2mpro
    return r.rename(columns={c: f"allwise_{c}" for c in r.columns if c != "key"})


def _simbad_query(sub: pd.DataFrame) -> pd.DataFrame:
    q = ("SELECT u.cid, b.main_id, b.otype, b.ra, b.dec, b.nbref FROM basic AS b, TAP_UPLOAD.t AS u "
         f"WHERE CONTAINS(POINT('ICRS', b.ra, b.dec), CIRCLE('ICRS', u.ra, u.dec, {SIMBAD_ARCSEC / 3600:.6f})) = 1")
    r = _tap_upload(SIMBAD_URL, q, sub)
    if r.empty:
        return pd.DataFrame(columns=["key"])
    pos = sub.set_index("key")
    r["sep"] = sep_arcsec(r.ra, r.dec, pos.loc[r.key].ra.to_numpy(), pos.loc[r.key].dec.to_numpy())
    r = r.sort_values("sep")
    agg = r.groupby("key").agg(
        simbad_id=("main_id", "first"), simbad_otype=("otype", "first"), simbad_sep=("sep", "first"),
        simbad_nbref=("nbref", "first"), simbad_n=("main_id", "size"),
        simbad_all=("main_id", lambda s: "; ".join(
            f"{m} [{o}] {d:.1f}\"" for m, o, d in zip(s, r.loc[s.index, "otype"], r.loc[s.index, "sep"], strict=True))),
    ).reset_index()
    tr = r[r.otype.isin(SIMBAD_TRANSIENT_OTYPES) | r.main_id.str.match(r"^(SN|AT) \d{4}")]
    tr = tr.groupby("key").main_id.first().rename("simbad_transient").reset_index()
    return agg.merge(tr, on="key", how="left")


def crossmatch_all(df: pd.DataFrame, use_net: bool = True) -> pd.DataFrame:
    if not use_net or df.empty:
        for s in ("gaia", "allwise", "simbad"):
            df[f"{s}_status"] = "not queried"
        return df
    g = _cached_service("gaia_dr3_2as", df, _gaia_query, chunk=100)
    df["gaia_status"] = g.status
    for c in ("gaia_id", "gaia_sep", "G", "bp_rp", "plx_snr", "pm_snr", "var_flag", "p_quasar", "n_gaia"):
        v = g[c] if c in g else pd.Series(np.nan, index=df.index)
        if c not in ("gaia_id", "var_flag"):
            v = pd.to_numeric(v, errors="coerce")
        df[c if c.startswith("gaia") or c == "n_gaia" else f"gaia_{c}"] = v
    df["gaia_id"] = df.gaia_id.astype("string")
    df["gaia_foreground"] = _to_bool(g["foreground"]) if "foreground" in g else False
    df["gaia_quasar"] = _to_bool(g["quasar"]) if "quasar" in g else False
    a = _cached_service("allwise_3as", df, _allwise_query, chunk=500)
    df["allwise_status"] = a.status
    for c in ("allwise_designation", "allwise_sep", "allwise_w1mpro", "allwise_w2mpro", "allwise_w1w2", "allwise_cc_flags",
              "allwise_ext_flg"):
        v = a[c] if c in a else pd.Series(np.nan, index=df.index)
        df[c] = v if c in ("allwise_designation", "allwise_cc_flags") else pd.to_numeric(v, errors="coerce")
    w1w2 = pd.to_numeric(df.allwise_w1w2, errors="coerce")
    df["agn_colour"] = (w1w2 >= crossmatch.AGN_W1W2) & (df.r_norm > 1.0)
    s = _cached_service("simbad_4as", df, _simbad_query, chunk=500)
    df["simbad_status"] = s.status
    for c in ("simbad_id", "simbad_otype", "simbad_sep", "simbad_nbref", "simbad_n", "simbad_all", "simbad_transient"):
        v = s[c] if c in s else pd.Series(np.nan, index=df.index)
        df[c] = pd.to_numeric(v, errors="coerce") if c in ("simbad_sep", "simbad_nbref", "simbad_n") else v
    df["simbad_agn"] = df.simbad_otype.isin(SIMBAD_AGN_OTYPES)
    return df


def _str(v) -> str:
    """'' for None / NaN / NA, else str(v)."""
    if v is None or v is pd.NA or (isinstance(v, float) and np.isnan(v)):
        return ""
    return str(v)


def identify(df: pd.DataFrame) -> pd.DataFrame:
    """'known' flag and a one-phrase 'what' per row, most specific first."""
    for c in ("simbad_transient", "simbad_id", "simbad_otype", "gaia_id"):
        if c not in df:
            df[c] = ""
    df["known_name"] = [next((x for x in (_str(a), _str(b), _str(c)) if x), "")
                        for a, b, c in zip(df.local_known, df.tns_name, df.simbad_transient, strict=True)]
    df["known"] = df.known_name != ""
    fg, qso, sagn, agn, dip = (_flag(df, c) for c in ("gaia_foreground", "gaia_quasar", "simbad_agn", "agn_colour", "dipole"))
    dcut = _flag(df, "dipole_cutout")
    pmn = simbad_pm_near(df)
    local_desc = {n: d for n, _, _, d in LOCAL_KNOWN}
    what = []
    for k, (_, r) in enumerate(df.iterrows()):
        ot, sid = _str(r.simbad_otype), _str(r.simbad_id)
        if _str(r.local_known):
            w = f"known: {r.local_known} ({local_desc[r.local_known]})"
        elif _str(r.tns_name):
            w = f"known transient: {r.tns_name}" + (f" ({r.tns_type})" if _str(r.tns_type) and r.tns_type != "nan" else "") + (
                f", disc {r.tns_disc}" if _str(r.tns_disc) else "")
        elif _str(r.simbad_transient):
            w = f"known transient (SIMBAD): {r.simbad_transient}"
        elif fg[k]:
            w = f"foreground star (Gaia {r.gaia_id}, plx/err {r.get('gaia_plx_snr', np.nan):.1f}, pm/err {r.get('gaia_pm_snr', np.nan):.1f})"
        elif qso[k] or sagn[k] or agn[k]:
            why = [x for x, f in (("Gaia P(QSO)>0.5", qso[k]), (f"SIMBAD {sid} [{ot}]", sagn[k]),
                                  (f"AllWISE W1-W2 {r.get('allwise_w1w2', np.nan):.2f} outside a26/2", agn[k])) if f]
            w = "AGN / background quasar (" + ", ".join(why) + ")"
        elif dip[k]:
            w = "moving foreground star (dipole)"
        elif pmn[k]:
            w = f"moving foreground star (SIMBAD PM* within {PM_ARCSEC:.0f}\")"
        elif dcut[k]:
            w = "moving foreground star (cutout dipole test)"
        elif ot in SIMBAD_LPV_OTYPES:
            w = f"known LPV/AGB (SIMBAD {sid} [{ot}])"
        elif r.cls == "lpv-like":
            w = "LPV (light curve)"
        elif sid:
            w = f"unknown (SIMBAD nearest: {sid} [{ot}] {r.simbad_sep:.1f}\")"
        else:
            w = "unknown"
        what.append(w)
    df["what"] = what
    return df


# ----------------------------------------------------------------------------------------------
# v2: cutout-level moving-star dipole test


def cutout_dipoles(df: pd.DataFrame, run_dir: Path, rows=None) -> pd.DataFrame:
    """detect.dipole_test on the late-minus-2010 difference cutout (per season, averaged; _event_image
    'fade') in W1 and W2 for every row with a cutout. Adds dipole_dchi2, dipole_balance, dipole_sep_px
    (the band with the larger dchi2) and dipole_cutout (either band flagged)."""
    for c, v in (("dipole_dchi2", np.nan), ("dipole_balance", np.nan), ("dipole_sep_px", np.nan), ("dipole_cutout", False)):
        df[c] = v
    idx = df.index if rows is None else rows
    cache = {}
    for i in idx:
        r = df.loc[i]
        key = (r.tile, r.phot_galaxy)
        if key not in cache:
            d = run_dir / r.tile / r.phot_galaxy
            z = np.load(d / "cutouts.npz") if (d / "cutouts.npz").exists() else None
            lc = pd.read_parquet(d / "lightcurves.parquet") if (d / "lightcurves.parquet").exists() else pd.DataFrame()
            cache = {key: (z, lc)}  # one galaxy-tile at a time (rows are processed grouped)
        z, lcs = cache[key]
        if z is None or not len(lcs):
            continue
        lc = lcs[lcs.group == r.group]
        best = None
        for band, fw in ((1, 2.3), (2, 2.6)):
            k = f"{r.group}_w{band}_diff"
            if k not in z.files:
                continue
            lb = lc[lc.band == band].sort_values("epoch")
            im = _event_image(np.asarray(z[k]), lb.epoch.tolist(), lb.mjd.tolist(), lb.season.tolist(), "fade", None)
            if im is None:
                continue
            t = detect.dipole_test(im, fwhm_px=fw)
            if best is None or np.nan_to_num(t["dchi2"], nan=-1) > np.nan_to_num(best["dchi2"], nan=-1):
                best = t
            if t["dipole"]:
                df.loc[i, "dipole_cutout"] = True
        if best is not None:
            df.loc[i, ["dipole_dchi2", "dipole_balance", "dipole_sep_px"]] = [best["dchi2"], best["balance"], best["sep_px"]]
    df["dipole_cutout"] = df.dipole_cutout.astype(bool)
    return df


# ----------------------------------------------------------------------------------------------
# v2: known positions (the runner's --known list) and the recall report

KNOWN_POSITIONS = HERE / "work" / "known_positions.csv"


def known_positions(targets: pd.DataFrame, tns: dict) -> pd.DataFrame:
    """Every TNS SN / LRN / ILRT / LBV / nova of 2009.5-2024.5 inside a target's search circle (the
    benchmark selection), plus the local known list, one row per (object, galaxy). The runner force-
    photometers all of them whatever the masks say."""
    rows = []
    for g, (objs, st) in tns.items():
        if st != "ok" or objs.empty or g not in targets.index:
            continue
        tg = targets.loc[g]
        typ = objs.get("Obj. Type", pd.Series("", index=objs.index)).fillna("").astype(str)
        disc = pd.to_datetime(objs.get("Discovery Date (UT)", pd.Series("", index=objs.index)), errors="coerce")
        yr = disc.dt.year + disc.dt.dayofyear / 365.25
        inside = sep_arcsec(tg.ra, tg.dec, objs.ra, objs.dec) / 60 <= float(tg.search_diam_arcmin) / 2
        sel = objs[inside & typ.str.startswith(BENCH_TYPES) & (yr >= 2009.5) & (yr <= 2024.5)]
        for _, o in sel.iterrows():
            rows.append(dict(name=str(o.Name), type=str(o.get("Obj. Type", "")), disc=str(o.get("Discovery Date (UT)", ""))[:10],
                             galaxy=g, ra=float(o.ra), dec=float(o.dec), source="TNS"))
    for n, a, d, desc in LOCAL_KNOWN:
        s = sep_arcsec(a, d, targets.ra, targets.dec) / 60 / (targets.search_diam_arcmin.astype(float) / 2)
        g = targets.index[int(np.argmin(s))]
        rows.append(dict(name=n, type=desc, disc="", galaxy=g, ra=a, dec=d, source="local"))
    return pd.DataFrame(rows).drop_duplicates(["name", "galaxy"]).reset_index(drop=True)


def recall_table(run_dir: Path, bench: pd.DataFrame | None = None, merged: pd.DataFrame | None = None) -> pd.DataFrame:
    """Per known object: the forced light curve from the tile where it sits furthest from the window
    edge (forced_known.parquet, written by the v2 runner), summarised by pipeline.recall_summary, the mask
    at its position, and whether the blind search found it (bench 'found', if given)."""
    from oddsky.imaging.pipeline import recall_summary

    parts = []
    for p in sorted(run_dir.glob("*/*/forced_known.parquet")):
        f = pd.read_parquet(p)
        f["phot_galaxy"] = p.parent.name
        parts.append(f)
    if not parts:
        return pd.DataFrame()
    fk = pd.concat(parts, ignore_index=True)
    rows = []
    for name, g in fk.groupby("name"):
        best = g.sort_values("edge_px", ascending=False).iloc[0]
        lc = g[(g.tile == best.tile) & (g.phot_galaxy == best.phot_galaxy)]
        disc = pd.to_datetime(str(best.disc), errors="coerce")
        dm = (disc - pd.Timestamp("1858-11-17")) / pd.Timedelta(days=1) if pd.notna(disc) else None
        rs = recall_summary(lc, dm)
        rec = dict(name=name, type=best.type, disc=best.disc, galaxy=best.phot_galaxy, tile=best.tile, mask=best["mask"],
                   mask_code=int(best.mask_code))
        for b in (1, 2):
            for k, v in rs.get(b, {}).items():
                rec[f"w{b}_{k}"] = v
        sig = [rs.get(b, {}).get("max_sig", np.nan) for b in (1, 2)]
        rec["max_sig"] = float(np.nanmax(np.abs(sig))) if np.isfinite(sig).any() else np.nan
        rec["forced_pass"] = bool(any(rs.get(b, {}).get("n_sig", 0) >= 2 and rs.get(b, {}).get("both_seasons", False) for b in (1, 2)))
        rows.append(rec)
    out = pd.DataFrame(rows)
    if bench is not None and len(bench) and "found" in bench:
        out = out.merge(bench[["name", "found", "cls", "triage", "rank_obs", "rank_fsn"]].drop_duplicates("name"), on="name", how="left")
    if merged is not None and len(merged) and "local_known" in merged:  # the local known list is not in the TNS benchmarks
        lk = merged[merged.local_known.astype(str) != ""].drop_duplicates("local_known").set_index("local_known")
        for c in ("found", "cls", "triage", "rank_obs", "rank_fsn"):
            if c not in out:
                out[c] = np.nan
        out["found"] = out["found"].astype(object)
        for i, nm in out.name.items():
            if nm in lk.index:
                r = lk.loc[nm]
                out.loc[i, ["found", "cls", "triage", "rank_obs", "rank_fsn"]] = [True, r.cls, r.triage_class, r.rank_obs, r.rank_fsn]
    return out


# ----------------------------------------------------------------------------------------------
# v2: injection-recovery of synthetic failed-SN fades into real light curves

YEAR0_MJD = 51544.5  # 2000.0
# De et al. 2024 (Science 386; github repo photometry.csv): NEOWISE W1/W2 of M31-2014-DS1, mJy
DS1_YR = np.array([2010.04, 2010.55, 2011.04, 2014.04, 2014.56, 2015.04, 2015.55, 2016.03, 2016.56, 2017.01, 2017.55, 2018.0,
                   2018.55, 2018.99, 2019.55, 2020.0, 2020.55, 2020.99, 2021.55, 2021.99])
DS1_W1 = np.array([0.979, 1.034, 0.967, 0.984, 1.095, 1.051, 1.16, 1.1, 1.345, 1.514, 1.435, 0.849, 0.787, 0.568, 0.645, 0.422,
                   0.442, 0.302, 0.355, 0.221])
DS1_W2 = np.array([1.014, 1.081, 0.922, 0.943, 0.996, 1.132, 1.064, 1.122, 1.252, 1.441, 1.246, 0.73, 0.613, 0.587, 0.52, 0.502,
                   0.399, 0.435, 0.371, 0.338])
# W2/W1 of the progenitor in Vega nanomaggies: DS1 2010-11 (1.006 mJy / 0.993 mJy) -> 1.83; BH1's lost light
# (W2 -0.06, W1 -0.045 mJy in this pipeline's forced photometry) -> 2.4
W2_OVER_W1 = {"DS1": 1.83, "BH1": 2.4}


def template(kind: str, t_yr: np.ndarray, t0: float) -> dict:
    """Flux in units of the pre-event level per band. DS1: De et al.'s light curve (smoothed by a 3-point
    running median), shifted so that its peak (2017.0) falls at t0, the decline continued beyond the last
    published epoch with the e-folding time of its last two years. BH1: flat, then from t0 an exponential
    fade (e-folding 1.5 yr) to 10% of the pre-event level (N6946-BH1's ~90% mid-IR loss over 2010-2016)."""
    out = {}
    for b in (1, 2):
        if kind == "DS1":
            y = metrics.running_median((DS1_W1 if b == 1 else DS1_W2) / np.mean((DS1_W1 if b == 1 else DS1_W2)[:3]), 3)
            tt = DS1_YR + (t0 - 2017.0)
            tau = 2.0 / np.log(y[-5] / y[-1]) if y[-1] < y[-5] else 5.0
            f = np.interp(t_yr, tt, y, left=1.0, right=np.nan)
            late = t_yr > tt[-1]
            f[late] = y[-1] * np.exp(-(t_yr[late] - tt[-1]) / tau)
        else:
            f = np.where(t_yr < t0, 1.0, 0.1 + 0.9 * np.exp(-(t_yr - t0) / 1.5))
        out[b] = f
    return out


def inject_lc(lc: pd.DataFrame, kind: str, t0: float, f_pre_w1: float) -> pd.DataFrame:
    """Add a synthetic star (pre-event W1 flux f_pre_w1 nmgy) to a real long-format light curve: the
    per-season reference takes the season's median of the star's flux (as diff.references would), the
    difference fluxes the rest."""
    lc = lc.copy()
    t = 2000 + (lc.mjd.to_numpy(float) - YEAR0_MJD) / 365.25
    shp = template(kind, t, t0)
    for b in (1, 2):
        m = (lc.band == b).to_numpy()
        F = f_pre_w1 * (1.0 if b == 1 else W2_OVER_W1[kind]) * shp[b][m]
        seas = lc.season.to_numpy()[m]
        ref = np.zeros_like(F)
        for s_ in np.unique(seas):
            k = seas == s_
            ref[k] = np.median(F[k])
        lc.loc[m, "flux"] = lc.flux.to_numpy(float)[m] + F - ref
        lc.loc[m, "ref_flux"] = lc.ref_flux.to_numpy(float)[m] + ref
    return lc


CLASS_KEYS = ("cls", "ds1_score", "cls_w1", "cls_w2", "gate_band", "band_agree", "ds1_score_w1", "ds1_score_w2")


def rescore_lc(row: pd.Series, lc: pd.DataFrame, gap_fade: bool = True) -> dict:
    """pipeline.score's per-band metrics and classes for one light curve (gap_fade=False: the h0012a
    classifier, without the 2011-13 gap-fade rule), plus the h0012a classes as v1_<key>."""
    m = {}
    for b in (1, 2):
        lb = lc[lc.band == b].sort_values("mjd")
        rf = lb.groupby("season").ref_flux.first().to_dict()
        f_al = metrics.align_seasons(lb.flux.to_numpy(), lb.season.to_numpy(), rf)
        m[b] = metrics.band_metrics(lb.mjd.to_numpy(), f_al, lb.err.to_numpy(), lb.season.to_numpy())
        m[b]["ref_flux"] = float(np.nanmedian(lb.ref_flux)) if len(lb) else np.nan
    rec = dict(metrics.classify_bands(m[1], m[2], gap_fade=gap_fade))
    rec.update({f"v1_{k}": v for k, v in metrics.classify_bands(m[1], m[2], gap_fade=False).items()})
    for b in (1, 2):
        for k, v in m[b].items():
            rec[f"w{b}_{k}"] = v
    return rec


CLEAN_XMATCH = dict(gaia_foreground=False, gaia_quasar=False, agn_colour=False, simbad_agn=False, simbad_otype="",
                    simbad_all="", simbad_sep=np.nan, allwise_w1w2=np.nan, dipole=False, dipole_cutout=False, known=False)


def injection_recovery(merged: pd.DataFrame, run_dir: Path, n_hosts: int = 200, seed: int = 12,
                       lw1_grid=(4e3, 1e4, 2.5e4, 6e4)) -> pd.DataFrame:
    """Inject DS1-like and BH1-like fades (pre-event W1 nu L_nu in lw1_grid, i.e. L_bol ~ 3e4-4e5 L_sun with
    the photospheric correction) into the real light curves of random candidates (galaxies drawn
    uniformly, then a random candidate) and rank each against the real failed-SN-like population under
    the v1 and v2 scores. Host pools: 'quiet' (not-variable candidates: real positions, noise and
    crowding) and 'any' (any candidate with photometry). Cross-match flags: 'clean' (a vanished RSG has
    no AGN colour, no proper motion) and 'inherit' (the host's, a pessimistic bound). Onset epochs are
    drawn uniformly: DS1 peak 2012.5-2020, BH1 fade start 2010.8-2019."""
    rng = np.random.default_rng(seed)
    pop = merged[merged.triage_class == "failed-SN-like"]
    P1 = np.sort(pop.fsn_score_v1.to_numpy(float))
    P2 = np.sort(pop.fsn_score.to_numpy(float))
    pop_uid = dict(zip(pop.uid, zip(pop.fsn_score_v1, pop.fsn_score, strict=True), strict=True))
    base = merged[merged.has_lc.astype(bool)]
    pools = {"quiet": base[(base.triage_class == "quiet") & (base.cls == "not-variable")], "any": base}
    plan = []
    for pool, cand in pools.items():
        gals = cand.galaxy.value_counts()
        gals = gals[gals >= 3].index.to_numpy()
        for _ in range(n_hosts):
            g = rng.choice(gals)
            plan.append((pool, cand[cand.galaxy == g].sample(1, random_state=int(rng.integers(1 << 31))).index[0]))
    lc_cache: dict = {}
    rows = []
    for pool, idx in plan:
        host = merged.loc[idx]
        key = (host.tile, host.phot_galaxy)
        if key not in lc_cache:
            lc_cache.clear()
            lc_cache[key] = pd.read_parquet(run_dir / host.tile / host.phot_galaxy / "lightcurves.parquet")
        lc0 = lc_cache[key]
        lc0 = lc0[lc0.group == host.group]
        if lc0.empty:
            continue
        f_unit = nu_lnu_lsun(nmgy_to_ujy(1.0, 1), 1, host.dist_mpc)  # L_sun per nmgy (W1)
        for kind in ("DS1", "BH1"):
            t0 = rng.uniform(2012.5, 2020.0) if kind == "DS1" else rng.uniform(2010.8, 2019.0)
            for lw1 in lw1_grid:
                lc = inject_lc(lc0, kind, t0, lw1 / f_unit)
                rec = rescore_lc(host, lc)
                for xm in ("clean", "inherit"):
                    r = host.copy()
                    for k, v in rec.items():
                        r[k] = v
                    if xm == "clean":
                        for k, v in CLEAN_XMATCH.items():
                            r[k] = v
                    r["dipole"] = False if xm == "clean" else r.get("dipole", False)
                    r["_lc_feats"] = lc_features(lc)
                    r["inj_kind"], r["inj_t0"], r["inj_Lw1"], r["inj_pool"], r["inj_xmatch"] = kind, t0, lw1, pool, xm
                    r["inj_host_uid"] = host.uid
                    rows.append(r)
    inj = pd.DataFrame(rows).reset_index(drop=True)
    inj = assign_lc_features(inj, dict(zip(inj.index, inj._lc_feats, strict=True))).drop(columns="_lc_feats")
    inj = amplitudes(inj)
    # v2 classifier (with the gap-fade rule) + v2 score
    inj["triage_class"] = inj.apply(triage_class, axis=1)
    inj["fsn_shape"] = inj.apply(fsn_shape, axis=1)
    inj["fsn_score"] = fsn_score(inj)
    # the h0012a pipeline: v1 classifier + v1 score; and v1 classifier + v2 score (the score change alone)
    v1 = inj.copy()
    for k in CLASS_KEYS:
        v1[k] = inj[f"v1_{k}"]
    v1["triage_class"] = v1.apply(triage_class, axis=1)
    v1["fsn_shape"] = v1.apply(fsn_shape, axis=1)
    inj["cls_v1"], inj["triage_class_v1"] = v1.cls, v1.triage_class
    inj["fsn_score_v1"] = fsn_score_v1(v1)
    inj["fsn_score_v2_v1cls"] = fsn_score(v1)

    def rank(scores, P, k):
        out = []
        for sc, host in zip(scores, inj.inj_host_uid, strict=True):
            if not sc > 0:
                out.append(np.inf)
                continue
            above = len(P) - np.searchsorted(P, sc, side="right")
            h = pop_uid.get(host)  # leave the host itself out of the population it is ranked against
            if h is not None and h[k] > sc:
                above -= 1
            out.append(float(above + 1))
        return out

    inj["inj_rank_v1"] = rank(inj.fsn_score_v1, P1, 0)
    inj["inj_rank_v2"] = rank(inj.fsn_score, P2, 1)
    inj["inj_rank_v2score_v1cls"] = rank(inj.fsn_score_v2_v1cls, P2, 1)
    return inj


def injection_summary(inj: pd.DataFrame) -> dict:
    def stats(g):
        out = {"n": int(len(g)), "classed_failed_SN_v2": float((g.triage_class == "failed-SN-like").mean()),
               "classed_failed_SN_v1": float((g.triage_class_v1 == "failed-SN-like").mean())}
        for v in ("v1", "v2score_v1cls", "v2"):
            rk = g[f"inj_rank_{v}"].to_numpy(float)
            out[v] = dict(median_rank=float(np.median(rk)) if np.isfinite(np.median(rk)) else None,
                          top10=float((rk <= 10).mean()), top30=float((rk <= 30).mean()), top100=float((rk <= 100).mean()))
        return out

    res = {"all": stats(inj)}
    for keys in (["inj_xmatch", "inj_pool"], ["inj_xmatch", "inj_kind"], ["inj_xmatch", "inj_kind", "inj_Lw1"]):
        for k, g in inj.groupby(keys):
            res[" / ".join(str(x) for x in k)] = stats(g)
    db = pd.cut(inj.dist_mpc, [0, 2, 5, 8, 11], labels=["<2", "2-5", "5-8", "8-11"])
    for (xm, d), g in inj.groupby([inj.inj_xmatch, db], observed=True):
        res[f"{xm} / dist {d} Mpc"] = stats(g)
    return res


# ----------------------------------------------------------------------------------------------
# gallery


def _event_image(diff: np.ndarray, epochs: list, mjd: list, season: list, mode: str, ev_epoch) -> np.ndarray | None:
    """'fade': per season, mean(last 3 epochs of the season) - mean(2010-11 epochs of the season),
    averaged; 'peak': the event epoch minus the 2010-11 mean of its own season."""
    mjd, season, epochs = np.asarray(mjd), np.asarray(season), np.asarray(epochs)
    early = mjd < metrics.EARLY_MJD
    if mode == "fade":
        ims = []
        for s in np.unique(season):
            ss = np.nonzero(season == s)[0]
            e, l_ = ss[early[ss]], ss[-3:] if ss.size >= 3 else ss
            if e.size and l_.size:
                ims.append(diff[l_].mean(0) - diff[e].mean(0))
        return np.mean(ims, 0) if ims else None
    k = np.nonzero(epochs == ev_epoch)[0]
    if not k.size:
        return None
    k = int(k[0])
    e = np.nonzero(early & (season == season[k]))[0]
    return diff[k] - (diff[e].mean(0) if e.size else 0)


def gallery(sel: pd.DataFrame, run_dir: Path, out_png: Path, title: str):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.gridspec import GridSpec

    W1C, W2C, INK, MUTED, GRID = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#e4e3df"
    n = len(sel)
    if n == 0:
        return
    H = 2.2 * n + 1.0
    fig = plt.figure(figsize=(15, H))
    gs = GridSpec(n, 4, figure=fig, width_ratios=[1, 1, 1, 3.6], wspace=0.08, hspace=0.85,
                  left=0.03, right=0.985, top=1 - 1.0 / H, bottom=0.3 / H)
    fig.text(0.03, 1 - 0.3 / H, title, ha="left", va="top", fontsize=12, color=INK)
    fig.text(0.03, 1 - 0.55 / H, "Cutouts 41 x 41 px (113\"), candidate at the green cross. Difference images: red = brighter, "
             "blue = fainter, symmetric scale;\n'(late-2010)' = last three epochs minus 2010-11 per season, '(event)' = the "
             "largest excursion minus 2010-11. Light curves: season-aligned forced PSF photometry.",
             ha="left", va="top", fontsize=8, color=MUTED)
    cache = {}
    for i, (_, r) in enumerate(sel.iterrows()):
        d = run_dir / r.tile / r.phot_galaxy
        if (r.tile, r.phot_galaxy) not in cache:
            z = np.load(d / "cutouts.npz") if (d / "cutouts.npz").exists() else {}
            lc = pd.read_parquet(d / "lightcurves.parquet") if (d / "lightcurves.parquet").exists() else pd.DataFrame()
            cache[(r.tile, r.phot_galaxy)] = (z, lc)
        z, lcs = cache[(r.tile, r.phot_galaxy)]
        lc = lcs[lcs.group == r.group] if len(lcs) else lcs
        mode = "fade" if r.cls in ("step-down", "fading") else "peak"
        gate = int(r.gate_band) if pd.notna(r.get("gate_band")) else 1
        panels = [(f"{r.group}_w1_ref", None, "W1 reference"), (f"{r.group}_w1_diff", 1, "W1 diff"),
                  (f"{r.group}_w2_diff", 2, "W2 diff")]
        for j, (key, band, lab) in enumerate(panels):
            ax = fig.add_subplot(gs[i, j])
            ax.set_xticks([]), ax.set_yticks([])
            for s in ax.spines.values():
                s.set_color(GRID)
            im = None
            if key in getattr(z, "files", []):
                arr = np.asarray(z[key])
                if band is None:
                    im = arr
                elif len(lc):
                    lb = lc[lc.band == band].sort_values("epoch")
                    im = _event_image(arr, lb.epoch.tolist(), lb.mjd.tolist(), lb.season.tolist(), mode,
                                      r.get(f"lc_w{gate}_ev_epoch"))
            if im is None:
                ax.text(0.5, 0.5, "no cutout", ha="center", va="center", fontsize=7, color=MUTED, transform=ax.transAxes)
            else:
                if band is None:
                    lo, hi = np.nanpercentile(im, [1, 99.5])
                else:
                    m = max(float(np.nanmax(np.abs(im[14:27, 14:27]))), 1e-6)
                    lo, hi = -m, m
                ax.imshow(im, origin="lower", cmap="gray_r" if band is None else "RdBu_r", vmin=lo, vmax=hi,
                          interpolation="nearest")
                ax.plot([20], [20], marker="+", ms=10, mew=0.8, color="#1f9e5a")
            ax.set_title(lab + ("" if band is None else (" (late-2010)" if mode == "fade" else " (event)")),
                         fontsize=7, color=MUTED, pad=2)
        ax = fig.add_subplot(gs[i, 3])
        for band, col in ((1, W1C), (2, W2C)):
            lb = lc[lc.band == band].sort_values("mjd") if len(lc) else lc
            if not len(lb):
                continue
            rf = lb.groupby("season").ref_flux.first().to_dict()
            f = metrics.align_seasons(lb.flux.to_numpy(), lb.season.to_numpy(), rf)
            base = r.get(f"lc_w{band}_base", 0.0)
            yr = 2000 + (lb.mjd.to_numpy() - 51544.5) / 365.25
            ax.errorbar(yr, nmgy_to_ujy(f - np.nan_to_num(base), band), yerr=nmgy_to_ujy(lb.err, band), fmt="o-", ms=3.2,
                        lw=1.0, elinewidth=0.7, color=col, label=f"W{band}", mec="white", mew=0.4)
        ax.axhline(0, color=MUTED, lw=0.6, ls=":")
        ax.grid(True, color=GRID, lw=0.5)
        ax.tick_params(labelsize=7, colors=MUTED)
        for s in ax.spines.values():
            s.set_color(GRID)
        ax.set_ylabel("change since 2010-11 (µJy)", fontsize=7, color=MUTED)
        if i == 0:
            ax.legend(fontsize=7, frameon=False, loc="upper right", ncol=2)
        tag = f"#{int(r.rank_fsn)} failed-SN" if r.sel_kind == "fsn" else f"#{int(r.rank_obs)} obscured"
        lum = (f"L_pre,bol≈{r.Lbol_pre_est:.1e}  depth≥{np.nanmax([r.depth_w1, r.depth_w2]):.2f}" if r.sel_kind == "fsn"
               else f"νLν,peak {r.L_peak:.1e} L☉  W1−W2(var) {r.colour_up:.2f}")
        ax.set_title(f"{tag} · {r.galaxy} ({r.dist_mpc:.2f} Mpc) · {r.ra:.5f} {r.dec:+.5f} · {r.cls} (W1 {r.cls_w1}, W2 {r.cls_w2})"
                     f" · {lum}\n{r.what[:150]}", fontsize=7.5, color=INK, loc="left", pad=3)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=110)
    plt.close(fig)


# ----------------------------------------------------------------------------------------------
# driver


BENCH_TYPES = ("SN", "LRN", "ILRT", "LBV", "Nova")


def benchmarks(df: pd.DataFrame, tns: dict, targets: pd.DataFrame, run_galaxies) -> pd.DataFrame:
    """Every TNS supernova / LRN / ILRT / LBV outburst / nova discovered 2009.5-2024.5 inside a searched
    galaxy's region (circle of radius search_diam/2), with the nearest merged candidate of ANY class within
    KNOWN_ARCSEC: was it found, how was it classed, and where does it rank? The 2009.5 start keeps events
    still bright in the 2010 epochs; the 2024.5 end is the last NEOWISE epoch."""
    rows = []
    seen = set()
    for g in run_galaxies:
        objs, st = tns.get(g, (pd.DataFrame(), "not queried"))
        if st != "ok" or objs.empty or g not in targets.index:
            continue
        tg = targets.loc[g]
        typ = objs.get("Obj. Type", pd.Series("", index=objs.index)).fillna("").astype(str)
        disc = pd.to_datetime(objs.get("Discovery Date (UT)", pd.Series("", index=objs.index)), errors="coerce")
        yr = disc.dt.year + disc.dt.dayofyear / 365.25
        inside = sep_arcsec(tg.ra, tg.dec, objs.ra, objs.dec) / 60 <= float(tg.search_diam_arcmin) / 2
        sel = objs[inside & typ.str.startswith(BENCH_TYPES) & (yr >= 2009.5) & (yr <= 2024.5)]
        for _, o in sel.iterrows():
            if o.Name in seen:
                continue
            seen.add(o.Name)
            sp = sep_arcsec(o.ra, o.dec, df.ra.to_numpy(), df.dec.to_numpy())
            k = int(np.argmin(sp)) if len(sp) else -1
            rec = dict(name=o.Name, type=o.get("Obj. Type", ""), disc=str(o.get("Discovery Date (UT)", ""))[:10],
                       galaxy=g, dist_mpc=float(tg.dist_mpc), ra=float(o.ra), dec=float(o.dec))
            if k >= 0 and sp[k] < KNOWN_ARCSEC:
                r = df.iloc[k]
                rec.update(found=True, sep=float(sp[k]), uid=r.uid, cls=r.cls, cls_w1=r.cls_w1, cls_w2=r.cls_w2,
                           triage=r.triage_class, var_sig=float(r.var_sig) if pd.notna(r.var_sig) else np.nan,
                           L_peak=float(r.L_peak) if pd.notna(r.L_peak) else np.nan,
                           rank_obs=r.rank_obs, rank_fsn=r.rank_fsn)
            else:
                rec.update(found=False, sep=float(sp[k]) if k >= 0 else np.nan)
            rows.append(rec)
    return pd.DataFrame(rows)


TABLE_COLS = [
    "rank_fsn", "rank_obs", "rank_fsn_v1", "fsn_score", "obs_score", "fsn_score_v1", "triage_class", "fsn_shape", "what",
    "known", "known_name", "low_confidence", "mask_code", "rough_max", "lc_w1_rough", "lc_w2_rough", "dipole_cutout",
    "dipole_dchi2", "dipole_balance",
    "uid", "galaxy", "dist_mpc", "dist_source", "ra", "dec", "r_norm", "tile", "n_tiles", "tiles_all", "also_in", "merged_uids",
    "edge_px", "channel", "cls", "cls_w1", "cls_w2", "gate_band", "band_agree", "var_sig", "ds1_score", "dipole",
    "w1_delta_neo_sig", "w2_delta_neo_sig", "w1_delta_late_sig", "w2_delta_late_sig", "w1_rise_sig", "w2_rise_sig",
    "up_w1_ujy", "up_w2_ujy", "fade_w1_ujy", "fade_w2_ujy", "L_up_w1", "L_up_w2", "L_peak", "L_fade_w1", "L_fade_w2",
    "L_pre_w1", "L_pre_w2", "Lbol_pre_est", "depth_w1", "depth_w2", "colour_up", "colour_fade",
    "lc_w1_recovery", "lc_w2_recovery", "lc_w1_t_peak",
    "tns_status", "tns_name", "tns_type", "tns_disc", "tns_sep", "local_known",
    "gaia_status", "gaia_id", "gaia_sep", "gaia_G", "gaia_bp_rp", "gaia_plx_snr", "gaia_pm_snr", "gaia_p_quasar",
    "gaia_var_flag", "gaia_foreground", "gaia_quasar", "allwise_status", "allwise_designation", "allwise_sep",
    "allwise_w1mpro", "allwise_w2mpro", "allwise_w1w2", "agn_colour", "simbad_status", "simbad_id", "simbad_otype",
    "simbad_sep", "simbad_nbref", "simbad_transient", "simbad_all",
]


def run(run_dir: Path, top: int = 8, tns_mode: str = "fetch", use_net: bool = True, name: str | None = None,
        reclassify: bool = False) -> dict:
    name = name or run_dir.name
    targets = load_targets()
    raw, reports = load_run(run_dir)
    log.info("%s: %d tiles, %d candidate rows", name, len(reports), len(raw))
    df = merge_candidates(raw, targets)
    log.info("merged: %d -> %d", len(raw), len(df))
    df = add_features(df, run_dir, reclassify=reclassify)
    df["triage_class"] = df.apply(triage_class, axis=1)
    df["fsn_shape"] = df.apply(fsn_shape, axis=1)
    surv = df.triage_class.isin(["failed-SN-like", "obscured-transient", "step-up"])
    tns = tns_for_galaxies(sorted(set(df.galaxy)), targets, fetch=(tns_mode == "fetch" and use_net)) \
        if use_net or tns_mode == "cache" else {}
    df = match_known(df, tns)
    s = crossmatch_all(df[surv].copy(), use_net=use_net)
    df = df.join(s[[c for c in s.columns if c not in df.columns]], how="left")
    for c in ("gaia_status", "allwise_status", "simbad_status"):
        df[c] = df[c].fillna("not queried (not a survivor)")
    surv_idx = df.index[surv]
    df = cutout_dipoles(df, run_dir, rows=df.loc[surv_idx].sort_values(["tile", "phot_galaxy"]).index)
    df = identify(df)
    df["fsn_score_v1"] = fsn_score_v1(df)
    df["fsn_score"] = fsn_score(df)
    df["obs_score"] = obs_score(df)
    for k in ("fsn", "fsn_v1", "obs"):
        sc = df[f"{k.replace('_v1', '')}_score_v1" if k == "fsn_v1" else f"{k}_score"]
        df[f"rank_{k}"] = sc.where(sc > 0).rank(ascending=False, method="first")
    CACHE.mkdir(parents=True, exist_ok=True)
    allc = df.copy()
    for c in allc.columns:
        if allc[c].dtype == object:
            allc[c] = allc[c].astype("string")
    allc.to_parquet(CACHE / f"merged_{name}.parquet")
    tab = df[surv].copy()
    tab = tab.sort_values(["fsn_score", "obs_score"], ascending=False)
    cols = [c for c in TABLE_COLS if c in tab.columns]
    out_csv = HERE / "work" / f"triage_{name}.csv"
    tab[cols].to_csv(out_csv, index=False, float_format="%.6g")
    sel = pd.concat([tab[tab.rank_fsn <= top].sort_values("rank_fsn").assign(sel_kind="fsn"),
                     tab[tab.rank_obs <= top].sort_values("rank_obs").assign(sel_kind="obs")])
    gallery(sel, run_dir, HERE / "figures" / f"triage_{name}_top.png",
            f"H-0012 triage, run {name}: top {top} by failed-SN score, then top {top} by obscured-transient score")
    known_rows = df[df.known].sort_values(["galaxy", "known_name"])
    bench = benchmarks(df, tns, targets, sorted(set(df.galaxy)))
    rec = recall_table(run_dir, bench, df)
    if len(rec):
        rec.to_csv(HERE / "work" / f"triage_{name}_recall.csv", index=False, float_format="%.6g")
        bench = bench.merge(rec[["name", "max_sig", "forced_pass", "mask"]].rename(
            columns={"max_sig": "forced_max_sig", "forced_pass": "forced_pass", "mask": "mask_at_position"}), on="name", how="left")
    bench.to_csv(HERE / "work" / f"triage_{name}_benchmarks.csv", index=False, float_format="%.6g")
    summary = dict(
        run=name, run_dir=str(run_dir), n_tiles=len(reports), n_galaxies=int(df.galaxy.nunique()),
        n_candidate_rows=len(raw), n_merged=len(df),
        n_reclassified=int((df.cls != df.cls_run).sum()) if "cls_run" in df else None, n_multi_tile=int((df.n_tiles > 1).sum()),
        n_cross_galaxy=int((df.also_in.astype(str) != "").sum()),
        classes=df.cls.value_counts().to_dict(), triage=df.triage_class.value_counts().to_dict(),
        fsn_shapes=df[df.triage_class == "failed-SN-like"].fsn_shape.value_counts().to_dict(),
        survivors_what=tab.what.str.replace(r"\s*\(.*$", "", regex=True).str.replace(r":.*$", "", regex=True).value_counts().to_dict(),
        status={c: df.loc[surv, c].str.split(":").str[0].value_counts().to_dict()
                for c in ("tns_status", "gaia_status", "allwise_status", "simbad_status")},
        recall=dict(n_known=int(len(rec)), n_forced_pass=int(rec.forced_pass.sum()) if len(rec) else 0,
                    n_found_blind=int(rec.found.fillna(False).astype(bool).sum()) if len(rec) and "found" in rec else 0,
                    forced_pass_not_found=rec[rec.forced_pass & ~rec.get("found", pd.Series(False, index=rec.index)).fillna(False).astype(bool)][
                        ["name", "type", "galaxy", "max_sig", "mask"]].to_dict("records") if len(rec) else []),
        known=[dict(name=r.known_name, galaxy=r.galaxy, uid=r.uid, sep=float(np.nanmin([r.tns_sep, 0.0 if r.local_known else np.nan,
                                                                                       r.get("simbad_sep", np.nan)])),
                    cls=r.cls, triage=r.triage_class, rank_fsn=None if pd.isna(r.rank_fsn) else int(r.rank_fsn),
                    rank_obs=None if pd.isna(r.rank_obs) else int(r.rank_obs),
                    rank_fsn_v1=None if pd.isna(r.rank_fsn_v1) else int(r.rank_fsn_v1), fsn_score=float(r.fsn_score),
                    obs_score=float(r.obs_score)) for _, r in known_rows.iterrows()],
        n_fsn_ranked=int(df.rank_fsn.notna().sum()), n_obs_ranked=int(df.rank_obs.notna().sum()),
        benchmarks=bench.to_dict("records"),
        tns_galaxies_not_queried=sorted(g for g, (_, st) in tns.items() if st != "ok"),
        per_galaxy=df.groupby("galaxy").agg(n=("uid", "size"), fsn=("triage_class", lambda s: int((s == "failed-SN-like").sum())),
                                            obs=("triage_class", lambda s: int((s == "obscured-transient").sum())),
                                            stepup=("triage_class", lambda s: int((s == "step-up").sum()))).to_dict("index"),
    )
    (HERE / "work" / f"triage_{name}_summary.json").write_text(json.dumps(summary, indent=1, default=str))
    log.info("wrote %s (%d survivors) and the gallery", out_csv, len(tab))
    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("run_dir")
    r.add_argument("--top", type=int, default=8)
    r.add_argument("--tns", choices=["fetch", "cache"], default="fetch",
                   help="fetch: query TNS for galaxies not yet cached (45 s each); cache: use only the cache")
    r.add_argument("--offline", action="store_true", help="no network at all (no TNS/Gaia/AllWISE/SIMBAD)")
    r.add_argument("--name")
    r.add_argument("--reclassify", action="store_true", help="recompute classes from the light curves (v2 classifier)")
    p = sub.add_parser("tns-prefetch")
    p.add_argument("--galaxies", nargs="*")
    sub.add_parser("known-list", help="work/known_positions.csv for the runner's --known (TNS cache + local list)")
    j = sub.add_parser("inject", help="injection-recovery: v1 vs v2 failed-SN score")
    j.add_argument("run_dir")
    j.add_argument("--name", required=True, help="merged table <cache>/merged_<name>.parquet from a v2 `run`")
    j.add_argument("--n", type=int, default=200, help="hosts per pool")
    j.add_argument("--seed", type=int, default=12)
    for sp in (r, j):
        sp.add_argument("--rough-floor", type=float, help=f"roughness error floor (fraction of the excursion; default {ROUGH_AMP_FLOOR})")
    a = ap.parse_args()
    if getattr(a, "rough_floor", None) is not None:
        globals()["ROUGH_AMP_FLOOR"] = a.rough_floor
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    if a.cmd == "known-list":
        t = load_targets()
        tns = tns_for_galaxies(list(t.index), t, fetch=False)
        kp = known_positions(t, tns)
        kp.to_csv(KNOWN_POSITIONS, index=False, float_format="%.7f")
        print(f"wrote {KNOWN_POSITIONS}: {len(kp)} positions in {kp.galaxy.nunique()} galaxies; "
              f"TNS not cached for {sum(st != 'ok' for _, st in tns.values())} galaxies")
        return
    if a.cmd == "inject":
        m = pd.read_parquet(CACHE / f"merged_{a.name}.parquet")
        inj = injection_recovery(m, Path(a.run_dir).expanduser(), n_hosts=a.n, seed=a.seed)
        cols = ["inj_kind", "inj_t0", "inj_Lw1", "inj_pool", "inj_xmatch", "inj_host_uid", "galaxy", "dist_mpc", "cls", "triage_class",
                "cls_v1", "triage_class_v1", "fsn_shape", "L_fade_w1", "Lbol_pre_est", "rough_max", "fsn_score_v1", "fsn_score_v2_v1cls",
                "fsn_score", "inj_rank_v1", "inj_rank_v2score_v1cls", "inj_rank_v2"]
        inj[cols].to_csv(HERE / "work" / f"injection_{a.name}.csv", index=False, float_format="%.5g")
        summ = injection_summary(inj)
        summ["population"] = dict(n_failed_SN_like=int((m.triage_class == "failed-SN-like").sum()),
                                  n_scored_v1=int((m.fsn_score_v1 > 0).sum()), n_scored_v2=int((m.fsn_score > 0).sum()))
        (HERE / "work" / f"injection_{a.name}.json").write_text(json.dumps(summ, indent=1, default=str))
        print(json.dumps({k: v for k, v in summ.items() if k.count("/") <= 1}, indent=1, default=str))
        return
    if a.cmd == "run":
        s = run(Path(a.run_dir).expanduser(), a.top, a.tns, not a.offline, a.name, a.reclassify)
        print(json.dumps({k: s[k] for k in ("run", "n_tiles", "n_galaxies", "n_candidate_rows", "n_merged", "classes",
                                            "triage", "status", "known")}, indent=1, default=str))
    else:
        t = load_targets()
        cones = tns_cones(t)
        if a.galaxies:
            cones = [c for c in cones if set(c["members"]) & set(a.galaxies)]
        log.info("%d TNS cones for %d galaxies", len(cones), sum(len(c["members"]) for c in cones))
        for i, c in enumerate(cones):
            objs, st = tns_cone(c)
            log.info("[%d/%d] %s r=%.1f' members=%d: %s, %d objects", i + 1, len(cones), c["key"], c["r_arcmin"],
                     len(c["members"]), st, len(objs))


if __name__ == "__main__":
    main()
