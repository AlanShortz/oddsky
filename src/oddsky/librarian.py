"""The Librarian: is it new? The Skeptic's companion. The Skeptic asks whether a signal is real; the Librarian asks whether
someone has already published it, so that nothing is called a discovery before the literature has been checked.

It is code, not an agent, for the same reason the Skeptic is: it gives the same answer every time, and it cannot decide that
this once the lookup can wait. H-0017 called a galaxy its "best candidate" when it was object 12 of Wang et al. 2018
(2018MNRAS.477.2943W); the bibliography of that position would have said so in ten seconds.

For a sky position it asks four sources and one directory:

- SIMBAD (TAP): the objects at the position and every paper SIMBAD attaches to them, with titles and the number of objects
  each paper lists. Given an epoch, stars are moved from J2000 to that date by their proper motion before matching.
- NED (TAP): the objects at the position (name, type, redshift and the paper the redshift is from).
- ADS: the papers it finds for SIMBAD's name and for every NED name. Needs a token (ADS_TOKEN, or ~/.config/oddsky/ads-token).
- The catalogues (CATALOGUES): large lists of variables and AGN that no bibliography shows object by object (VSX, VarWISE,
  Milliquas, two WISE AGN catalogues), each asked by cone.
- The shelves (src/oddsky/shelves/*.csv): published samples that the archives do not index by object.

Every source answers with a status: "ok", "empty" (it answered: nothing there) or "unavailable" (the query failed, or there
is no token). An unavailable source is never read as "nothing found": `prior_art()` reports it and sets `complete` to False.
ADS has two more: "not_asked" (there was no object name to ask about) and "unresolved" (ADS did not recognise any name as an
object and found nothing in its abstracts; that is not ADS saying there are no papers).

Nothing here calls the network except `simbad()`, `ned()`, `ads_papers()` and `catalogues()`.
"""

from __future__ import annotations

import csv
import functools
import io
import math
import os
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .data.http import request
from .data.provenance import Provenance, now_iso

SIMBAD_TAP = "https://simbad.harvard.edu/simbad/sim-tap/sync"
NED_TAP = "https://ned.ipac.caltech.edu/tap/sync"
ADS_API = "https://api.adsabs.harvard.edu/v1"
# The CfA mirror: the CDS VizieR server and the all-catalogue search time out from here (2026-11-05).
VIZIER_TSV = "https://vizier.cfa.harvard.edu/viz-bin/asu-tsv"
IRSA_TAP = "https://irsa.ipac.caltech.edu/TAP/sync"
ADS_TOKEN_FILE = Path("~/.config/oddsky/ads-token")
ADS_ROWS = 200       # per page
ADS_MAX_ROWS = 1000  # stop paging here; the answer is then not complete, and says so
ADS_MAX_NAMES = 6    # names put to ADS for one position (it needs about 17 s to translate each, 2026-11-05)
# A lookup takes seconds to half a minute. A service that is down is reported as unavailable, not waited for.
TIMEOUT = 60.0
IRSA_TIMEOUT = 120.0  # IRSA can be slow
RETRIES = 2

NEARBY_ARCSEC = 30.0       # with nothing inside the radius, the nearest object within this is named
MAX_PM_ARCSEC_YR = 11.0    # no star moves faster (Barnard's Star: 10.4"/yr)
# A paper that lists more objects than this is a survey or a catalogue: its title is about the list, not about any one
# object in it (SIMBAD's ref.nbobject). A census of a hundred hosts with the phenomenon in its title is about those hosts.
ABOUT_MAX_OBJECTS = 500

SHELVES_DIR = Path(__file__).parent / "shelves"
SOURCES = {"simbad": "SIMBAD", "ned": "NED", "ads": "ADS", "catalogues": "the catalogues"}

# Keywords matched against paper titles, case-insensitively and on word boundaries; a hyphen counts as a space, so
# "changing look" also matches "changing-look". A trailing * matches any ending ("eclips*": eclipse, eclipses, eclipsing).
# Without it the whole word must match ("dip" is not "dipole", "nova" is not "innovative"). Plain data: add a topic or a
# keyword here. A keyword too many costs a title to read; a keyword too few can cost a false discovery. Some titles no
# keyword will catch ("Mrk 1018 returns to the shadows", "Where's the flux?").
TOPICS: dict[str, tuple[str, ...]] = {
    "transient": ("tidal disruption*", "TDE", "TDEs", "disrupt*", "flar*", "outburst*", "burst*", "erupt*", "echo*",
                  "changing look*", "changing state*", "awaken*", "supernova*", "nova", "novae", "kilonova*", "transient*",
                  "fad*", "decline*", "declining", "brightening*", "rebrightening*", "variab*", "variation*"),
    "dimming": ("dip", "dips", "dipper*", "dimm*", "occult*", "eclips*", "disappear*", "vanish*"),
    "infrared_excess": ("infrared excess*", "IR excess*", "debris disk*", "debris disc*", "dust*", "circumstellar"),
    "binary": ("binar*", "companion*", "orbit*"),
}

# SIMBAD object types (basic.otype; names from SIMBAD's otypedef table) that say a transient has been seen here. An object
# of one of these types within the radius makes the verdict "studied", whatever its papers are called. Plain data.
TRANSIENT_OTYPES: dict[str, str] = {
    "SN*": "supernova", "SN?": "supernova candidate", "No*": "nova", "No?": "nova candidate", "ev": "transient event",
    "gB": "gamma-ray burst", "rB": "radio burst", "CV*": "cataclysmic binary", "CV?": "cataclysmic binary candidate",
}

# Large catalogues asked by cone. Membership never shows in a bibliography: SIMBAD and ADS attach the catalogue's paper to a
# handful of its objects at most. Plain data: add a catalogue here.
#   kind "variable": the object is published as variable. A hit makes the verdict "studied".
#   kind "agn":      the object is listed as an AGN or an AGN candidate. A hit is reported and does not change the verdict.
#   service "vizier": a single-catalogue cone on the CfA VizieR mirror (`table` is the VizieR id; every table under it is
#                     searched). service "irsa": a cone on an IRSA TAP table with ra, dec columns.
#   name_column / class_column: the catalogue's own identifier and class for the object, shown with a hit.
CATALOGUES: tuple[dict, ...] = (
    {"key": "vsx", "name": "VSX", "kind": "variable", "service": "vizier", "table": "B/vsx/vsx",
     "bibcode": "2006SASS...25...47W", "name_column": "Name", "class_column": "Type"},
    {"key": "varwise", "name": "VarWISE", "kind": "variable", "service": "irsa", "table": "varwiseext",
     "bibcode": "2026ApJS..284...41P", "name_column": "designation", "class_column": "vartype"},
    {"key": "milliquas", "name": "Milliquas", "kind": "agn", "service": "vizier", "table": "VII/294",
     "bibcode": "2023OJAp....6E..49F", "name_column": "Name", "class_column": "Type"},
    {"key": "secrest2015", "name": "Secrest et al. 2015", "kind": "agn", "service": "vizier", "table": "J/ApJS/221/12",
     "bibcode": "2015ApJS..221...12S", "name_column": "WISEA", "class_column": None},
    {"key": "assef2018", "name": "Assef et al. 2018", "kind": "agn", "service": "vizier", "table": "J/ApJS/234/23",
     "bibcode": "2018ApJS..234...23A", "name_column": "WISEA", "class_column": None},
)
CATALOGUE_KINDS = ("variable", "agn")


# ----------------------------------------------------------------------------- topics
def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[-‐-―]", " ", text)).strip().lower()


@functools.cache
def _pattern(keywords: tuple[str, ...]) -> re.Pattern:
    alts = [re.escape(_normalise(k.rstrip("*"))) + (r"\w*" if k.endswith("*") else "") for k in keywords]
    return re.compile(r"\b(?:" + "|".join(alts) + r")\b")


def matched_topics(title: str, topics: list[str] | tuple[str, ...] | None = None) -> list[str]:
    """The topics (all of TOPICS, or the ones named) with a keyword in this title, in TOPICS order."""
    text = _normalise(title or "")
    return [t for t in (topics or TOPICS) if _pattern(tuple(TOPICS[t])).search(text)]


def _wanted(topics: str | list[str] | tuple[str, ...] | None) -> list[str]:
    if topics is None or topics == [] or topics == ():
        return list(TOPICS)
    names = [topics] if isinstance(topics, str) else list(topics)
    unknown = [t for t in names if t not in TOPICS]
    if unknown:
        raise ValueError(f"unknown topic(s) {unknown}; topics are {list(TOPICS)}")
    return [t for t in TOPICS if t in names]


# ----------------------------------------------------------------------------- geometry
def _sep_arcsec(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    """Angular separation in arcsec (haversine: exact at the poles and across RA = 0, and stable for small angles)."""
    p1, p2 = math.radians(dec1), math.radians(dec2)
    a = math.sin(0.5 * (p2 - p1)) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(0.5 * math.radians(ra2 - ra1)) ** 2
    return 3600.0 * math.degrees(2.0 * math.asin(min(1.0, math.sqrt(a))))


def _moved(ra: float, dec: float, pmra: float, pmdec: float, years: float) -> tuple[float, float]:
    """A position after `years` of proper motion (pmra = mu_alpha cos(dec) and pmdec in mas/yr), along a great circle."""
    east, north = pmra * years / 3.6e6, pmdec * years / 3.6e6  # degrees
    d = math.radians(math.hypot(east, north))
    if d == 0.0:
        return ra, dec
    pa, p1 = math.atan2(east, north), math.radians(dec)
    p2 = math.asin(max(-1.0, min(1.0, math.sin(p1) * math.cos(d) + math.cos(p1) * math.sin(d) * math.cos(pa))))
    dl = math.atan2(math.sin(pa) * math.sin(d) * math.cos(p1), math.cos(d) - math.sin(p1) * math.sin(p2))
    return (ra + math.degrees(dl)) % 360.0, math.degrees(p2)


def _cone(frame: str, ra: float, dec: float, radius_arcsec: float) -> str:
    return (f"CONTAINS(POINT('{frame}',ra,dec),CIRCLE('{frame}',{ra:.7f},{dec:.7f},{radius_arcsec / 3600:.7f}))=1")


def _float(value) -> float | None:
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


# ----------------------------------------------------------------------------- SIMBAD and NED
def _tap(method: str, url: str, query: str, first_column: str, timeout: float = TIMEOUT) -> list[dict]:
    """Rows of a TAP CSV answer. A header alone is an empty table; an answer that does not start with the expected header
    is an error document, and raises: it is not "no rows"."""
    form = {"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": query}
    r = request(method, url, retries=RETRIES, timeout=timeout, **({"data": form} if method == "POST" else {"params": form}))
    text = r.text.lstrip("﻿").strip()
    if text.split(",", 1)[0].split("\n", 1)[0].strip().strip('"') != first_column:
        raise ValueError(f"not a CSV table: {text[:120]!r}")
    return list(csv.DictReader(io.StringIO(text)))


SIMBAD_COLUMNS = "oid, main_id, otype, ra, dec, pmra, pmdec, nbref"


def simbad(ra: float, dec: float, radius_arcsec: float = 5.0, epoch: float | None = None) -> tuple[dict, Provenance]:
    """SIMBAD at a position: `{"object", "nearest", "n_objects", "objects", "papers": [{bibcode, title, n_objects}],
    "nearby"}`. Each object is `{main_id, otype, ra, dec, sep_arcsec, n_refs}`. `objects` are those within the radius,
    nearest first; `object` is the one of them with the most references (the galaxy, not an X-ray source inside it) and
    `nearest` the nearest; the papers are those of all of them, each with the number of objects the paper lists. With
    nothing inside the radius, `nearby` is the nearest object within 30".

    SIMBAD's positions are for J2000. Given an `epoch` (a decimal year, the date of the position asked about), every object
    with a catalogued proper motion is moved to that date first, and a second query finds stars fast enough to have come
    from outside the first cone (Barnard's Star moves 109" between 2000 and 2010.5); these are merged with the plain cone,
    and `sep_arcsec` is then the separation at the epoch. Without an epoch nothing is moved.

    `prov.status` is 'ok', 'empty' (SIMBAD answered: no object within the radius) or 'unavailable' (a query failed; if it
    was the reference query, the objects are still returned and the paper list is not to be trusted)."""
    prov = Provenance(archive="SIMBAD TAP (simbad.harvard.edu)",
                      query={"ra": ra, "dec": dec, "radius_arcsec": radius_arcsec, **({} if epoch is None else {"epoch": epoch})})
    out: dict = {"object": None, "nearest": None, "n_objects": 0, "objects": [], "papers": [], "nearby": None}
    # This mirror rejects aliased columns and ORDER BY alias.col: the queries stay unaliased, and sorting is done here.
    look = max(radius_arcsec, NEARBY_ARCSEC)
    years = 0.0 if epoch is None else epoch - 2000.0
    try:
        rows = _tap("POST", SIMBAD_TAP, f"SELECT {SIMBAD_COLUMNS} FROM basic WHERE {_cone('ICRS', ra, dec, look)}", "oid")
        wide = radius_arcsec + MAX_PM_ARCSEC_YR * abs(years)
        if wide > look:
            # only a star that covered the gap between the two cones since J2000 can be missing from the first
            fast = 1000.0 * (look - radius_arcsec) / abs(years)  # mas/yr
            rows += _tap("POST", SIMBAD_TAP, f"SELECT {SIMBAD_COLUMNS} FROM basic WHERE {_cone('ICRS', ra, dec, wide)} "
                         f"AND pmra*pmra+pmdec*pmdec > {fast * fast:.0f}", "oid")
    except Exception as e:  # noqa: BLE001
        prov.status = "unavailable"
        prov.notes.append(str(e)[:200])
        return out, prov
    inside, outside, seen_oid = [], [], set()
    for row in rows:
        if row["oid"] in seen_oid:
            continue
        seen_oid.add(row["oid"])
        o_ra, o_dec = float(row["ra"]), float(row["dec"])
        at_j2000 = sep = _sep_arcsec(o_ra, o_dec, ra, dec)
        pmra, pmdec = _float(row.get("pmra")), _float(row.get("pmdec"))
        if years and pmra is not None and pmdec is not None:
            sep = _sep_arcsec(*_moved(o_ra, o_dec, pmra, pmdec, years), ra, dec)
        obj = {"main_id": " ".join(row["main_id"].split()), "otype": row.get("otype") or None, "ra": o_ra, "dec": o_dec,
               "sep_arcsec": round(sep, 2), "n_refs": int(_float(row.get("nbref")) or 0), "oid": row["oid"]}
        (inside if min(sep, at_j2000) <= radius_arcsec else outside).append(obj)
    inside.sort(key=lambda o: o["sep_arcsec"])
    oids = [o.pop("oid") for o in inside]
    for o in outside:
        o.pop("oid")
    if not inside:
        prov.status = "empty"
        near = [o for o in outside if o["sep_arcsec"] <= NEARBY_ARCSEC]
        out["nearby"] = min(near, key=lambda o: o["sep_arcsec"]) if near else None
        return out, prov
    out.update(objects=inside, n_objects=len(inside), nearest=inside[0],
               object=max(inside, key=lambda o: (o["n_refs"], -o["sep_arcsec"])))
    try:
        refs = []
        for i in range(0, len(oids), 200):
            refs += _tap("POST", SIMBAD_TAP, "SELECT oidref, bibcode, title, nbobject FROM has_ref JOIN ref ON oidbib=oidbibref "
                         f"WHERE oidref IN ({', '.join(oids[i:i + 200])})", "oidref")
    except Exception as e:  # noqa: BLE001
        prov.status = "unavailable"
        prov.notes.append(f"object found, but its references could not be read: {str(e)[:200]}")
        return out, prov
    seen: dict[str, dict] = {}
    for r in refs:
        if r.get("bibcode"):
            n = _float(r.get("nbobject"))
            seen.setdefault(r["bibcode"].strip(), {"bibcode": r["bibcode"].strip(), "title": r.get("title") or "",
                                                   "n_objects": None if n is None else int(n)})
    out["papers"] = list(seen.values())
    prov.rows_raw, prov.rows_kept = len(refs), len(seen)
    return out, prov


def ned(ra: float, dec: float, radius_arcsec: float = 5.0) -> tuple[dict, Provenance]:
    """NED at a position: `{"object", "objects", "nearby"}`. Each object is `{prefname, type, z, z_bibcode, ra, dec,
    sep_arcsec}`; `objects` are those within the radius, nearest first, and `object` is the nearest, with `n_objects`.
    With nothing inside the radius, `nearby` is the nearest object within 30". `prov.status` is 'ok', 'empty' (NED
    answered: no object within the radius) or 'unavailable'."""
    prov = Provenance(archive="NED TAP (NEDTAP.objdir)", query={"ra": ra, "dec": dec, "radius_arcsec": radius_arcsec})
    out: dict = {"object": None, "objects": [], "nearby": None}
    look = max(radius_arcsec, NEARBY_ARCSEC)
    try:
        rows = _tap("GET", NED_TAP, f"SELECT * FROM NEDTAP.objdir WHERE {_cone('J2000', ra, dec, look)}", "prefname")
        objs = sorted(({"prefname": " ".join(row["prefname"].split()), "type": row.get("prefphytype") or None,
                        "z": _float(row.get("z")), "z_bibcode": (row.get("z_bibcode") or "").strip() or None,
                        "ra": float(row["ra"]), "dec": float(row["dec"]),
                        "sep_arcsec": round(_sep_arcsec(float(row["ra"]), float(row["dec"]), ra, dec), 2)} for row in rows),
                      key=lambda o: o["sep_arcsec"])
    except Exception as e:  # noqa: BLE001
        prov.status = "unavailable"
        prov.notes.append(str(e)[:200])
        return out, prov
    prov.rows_raw = len(rows)
    inside = [o for o in objs if o["sep_arcsec"] <= radius_arcsec]
    if not inside:
        prov.status = "empty"
        out["nearby"] = next((o for o in objs if o["sep_arcsec"] <= NEARBY_ARCSEC), None)
        return out, prov
    prov.rows_kept = len(inside)
    out.update(objects=inside, object={**inside[0], "n_objects": len(inside)})
    return out, prov


# ----------------------------------------------------------------------------- ADS
def ads_token() -> str | None:
    """The ADS API token: $ADS_TOKEN, else ~/.config/oddsky/ads-token. Never printed, logged or stored in a result."""
    if t := os.environ.get("ADS_TOKEN", "").strip():
        return t
    f = ADS_TOKEN_FILE.expanduser()
    return (f.read_text().strip() or None) if f.is_file() else None


def ads_name(simbad_main_id: str) -> str:
    """A SIMBAD main_id as the literature writes it: without SIMBAD's own prefixes ("NAME Barnard's star", "V* KT Eri",
    "* alf Lyr", "EM* AS 209")."""
    return re.sub(r"^(?:NAME|[A-Za-z]{0,2}\*{1,2}) +", "", " ".join(simbad_main_id.split()))


def _ads_resolved(translated: str) -> bool:
    """Did ADS turn the name into an object identifier? An unrecognised name comes back as `simbid:"0"` / `nedid:"0"`,
    which matches no paper: the search is then only for the name as text in abstracts."""
    ids = re.findall(r'\b(?:simbid|nedid):"?([^"\s)]+)"?', translated)
    return any(i != "0" for i in ids)


def ads_papers(names: str | list[str] | tuple[str, ...], bibcodes: list[str] | tuple[str, ...] = ()) -> tuple[list[dict], Provenance]:
    """The papers ADS finds for object names (and, by bibcode, the papers named in `bibcodes`): `[{bibcode, title, year}]`,
    newest first. ADS translates each name into a query (abstract text, SIMBAD id, NED id); the translations are searched
    together. `prov.status` is

    - 'ok': papers were found;
    - 'empty': ADS recognised at least one name as an object and holds no paper on it;
    - 'unresolved': ADS recognised none of the names (it answers `simbid:"0"` with no NED id) and found nothing in its
      abstracts either. The question was not really put: this is not 'empty';
    - 'not_asked': there was no name to ask about;
    - 'unavailable': no token, or a request failed.

    ADS holding more than ADS_MAX_ROWS papers is in the notes, and `prov.rows_raw > prov.rows_kept` then."""
    names = [names] if isinstance(names, str) else [n for n in names if n]
    prov = Provenance(archive="NASA ADS (papers on the SIMBAD and NED names)", query={"objects": names, "bibcodes": list(bibcodes)})
    if not names and not bibcodes:
        prov.status = "not_asked"
        prov.notes.append("not asked: there is no object name to look up")
        return [], prov
    token = ads_token()
    if token is None:
        prov.status = "unavailable"
        prov.notes.append("no ADS token (set ADS_TOKEN or write it to ~/.config/oddsky/ads-token)")
        return [], prov
    auth = {"Authorization": f"Bearer {token}"}

    def translate(name: str) -> str:
        quoted = name.replace("\\", "\\\\").replace('"', '\\"')
        return request("POST", f"{ADS_API}/objects/query", retries=RETRIES, timeout=TIMEOUT, headers=auth,
                       json={"query": [f'object:"{quoted}"']}).json()["query"]

    docs: list[dict] = []
    try:
        # one name per request (ADS translates only the first of several), a few at a time: each takes about 17 s
        with ThreadPoolExecutor(max_workers=4) as pool:
            translated = list(pool.map(translate, names))
        unresolved = [n for n, t in zip(names, translated, strict=True) if not _ads_resolved(t)]
        q = " OR ".join(translated + [f'bibcode:"{b}"' for b in bibcodes])
        found = None
        while found is None or len(docs) < min(found, ADS_MAX_ROWS):
            params = {"q": q, "fl": "bibcode,title,year", "sort": "date desc", "rows": ADS_ROWS,
                      **({"start": len(docs)} if docs else {})}
            resp = request("GET", f"{ADS_API}/search/query", retries=RETRIES, timeout=TIMEOUT, headers=auth,
                           params=params).json()["response"]
            found = int(resp["numFound"])
            if not resp["docs"]:
                break
            docs += resp["docs"]
    except Exception as e:  # noqa: BLE001
        prov.status = "unavailable"
        prov.notes.append(str(e)[:200].replace(token, "<token>"))
        return [], prov
    prov.rows_raw, prov.rows_kept = found, len(docs)
    if unresolved:
        prov.notes.append("ADS did not recognise " + _and([f'"{n}"' for n in unresolved]) + " as an object (simbid:\"0\", no "
                          "NED id): for " + ("that name" if len(unresolved) == 1 else "those names")
                          + " only the text of abstracts was searched")
    if len(docs) < found:
        prov.notes.append(f"ADS holds {found} papers; only the newest {len(docs)} were read")
    if not docs:
        prov.status = "unresolved" if len(unresolved) == len(names) else "empty"
        return [], prov
    papers = []
    for d in docs:
        title = d.get("title") or ""
        papers.append({"bibcode": d.get("bibcode"), "title": title[0] if isinstance(title, list) and title else str(title or ""),
                       "year": d.get("year")})
    return papers, prov


# ----------------------------------------------------------------------------- the catalogues
def _vizier_tables(text: str) -> list[tuple[str, list[dict]]]:
    """The tables of a VizieR asu-tsv answer: `[(table name, rows)]`. A table with no row is listed with `[]`. An answer
    that carries an error, or no table at all, raises: it is not "no rows"."""
    if m := re.search(r"^#INFO\tError=([^\t\n]*)", text, re.M):
        raise ValueError(f"VizieR: {m.group(1).strip()}")
    tables: list[tuple[str, list[dict]]] = []
    name, block = None, []

    def close():
        if name is None:
            return
        lines = [ln for ln in block if not ln.startswith("#")]
        rule = next((i for i, ln in enumerate(lines) if re.fullmatch(r"-+(\t-+)*", ln.strip())), None)
        header = next((ln for ln in lines[:rule] if ln.strip()), None) if rule is not None else None
        rows = []
        if header is not None:
            cols = [c.strip() for c in header.split("\t")]
            rows = [dict(zip(cols, (c.strip() for c in ln.split("\t")), strict=False)) for ln in lines[rule + 1:] if ln.strip()]
        tables.append((name, rows))

    for ln in text.splitlines():
        if ln.startswith("#Table"):
            close()
            name, block = ln.split("\t", 1)[-1].strip().rstrip(":"), []
        elif name is not None:
            if ln.startswith("#Name:") and not block:  # the line after "#Table": the table's VizieR name
                name = ln.split(":", 1)[1].strip()
            block.append(ln)
    close()
    if not tables:
        raise ValueError(f"not a VizieR table: {text[:120]!r}")
    return tables


def _vizier_cone(cat: dict, ra: float, dec: float, radius_arcsec: float) -> list[dict]:
    r = request("GET", VIZIER_TSV, retries=RETRIES, timeout=TIMEOUT,
                params={"-source": cat["table"], "-c": f"{ra:.7f} {dec:+.7f}", "-c.rs": f"{radius_arcsec:g}", "-out.max": "50",
                        "-out.add": "_r"})
    hits = []
    for table, rows in _vizier_tables(r.text):
        for row in rows:
            hits.append({"object": row.get(cat["name_column"]) or None, "class": row.get(cat.get("class_column") or "") or None,
                         "sep_arcsec": _float(row.get("_r")), "table": table})
    return hits


def _irsa_cone(cat: dict, ra: float, dec: float, radius_arcsec: float) -> list[dict]:
    cols = ", ".join(c for c in (cat["name_column"], "ra", "dec", cat.get("class_column")) if c)
    rows = _tap("POST", IRSA_TAP, f"SELECT {cols} FROM {cat['table']} WHERE {_cone('ICRS', ra, dec, radius_arcsec)}",
                cat["name_column"], timeout=IRSA_TIMEOUT)
    return [{"object": " ".join((row.get(cat["name_column"]) or "").split()) or None,
             "class": (row.get(cat.get("class_column") or "") or "").strip() or None,
             "sep_arcsec": _sep_arcsec(float(row["ra"]), float(row["dec"]), ra, dec), "table": cat["table"]} for row in rows]


def catalogues(ra: float, dec: float, radius_arcsec: float = 5.0) -> list[dict]:
    """Every catalogue in CATALOGUES asked for entries within the radius: `[{key, name, kind, bibcode, status, notes,
    hits: [{object, class, sep_arcsec, table}]}]`, hits nearest first. Each catalogue has its own status: 'ok' (it holds
    an entry here), 'empty' (it answered: no entry) or 'unavailable' (the query failed)."""
    out = []
    for cat in CATALOGUES:
        entry = {"key": cat["key"], "name": cat["name"], "kind": cat["kind"], "bibcode": cat["bibcode"], "status": "ok",
                 "notes": [], "hits": []}
        try:
            hits = (_irsa_cone if cat["service"] == "irsa" else _vizier_cone)(cat, ra, dec, radius_arcsec)
            for h in hits:
                h["sep_arcsec"] = None if h["sep_arcsec"] is None else round(h["sep_arcsec"], 2)
            entry["hits"] = sorted(hits, key=lambda h: (h["sep_arcsec"] is None, h["sep_arcsec"] or 0.0))
            entry["status"] = "ok" if hits else "empty"
        except Exception as e:  # noqa: BLE001
            entry["status"] = "unavailable"
            entry["notes"].append(str(e)[:200])
        out.append(entry)
    return out


# ----------------------------------------------------------------------------- the shelves
def load_shelves(directory: Path | str | None = None) -> list[dict]:
    """Every shelf in the directory (default: src/oddsky/shelves): `{shelf, title, bibcode, topics, sources: [{name, ra,
    dec}]}`. A shelf is a CSV: comment lines `# title: ...`, `# bibcode: ...`, `# topics: a, b`, then the columns
    name,ra,dec in degrees. An empty or missing directory is no shelves. A shelf that cannot be read, or that holds no
    row, raises: a broken or empty shelf must not look like a shelf without the object."""
    d = Path(directory) if directory is not None else SHELVES_DIR
    shelves = []
    for f in sorted(d.glob("*.csv")) if d.is_dir() else []:
        meta: dict[str, str] = {}
        body = []
        for line in f.read_text().splitlines():
            if line.lstrip().startswith("#"):
                key, colon, value = line.lstrip()[1:].partition(":")
                if colon:
                    meta[key.strip().lower()] = value.strip()
            elif line.strip():
                body.append(line)
        if not meta.get("title") or not meta.get("bibcode"):
            raise ValueError(f"shelf {f.name}: needs '# title: ...' and '# bibcode: ...' comment lines")
        sources = []
        for n, raw in enumerate(csv.DictReader(body), start=1):
            row = {(k or "").strip().lower(): v for k, v in raw.items()}
            try:
                src = {"name": row["name"].strip(), "ra": float(row["ra"]), "dec": float(row["dec"])}
            except (KeyError, ValueError, TypeError, AttributeError) as e:
                raise ValueError(f"shelf {f.name}, row {n}: needs columns name,ra,dec with ra and dec in degrees "
                                 f"({type(e).__name__}: {e})") from None
            if not (0.0 <= src["ra"] < 360.0 and -90.0 <= src["dec"] <= 90.0):
                raise ValueError(f"shelf {f.name}, row {n}: ra {src['ra']}, dec {src['dec']} are not degrees on the sky")
            sources.append(src)
        if not sources:
            raise ValueError(f"shelf {f.name}: no rows. A shelf holds a published sample; an empty one would answer "
                             "'not in this paper' for every position")
        shelves.append({"shelf": f.stem, "title": meta["title"], "bibcode": meta["bibcode"],
                        "topics": [t.strip() for t in meta.get("topics", "").split(",") if t.strip()], "sources": sources})
    return shelves


def shelf_hits(ra: float, dec: float, radius_arcsec: float = 5.0, directory: Path | str | None = None) -> list[dict]:
    """The shelves holding a source within the radius of (ra, dec): `{shelf, title, bibcode, topics, name, sep_arcsec}`,
    with the nearest source of each. No network."""
    hits = []
    for s in load_shelves(directory):
        near = [(_sep_arcsec(x["ra"], x["dec"], ra, dec), x["name"]) for x in s["sources"]]
        near = [x for x in near if x[0] <= radius_arcsec]
        if near:
            sep, name = min(near)
            hits.append({"shelf": s["shelf"], "title": s["title"], "bibcode": s["bibcode"], "topics": s["topics"],
                         "name": name, "sep_arcsec": round(sep, 2)})
    return hits


# ----------------------------------------------------------------------------- the question
def _year(bibcode: str) -> int | None:
    return int(bibcode[:4]) if bibcode[:4].isdigit() else None


def _and(names: list[str]) -> str:
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def unavailable_names(pa: dict) -> list[str]:
    """Display names of the sources that could not be queried in a `prior_art()` result; a catalogue goes by its own name."""
    names = []
    for k, v in (pa.get("sources") or {}).items():
        if v.get("status") != "unavailable":
            continue
        down = [c["name"] for c in pa.get("catalogues") or [] if c.get("status") == "unavailable"] if k == "catalogues" else []
        names += down or [SOURCES.get(k, k)]
    return names


def incomplete_reasons(pa: dict) -> list[str]:
    """Why a `prior_art()` result is not final, in words: sources that could not be queried, and an ADS list cut short."""
    why = []
    if down := unavailable_names(pa):
        why.append(f"{_and(down)} could not be queried")
    if cut := ((pa.get("sources") or {}).get("ads") or {}).get("truncated"):
        why.append(f"ADS holds {cut['found']} papers and only the newest {cut['read']} were read")
    return why


def prior_art(ra: float, dec: float, radius_arcsec: float = 5.0, topics: str | list[str] | None = None,
              epoch: float | None = None) -> dict:
    """Is it new? Everything the archives, the catalogues and the shelves hold on a position, and a verdict:

    - "unlisted": no SIMBAD object, no NED object, no shelf hit, no entry in a catalogue of variables.
    - "catalogued": an object exists, and no paper title matches the topics. This is not evidence that nothing is
      published: it says the bibliographies the Librarian can read hold nothing on the topics under this object.
    - "mentioned": titles match the topics, but only in papers that list more than ABOUT_MAX_OBJECTS objects (surveys,
      catalogues, rate papers): the object is in their tables, and they are not about it.
    - "studied": a title on the topics in a paper about at most ABOUT_MAX_OBJECTS objects (or of unknown size: a paper
      only ADS lists), a shelf hit, a SIMBAD object of a transient type (TRANSIENT_OTYPES), or an entry in a catalogue of
      variables. Read those before calling anything new.

    An entry in an AGN catalogue is reported (`catalogue_hits`, and in the summary) and does not change the verdict.

    `epoch` is the date of the position as a decimal year (2010.5 for AllWISE). Give it for anything that may be a nearby
    star: SIMBAD is then searched for stars whose proper motion puts them at the position on that date. NED, the
    catalogues and the shelves are matched at their catalogued positions. None: nothing is moved.

    Papers from SIMBAD, ADS and NED (the redshift's source) are merged by bibcode; `topical_papers` (newest first) are those
    whose title matches one of `topics` (default: all of TOPICS), each with `n_objects` (SIMBAD's count, None if unknown)
    and `big_list`. `complete` is False when a source could not be queried or ADS held more papers than were read: the
    verdict is then what was read, and is not final. `summary` says all of this in a sentence or two."""
    wanted = _wanted(topics)
    sim, p_sim = simbad(ra, dec, radius_arcsec, epoch=epoch)
    ned_all, p_ned = ned(ra, dec, radius_arcsec)
    sim_obj, ned_obj = sim.get("object"), ned_all.get("object")
    sim_objs = sim.get("objects") or ([sim_obj] if sim_obj else [])
    ned_objs = ned_all.get("objects") or ([ned_obj] if ned_obj else [])

    # ADS is asked about SIMBAD's name for the object and every NED name in the cone. NED's preferred name alone is, at a
    # survey position, the survey's own designation, which no paper uses.
    names: list[str] = []
    for n in ([ads_name(sim_obj["main_id"])] if sim_obj else []) + [o["prefname"] for o in ned_objs]:
        if n and n.casefold() not in {x.casefold() for x in names}:
            names.append(n)
    z_bibs = list(dict.fromkeys(o["z_bibcode"] for o in ned_objs if o.get("z_bibcode")))
    if names:
        ads, p_ads = ads_papers(names[:ADS_MAX_NAMES], z_bibs)
        if len(names) > ADS_MAX_NAMES:
            p_ads.notes.append(f"{len(names) - ADS_MAX_NAMES} more NED names in the cone were not put to ADS")
    else:
        # With no object there is nothing to ask ADS about. With SIMBAD or NED down the question could not be put, and
        # that is a source that was not queried.
        down = [SOURCES[k] for k, p in (("simbad", p_sim), ("ned", p_ned)) if p.status == "unavailable"]
        ads, p_ads = [], Provenance(
            archive="NASA ADS (papers on the SIMBAD and NED names)", status="unavailable" if down else "not_asked",
            notes=["not asked: " + (f"{_and(down)} could not be queried, so there was no object name to look up" if down
                                    else "there is no SIMBAD or NED object to look up")])

    papers: dict[str, dict] = {}
    for source, rows in (("simbad", sim.get("papers") or []), ("ads", ads), ("ned", [{"bibcode": b} for b in z_bibs])):
        for r in rows:
            bib = str(r.get("bibcode") or "").strip()
            if not bib:
                continue
            title = " ".join(str(r.get("title") or "").split())
            p = papers.setdefault(bib, {"bibcode": bib, "year": _year(bib), "title": title, "sources": [], "topics": [],
                                        "n_objects": None, "big_list": False})
            p["title"] = p["title"] or title
            if source not in p["sources"]:
                p["sources"].append(source)
            p["topics"] = [t for t in TOPICS if t in p["topics"] or t in matched_topics(title)]
            if r.get("n_objects") is not None:
                p["n_objects"] = int(r["n_objects"])
                p["big_list"] = p["n_objects"] > ABOUT_MAX_OBJECTS
    topical = sorted((p for p in papers.values() if set(p["topics"]) & set(wanted)),
                     key=lambda p: (p["year"] or 0, p["bibcode"]), reverse=True)
    about = [p for p in topical if not p["big_list"]]

    shelves = shelf_hits(ra, dec, radius_arcsec)
    otype_hits = [{"main_id": o.get("main_id"), "otype": o["otype"], "label": TRANSIENT_OTYPES[o["otype"]],
                   "sep_arcsec": o.get("sep_arcsec")} for o in sim_objs if o.get("otype") in TRANSIENT_OTYPES]
    cats = catalogues(ra, dec, radius_arcsec)
    cat_hits = [{"catalogue": c["key"], "name": c["name"], "kind": c["kind"], "bibcode": c["bibcode"], **c["hits"][0],
                 "n_hits": len(c["hits"])} for c in cats if c.get("hits")]
    cats_down = [c for c in cats if c["status"] == "unavailable"]

    nearby = None
    if not sim_obj and not ned_obj:
        near = [{"source": src, "name": o.get(key), "type": o.get(kind), "sep_arcsec": o.get("sep_arcsec")}
                for src, o, key, kind in (("SIMBAD", sim.get("nearby"), "main_id", "otype"),
                                          ("NED", ned_all.get("nearby"), "prefname", "type")) if o]
        nearby = min(near, key=lambda o: o["sep_arcsec"]) if near else None
    nearest = sim.get("nearest") or sim_obj
    truncated = p_ads.status == "ok" and p_ads.rows_raw > p_ads.rows_kept
    out = {
        "ra": ra, "dec": dec, "radius_arcsec": radius_arcsec, "epoch": epoch, "topics": wanted, "checked_at": now_iso(),
        "sources": {
            **{k: {"archive": p.archive, "status": p.status, "notes": p.notes} for k, p in (("simbad", p_sim), ("ned", p_ned))},
            "ads": {"archive": p_ads.archive, "status": p_ads.status, "notes": p_ads.notes, "asked": names[:ADS_MAX_NAMES],
                    "truncated": {"found": p_ads.rows_raw, "read": p_ads.rows_kept} if truncated else None},
            "catalogues": {"archive": "catalogue cones (VizieR at CfA, IRSA): " + ", ".join(c["name"] for c in cats),
                           "status": "unavailable" if cats_down else "ok" if cat_hits else "empty",
                           "notes": [f"{c['name']}: {'; '.join(c['notes']) or 'no reason given'}" for c in cats_down]},
        },
        "simbad": ({"main_id": sim_obj.get("main_id"), "otype": sim_obj.get("otype"), "sep_arcsec": sim_obj.get("sep_arcsec"),
                    "n_refs": sim_obj.get("n_refs"), "n_objects": sim.get("n_objects") or 1,
                    "nearest": {k: nearest.get(k) for k in ("main_id", "otype", "sep_arcsec")}} if sim_obj else None),
        "ned": ({"prefname": ned_obj.get("prefname"), "type": ned_obj.get("type"), "z": ned_obj.get("z"),
                 "z_bibcode": ned_obj.get("z_bibcode"), "sep_arcsec": ned_obj.get("sep_arcsec"),
                 "n_objects": ned_obj.get("n_objects") or len(ned_objs), "names": [o["prefname"] for o in ned_objs]}
                if ned_obj else None),
        "nearby": nearby,
        "n_papers": len(papers), "n_topical": len(topical), "n_about": len(about), "topical_papers": topical,
        "shelf_hits": shelves, "otype_hits": otype_hits, "catalogues": cats, "catalogue_hits": cat_hits,
    }
    out["complete"] = not incomplete_reasons(out)
    out["verdict"] = ("studied" if about or shelves or otype_hits or any(h["kind"] == "variable" for h in cat_hits) else
                      "mentioned" if topical else
                      "catalogued" if sim_obj or ned_obj or papers else "unlisted")
    out["reasons"] = _reasons(out)
    out["summary"] = _summary(out)
    return out


def _name(pa: dict) -> str:
    return (pa.get("simbad") or {}).get("main_id") or (pa.get("ned") or {}).get("prefname") or "this position"


def _newest(papers: list[dict]) -> str:
    return f"the newest is {papers[0]['bibcode']}, \"{papers[0]['title'].rstrip('.')}\""


def _reasons(pa: dict) -> list[str]:
    """Why a position is "studied", one clause per reason: papers about it, a shelf, a transient object type, a catalogue of
    variables. Empty for the other verdicts."""
    n, top = pa["n_papers"], pa["topical_papers"]
    about = [p for p in top if not p.get("big_list")]
    reasons = []
    if about:
        lists = len(top) - len(about)
        reasons.append(f"{len(about)} of {n} {'paper' if n == 1 else 'papers'} on {_name(pa)} "
                       f"{'matches' if len(about) == 1 else 'match'} the topics ({', '.join(pa['topics'])})"
                       + (f", not counting {lists} {'list' if lists == 1 else 'lists'} of more than {ABOUT_MAX_OBJECTS} objects"
                          if lists else "") + f"; {_newest(about)}")
    if shelves := pa["shelf_hits"]:
        more = f" and {len(shelves) - 1} more" if len(shelves) > 1 else ""
        reasons.append(f"{'it' if reasons else _name(pa)} is in a published sample on the shelves as {shelves[0]['name']}: "
                       f"{shelves[0]['bibcode']}, \"{shelves[0]['title'].rstrip('.')}\"{more}")
    if hits := pa["otype_hits"]:
        more = f" and {len(hits) - 1} more" if len(hits) > 1 else ""
        reasons.append(f"SIMBAD has a {hits[0]['label']} here, {hits[0]['main_id']} ({hits[0]['otype']}){more}")
    for h in pa["catalogue_hits"]:
        if h["kind"] == "variable":
            reasons.append(f"{h['name']} lists a variable here, {h['object']}" + (f" (type {h['class']})" if h.get("class") else ""))
    return reasons


def _summary(pa: dict) -> str:
    n, top, verdict = pa["n_papers"], pa["topical_papers"], pa["verdict"]
    name, topics, radius = _name(pa), ", ".join(pa["topics"]), f"{pa['radius_arcsec']:g}\""
    papers = "paper" if n == 1 else "papers"
    why = incomplete_reasons(pa)
    if verdict == "studied":
        body = "; ".join(pa["reasons"][:2])  # the rest are in `reasons`
    elif verdict == "mentioned":
        body = (f"{len(top)} of {n} {papers} on {name} {'matches' if len(top) == 1 else 'match'} the topics ({topics}), "
                f"{'a list' if len(top) == 1 else 'all of them lists'} of more than {ABOUT_MAX_OBJECTS} objects; {_newest(top)}")
    elif verdict == "catalogued":
        body = (f"{name} is listed in {n} {papers}, and no title matches the topics ({topics})" if n else
                f"{name} is in the archives with no paper attached")
        if pa["sources"]["ads"]["status"] == "unresolved":
            body += "; ADS did not recognise the name, so only the text of its abstracts was searched"
    else:
        body = (f"no SIMBAD object, no NED object and no shelf entry within {radius}" if not why else
                f"the sources that answered hold nothing within {radius}")
        if near := pa.get("nearby"):
            body += f"; the nearest is {near['name']} ({near['source']}), {near['sep_arcsec']:.1f}\" away"
    agn = [h["name"] for h in pa["catalogue_hits"] if h["kind"] == "agn"]
    tail = f" It is listed as an AGN or AGN candidate in {_and(agn)}." if agn else ""
    if not why:
        return f"{verdict.capitalize()}: {body}.{tail}"
    return f"Not final ({'; '.join(why)}); so far {verdict}: {body}.{tail}"
