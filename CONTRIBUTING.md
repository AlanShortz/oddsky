# Contributing to Oddsky

> "There must be no barriers to freedom of inquiry." — J. Robert Oppenheimer

You need no permission, no account, and no credentials to investigate. You need curiosity, an
agent (or your own two hands), and the willingness to be wrong in public.

## Investigate a case

```bash
git clone https://github.com/AlanShortz/oddsky && cd oddsky
uv sync --all-extras          # or: python -m venv .venv && pip install -e ".[all,dev]"
claude mcp add oddsky -- uv run oddsky mcp
```

Then ask your agent something like: *"Open Oddsky case OS-0002. Run the skeptic first, then try to
break the leading hypothesis. Tag every claim honestly."* Everything it records lands in
`cases/OS-0002/` (claims and hypotheses in `case.yaml`, every computation in `ledger.jsonl`). Add a
write-up at `cases/OS-0002/investigations/<you>-<date>.md` and open a pull request.

No agent? Every tool is also a command: `oddsky tools`, then e.g.
`oddsky call find_excursions '{"case":"OS-0002","series":"AAVSO:V"}'`.

## Open a new case

`oddsky open "V838 Mon" --title "..." --hook "..."` resolves the name, fetches Gaia, NEOWISE,
AAVSO, ZTF, ASAS-SN and TESS, and creates `cases/OS-NNNN/`. Run `oddsky skeptic OS-NNNN` before
you get excited.

## Review

A review is a pull request that adds `cases/OS-NNNN/reviews/<you>.md`: what you checked, what you
reproduced (`oddsky replay OS-NNNN`), what you'd want to see before believing it. Reviews by
professional astronomers can move a case to `validated` (see docs/EPISTEMICS.md).

## Rules of the house

1. Tag claims honestly. Speculation is welcome; disguised speculation is not.
2. Cite tool calls for computed claims. If it can't be replayed, it's an anecdote.
3. Credit the observers. Much of this data was taken by amateurs on their own time.
4. Negative results get merged with the same enthusiasm as discoveries.
5. Be kind. Being wrong is how we find things out.

## Code

`pytest` must pass offline (archive clients are not called in tests). `ruff check .` must be clean.
The web viewer in `web/` is zero-build static files; regenerate its data with `oddsky export-web`.
