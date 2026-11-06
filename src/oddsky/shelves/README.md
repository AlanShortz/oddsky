# Shelves

A shelf is a published sample that the archives do not index by object. SIMBAD and NED attach a paper to an
object only when someone has linked the two. A table of 19 galaxies in a journal PDF, or a candidate list in a
supplementary file, often never gets linked. The Librarian (`src/oddsky/librarian.py`) reads every `*.csv` in
this directory and reports a position that falls on one of them as "studied".

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
- Other `#` lines are comments. Extra columns are ignored.
- Name the file after the paper, for example `wang2018_mir_decline.csv`.

## Rules

- A shelf holds what the paper published, copied from its table, and nothing else. Do not add rows from memory
  and do not fill in coordinates by guessing. Say in a comment line where the rows came from (table number,
  VizieR catalogue, supplementary file) and when.
- Shelve the whole sample, not the rows that matter today. A partial shelf reads as "not in this paper" for
  every row left out.
- A shelf that cannot be parsed raises an error. It must never look like a shelf that does not hold the object.

There are no shelves yet. An empty directory is fine: the Librarian then reports no shelf hits.
