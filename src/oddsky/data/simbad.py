"""SIMBAD: names, object types, and the literature trail. Open mode only (it would end any blind trial)."""

from __future__ import annotations

import contextlib
import io
import warnings

from .provenance import Provenance


def resolve(name: str) -> tuple[dict | None, Provenance]:
    from astroquery.simbad import Simbad

    prov = Provenance(archive="CDS SIMBAD", query={"name": name})
    s = Simbad()
    s.add_votable_fields("otype", "ids", "V")
    with warnings.catch_warnings(), contextlib.redirect_stdout(io.StringIO()):
        warnings.simplefilter("ignore")
        try:
            t = s.query_object(name)
        except Exception as e:  # noqa: BLE001
            prov.status = "unavailable"
            prov.notes.append(str(e)[:200])
            return None, prov
    if t is None or len(t) == 0:
        prov.status = "empty"
        return None, prov
    row = t[0]
    cols = {c.lower(): c for c in t.colnames}

    def get(*names):
        for n in names:
            if n in cols:
                v = row[cols[n]]
                return None if getattr(v, "mask", False) else v
        return None

    ids = str(get("ids") or "").split("|")
    out = dict(
        main_id=str(get("main_id")),
        ra=float(get("ra")), dec=float(get("dec")),
        otype=str(get("otype") or ""),
        V=float(get("v", "flux_v")) if get("v", "flux_v") is not None else None,
        ids=[i.strip() for i in ids if i.strip()],
    )
    prov.rows_raw = prov.rows_kept = 1
    return out, prov


def bibliography(main_id: str, limit: int = 25) -> list[dict]:
    """Most-recent references that mention the object (bibcode, year, title)."""
    from astroquery.simbad import Simbad

    q = (
        'SELECT TOP {n} ref.bibcode, ref."year" AS yr, ref.title FROM ref '  # "year" is reserved in ADQL
        "JOIN has_ref ON ref.oidbib = has_ref.oidbibref "
        "JOIN ident ON ident.oidref = has_ref.oidref "
        "WHERE ident.id = '{id}' ORDER BY yr DESC"
    ).format(n=limit, id=main_id.replace("'", "''"))
    with warnings.catch_warnings(), contextlib.redirect_stdout(io.StringIO()):
        warnings.simplefilter("ignore")
        t = Simbad.query_tap(q)  # errors propagate: "no papers" and "query failed" must look different
    return [dict(bibcode=str(r["bibcode"]), year=int(r["yr"]), title=str(r["title"])) for r in t]
