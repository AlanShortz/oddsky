"""What the release itself says about our targets, and which of its lenses nobody else reported.

  lens_catalogue     the release's vari_microlensing with positions (DR3: 363 rows; DR4: 1,360)
  classifier_only    classifier MICROLENSING sources missing from vari_microlensing (H-0010's question, any release;
                     DR3 must give 254 and 67, H-0010's acceptance test)
  target_flags       has_epoch_photometry / phot_variable_flag for our ids ("absent" epoch photometry is explained, not an error)
  target_classes     the classifier's best class for our ids
  idmap              DR3 -> release ids from the neighbourhood table: nearest within 0.5" and |dG| <= 0.3 (the ensemble's rule,
                     dr4_ensemble.md 2.5 item 4), else the DR3 id unchanged
  cones              Gaia sources within 4" of strong NEOWISE events that had none in DR3
  crossmatch         per target: catalogued as a lens by this release? in the reference lens lists? And the release's lenses
                     that are in none of our lists and no survey's: candidates for NEOWISE follow-up
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .config import Release

GAIA_T0_MJD = 55197.0  # vari_microlensing tmax is BJD(TCB) - 2455197.5


def lens_catalogue(arc, rel: Release) -> pd.DataFrame:
    q = (f"SELECT m.*, s.ra AS ra_, s.dec AS dec_, s.phot_g_mean_mag AS g_mean FROM {rel.table('vari_microlensing')} AS m "
         f"LEFT JOIN {rel.table('gaia_source')} AS s ON s.source_id = m.source_id")
    d = arc.tap(q)
    if len(d):
        d = d.rename(columns={"ra_": "ra", "dec_": "dec"})
        if "paczynski0_tmax" in d:
            d["tmax_mjd"] = d.paczynski0_tmax.astype(float) + GAIA_T0_MJD
        if "paczynski0_te" in d:
            d["tE"] = d.paczynski0_te.astype(float)
    return d


def classifier_only(arc, rel: Release) -> pd.DataFrame:
    cls, score = rel.classifier_cols
    q = (f"SELECT c.source_id, c.{score} AS score, m.source_id AS in_cat FROM {rel.table('vari_classifier_result')} AS c "
         f"LEFT JOIN {rel.table('vari_microlensing')} AS m ON m.source_id = c.source_id "
         f"WHERE c.{cls} = '{rel.microlensing_class}'")
    d = arc.tap(q)
    if len(d):
        d["in_vari_microlensing"] = d.in_cat.notna()
        d = d.drop(columns="in_cat")
    return d


def target_flags(arc, rel: Release, ids: list[str]) -> pd.DataFrame:
    cols = "source_id, has_epoch_photometry, phot_variable_flag"
    return arc.tap_in(f"SELECT {cols} FROM {rel.flags_table} WHERE source_id IN ({{ids}})", ids)


def target_classes(arc, rel: Release, ids: list[str]) -> pd.DataFrame:
    cls, score = rel.classifier_cols
    return arc.tap_in(f"SELECT source_id, {cls} AS best_class, {score} AS best_score FROM "
                      f"{rel.table('vari_classifier_result')} WHERE source_id IN ({{ids}})", ids)


def idmap_rule(nb: pd.DataFrame, ids: list[str], max_mas: float = 500.0, max_dg: float = 0.3) -> pd.DataFrame:
    """nb: old_id, new_id, dist_mas, dmag rows from the neighbourhood table. Nearest within max_mas and |dmag| <= max_dg."""
    out = []
    for s in ids:
        c = nb[nb.old_id == s] if len(nb) else nb
        ok = c[(c.dist_mas.astype(float) <= max_mas) & (c.dmag.astype(float).abs() <= max_dg)] if len(c) else c
        if len(ok):
            b = ok.loc[ok.dist_mas.astype(float).idxmin()]
            out.append(dict(dr3_source_id=s, new_source_id=str(b.new_id), dist_mas=float(b.dist_mas), dmag=float(b.dmag),
                            n_candidates=len(c), rule="nearest within 0.5\" and 0.3 mag"))
        else:
            out.append(dict(dr3_source_id=s, new_source_id=s, dist_mas=np.nan, dmag=np.nan, n_candidates=len(c),
                            rule="no neighbourhood match: DR3 id used as is"))
    return pd.DataFrame(out)


def idmap(arc, rel: Release, ids: list[str]) -> pd.DataFrame:
    tab, old, new, dist, dmag = rel.neighbourhood
    nb = arc.tap_in(f"SELECT {old} AS old_id, {new} AS new_id, {dist} AS dist_mas, {dmag} AS dmag FROM {tab} "
                    f"WHERE {old} IN ({{ids}})", ids)
    if len(nb):
        nb["old_id"], nb["new_id"] = nb.old_id.astype(str), nb.new_id.astype(str)
    return idmap_rule(nb, ids)


def cones(arc, rel: Release, rows: pd.DataFrame, radius_arcsec: float = 4.0) -> pd.DataFrame:
    out = []
    for r in rows.itertuples():
        if not np.isfinite(r.ra):
            continue
        q = (f"SELECT source_id, ra, dec, phot_g_mean_mag, bp_rp, DISTANCE(POINT({r.ra},{r.dec}), POINT(ra, dec))*3600 AS sep "
             f"FROM {rel.table('gaia_source')} WHERE 1 = CONTAINS(POINT(ra, dec), CIRCLE({r.ra}, {r.dec}, {radius_arcsec / 3600}))")
        try:
            d = arc.tap(q, sync=True)
        except Exception as e:  # noqa: BLE001
            out.append(dict(name=r.name, t_event=r.t_event, error=f"{type(e).__name__}: {str(e)[:200]}"))
            continue
        if d.empty:
            out.append(dict(name=r.name, t_event=r.t_event, n=0))
        for x in d.itertuples():
            out.append(dict(name=r.name, t_event=r.t_event, n=len(d), source_id=str(x.source_id), sep=round(float(x.sep), 2),
                            G=x.phot_g_mean_mag, bp_rp=x.bp_rp))
    return pd.DataFrame(out)


VIZIER_ASU = "https://vizier.idia.ac.za/viz-bin/asu-tsv"


def vsx(rows: pd.DataFrame, radius_arcsec: float = 10.0, pause_s: float = 1.5, on_error=None, get=None) -> pd.DataFrame:
    """VSX entries within radius of each (release_source_id, ra, dec), nearest first: 'name type sep"; ...', 'none', or
    'error: ...' (never an empty string for a failed query). A first novelty pass only: TNS, SIMBAD, ADS come after."""
    import time

    import httpx
    get = get or (lambda **kw: httpx.get(VIZIER_ASU, timeout=60, **kw))
    out = []
    for r in rows.itertuples():
        if not np.isfinite(r.ra):
            out.append(dict(release_source_id=r.release_source_id, vsx="error: no position"))
            continue
        try:
            resp = get(params={"-source": "B/vsx/vsx", "-c": f"{r.ra} {r.dec}", "-c.rs": str(radius_arcsec),
                               "-out": "Name,Type", "-out.add": "_r", "-sort": "_r"})
            resp.raise_for_status()
            lines = [x for x in resp.text.splitlines() if x and not x.startswith("#")]
            body = [x.split("\t") for x in lines[2:] if not x.startswith("-")]  # header, then unit/dash lines
            got = [f"{b[1].strip()} {b[2].strip()} {float(b[0]):.1f}\"" for b in body if len(b) >= 3]
            out.append(dict(release_source_id=r.release_source_id, vsx="; ".join(got) or "none"))
        except Exception as e:  # noqa: BLE001
            msg = f"error: {type(e).__name__}: {str(e)[:120]}"
            out.append(dict(release_source_id=r.release_source_id, vsx=msg))
            if on_error:
                on_error("vsx", msg)
        time.sleep(pause_s)
    return pd.DataFrame(out, columns=["release_source_id", "vsx"])


def _sky_match(ra1, dec1, ra2, dec2, radius_arcsec):
    """Index pairs (i, j) with separation < radius (small lists; brute force in chunks)."""
    ra1, dec1, ra2, dec2 = (np.radians(np.asarray(x, float)) for x in (ra1, dec1, ra2, dec2))
    pairs = []
    for i in range(len(ra1)):
        c = np.sin(dec1[i]) * np.sin(dec2) + np.cos(dec1[i]) * np.cos(dec2) * np.cos(ra2 - ra1[i])
        sep = np.degrees(np.arccos(np.clip(c, -1, 1))) * 3600
        for j in np.flatnonzero(sep < radius_arcsec):
            pairs.append((i, int(j), float(sep[j])))
    return pairs


def reference_lenses(root: Path = Path(".")) -> pd.DataFrame:
    p = root / "hunts/H-0008/ext/reference_lenses.csv"
    return pd.read_csv(p) if p.exists() else pd.DataFrame(columns=["name", "ra", "dec", "t0_mjd", "tE", "source"])


def neowise_events(root: Path = Path(".")) -> pd.DataFrame:
    parts = []
    for f in ("hunts/H-0009/work/sky4_classified.csv", "hunts/H-0008/work/sky3_classified.csv"):
        p = root / f
        if p.exists():
            parts.append(pd.read_csv(p, usecols=["designation", "ra", "dec", "t", "dw1", "dw2", "class"]))
    return pd.concat(parts, ignore_index=True).drop_duplicates(["designation", "t"]) if parts else pd.DataFrame()


def crossmatch(tg: pd.DataFrame, cat: pd.DataFrame, idm: pd.DataFrame | None, ref: pd.DataFrame,
               nw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(per-target table, release lenses unknown to us and to the reference lists)."""
    m = dict(zip(idm.dr3_source_id, idm.new_source_id, strict=True)) if idm is not None and len(idm) else {}
    cat_ids = set(cat.source_id.astype(str)) if len(cat) else set()
    t = tg.copy()
    t["release_source_id"] = t.source_id.map(lambda s: m.get(s, s))
    t["in_release_lens_catalogue"] = t.release_source_id.isin(cat_ids) & (t.source_id != "")
    # reference lens within 6" and (if the target has an event time) within max(2 tE, 60 d)
    t["reference_lens"] = ""
    ok = t.ra.notna().to_numpy()
    if len(ref) and ok.any():
        idx = np.flatnonzero(ok)
        for i, j, sep in _sky_match(t.ra.to_numpy()[idx], t.dec.to_numpy()[idx], ref.ra, ref.dec, 6.0):
            r = ref.iloc[j]
            te = float(r.tE) if np.isfinite(r.tE) else 30.0
            tev = t.t_event.iloc[idx[i]]
            if np.isfinite(tev) and abs(tev - float(r.t0_mjd)) > max(2 * te, 60):
                continue
            k = t.index[idx[i]]
            t.at[k, "reference_lens"] = (t.at[k, "reference_lens"] + ";" if t.at[k, "reference_lens"] else "") + \
                f"{r['name']} ({r.source}, {sep:.1f}\")"
    # the release's lenses that are in none of our lists and in no reference list
    new = pd.DataFrame()
    if len(cat):
        ours = set(t.release_source_id)
        c = cat[~cat.source_id.astype(str).isin(ours)].copy()
        c["reference_lens"] = ""
        c["neowise_event"] = ""
        good = c.ra.notna().to_numpy()
        if good.any() and len(ref):
            idx = np.flatnonzero(good)
            for i, j, sep in _sky_match(c.ra.to_numpy()[idx], c.dec.to_numpy()[idx], ref.ra, ref.dec, 6.0):
                r, k = ref.iloc[j], c.index[idx[i]]
                te = float(r.tE) if np.isfinite(r.tE) else 30.0
                if "tmax_mjd" in c and np.isfinite(c.at[k, "tmax_mjd"]) and abs(c.at[k, "tmax_mjd"] - float(r.t0_mjd)) > max(2 * te, 60):
                    continue
                c.at[k, "reference_lens"] += f"{r['name']} ({r.source}, {sep:.1f}\");"
        if good.any() and len(nw):
            idx = np.flatnonzero(good)
            for i, j, sep in _sky_match(c.ra.to_numpy()[idx], c.dec.to_numpy()[idx], nw.ra, nw.dec, 3.0):
                e, k = nw.iloc[j], c.index[idx[i]]
                c.at[k, "neowise_event"] += f"{e.designation} t={e.t:.0f} dW1={e.dw1:+.2f} [{e['class']}] {sep:.1f}\";"
        c["unreported"] = c.reference_lens == ""
        new = c
    return t, new
