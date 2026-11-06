# Epistemics: how Oddsky keeps itself honest

## Claim tags

| tag | meaning | example |
|---|---|---|
| `observed` | read straight off the data, no modelling | "W2 is 0.8 mag brighter in 2018-2020 than in 2014-2017" |
| `computed` | the output of a named tool call | "W1-W2 tracks W1 with r = -0.98 (K7)" |
| `inferred` | reasoning from evidence to a conclusion | "the IR excess is warm dust near the star" |
| `speculated` | a guess worth writing down | "two planetary embryos collided" |

Observed and computed claims should cite ledger call ids (`K12`). Every call is logged with its
arguments and a digest of its result in `ledger.jsonl`; `oddsky replay <case>` re-runs them and
fails loudly if any result has changed.

## The discovery ladder

`observation → anomaly → reproduced → interpreted → validated`, with two honourable exits:
`artifact` (it was the instrument or a neighbour) and `closed` (explained, nothing new).

- **anomaly**: something the Skeptic cannot explain away.
- **reproduced**: seen by an independent instrument or observer, or re-derived by a second
  investigator from the raw archive data.
- **interpreted**: a hypothesis survives its strongest objection and makes a prediction.
- **validated**: a sealed prediction came true, or a professional astronomer reviewed the case and
  signed it (`reviews/` in the case directory). Model consensus is never validation.

## The Skeptic

Deterministic code, not an agent. It checks: neighbours inside each survey's beam (Gaia DR3),
WISE saturation and quality cuts, whether the optical record has an independent second source,
whether a series starts mid-event (against Gaia's 2014-2017 baseline), whether a dip is
consistent across bands, whether a period is just the day/month/year/TESS orbit or a window
alias, whether an event's onset fell in a gap, TESS dips near momentum dumps and sector edges,
and astrometric wobble (RUWE). It cannot be argued with. That is the point.

## The Librarian

Also deterministic code, not an agent. The Skeptic asks "is it real?". The Librarian asks "is it
new?". For a sky position it looks up the objects in SIMBAD and NED, merges the papers that SIMBAD
and ADS attach to them, and matches their titles against topic keywords (transient, dimming,
infrared excess, binary). It also asks five large catalogues by cone (VSX, VarWISE, Milliquas,
and the WISE AGN catalogues of Secrest et al. 2015 and Assef et al. 2018) and the shelves. It
gives one of four verdicts:

- **unlisted**: no SIMBAD object, no NED object, no shelf entry. If something lies within 30",
  the answer names it.
- **catalogued**: an object exists, but no paper title matches the topics.
- **mentioned**: titles match the topics, but only in papers that list more than 500 objects
  (surveys, catalogues, rate papers). The object is in their tables; they are not about it.
- **studied**: a title matches in a paper about at most 500 objects, or a shelf holds the
  position, or SIMBAD types an object there as a transient (supernova, nova, transient event
  and the like), or a catalogue of variables (VSX, VarWISE) lists it. These must be read before
  anything is called new.

"Catalogued" is not evidence that nothing is published. It means the bibliographies the
Librarian can read hold nothing on the topics under this object. At a survey position that is
often very little: SIMBAD has no object, NED's object is the survey's own entry, and ADS knows
no paper under that name. Papers whose titles the keywords miss, objects published under a
position instead of a name, and lists nobody shelved all read "catalogued". The same holds
for "unlisted" and "mentioned". Only "studied" is a finding; the other three say what was not
found, and where.

Membership of an AGN catalogue (Milliquas, Secrest, Assef) is reported in the answer and does
not change the verdict: it says what the object probably is, not that its behaviour has been
published. A paper that only ADS lists has no object count and is taken to be about the object.

SIMBAD's positions are for J2000, so a star with a large proper motion is not where a later
survey saw it: give the epoch of the position (`--epoch 2010.5` for AllWISE) and SIMBAD's stars
are moved to that date before matching; NED, the catalogues and the shelves are matched as
catalogued.

A source that could not be queried is reported as unavailable. It is never read as "nothing
found", and the verdict is then not final. The same goes for an ADS list longer than the 1000
papers that are read. ADS has two more answers that are not "nothing found": "not asked" (there
was no object name to look up) and "unresolved" (ADS did not recognise the name as an object,
and only the text of its abstracts was searched). The shelves (`src/oddsky/shelves/`) hold
published samples that the archives do not index by object: a table in a paper that nobody
linked to its sources. `oddsky librarian RA DEC` asks for one position; `oddsky fetch` stores
the answer with the case, and the Skeptic reports it as the `prior_art` check ("studied" is a
warning; the other three pass when every source answered).

It exists because H-0017 called a galaxy its "best candidate" when it was object 12 of Wang et
al. 2018. The bibliography of that position would have said so in ten seconds. A title match is
a reason to read a paper, not a reading of it.

## Texts that leave the repo

A case has a ledger; a paper, an email to an astronomer or a hunt write-up did not, and that is where
errors got through. The first draft of the H-0016 research note (2026-11-05) carried a rate with the
wrong denominator, "isolated" where the data said 33 of 46, and a count nobody could trace: each was
typed from a working summary, not recomputed. The rules since:

- **Every number has a receipt.** A claims file next to the document recomputes each number from the
  data tables, and `oddsky paper-check <claims.py>` fails on a value that does not round to what the
  text prints, on a numeral nobody declared, and on a declared phrase the text no longer contains.
  A number that cannot be recomputed from files (a remote count) is declared `external` with its
  source and is listed in every report.
- **"All", "none" and "every" are tested on every row**, not on the examples that suggested them
  (`Claims.every`).
- **The referee reads the final text.** A review binds to the document's sha256;
  `paper-check --final` fails if the text changed after the review. Reviewing the hunt and then
  writing the paper does not count.
- **A comparison is reported after both sides have had the same checks.** The first H-0017 count
  (186 nuclei heated against 116 cooled) compared a validated list with an unvalidated one; most of
  the 186 were sources AllWISE had split in two. Until then a number is called provisional, in
  those words.
- **A fetch that failed is `untested`**, never a class of result, and a script whose inputs mostly
  failed exits non-zero. (An image service outage once labelled thirteen sources "partial".)

## Trials

**Blind**: identity, coordinates and dates scrubbed, observers pseudonymised; the investigator
ranks explanation classes with probabilities. Scored by top-1, top-2 and multi-class Brier score
(uniform guessing over 11 classes: top-1 0.09, Brier 0.91).

**Hindsight**: also cut at a date. The investigator registers machine-checkable predictions about
what happens next; the scorer maps them back onto the real calendar and grades them against what
the sky did. Brier score on the stated probabilities.

**Sealing**: answers are written with a random salt, and their sha256 is committed before any
investigator runs. The plaintext is revealed afterwards; `oddsky trial verify` checks it matches.

**Known leaks** (we say them out loud): blinding hides names, not physics. A famous phenomenon
can be recognised from its shape, and recognising it is legitimate. Magnitudes and Gaia context
narrow the field. Investigators with filesystem access could read the answers; MCP blind mode
(`oddsky mcp --blind <packet>`) is the enforcement path, the CLI is the honour system.

## What a future evaluation study looks like (not v1)

Four arms on the same sealed case set: agent alone; agent + Skeptic; human alone; human + agent.
Measure accuracy, calibration, and how often each arm is fooled by planted artifacts ("salted"
packets, where we inject a known instrumental signal into real data).
