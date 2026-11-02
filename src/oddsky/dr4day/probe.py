"""Stage 0: what does the archive actually serve for this release? Run first; every other stage depends on it.

Checks, each recorded as ok / error with the message:
  tables        the release's TAP tables (tap_schema), the logical tables the pipeline needs, and every vari_* table;
  columns       the columns the pipeline reads in the classifier, neighbourhood and flags tables;
  lens_labels   the classifier labels attached to the release's vari_microlensing sources (DR4's label is not in the draft);
  datalink      the DataLink products offered for a reference source (DR4 should add EPOCH_ASTROMETRY, EPOCH_FLAGS_VARI, ...);
  epoch         one EPOCH_PHOTOMETRY request: the raw columns, which layout `gaia_epoch.column_map` recognises (or which
                columns are missing), and whether the times convert into the release's span.
`fixes` lists the overrides (`--set key=value`) or code changes each failure points to.
"""

from __future__ import annotations

import numpy as np

from ..data import gaia_epoch
from .archive import Archive
from .config import Release

REFERENCE_SOURCE = "5959812622743175552"  # OS-0026: a Gaia DR3 lens with DR3 epoch photometry; most DR3 ids persist in DR4


def _step(out: dict, name: str, fn):
    try:
        out[name] = {"ok": True, **fn()}
    except Exception as e:  # noqa: BLE001  every failure is recorded with its message
        out[name] = {"ok": False, "error": f"{type(e).__name__}: {str(e)[:400]}"}


def run(arc: Archive, rel: Release, reference: str = REFERENCE_SOURCE) -> dict:
    out: dict = {"release": rel.name, "schema": rel.schema, "logged_in": arc.logged_in, "chunk": arc.chunk}
    fixes: list[str] = []

    def tables():
        t = arc.tap(f"SELECT table_name FROM tap_schema.tables WHERE schema_name = '{rel.schema}'", sync=True)
        names = sorted(t.table_name.astype(str)) if len(t) else []
        if not names:
            raise RuntimeError(f"schema {rel.schema} has no tables (not released yet, or renamed)")
        need = dict(rel.tables, neighbourhood=rel.neighbourhood[0], flags=rel.flags_table)
        missing = {k: v for k, v in need.items() if v not in names and v.split(".")[-1] not in names}
        for k, v in missing.items():
            fixes.append(f"table {v} not found: --set tables.{k}=<name> (see vari/all tables listed in probe.json)")
        return {"n_tables": len(names), "missing": missing,
                "vari_tables": [n for n in names if "vari_" in n], "all_tables": names}

    def columns():
        want = {rel.table("vari_classifier_result"): list(rel.classifier_cols) + ["source_id"],
                rel.neighbourhood[0]: list(rel.neighbourhood[1:]),
                rel.flags_table: ["source_id", "has_epoch_photometry", "phot_variable_flag"],
                rel.table("vari_microlensing"): ["source_id"]}
        res = {}
        for tab, cols in want.items():
            c = arc.tap(f"SELECT column_name FROM tap_schema.columns WHERE table_name = '{tab}'", sync=True)
            have = set(c.column_name.astype(str)) if len(c) else set()
            if not have:  # some services list unqualified table names
                c = arc.tap(f"SELECT column_name FROM tap_schema.columns WHERE table_name = '{tab.split('.')[-1]}'", sync=True)
                have = set(c.column_name.astype(str)) if len(c) else set()
            miss = [x for x in cols if x not in have]
            res[tab] = {"n_columns": len(have), "missing": miss}
            if miss:
                fixes.append(f"{tab} lacks {miss}: fix the matching setting (classifier_cols / neighbourhood / flags_table)")
        return {"tables": res}

    def lens_labels():
        cls, score = rel.classifier_cols
        q = (f"SELECT TOP 2000 c.{cls} AS cls FROM {rel.table('vari_microlensing')} AS m "
             f"JOIN {rel.table('vari_classifier_result')} AS c ON c.source_id = m.source_id")
        d = arc.tap(q)
        counts = d.cls.astype(str).value_counts().to_dict() if len(d) else {}
        if counts and rel.microlensing_class not in counts:
            fixes.append(f"no classifier label {rel.microlensing_class!r} among lens sources {list(counts)[:6]}: "
                         "--set microlensing_class=<label>")
        return {"labels_of_lens_sources": counts}

    def datalink():
        r = arc.links(reference)
        if rel.retrieval_epoch not in r["retrieval_types"]:
            fixes.append(f"DataLink offers no {rel.retrieval_epoch} for {reference}: {r}; --set retrieval_epoch=<type>")
        return r

    def epoch():
        raws = arc.epoch_raw([reference])
        if not raws:
            raise RuntimeError(f"no epoch photometry returned for {reference}")
        raw = raws[0]
        cols = list(raw.columns)
        try:
            layout, _ = gaia_epoch.column_map(raw)
        except KeyError as e:
            fixes.append(f"gaia_epoch.column_map does not recognise the layout: {e}. Add the release's names to "
                         "COLUMN_MAPS in src/oddsky/data/gaia_epoch.py (dr4_ensemble.md 2.5 item 2 allows this)")
            return {"columns": cols, "layout": None}
        df = gaia_epoch.to_series(raw)
        t0, t1 = float(df.t_mjd.min()), float(df.t_mjd.max())
        in_span = rel.in_span(t0, 5) and rel.in_span(t1, 5)
        if not in_span:
            fixes.append(f"epoch times {t0:.1f}-{t1:.1f} fall outside {rel.epoch_start_mjd}-{rel.epoch_end_mjd}: "
                         "check GAIA_T0_MJD in gaia_epoch.py against the release's stated zero point")
        return {"columns": cols, "layout": layout, "n_rows": len(df), "bands": sorted(df.band.unique()),
                "t_min": round(t0, 2), "t_max": round(t1, 2), "times_in_span": in_span,
                "flags": df.flag.value_counts().to_dict(), "median_G": round(float(np.median(df[df.band == "G"].mag)), 3)}

    _step(out, "tables", tables)
    for name, fn in (("columns", columns), ("lens_labels", lens_labels)):
        if out["tables"]["ok"]:
            _step(out, name, fn)
        else:
            out[name] = {"ok": False, "error": f"skipped: schema {rel.schema} not served"}
    for name, fn in (("datalink", datalink), ("epoch", epoch)):
        _step(out, name, fn)
    for name in ("tables", "columns", "lens_labels", "datalink", "epoch"):
        if not out[name]["ok"] and not out[name]["error"].startswith("skipped"):
            fixes.append(f"{name}: {out[name]['error']}")
    out["fixes"] = fixes
    out["ok"] = all(out[n]["ok"] for n in ("tables", "datalink", "epoch")) and out["epoch"].get("layout") is not None
    return out
