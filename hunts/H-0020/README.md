# H-0020: twice-seen

Opened 2026-11-10. An astronomer who advises the project named the two things that cost him most: artificial-star tests
("you have to do that yourself every time manually", a year per dataset), and that nobody has put all the data on AGB stars
in one place *with its quality*. This hunt builds a tool for the first and uses it to start the second.

**Status.** A tool, a first quality card for Hubble's automatic catalogue, and version 0 of an AGB table. Tested in
simulation; on real data it passes one physical check and has not yet been compared with a real artificial-star test.
Refereed: see `reviews/`. Nothing here has been sent anywhere.

## Abstract

An artificial-star test asks how many stars of known brightness a catalogue recovers, and how wrongly. Where a much deeper
or sharper catalogue covers the same sky, the sky has already run part of that test: the deeper catalogue's stars are real
stars of known brightness in real crowding, and the other catalogue found them or did not. `oddsky.analysis.twiceseen` ties
two catalogues (offset, rotation and distortion), keeps the common sky, corrects for chance matches, and tabulates the
fraction recovered, the offset, the scatter and the gross-error rate by magnitude and crowding, marking the rows the
deeper catalogue cannot judge. In simulation it returns a planted half-recovery magnitude to 0.08 mag. On five Hubble fields
with a short and a long visit, the short visit's half-recovery lands where its own signal-to-noise is 4.5 to 5.2 in four,
just above the catalogue's cut at 4. Against PSF photometry, the Hubble Source Catalog recovers 99.0% of isolated stars
above the red-giant tip with 0.05 mag scatter; crowded stars just below the tip are 89% recovered, 0.07 mag too bright, and
13% of them are off by more than 0.3 mag. On its first real run the tool showed that this project's own catalogue client
was losing a fifth of its rows.

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
rotated by 0.02 degrees, with a planted half-recovery magnitude: returned to 0.08 mag; bright stars complete; planted
scatter returned; a planted zero-point offset reported; rows beyond the truth catalogue's horizon marked; chance matches
in a dense field do not inflate the faint end; catalogues of different fields refused.

**Short visit against long visit (`work/shallow_deep.csv`).**

| field | short, long exposure (s) | truth stars | half-recovery (F814W, Vega) | short visit's S/N there | recovered where judged, isolated / crowded |
|---|---|---|---|---|---|
| Garland | 1,622 / 19,200 | 38,798 | 27.28 | 4.5 | 93% / 91% |
| KKH 37 | 900 / 2,541 | 14,767 | 26.90 | 4.9 | 84% / 77% |
| NGC 4163 | 900 / 2,250 | 95,138 | 26.96 | 4.5 | 90% / 79% |
| M81 outer | 1,580 / 29,953 | 49,594 | 27.07 | 5.2 | 91% / 87% |
| IC 2574 | 4,784 / 6,400 | 26,889 | 27.27 | 7.7 | 92% / 87% |

- Every half-recovery magnitude is fainter than the horizon the tool allows itself (one magnitude brighter than the peak of
  the truth catalogue's luminosity function), so by its own rule these are lower bounds on depth, not measurements. The
  rule is conservative for the two very deep truth fields and right for IC 2574, where the two visits are nearly equal.
- The physical check: DOLPHOT's good-star list requires S/N of 4 in both filters, so half-recovery should fall a little
  above S/N 4 in the short visit. It does in four fields (4.5 to 5.2). IC 2574 gives 7.7, the equal-depth bias the
  docstring warns of.
- Bright stars are not fully recovered in the short visits: 84 to 93% of isolated ones. In NGC 4163 recovery rises from
  77% in the central 10 arcsec to 93% beyond 80, and falls with the truth catalogue's own crowding measure. I read this as
  real loss in the short visit's good-star list. It has not been checked against ANGST's artificial-star results.

**The Hubble Source Catalog against PSF photometry (`work/hsc_quality.csv`).** Seven fields in five galaxies, 89,354 truth
stars, matched at 0.10 arcsec.

| stars | recovered | offset (mag, negative = too bright) | scatter (mag) | off by more than 0.3 mag |
|---|---|---|---|---|
| above the tip, isolated | 99.0% (98.4 to 100) | −0.001 | 0.051 | 1.8% |
| above the tip, crowded | 96.8% (95.3 to 98.2) | −0.029 | 0.084 | 5.6% |
| up to 1 mag below, isolated | 97.2% (96.0 to 99.0) | −0.027 | 0.084 | 4.4% |
| up to 1 mag below, crowded | 89.3% (88.3 to 97.6) | −0.073 | 0.124 | 12.7% |

- The catalogue's aperture magnitudes are 0.69 to 0.71 mag fainter than DOLPHOT's Vega magnitudes in every field: the AB
  to Vega difference plus the aperture correction, measured, not assumed.
- "Crowded" means one or more neighbours within 0.5 arcsec no more than a magnitude fainter.
- These gross-error rates are the same phenomenon as the 1.5% of control stars that "changed" by 0.3 mag in H-0019.

**What the first real run exposed.** In IC 2574 a quarter of bright isolated stars were missing from the catalogue, the
same fraction at every brightness and stellar density. That is not how crowding behaves, and it was not the catalogue: the
service's paging has no stable order, so this project's client lost rows from every query longer than 50,000 (IC 2574:
73,982 stored of 91,270). Fixed in `oddsky.data.hsc` (it now halves the right-ascension range instead of paging). H-0019
was re-run on complete data: 21,494 stars in 14 galaxies in place of 15,145 in 13, pooled excess 0.0341 ± 0.0017 where it
was 0.0343 ± 0.0020 (`hunts/H-0019/work/refetch_comparison.csv`).

**AGB atlas, version 0 (`atlas/`, `scripts/02_atlas.py`).** 76,986 red stars within 2 mag above or 0.5 mag below the tip
in 42 galaxies, each seen at least twice by ACS in F814W; 55,183 have two visits more than 100 days apart. Per star:
position, magnitude, colour, height above the tip, number of visits, the change between first and last visit and between
the two closest visits, the scatter of control stars in the same images, crowding, and what the quality card says about
a star like it (recovered fraction, offset, scatter, gross-error rate; from the galaxy's own card for four galaxies, pooled
for the rest), plus known-variable identifications where I have them (138 Miras of Yuan et al. 2017 in M33) and the
Librarian's verdict for the H-0019 candidates. With crowding attached, the H-0019 signal separates: 5.3% of isolated
stars above the tip change by more than 0.3 mag against 4.5% of crowded ones, with the control at 1.5% in both.

## 4. Analysis: what is not established

- **No comparison with a real artificial-star test yet.** ANGST published completeness limits from artificial stars for
  these fields, and every VizieR mirror tried on 2026-11-10 was down or lacked the table. One field with artificial-star
  results and a deeper overlapping catalogue would settle whether the curves agree.
- **The truth is not true.** DOLPHOT blends stars too, and its good-star cuts remove real stars. A truth star lost to the
  deeper catalogue's own cuts is invisible here.
- **The horizon rule is a guess.** One magnitude above the luminosity-function peak is not derived from anything.
- **The quality card is from five galaxies** at 2 to 4 Mpc with ACS. Pooling it onto 38 other galaxies in the atlas is a
  placeholder; denser fields will be worse.
- **The atlas is a table of one catalogue's stars**, not all AGB data in one place. It has no infrared, no periods except
  M33's, and its magnitudes are aperture magnitudes. Three galaxies have tips more than 0.2 mag from the prediction
  (flagged `tip_soft`); M31 is left out.
- **Two things were fixed on the way** that a referee should look at: the polynomial distortion term in the tie, and the
  chance-match correction.

## 5. Conclusions

1. Where a deeper catalogue exists, completeness, offset, scatter and gross-error rate by magnitude and crowding come out
   of two files in under a minute, with the rows it cannot judge marked.
2. Hubble's automatic catalogue is good for isolated stars near the tip and measurably wrong for crowded ones. The
   numbers are now attached to every star in the atlas.
3. The tool's first use on real data found a data-loss bug in this project. That is what a quality model is for.

**Next.** The comparison with real artificial stars (ANGST's tables, or a field the advisor has). The newer per-visit
Hubble catalogues, if they are what he meant. Spitzer and JWST photometry joined to the atlas. A forecast for few-visit
surveys drawn from real light curves and this noise model.

## Files

`scripts/01_twice_seen.py`, `scripts/02_atlas.py`; `work/`; `atlas/` (parquet, a 200-row sample, the galaxy list);
`src/oddsky/analysis/twiceseen.py`, `tests/test_twiceseen.py`; command: `oddsky twice-seen TRUTH TEST`.
