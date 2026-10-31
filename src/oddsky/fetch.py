"""Open a case on a real star and pull its evidence from the archives."""

from __future__ import annotations

import logging

import pandas as pd

from .case.model import Case, Target
from .case.store import CaseStore
from .data import aavso, asassn, atlas, gaia, gaia_epoch, neowise, simbad, tess, ztf
from .paths import cases_dir

log = logging.getLogger("oddsky")

SURVEYS = ("gaia", "gaia_epoch", "neowise", "aavso", "ztf", "atlas", "asassn", "tess")


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

    store.write_provenance(prov)
    store.write_context(ctx)
    store.save(case)
    return report
