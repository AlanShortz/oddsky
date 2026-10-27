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
