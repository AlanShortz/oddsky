"""The Librarian: is it new? The Skeptic's companion. The Skeptic asks whether a signal is real; the Librarian asks whether
someone has already published it, so that nothing is called a discovery before the literature has been checked.

It is code, not an agent, for the same reason the Skeptic is: it gives the same answer every time, and it cannot decide that
this once the lookup can wait. H-0017 called a galaxy its "best candidate" when it was object 12 of Wang et al. 2018
(2018MNRAS.477.2943W); the bibliography of that position would have said so in ten seconds.

For a sky position it asks three services and one directory:

- SIMBAD (TAP): the object at the position and every paper SIMBAD attaches to it, with titles.
- NED (TAP): the object at the position (name, type, redshift).
- ADS: the papers attached to that NED object. Needs a token (ADS_TOKEN, or ~/.config/oddsky/ads-token).
- The shelves (src/oddsky/shelves/*.csv): published samples that the archives do not index by object.

Every source answers with a status: "ok", "empty" (it answered: nothing there) or "unavailable" (the query failed, or there
is no token). An unavailable source is never read as "nothing found": `prior_art()` reports it and sets `complete` to False.

Nothing here calls the network except `simbad()`, `ned()` and `ads_papers()`.
"""

from __future__ import annotations

import csv
import functools
import io
import math
import os
import re
from pathlib import Path

from .data.http import request
from .data.provenance import Provenance, now_iso

SIMBAD_TAP = "https://simbad.harvard.edu/simbad/sim-tap/sync"
NED_TAP = "https://ned.ipac.caltech.edu/tap/sync"
ADS_API = "https://api.adsabs.harvard.edu/v1"
ADS_TOKEN_FILE = Path("~/.config/oddsky/ads-token")
ADS_ROWS = 200       # per page
ADS_MAX_ROWS = 1000  # stop paging here and say so
# A lookup takes seconds to half a minute (ADS needs about 17 s to translate an object name, 2026-11-05). A service that is
# down is reported as unavailable, not waited for.
TIMEOUT = 60.0
RETRIES = 2

SHELVES_DIR = Path(__file__).parent / "shelves"
SOURCES = {"simbad": "SIMBAD", "ned": "NED", "ads": "ADS"}

# Keywords matched against paper titles, case-insensitively and on word boundaries; a hyphen counts as a space, so
# "changing look" also matches "changing-look". A trailing * matches any ending ("eclips*": eclipse, eclipses, eclipsing).
# Without it the whole word must match ("dip" is not "dipole", "nova" is not "innovative"). Plain data: add a topic or a
# keyword here. A keyword too many costs a title to read; a keyword too few can cost a false discovery.
TOPICS: dict[str, tuple[str, ...]] = {
    "transient": ("tidal disruption*", "TDE", "TDEs", "flar*", "outburst*", "echo*", "changing look*", "supernova*", "nova",
                  "novae", "transient*", "fad*", "decline*", "declining", "brightening*", "rebrightening*", "variab*"),
    "dimming": ("dip", "dips", "dipper*", "dimm*", "occult*", "eclips*", "disappear*", "vanish*"),
    "infrared_excess": ("infrared excess*", "IR excess*", "debris disk*", "debris disc*", "dust*", "circumstellar"),
    "binary": ("binar*", "companion*", "orbit*"),
}


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


# ----------------------------------------------------------------------------- the three services
def _sep_arcsec(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    dra = ((ra1 - ra2 + 180.0) % 360.0 - 180.0) * math.cos(math.radians(0.5 * (dec1 + dec2)))
    return 3600.0 * math.hypot(dra, dec1 - dec2)


def _cone(frame: str, ra: float, dec: float, radius_arcsec: float) -> str:
    return (f"CONTAINS(POINT('{frame}',ra,dec),CIRCLE('{frame}',{ra:.7f},{dec:.7f},{radius_arcsec / 3600:.7f}))=1")


def _tap(method: str, url: str, query: str, first_column: str) -> list[dict]:
    """Rows of a TAP CSV answer. A header alone is an empty table; an answer that does not start with the expected header
    is an error document, and raises: it is not "no rows"."""
    form = {"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": query}
    r = request(method, url, retries=RETRIES, timeout=TIMEOUT, **({"data": form} if method == "POST" else {"params": form}))
    text = r.text.lstrip("﻿").strip()
    if text.split(",", 1)[0].split("\n", 1)[0].strip().strip('"') != first_column:
        raise ValueError(f"not a CSV table: {text[:120]!r}")
    return list(csv.DictReader(io.StringIO(text)))


def _nearest(rows: list[dict], ra: float, dec: float) -> tuple[dict, float]:
    seps = [_sep_arcsec(float(r["ra"]), float(r["dec"]), ra, dec) for r in rows]
    i = min(range(len(rows)), key=seps.__getitem__)
    return rows[i], seps[i]


def simbad(ra: float, dec: float, radius_arcsec: float = 5.0) -> tuple[dict, Provenance]:
    """SIMBAD at a position: `{"object": {main_id, otype, ra, dec, sep_arcsec} or None, "n_objects", "papers": [{bibcode,
    title}]}`. The object is the nearest within the radius; the papers are those of every object within it. `prov.status`
    is 'ok', 'empty' (SIMBAD answered: no object) or 'unavailable' (a query failed; if it was the reference query, the
    object is still returned and the paper list is not to be trusted)."""
    prov = Provenance(archive="SIMBAD TAP (simbad.harvard.edu)", query={"ra": ra, "dec": dec, "radius_arcsec": radius_arcsec})
    out: dict = {"object": None, "n_objects": 0, "papers": []}
    # This mirror rejects aliased columns and ORDER BY alias.col: the queries stay unaliased, and sorting is done here.
    cone = _cone("ICRS", ra, dec, radius_arcsec)
    try:
        rows = _tap("POST", SIMBAD_TAP, f"SELECT main_id, otype, ra, dec FROM basic WHERE {cone}", "main_id")
        if rows:
            row, sep = _nearest(rows, ra, dec)
            out["object"] = {"main_id": " ".join(row["main_id"].split()), "otype": row.get("otype") or None,
                             "ra": float(row["ra"]), "dec": float(row["dec"]), "sep_arcsec": round(sep, 2)}
            out["n_objects"] = len(rows)
    except Exception as e:  # noqa: BLE001
        prov.status = "unavailable"
        prov.notes.append(str(e)[:200])
        return out, prov
    if not rows:
        prov.status = "empty"
        return out, prov
    try:
        refs = _tap("POST", SIMBAD_TAP, "SELECT bibcode, title FROM basic JOIN has_ref ON oidref=oid "
                    f"JOIN ref ON oidbib=oidbibref WHERE {cone}", "bibcode")
    except Exception as e:  # noqa: BLE001
        prov.status = "unavailable"
        prov.notes.append(f"object found, but its references could not be read: {str(e)[:200]}")
        return out, prov
    seen: dict[str, dict] = {}
    for r in refs:
        if r.get("bibcode"):
            seen.setdefault(r["bibcode"].strip(), {"bibcode": r["bibcode"].strip(), "title": r.get("title") or ""})
    out["papers"] = list(seen.values())
    prov.rows_raw, prov.rows_kept = len(refs), len(seen)
    return out, prov


def ned(ra: float, dec: float, radius_arcsec: float = 5.0) -> tuple[dict | None, Provenance]:
    """The NED object nearest to a position within the radius: `{prefname, type, z, ra, dec, sep_arcsec, n_objects}`, or
    None. `prov.status` is 'ok', 'empty' (NED answered: no object) or 'unavailable'."""
    prov = Provenance(archive="NED TAP (NEDTAP.objdir)", query={"ra": ra, "dec": dec, "radius_arcsec": radius_arcsec})
    try:
        rows = _tap("GET", NED_TAP, f"SELECT * FROM NEDTAP.objdir WHERE {_cone('J2000', ra, dec, radius_arcsec)}", "prefname")
        obj = None
        if rows:
            row, sep = _nearest(rows, ra, dec)
            obj = {"prefname": " ".join(row["prefname"].split()), "type": row.get("prefphytype") or None,
                   "z": float(row["z"]) if row.get("z") not in (None, "") else None,
                   "ra": float(row["ra"]), "dec": float(row["dec"]), "sep_arcsec": round(sep, 2), "n_objects": len(rows)}
    except Exception as e:  # noqa: BLE001
        prov.status = "unavailable"
        prov.notes.append(str(e)[:200])
        return None, prov
    prov.rows_raw = len(rows)
    if obj is None:
        prov.status = "empty"
        return None, prov
    prov.rows_kept = 1
    return obj, prov


def ads_token() -> str | None:
    """The ADS API token: $ADS_TOKEN, else ~/.config/oddsky/ads-token. Never printed, logged or stored in a result."""
    if t := os.environ.get("ADS_TOKEN", "").strip():
        return t
    f = ADS_TOKEN_FILE.expanduser()
    return (f.read_text().strip() or None) if f.is_file() else None


def ads_papers(name: str) -> tuple[list[dict], Provenance]:
    """The papers ADS finds for a NED object name: `[{bibcode, title, year}]`. ADS translates the name into a query
    (abstract text, SIMBAD id, NED id), which is then searched. `prov.status` is 'ok', 'empty' (ADS answered: no papers) or
    'unavailable' (no token, or a request failed): without a token this source has not been asked, which is not 'empty'."""
    prov = Provenance(archive="NASA ADS (papers attached to the NED object)", query={"object": name})
    token = ads_token()
    if token is None:
        prov.status = "unavailable"
        prov.notes.append("no ADS token (set ADS_TOKEN or write it to ~/.config/oddsky/ads-token)")
        return [], prov
    auth = {"Authorization": f"Bearer {token}"}
    docs: list[dict] = []
    try:
        quoted = name.replace("\\", "\\\\").replace('"', '\\"')
        r = request("POST", f"{ADS_API}/objects/query", retries=RETRIES, timeout=TIMEOUT, headers=auth,
                    json={"query": [f'object:"{quoted}"']})
        q = r.json()["query"]
        found = None
        while found is None or len(docs) < min(found, ADS_MAX_ROWS):
            params = {"q": q, "fl": "bibcode,title,year", "rows": ADS_ROWS, **({"start": len(docs)} if docs else {})}
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
    if len(docs) < found:
        prov.notes.append(f"ADS holds {found} papers; only the first {len(docs)} were read")
    if not docs:
        prov.status = "empty"
        return [], prov
    papers = []
    for d in docs:
        title = d.get("title") or ""
        papers.append({"bibcode": d.get("bibcode"), "title": title[0] if isinstance(title, list) and title else str(title or ""),
                       "year": d.get("year")})
    return papers, prov


# ----------------------------------------------------------------------------- the shelves
def load_shelves(directory: Path | str | None = None) -> list[dict]:
    """Every shelf in the directory (default: src/oddsky/shelves): `{shelf, title, bibcode, topics, sources: [{name, ra,
    dec}]}`. A shelf is a CSV: comment lines `# title: ...`, `# bibcode: ...`, `# topics: a, b`, then the columns
    name,ra,dec in degrees. An empty or missing directory is no shelves. A shelf that cannot be read raises: a broken
    shelf must not look like a shelf without the object."""
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
    """Display names of the sources that could not be queried in a `prior_art()` result."""
    return [SOURCES.get(k, k) for k, v in (pa.get("sources") or {}).items() if v.get("status") == "unavailable"]


def prior_art(ra: float, dec: float, radius_arcsec: float = 5.0, topics: str | list[str] | None = None) -> dict:
    """Is it new? Everything the archives and the shelves hold on a position, and a verdict:

    - "unlisted": no SIMBAD object, no NED object, no shelf hit.
    - "catalogued": an object exists, but no paper title matches the topics and no shelf holds it.
    - "studied": at least one paper title matches the topics, or a shelf holds it. Read those before calling anything new.

    Papers from SIMBAD and from NED/ADS are merged by bibcode; `topical_papers` (newest first) are those whose title matches
    one of `topics` (default: all of TOPICS). `complete` is False when a source could not be queried: the verdict is then
    what the answering sources support, and is not final. `summary` says all of this in one sentence."""
    wanted = _wanted(topics)
    sim, p_sim = simbad(ra, dec, radius_arcsec)
    ned_obj, p_ned = ned(ra, dec, radius_arcsec)
    if ned_obj:
        ads, p_ads = ads_papers(ned_obj["prefname"])
    else:
        # ADS is asked about the NED object. With no NED object there is nothing to ask; with NED down, the question
        # could not be put, and that is a source that was not queried.
        down = p_ned.status == "unavailable"
        ads, p_ads = [], Provenance(archive="NASA ADS (papers attached to the NED object)",
                                    status="unavailable" if down else "empty",
                                    notes=["not asked: " + ("NED could not be queried, so there was no object name to look up"
                                                            if down else "there is no NED object to look up")])
    papers: dict[str, dict] = {}
    for source, rows in (("simbad", sim.get("papers") or []), ("ads", ads)):
        for r in rows:
            bib = str(r.get("bibcode") or "").strip()
            if not bib:
                continue
            title = " ".join(str(r.get("title") or "").split())
            p = papers.setdefault(bib, {"bibcode": bib, "year": _year(bib), "title": title, "sources": [], "topics": []})
            p["title"] = p["title"] or title
            if source not in p["sources"]:
                p["sources"].append(source)
            p["topics"] = [t for t in TOPICS if t in p["topics"] or t in matched_topics(title)]
    topical = sorted((p for p in papers.values() if set(p["topics"]) & set(wanted)),
                     key=lambda p: (p["year"] or 0, p["bibcode"]), reverse=True)
    shelves = shelf_hits(ra, dec, radius_arcsec)
    sim_obj = sim.get("object")
    out = {
        "ra": ra, "dec": dec, "radius_arcsec": radius_arcsec, "topics": wanted, "checked_at": now_iso(),
        "sources": {k: {"archive": p.archive, "status": p.status, "notes": p.notes}
                    for k, p in (("simbad", p_sim), ("ned", p_ned), ("ads", p_ads))},
        "simbad": ({"main_id": sim_obj.get("main_id"), "otype": sim_obj.get("otype"), "sep_arcsec": sim_obj.get("sep_arcsec"),
                    "n_objects": sim.get("n_objects") or 1} if sim_obj else None),
        "ned": ({"prefname": ned_obj.get("prefname"), "type": ned_obj.get("type"), "z": ned_obj.get("z"),
                 "sep_arcsec": ned_obj.get("sep_arcsec"), "n_objects": ned_obj.get("n_objects") or 1} if ned_obj else None),
        "n_papers": len(papers), "n_topical": len(topical), "topical_papers": topical, "shelf_hits": shelves,
    }
    out["complete"] = not unavailable_names(out)
    out["verdict"] = ("studied" if topical or shelves else
                      "catalogued" if sim_obj or ned_obj or papers else "unlisted")
    out["summary"] = _summary(out)
    return out


def _summary(pa: dict) -> str:
    n, top, shelves, verdict = pa["n_papers"], pa["topical_papers"], pa["shelf_hits"], pa["verdict"]
    name = (pa["simbad"] or {}).get("main_id") or (pa["ned"] or {}).get("prefname") or "this position"
    topics = ", ".join(pa["topics"])
    papers = "paper" if n == 1 else "papers"
    if verdict == "studied":
        parts = []
        if top:
            parts.append(f"{len(top)} of {n} {papers} on {name} {'matches' if len(top) == 1 else 'match'} the topics "
                         f"({topics}); the newest is {top[0]['bibcode']}, \"{top[0]['title'].rstrip('.')}\"")
        if shelves:
            more = f" and {len(shelves) - 1} more" if len(shelves) > 1 else ""
            parts.append(f"{'it' if top else name} is in a published sample on the shelves as {shelves[0]['name']}: "
                         f"{shelves[0]['bibcode']}, \"{shelves[0]['title'].rstrip('.')}\"{more}")
        body = "; ".join(parts)
    elif verdict == "catalogued":
        body = (f"{name} is listed in {n} {papers}, and no title matches the topics ({topics})" if n else
                f"{name} is in the archives with no paper attached")
    elif pa["complete"]:
        body = f"no SIMBAD object, no NED object and no shelf entry within {pa['radius_arcsec']:g}\""
    else:
        body = f"the sources that answered hold nothing within {pa['radius_arcsec']:g}\""
    if pa["complete"]:
        return f"{verdict.capitalize()}: {body}."
    return f"Not final ({_and(unavailable_names(pa))} could not be queried); so far {verdict}: {body}."
