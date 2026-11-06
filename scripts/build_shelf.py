"""Build a Librarian shelf (src/oddsky/shelves/<name>.csv) from named VizieR tables: every row's J2000 position, under the
name the paper gives the object.

usage: build_shelf.py TABLE[,TABLE...] SHELF_NAME BIBCODE TOPICS "TITLE" [--name-column COL] [--drop NAME ...] [--note TEXT]
  e.g. build_shelf.py J/MNRAS/491/4925/table2 graham2020_csq 2020MNRAS.491.4925G transient "Understanding ... quasars"

Name the tables, not the catalogue: a catalogue's other tables are often not the paper's sample. `J/MNRAS/491/4925` holds
Graham et al.'s 111 changing-state quasars (table2), a compilation of other people's changing-look quasars (tablea1) and an
observing log whose names carry three sign and typing errors (tableb1); a shelf built from all three called 61 literature
objects Graham's and put three objects where there is nothing. A bare catalogue id is refused.

The name is the table's own identifier column (the one VizieR marks `meta.id;meta.main`, or --name-column); only a table
without one gets a name made from the coordinates. The CfA mirror is used because the CDS server times out from here."""
import argparse
import re
import sys
from pathlib import Path

import requests

VIZIER = "https://vizier.cfa.harvard.edu/viz-bin/asu-tsv"
SHELVES = Path(__file__).resolve().parent.parent / "src" / "oddsky" / "shelves"


def designation(ra: float, dec: float) -> str:
    h, d = ra / 15, abs(dec)
    return (f"J{int(h):02d}{int(h * 60 % 60):02d}{h * 3600 % 60:05.2f}{'+' if dec >= 0 else '-'}"
            f"{int(d):02d}{int(d * 60 % 60):02d}{d * 3600 % 60:04.1f}")


def read_table(table: str, name_column: str | None) -> tuple[list[tuple[str, float, float]], str | None]:
    """The rows of one VizieR table as (name, ra, dec), and the name column used (None: names made from coordinates)."""
    t = requests.get(VIZIER, params={"-source": table, "-out.max": "999999", "-out.add": "_RAJ2000,_DEJ2000"}, timeout=120).text
    if m := re.search(r"^#INFO\tError=([^\t\n]*)", t, re.M):
        sys.exit(f"VizieR, {table}: {m.group(1).strip()}")
    if len(re.findall(r"^#Table\t", t, re.M)) != 1:
        sys.exit(f"{table}: VizieR answered with {len(re.findall(r'^#Table', t, re.M))} tables; name one table, e.g. {table}/table1")
    main_ids = [m.group(1) for m in re.finditer(r"^#Column\t([^\t]+)\t[^\n]*\[ucd=meta\.id;meta\.main\]", t, re.M)]
    lines = [ln for ln in t.splitlines() if not ln.startswith("#")]
    rule = next((i for i, ln in enumerate(lines) if re.fullmatch(r"-+(\t-+)*", ln.strip())), None)
    if rule is None:
        sys.exit(f"{table}: no rows")
    cols = [c.strip() for c in next(ln for ln in lines[:rule] if ln.strip()).split("\t")]
    if name_column and name_column not in cols:
        sys.exit(f"{table}: no column {name_column!r}; columns are {cols}")
    name_column = name_column or next((c for c in main_ids if c in cols), None)
    rows = []
    for ln in lines[rule + 1:]:
        if not ln.strip():
            continue
        row = dict(zip(cols, (c.strip() for c in ln.split("\t")), strict=False))
        try:
            ra, dec = float(row["_RAJ2000"]), float(row["_DEJ2000"])
        except (KeyError, ValueError):
            sys.exit(f"{table}: a row without a J2000 position: {ln[:80]!r}")
        name = " ".join(row[name_column].split()) if name_column else ""
        rows.append((name or designation(ra, dec), ra, dec))
    return rows, name_column


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("tables", help="VizieR table names, comma-separated (J/MNRAS/491/4925/table2), not a bare catalogue id")
    ap.add_argument("shelf")
    ap.add_argument("bibcode")
    ap.add_argument("topics")
    ap.add_argument("title")
    ap.add_argument("--name-column", help="the table's column to use as the name (default: its main identifier column)")
    ap.add_argument("--drop", action="append", default=[], metavar="NAME", help="leave out the row with this name; repeatable. "
                    "Say why with --note")
    ap.add_argument("--note", action="append", default=[], help="a comment line for the shelf; repeatable")
    a = ap.parse_args()

    rows, used = [], []
    for table in a.tables.split(","):
        got, column = read_table(table.strip(), a.name_column)
        rows += got
        used.append(f"{table.strip()} ({len(got)} rows, named by {'its column ' + column if column else 'their coordinates'})")
    missing = [d for d in a.drop if d not in {r[0] for r in rows}]
    if missing:
        sys.exit(f"--drop: no row named {missing}")
    rows = sorted({r for r in rows if r[0] not in a.drop}, key=lambda r: (r[1], r[2], r[0]))
    if not rows:
        sys.exit("no rows with positions")
    if "," in "".join(r[0] for r in rows):
        sys.exit("a name contains a comma; the shelf format has no quoting")
    out = SHELVES / f"{a.shelf}.csv"
    with open(out, "w") as f:
        f.write(f"# title: {a.title}\n# bibcode: {a.bibcode}\n# topics: {a.topics}\n")
        f.write(f"# source: VizieR {'; '.join(used)}; positions are VizieR's _RAJ2000, _DEJ2000; fetched from "
                "vizier.cfa.harvard.edu with scripts/build_shelf.py\n")
        for d in a.drop:
            f.write(f"# dropped: {d}\n")
        for note in a.note:
            f.write(f"# note: {note}\n")
        f.write("name,ra,dec\n")
        for name, ra, dec in rows:
            f.write(f"{name},{ra:.5f},{dec:.5f}\n")
    print(out, len(rows), "rows")


if __name__ == "__main__":
    main()
