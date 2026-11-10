# Show HN draft

> Not ready to post: needs the package on PyPI (`uvx oddsky`), the
> GitHub org, and the domain. Update the numbers if Trial 002 has run.

**Title:** Show HN: Oddsky – an open observatory your AI agent can use to investigate strange stars

**URL:** https://oddsky.org (static site) · repo: github.com/oddsky-org/oddsky

**Text:**

Hi HN. Oddsky is an open-source set of astronomy tools served over MCP, so any agent (Claude
Code, Codex, Cursor, a local model) can investigate real stars with real archive data: Gaia,
NEOWISE, TESS, and a century of AAVSO amateur photometry. I'm the software person; a professional astronomer who works on dusty dying stars advises me.

We built it around the obvious failure mode: an LLM will happily write you a beautiful, wrong
explanation of a light curve. So Oddsky makes the work checkable:

- every claim is tagged observed / computed / inferred / speculated;
- every number cites the tool call that produced it, and `oddsky replay` re-runs the whole ledger;
- a deterministic "Skeptic" checks for the usual impostors (blended neighbours, saturation, a
  single observer, momentum dumps, survey-cadence aliases) before anyone gets excited;
- predictions must be machine-checkable and are sealed with a timestamp, and the archive grades them.

The first case is ASASSN-21qj, a Sun-like star whose infrared lit up in 2018, three years before it
faded by 2 magnitudes (published as a probable planetary collision). Our agent's investigation
is all replayable tool calls. It found that the star has been back to normal and flat to 0.5% since
early 2025, that a 2025 "recovery" in two filters is a calibration artifact, and it sealed three
predictions for 2027.

We also ran a blind trial: ten packets with names and dates removed, answers sha256-sealed before
the run. Opus 5.5 got 10/10, but it recognised 8 of the stars, and we say so. Haiku 5.5 got 5/10.
From data cut a year before EE Cep's 2025 eclipse, Opus forecast the eclipse's timing and depth.
We also found and published a bug in our own grader.

We then pointed it at all of Gaia DR3 to look for new things. It found two eclipsing binaries nobody had
catalogued (Gaia's pipeline had given them periods of 36 and 53 minutes). It also found, we thought, a star eclipsed every
2.38 days by a Sun-sized object that gives off no light. Before we told anyone, an Oddsky referee agent took that
apart in 30 minutes: we had folded at a fifth of the true period and stacked two eclipses on top of each other. It's an
ordinary pair of K dwarfs. The whole thing, the mistake included, is in the repo.

Then we read every NEOWISE infrared measurement of the sky (146.6 billion detections, 165 million stars) on Google
Cloud in two hours, for a few dollars, looking for stars that suddenly grew hot dust. Out of the vetting came a G dwarf
that vanished for about 95 days in 2017: at the deepest, more than 99% of its light was blocked, three surveys saw it independently, and
afterwards it began to glow in the infrared. We can't find anyone who has reported it. Whatever crossed it was at
least 0.15 AU across.

No account and no API key. A case is a directory, so forking an investigation is a git fork and a
review is a PR. We would love: astronomers telling us what's wrong, and people pointing their agents
at the cases.

The universe is an open question.
