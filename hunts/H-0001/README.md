# Hunt H-0001: Sun-like stars that Gaia caught fading

**Question.** Which main-sequence FGK stars did Gaia see dim (2014-2017), and which of those has nobody
explained?

**Funnel** (every step is a script in `scripts/hunt_h0001*.py`; every number below is reproducible):

| step | stars | what removed them |
|---|---|---|
| Gaia DR3 `vari_summary`: G 10.5-15.5, FGK colour, near the main sequence, parallax/error > 10, RUWE < 1.4, clean images, G range > 0.2 mag, skewness > 2.5 (fading) | 22,125 | |
| not classified by Gaia as an eclipsing binary | 2,020 | 20,105 eclipsing binaries |
| a dip deeper than 0.8 mag confirmed on 2+ transits, excluding 3+ mag single-transit window artifacts | 18 | eclipses of similar stars can't exceed ~0.75 mag; 62 stars carried spurious transits |
| not already catalogued (VSX, SIMBAD) | 0 | 8 known Algol-type binaries (ASAS-SN, ZTF, SSS, OGLE), 1 known young star, 1 blend with a catalogued eclipsing neighbour, 6 Gaia-only "VAR" entries (ZTF shows most are unclassified eclipsing binaries), NSV 1302 (a known Per OB2 young star, opened as case OS-0010) |

**Verdict.** No new main-sequence dipper in this sample. The negative result is the finding:
with ~50 sparse Gaia epochs, deep "fading" on a Sun-like star is almost always an Algol (a hot dwarf
eclipsed by a cool subgiant) or a Gaia windowing artifact. Two lessons now built into Oddsky:
Gaia epoch photometry is a series (`GAIA:G/BP/RP`), and the Skeptic's blend check caught the one
case where the dips belonged to a catalogued neighbour.

Files: `query.adql`, `candidates.csv` (22,125), `scored.csv` (2,020), `vet/*.json` (external checks),
`epoch/` (Gaia light curves, not committed: re-fetch with the scripts).
