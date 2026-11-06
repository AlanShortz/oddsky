# Shelves

A shelf is a published sample that the archives do not index by object. SIMBAD and NED attach a paper to an
object only when someone has linked the two. A table of 19 galaxies in a journal PDF, or a candidate list in a
supplementary file, often never gets linked. The Librarian (`src/oddsky/librarian.py`) reads every `*.csv` in
this directory and reports a position that falls on one of them as "studied", whatever else it finds.

## Format

One CSV file per published sample. Leading comment lines carry the metadata, then the columns `name,ra,dec`:

```
# title: <the paper's title, as published>
# bibcode: <the paper's ADS bibcode>
# topics: transient
name,ra,dec
<name as the paper gives it>,<RA in degrees, J2000>,<Dec in degrees, J2000>
```

- `# title:` and `# bibcode:` are required. A shelf without them does not load.
- `# topics:` is a comma list of topic names from `TOPICS` in `librarian.py`. It is shown with a hit. A hit on
  any shelf makes the verdict "studied", whatever the topics asked for.
- `ra` and `dec` are decimal degrees (0 to 360, -90 to 90). Not hours, not sexagesimal. The loader refuses
  values outside those ranges.
- `name` is the name the paper gives the object (`SDSS J002331.3+055354.8`), not one made up from the
  coordinates, so that a hit can be found in the paper's table.
- A shelf needs at least one row. A shelf with none does not load: it would answer "not in this paper" for
  every position.
- Other `#` lines are comments (`# source:`, `# note:`, `# dropped:`). Extra columns are ignored.
- Name the file after the paper, for example `wang2018_mir_decline.csv`.

## Rules

- A shelf holds what the paper published, copied from its table, and nothing else. Do not add rows from memory
  and do not fill in coordinates by guessing. Say in a comment line where the rows came from (table number,
  VizieR catalogue, supplementary file) and when.
- Shelve the whole sample, not the rows that matter today. A partial shelf reads as "not in this paper" for
  every row left out.
- A shelf holds the paper's own sample. A paper's other tables are often not that: a compilation of objects
  from the literature belongs to the papers it cites, and an observing log can carry typing errors that the
  sample table does not. Shelve the table that defines the sample, and say in a comment which tables were
  left out and why.
- If a shelf does not hold everything the paper names (objects discussed outside its table), say so in a
  `# note:` line.
- A shelf that cannot be parsed, or that has no rows, raises an error. It must never look like a shelf that
  does not hold the object.

## Building a shelf from VizieR

```
uv run python scripts/build_shelf.py J/MNRAS/491/4925/table2 graham2020_csq 2020MNRAS.491.4925G transient \
    "Understanding extreme quasar optical variability with CRTS - II. Changing-state quasars" --note "..."
```

The script takes VizieR table names (comma-separated for several), not a catalogue id: it refuses
`J/MNRAS/491/4925`, because that would shelve every table under it. It keeps the table's own name column
(the one VizieR marks as the main identifier, or `--name-column`), and falls back to a name made from the
coordinates only when the table has none. `--drop NAME` leaves a row out; say why with `--note`. Check a
new shelf against the paper before trusting it: VizieR computes positions from the table, and a sign error
in a table becomes an object where there is nothing.

## The shelves

| shelf | holds | left out |
| --- | --- | --- |
| `wang2018_mir_decline` | Table 1 of Wang et al. 2018 (14 galaxies), typed from the paper | objects the paper names outside Table 1 (SDSS J095858.5+021459) |
| `graham2020_csq` | Table 2 of Graham et al. 2020 (111 changing-state quasars), from VizieR | table A1 (61 changing-look quasars from the literature: other papers' objects; the key to its reference numbers is in a ReadMe that could not be read on 2026-11-05) and table B1 (the observing log; three of its names are wrong) |
| `jiang2021_mirong` | VizieR J/ApJS/252/32, its one table (137 MIRONG galaxies), named by coordinates | |
| `macleod2019_clq` | VizieR J/ApJ/874/8, both tables (changing-look quasar candidates and their spectral decomposition), named by coordinates | not yet rebuilt from named tables |

An empty directory is fine: the Librarian then reports no shelf hits.

Shelves are for samples of tens or hundreds of objects. Catalogues of thousands or millions (VSX, VarWISE,
Milliquas, the WISE AGN catalogues) are asked by cone instead: see `CATALOGUES` in `librarian.py`.
