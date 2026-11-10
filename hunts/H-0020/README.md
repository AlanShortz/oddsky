# H-0020: twice-seen

Opened 2026-11-10. An astronomer who advises the project named the two things that cost him most: artificial-star tests
("you have to do that yourself every time manually", a year per dataset), and that nobody has put all the data on AGB stars
in one place *with its quality*. This hunt builds a tool for the first and uses it to start the second.

**Status.** A tool, a first quality card for Hubble's automatic catalogue, and version 0 of an AGB table. An independent
referee (`reviews/claude-referee-2026-11-10.md`) reproduced the arithmetic, confirmed the downloader fix, and found four of
my readings wrong and two bugs; this page and the tool are the versions after that report, and the changes made in
response have not been refereed again. Not yet compared with a real artificial-star test. Nothing here has been sent
anywhere.

## Abstract

An artificial-star test asks how many stars of known brightness a catalogue recovers, and how wrongly. Where a deeper
and sharper catalogue covers the same sky, the sky has already run part of that test: its stars are real stars of known
brightness in real crowding, and the other catalogue found them or did not. `oddsky.analysis.twiceseen` ties two
catalogues, keeps the common sky, corrects for chance matches, and tabulates the fraction recovered, displaced, the
offset, the scatter and the gross-error rate by magnitude and crowding, marking the rows the deeper catalogue cannot
judge. In simulation it returns a planted half-recovery magnitude to 0.01 mag. Against ANGST PSF photometry in five
galaxies, the Hubble Source Catalog recovers 99.3% of isolated stars above the red-giant tip with 0.04 mag scatter;
crowded stars just below the tip are 92% recovered, 0.06 mag too bright, and 10% of them are off by more than 0.3 mag.
Selecting point-like sources cuts those gross errors to about 1% and keeps only 60 to 87% of the stars. On its first
real run the tool showed that this project's own catalogue client was losing a fifth of its rows. It is a quick external
check, not a replacement for artificial stars: two catalogues of the same resolution overstate completeness by several
points, and the tool has no colour axis yet.

## Figures

None yet. The tables are `work/shallow_deep.csv`, `work/hsc_quality.csv` and `work/tables/`.

## 1. Introduction

**The job.** Someone with a star catalogue of a crowded field needs three functions before any population result can be
trusted: how many stars of a given brightness are in the catalogue, how far off their magnitudes are, and how often they
are badly wrong. The standard answer is to inject artificial stars into the images and run the photometry again, tens of
thousands of times. It needs the images, the code and the computing, and it is redone for every field.

**The observation.** Archives are full of fields seen twice at different depth or resolution. Completeness measured against
a deeper catalogue is an old idea in survey work. What is built here is a general, tested routine for it with its limits
stated, and its application to a catalogue that ships with no quality model at all.

**What it cannot do** (also in the module's docstring): it grades one catalogue relative to another, so it is valid only
well above the deeper catalogue's own limit; it cannot see stars both miss; two catalogues of equal depth overstate
completeness, because the same crowding hides a star from both; and it answers for the stars that are there, not for any
star anywhere, which a real artificial-star test can.

## 2. Data

- ANGST DOLPHOT "good star" catalogues (Dalcanton et al. 2009, MAST high-level science products), F814W, for five fields
  with a short and a long visit, and as the truth for part B.
- The Hubble Source Catalog v3 summary table, F814W, fetched to 1.3 mag below each galaxy's red-giant tip (hunts/H-0019,
  re-fetched complete on 2026-11-10).

## 3. Results

**Simulation (`tests/test_twiceseen.py`).** A deep catalogue and a shallow one of the same field, shifted by 0.7 arcsec,
rotated by 0.02 degrees, with a planted half-recovery magnitude: returned to 0.01 mag; bright stars complete; planted
scatter returned; a planted zero-point offset reported; rows beyond the truth catalogue's horizon marked; chance matches
in a dense field do not inflate the faint end; catalogues of different fields, and a mirrored field, refused; a star seen
but moved counted as displaced; fainter truth stars counted as neighbours when only bright ones are graded.

**Short visit against long visit (`work/shallow_deep.csv`).**

| field | short, long exposure (s) | truth stars | half-recovery (F814W, Vega) | S/N predicted for the short visit there | truth's S/N there | recovered 1.5 mag or more above it, isolated / crowded |
|---|---|---|---|---|---|---|
| Garland | 1,622 / 19,200 | 38,798 | 27.28 | 4.9 | 17.0 | 94% / 92% |
| KKH 37 | 900 / 2,541 | 14,440 | 26.91 | 5.1 | 8.5 | 85% / 77% |
| NGC 4163 | 900 / 2,250 | 94,499 | 26.96 | 4.5 | 7.1 | 90% / 80% |
| M81 outer | 1,580 / 29,953 | 49,566 | 27.07 | 6.4 | 27.8 | 92% / 93% |
| IC 2574 | 4,784 / 6,400 | 26,889 | 27.27 | 8.8 | 10.2 | 92% / 89% |

- For Garland and M81 the truth has S/N 17 and 28 at the half-recovery magnitude, so those two are measurements. For the
  other three the truth is barely deeper and the value is uncertain in both directions.
- The physical check, made non-circular after the referee: DOLPHOT's good-star list needs S/N of 4 in both filters, so
  half-recovery should fall where the short visit's S/N, predicted from the long visit's S/N of the same stars scaled
  by exposure time, is a little above 4. It does in three fields (4.5 to 5.1) and not in M81 (6.4) or IC 2574 (8.8). The
  referee traced those two to the second filter: recovery near the limit falls from 78% to 59% from the bluest to the
  reddest quarter in IC 2574, and M81's reddest fifth of bright isolated stars is 78% recovered against 95 to 98% for the
  rest. A table by magnitude alone averages over that.
- Bright stars are not fully recovered in the short visits (85 to 94% of isolated ones, after removing the detector
  gap, which had held 4 to 6% of truth stars in two fields). In NGC 4163 recovery rises outward and falls with the truth
  catalogue's own crowding measure. Part is real loss in the short visit's good-star list and part is the colour effect
  above. Not checked against ANGST's artificial-star results.

**The Hubble Source Catalog against PSF photometry (`work/hsc_quality.csv`).** Five fields in five galaxies (39,074 truth
stars graded; neighbours counted from the full-depth truth), matched at 0.10 arcsec. The two densest NGC 300 fields are
not in it: the tool refused them (too many chance matches against so deep a truth).

| all catalogue sources | recovered (range over fields) | displaced | offset (mag, negative = too bright) | scatter | off by > 0.3 mag (range) |
|---|---|---|---|---|---|
| above the tip, isolated | 99.3% (98.4 to 100) | 0.3% | −0.003 | 0.042 | 1.2% (0.6 to 2.6) |
| above the tip, crowded | 96.6% (95.3 to 98.2) | 2.6% | −0.026 | 0.067 | 4.3% (1.7 to 9.2) |
| up to 1 mag below, isolated | 98.6% (97.8 to 99.6) | 0.6% | −0.011 | 0.063 | 2.0% (0.7 to 2.7) |
| up to 1 mag below, crowded | 91.8% (90.4 to 98.0) | 6.2% | −0.060 | 0.110 | 10.0% (1.4 to 13.3) |

| point-like sources only (concentration index 0.85 to 1.30) | recovered | offset | scatter | off by > 0.3 mag |
|---|---|---|---|---|
| above the tip, isolated | 86.7% | −0.002 | 0.039 | 0.5% |
| above the tip, crowded | 66.5% | −0.014 | 0.051 | 0.8% |
| up to 1 mag below, isolated | 82.7% | −0.010 | 0.055 | 0.4% |
| up to 1 mag below, crowded | 60.3% | −0.033 | 0.074 | 1.1% |

- "Displaced" stars have no catalogue source within 0.10 arcsec and one within 0.25: seen, with the centroid pulled by a
  neighbour. Most of the crowded stars that are "not recovered" are these.
- The offset is the catalogue's aperture taking in neighbours: there is none without a neighbour, it grows with the
  neighbour's flux, and gross errors are 12% too bright against 0.2% too faint (referee).
- The point-like cut, which H-0019 used, trades a third of the crowded stars for a tenfold drop in gross errors.
- The catalogue's aperture magnitudes are 0.69 to 0.71 mag fainter than DOLPHOT's Vega magnitudes in every field: the AB
  to Vega difference plus the aperture correction, measured.
- Above the tip part of the gross-error rate is real variability (the errors there are symmetric); the two catalogues'
  epochs differ.
- "Crowded" means one or more neighbours within 0.5 arcsec no more than a magnitude fainter.

**What the first real run exposed.** In IC 2574 a quarter of bright isolated stars were missing from the catalogue, the
same fraction at every brightness and stellar density. That is not how crowding behaves, and it was not the catalogue: the
service's paging has no stable order, so this project's client lost rows from every query longer than 50,000 (IC 2574:
73,982 stored where one clean pass returns 91,270). Fixed in `oddsky.data.hsc` (it now halves the right-ascension range instead of paging). H-0019
was re-run on complete data: 21,494 stars in 14 galaxies in place of 15,145 in 13, pooled excess 0.0341 ± 0.0017 where it
was 0.0343 ± 0.0020 (`hunts/H-0019/work/refetch_comparison.csv`).

**AGB atlas, version 0 (`atlas/`, `scripts/02_atlas.py`).** 76,986 red stars within 2 mag above or 0.5 mag below the tip
in 42 galaxies, each seen at least twice by ACS in F814W; 55,183 have two visits more than 100 days apart. Per star:
position, magnitude, colour, height above the tip, number of visits, the change between first and last visit and between
the two closest visits, the scatter of control stars in the same images, crowding, and what the point-like quality card
says about a star like it (from the galaxy's own card for five galaxies, pooled for the other 37), plus known-variable
identifications where I have them (138 Miras of Yuan et al. 2017 in M33) and the Librarian's verdict for the first H-0019
candidates. With crowding attached, 5.3 ± 0.2% of isolated stars up to 1 mag above the tip change by more than 0.3 mag
against 4.5 ± 0.2% of crowded ones (2.4σ).

## 4. Analysis: what is not established

- **No comparison with a real artificial-star test yet.** ANGST published completeness limits from artificial stars for
  these fields; every VizieR mirror tried on 2026-11-10 was down or lacked the table. One field with artificial-star
  results and a deeper overlapping catalogue would settle whether the curves agree.
- **Same resolution, same blind spots.** Two Hubble catalogues lose the same blended stars. In the referee's simulation
  with real blending, recovery is overstated by 2.5 points for bright stars and 6 to 8 points a magnitude above the limit,
  however deep the truth is. The short-against-long numbers above carry that bias. The catalogue-against-PSF numbers
  carry less of it, because the truth there is sharper, not only deeper.
- **Matching is by position only.** With no magnitude tolerance a neighbour can stand in for a lost star: in the same
  simulation crowded completeness was overstated by 4 to 7 points at 0.10 arcsec resolution.
- **No colour axis.** A catalogue that requires a second filter loses red or blue stars; the table averages over it.
- **The truth is not true.** DOLPHOT blends stars too, and its good-star cuts remove real stars.
- **The card is five fields.** Its gross-error rate runs from 1% to 13% between them, so pooling it onto 37 other galaxies
  in the atlas is a placeholder. The atlas counts neighbours from the catalogue itself, cut 1.3 mag below the tip, and
  that crowding class agrees with the card's only 61 to 68% of the time (referee).
- **The atlas is one catalogue's stars**, not all AGB data in one place: no infrared, no periods except M33's, aperture
  magnitudes. Three galaxies have tips more than 0.2 mag from the prediction (`tip_soft`); M31 is left out.
- **Prior art.** Grading a catalogue against a deeper one is standard practice (artificial stars: Stetson 1987; ANGST:
  Dalcanton et al. 2009; PHAT: Williams et al. 2014; the Hubble Source Catalog's own validation: Whitmore et al. 2016;
  Gaia completeness against Hubble; injection into survey images, Balrog). These are named from memory and not searched;
  I did not look for an existing comparison of this catalogue with DOLPHOT. What is offered here is a tested routine
  with stated limits and the numbers for one catalogue, not a new idea.

## 5. Conclusions

1. Where a deeper, sharper catalogue exists, recovery, displacement, offset, scatter and gross-error rate by magnitude and
   crowding come out of two files in under a minute, with the rows it cannot judge marked. Useful as a quick external
   check; it overstates completeness when the two catalogues share a resolution.
2. Hubble's automatic catalogue is good for isolated stars near the tip. Crowded stars are too bright by 0.03 to 0.06 mag
   and wrong by more than 0.3 mag up to a tenth of the time; selecting point-like sources removes most of that and a
   third of the stars with it. Those numbers are attached to every star in the atlas.
3. The tool's first use on real data found a data-loss bug in this project.

**Next.** The comparison with real artificial stars. A magnitude tolerance and a colour axis in the matching. The newer
per-visit Hubble catalogues, if they are what the advisor meant. Spitzer and JWST photometry joined to the atlas. A
forecast for few-visit surveys drawn from real light curves and this noise model.

## Files

`scripts/01_twice_seen.py`, `scripts/02_atlas.py`; `work/`; `atlas/` (parquet, a 200-row sample, the galaxy list);
`src/oddsky/analysis/twiceseen.py`, `tests/test_twiceseen.py`; command: `oddsky twice-seen TRUTH TEST`.
