<p align="center"><img src="web/og.png" alt="Oddsky: ASASSN-21qj, infrared and optical on one time axis" width="720"></p>

# oddsky

*The universe is an open question.*

**An open observatory your AI agent can use.** Point Claude Code, Codex, Cursor or a local model at
real telescope data on strange stars. What comes back is an investigation you can check: every
claim is tagged with how we know it, every number has a receipt you can replay, and every prediction
is sealed and then graded by the sky.

Oddsky ships the observatory, not the AI. It costs nothing to run, needs no account or API key,
and works with whatever agent you already have.

```bash
claude mcp add oddsky -- uvx oddsky mcp
# before the PyPI release, from a clone:
claude mcp add oddsky -- uv run --directory /path/to/oddsky oddsky mcp
```

Then ask: *"Open Oddsky case OS-0001. Run the skeptic first, then try to break the leading
hypothesis. Tag every claim honestly."*

## The first case: the star that glowed before it dimmed

[ASASSN-21qj](cases/OS-0001) is a Sun-like star 1,850 light-years away. NEOWISE shows its infrared
switching on between November 2017 and April 2018: W2 brightened 0.8 mag, and the excess has a
colour temperature of about 1,000 K. Three years later the visible star began to flicker and fade
by up to 2 magnitudes, more in blue than in red, which is what small dust grains do. The first
Oddsky investigation ([write-up](cases/OS-0001/investigations/claude-opus-5.5-2026-10-27.md)) was
done entirely through Oddsky tools: 95 logged tool calls, 17 tagged claims, 6 competing hypotheses.
It also found two things no paper has reported, because they happened after the papers were written:

- the star has been back at its pre-event brightness, and flat to 0.005 mag, since early 2025;
- an apparent 2025 "recovery" in the I and R bands is a step change on one night, a calibration
  artifact in the only optical record.

It then sealed three predictions for 2027 with probabilities attached. The sky will grade them.

The optical light curve is 7,115 measurements by one amateur astronomer, Franz-Josef Hambsch (AAVSO
code HMB). Oddsky credits observers by name, and the Skeptic warns that a single observer is a
single point of failure.

## What's in the box

| | |
|---|---|
| **The observatory** | 21 MCP tools: case overview, light curves, changepoints, excursions (dips and flares), Lomb-Scargle with spectral-window alias flags, cross-band colour slopes, WISE colour and infrared-excess temperature, Gaia neighbours, and tools for recording claims, hypotheses and predictions. `oddsky tools` lists them. |
| **Archives** | Gaia DR3 (context, neighbours, variability), NEOWISE 2014-2024 (quality-cut, visit-binned), AAVSO (a century of amateur photometry), TESS (SPOC/QLP), ZTF, ASAS-SN. Every cut is written to provenance. |
| **The Skeptic** | Deterministic artifact checks: blends inside each survey's beam, saturation, single-observer data, series that start mid-event (against Gaia's baseline), colour coherence across bands, survey-rhythm aliases, unobserved onsets, TESS dips on momentum dumps and sector edges, RUWE. It is code, so it cannot be talked out of a warning. |
| **Cases** | A case is a directory (`cases/OS-0001/`): `case.yaml` holds the argument, `data/` the evidence, and `ledger.jsonl` every tool call with a digest of its result. Fork = fork. Review = pull request. `oddsky replay OS-0001` re-runs the ledger. |
| **Trials** | Blind (identity, coordinates and dates scrubbed; name the explanation), hindsight (data cut at a date; forecast what happens next, graded against what actually happened), and salted (real data with planted spacecraft artifacts). Answers are sha256-sealed before anyone runs. |
| **The viewer** | `web/`: zero-build static site. The shared time axis, tagged claims with receipts, hypotheses, sealed predictions, the Skeptic report, provenance. Red-light mode for the observatory at night. |

## Strange Stars Trial 001

Ten packets of real archive data with names, coordinates and dates removed, including one ordinary
star and one quiet star with **planted** spacecraft artifacts. Two are hindsight packets, cut at a
date. The answers were sealed (`sha256 4608af90…`, committed in `eac42b3`) before any investigator
ran, then revealed and verified (`oddsky trial verify trials/strange-stars-001`). Two agents used
the same tools and the same prompt:

| | top-1 | Brier (lower is better) | mean p(truth) | hindsight forecasts |
|---|---|---|---|---|
| claude-opus-5.5 | **10/10** | **0.10** | 0.77 | 7 of 8 true (the miss was rated 8%); Brier 0.09 |
| claude-haiku-5.5 | 5/10 | 0.71 | 0.38 | 2 of 3 resolved true; 3 still pending |
| uniform guessing | 0.9/10 | 0.91 | 0.09 | |

What's worth knowing, including the parts that don't flatter anyone:

- **Opus recognised 8 of the 10 stars** (self-reported, tagged as speculation): R CrB, SS Cyg,
  EE Cep, ASASSN-21qj and others. Blinding hides names, not physics. On the two packets it did not
  recognise (the ordinary star and the salted one) it went 2/2. Trial 002 needs stars nobody has
  written about, and that's where the advisor comes in.
- **EE Cep, from data cut a year before its 2025 eclipse:** Opus timed the next eclipse from the
  previous six (period 2048 d) and registered four forecasts. All four came true, including the one
  it had rated at 45%. Haiku called the star a pulsator.
- **The salted packet nearly fooled Opus:** artifact 0.33 against dust 0.30. Its reason is a fair
  criticism of us: our planted dips were smoother and longer than real momentum-dump glitches.
  Haiku missed them entirely and called the star normal.
- **We found a bug in our own grader.** "Brightest" was the 2nd percentile of all points, so dense
  quiescent sampling hid real SS Cyg outbursts and two correct forecasts were graded false. v2
  uses nightly medians. Because the change came after the reveal, both gradings are published in
  [the scorecards](trials/strange-stars-001/results).

Every claim, hypothesis and prediction the agents made is in `trials/strange-stars-001/runs/`, and
every tool call in it replays.

## Run it locally

```bash
git clone https://github.com/oddsky-org/oddsky && cd oddsky
uv sync --all-extras                       # Python 3.11-3.14
uv run oddsky skeptic OS-0001              # the Skeptic's report on the first case
uv run oddsky call ir_excess '{"case":"OS-0001","baseline_start":"2014-01-01","baseline_end":"2017-12-31","start":"2018-03-01","end":"2020-12-31"}'
uv run oddsky open "V838 Mon" --hook "..." # open a new case on any star and fetch its data
uv run oddsky export-web && python -m http.server -d web 8765
```

Blind trial over MCP: `claude mcp add oddsky-trial -- uv run oddsky mcp --blind trials/strange-stars-001/packets/T03`.

## Seed cases

| case | star | status |
|---|---|---|
| [OS-0001](cases/OS-0001) | ASASSN-21qj: the star that glowed before it dimmed | reproduced |
| [OS-0002](cases/OS-0002) | KIC 8462852 (Boyajian's Star) | observation |
| [OS-0003](cases/OS-0003) | EE Cep: the eclipse that comes back every 5.6 years | observation |
| [OS-0004](cases/OS-0004) | R CrB: the star that smokes | observation |
| [OS-0005](cases/OS-0005) | R Cyg: a Mira, strange to the eye and ordinary to astrophysics | observation |
| [OS-0006](cases/OS-0006) | SS Cyg: the prototype dwarf nova | observation |
| [OS-0007](cases/OS-0007) | AA Tau: the young star that went dark in 2011 | observation |
| OS-0008/9 | two quiet control stars in the TESS continuous viewing zone | trial controls |

Each one is an open invitation to investigate.

## Philosophy

> "The first principle is that you must not fool yourself, and you are the easiest person to fool."
> — Richard Feynman, *Cargo Cult Science* (1974)

> "There must be no barriers to freedom of inquiry."
> — J. Robert Oppenheimer (1949)

AI agents are tireless and fluent, and that makes them dangerous in science, because they produce
convincing nonsense without effort. Oddsky's answer is structural rather than a matter of tone:
epistemic tags, receipts, a Skeptic that is code, predictions sealed in advance, and trials with
sealed answers. Read [the manifesto](docs/MANIFESTO.md) and [how Oddsky keeps itself
honest](docs/EPISTEMICS.md).

## Credits

Built by Alan Shortz and the advisor, with Claude. The data come from ESA Gaia, NASA/IPAC
NEOWISE, the AAVSO International Database and its observers worldwide, NASA TESS via MAST, ZTF,
and ASAS-SN. MIT licensed. See [CONTRIBUTING](CONTRIBUTING.md) and, for the scientific defaults
that are still open questions, [docs/OPEN_QUESTIONS.md](docs/OPEN_QUESTIONS.md).
