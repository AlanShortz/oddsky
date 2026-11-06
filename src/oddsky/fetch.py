"""Open a case on a real star and pull its evidence from the archives."""

from __future__ import annotations

import logging

import pandas as pd

from . import librarian
from .case.model import Case, Target
from .case.store import CaseStore
from .data import aavso, allwise, asassn, atlas, gaia, gaia_epoch, neowise, simbad, tess, ztf
from .data.provenance import Provenance
from .paths import cases_dir

log = logging.getLogger("oddsky")

# "librarian" is not a survey: it is the literature check (oddsky.librarian) the Skeptic's prior_art check reads. It is in
# the default set, like every other network source here, so that a case is never opened without it.
SURVEYS = ("gaia", "allwise", "gaia_epoch", "neowise", "aavso", "ztf", "atlas", "asassn", "tess", "librarian")


def open_case(name: str, title: str | None = None, hook: str = "", ra: float | None = None,
              dec: float | None = None, hunt: str | None = None) -> CaseStore:
    """Resolve a name (SIMBAD, then AAVSO VSX) and create cases/OS-NNNN/."""
    try:
        return CaseStore.find(name)
    except FileNotFoundError:
        pass
    target = Target(name=name)
    if ra is None or dec is None:
        info, _ = simbad.resolve(name)
        if info:
            target = Target(name=name, ra=info["ra"], dec=info["dec"], otype=info["otype"],
                            aliases=[i for i in info["ids"] if i != name][:40])
        else:
            vsx = aavso.vsx_object(name)
            if not vsx:
                raise ValueError(f"could not resolve '{name}' in SIMBAD or AAVSO VSX; pass ra/dec")
            target = Target(name=vsx["Name"], ra=float(vsx["RA2000"]), dec=float(vsx["Declination2000"]),
                            otype=vsx.get("VariabilityType"))
    else:
        target = Target(name=name, ra=ra, dec=dec)
    cid = CaseStore.next_case_id()
    store = CaseStore(cases_dir() / cid)
    store.save(Case(id=cid, title=title or name, hook=hook, target=target, hunt=hunt))
    return store


def gaia_id_in_name(name: str | None) -> int | None:
    """The source_id in a target named "Gaia DR3 <id>" (or DR2/EDR3), else None."""
    import re

    m = re.match(r"\s*Gaia\s+(?:DR3|EDR3|DR2)\s+(\d{6,})\s*$", name or "")
    return int(m.group(1)) if m else None


def fetch(store: CaseStore, surveys: tuple[str, ...] | list[str] = SURVEYS) -> dict:
    case = store.load()
    t = case.target
    if t is None or t.ra is None:
        raise ValueError("case has no target coordinates")
    prov = store.provenance()
    ctx = store.context()
    report = {}

    def record(key, df, p):
        prov[key] = p.model_dump()
        if df is not None and not df.empty:
            store.write_series(key, df)
        report[key] = {"status": p.status, "rows": p.rows_kept}

    if "gaia" in surveys:
        cone, p = gaia.cone(t.ra, t.dec, 30.0)
        prov["gaia"] = p.model_dump()
        if not cone.empty:
            close = cone[cone.sep_arcsec < 3.0]
            named = gaia_id_in_name(t.name)
            if named is not None and (cone.source_id.astype("int64") == named).any():
                # A case opened as "Gaia DR3 <id>" is about that source, even when a brighter star sits nearby (OS-0026's
                # event is on a G 17.9 star 0.6" from a brighter one).
                tgt = cone[cone.source_id.astype("int64") == named].iloc[0]
            else:
                # Otherwise the target is the brightest source within 3"; a faint closer source is a neighbour.
                tgt = (close.sort_values("phot_g_mean_mag") if not close.empty else cone).iloc[0]
            case.target.gaia_source_id = int(tgt.source_id)
            ctx["gaia"] = gaia.context(tgt)
            ctx["gaia"]["sep_from_target_coords_arcsec"] = float(tgt.sep_arcsec)
            ctx["gaia_variability"] = gaia.variability(int(tgt.source_id))
            nb = gaia.neighbors(cone, int(tgt.source_id))
            ctx["neighbors"] = nb.round(4).to_dict(orient="records")
        report["gaia"] = {"status": p.status, "rows": p.rows_kept}

    if "allwise" in surveys:
        # The AllWISE (2010-11) catalogue row: the Skeptic tests its profile-fit photometry (H-0016), and it is the only
        # mid-infrared measurement of the star before NEOWISE.
        row, p = allwise.catalog(t.ra, t.dec, 3.0)
        prov["allwise"] = p.model_dump()
        if row is not None:
            ctx["allwise"] = row
        report["allwise"] = {"status": p.status, "rows": p.rows_kept}
        if row is not None and allwise.diagnose(row, ctx.get("gaia"))["verdict"] in ("suspect", "bad"):
            # H-0016 section 4d: the Reject Table may hold a second, correct extraction of the same star. Only asked for a
            # suspect entry (IRSA is slow). The status is stored with the entries so that a failed query is never read as
            # "no duplicate".
            entries, p = allwise.reject_entries(row["ra"], row["dec"], 3.0)
            prov["allwise_reject"] = p.model_dump()
            earlier = ctx.get("allwise_reject")
            if p.status != "unavailable" or not earlier or earlier.get("status") == "unavailable":
                # (a failed re-query does not replace an earlier answer: the catalogue does not change)
                ctx["allwise_reject"] = {"status": p.status, "entries": entries,
                                         "duplicate": allwise.best_duplicate(row, entries)}
            report["allwise_reject"] = {"status": p.status, "rows": p.rows_kept}
        elif row is not None:
            ctx.pop("allwise_reject", None)

    if "gaia_epoch" in surveys and case.target.gaia_source_id:
        record("gaia_epoch", *gaia_epoch.lightcurve(case.target.gaia_source_id))

    if "neowise" in surveys:
        record("neowise", *neowise.lightcurve(t.ra, t.dec))

    if "neowise_exp" in surveys:
        record("neowise_exp", *neowise.exposures(t.ra, t.dec))

    if "aavso" in surveys:
        df, p = pd.DataFrame(), None
        for name in [t.name, *t.aliases[:6]]:
            df, p = aavso.lightcurve(name)
            if not df.empty:
                p.notes.append(f"matched AAVSO name '{name}'")
                break
        record("aavso", df, p)

    if "ztf" in surveys:
        record("ztf", *ztf.lightcurve(t.ra, t.dec))

    if "atlas" in surveys:
        record("atlas", *atlas.lightcurve(t.ra, t.dec))

    if "asassn" in surveys:
        record("asassn", *asassn.lightcurve(t.ra, t.dec))

    if "tess" in surveys:
        df, p, meta = tess.lightcurve(t.ra, t.dec)
        record("tess", df, p)
        if meta.get("sectors"):
            ctx["tess"] = meta

    if "librarian" in surveys:
        # Is it new? SIMBAD, NED, ADS, the catalogues and the shelves at the case position. Each source's status is stored
        # with the answer, so a source that could not be queried is never read as "nothing published".
        pa = librarian.prior_art(t.ra, t.dec)
        down = librarian.unavailable_names(pa)
        p = Provenance(archive="The Librarian (SIMBAD, NED, ADS, catalogues, shelves)",
                       query={"ra": t.ra, "dec": t.dec, "radius_arcsec": pa["radius_arcsec"]},
                       rows_raw=pa["n_papers"], rows_kept=pa["n_topical"],
                       status="unavailable" if down else "empty" if pa["verdict"] == "unlisted" else "ok",
                       notes=[f"{k}: {v['status']}" + (f" ({'; '.join(v['notes'])})" if v["notes"] else "")
                              for k, v in pa["sources"].items() if v["status"] == "unavailable"]
                       + [w for w in librarian.incomplete_reasons(pa) if w.startswith("ADS holds")])
        prov["librarian"] = p.model_dump()
        earlier = ctx.get("prior_art")
        if pa["complete"] or not earlier or not earlier.get("complete"):
            # (an incomplete re-check does not replace an earlier complete one; the report says it was incomplete)
            ctx["prior_art"] = pa
        report["librarian"] = {"status": p.status, "rows": pa["n_papers"], "verdict": pa["verdict"],
                               **({"unavailable": down} if down else {})}

    store.write_provenance(prov)
    store.write_context(ctx)
    # Archive fetches can take an hour (ATLAS queues); claims, hypotheses and predictions may have been recorded meanwhile.
    # Never write back the Case loaded at the start: reload it and carry over only what this function changed (OS-0036 lost
    # five claims and a prediction to a stale save on 2026-11-03).
    fresh = store.load()
    if case.target is not None and fresh.target is not None:
        fresh.target.gaia_source_id = case.target.gaia_source_id
    store.save(fresh)
    return report
