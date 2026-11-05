# Referee report: RNAAS_AllWISE_profile_fit_draft.md (DRAFT v4)

**Verdict: FIX THEN SUBMIT**

reviewed-sha256: ed14cc8a688c09fc1e23a5db62edd1525b9420d1fe30513cb7d20472a2c4c75e

The central claim survives an independent IRSA re-pull (Catalog and Reject Table, all 48 stars). Seven things are wrong as written.

## Errors (must fix)

**1. "Here 16 of the 19 good extractions carry no same-Tile mark; … later extraction in 17 cases and the one farther from the Tile edge in 17, by at most 1.6 pixels."**
IRSA gives rel = null for 17. `build_receipts.py` merges on designation, so the J180239 same-Tile row (cntr 2719056101351011254) inherited rel = 's' from the adjacent-Tile entry; claims.py reads the same table and passes. "17 farther" also mixes mechanisms: 16 of the 17 have best_use_cntr = catalog entry, farther from the edge in 16 of 16; J220346 lost to a third extraction (src 2626); the two rel = 'r' cases have the catalog entry at the lower src.

**2. "The Explanatory Supplement (section V.4.b) describes … farthest from its Tile edge is kept whatever its quality."**
V.4.b defers the rule to All-Sky Supplement V.3.c, which says 2.5″ groups may hold several detections from one Tile and all go through distance-to-edge: documented behaviour, not inference. "Whatever its quality" is wrong (pre-filter). `src` is documented as approximate brightness order, not extraction order. Unmentioned: the same-Tile step uses 3.9″ and should have caught these pairs. Replace from "The Explanatory Supplement" to "by the geometric rule." with:

> The Supplement describes two steps. Same-Tile groups within 3.9″ are classified first, the earlier extraction being kept and the others rejected (rel = 'r'; section V.4.b). Remaining groups within 2.5″, which may include several detections from one Tile, are resolved by keeping the detection farthest from its Tile edge (Cutri et al. 2012, section V.3.c). Two of the 19 good extractions were rejected by the first step; the catalog entry has the lower source number. The other 17 pairs carry no same-Tile mark although they lie within 3.9″; why is not established. For 16 of them best_use_cntr names the catalog entry, which in all 16 is the one farther from the edge, by 0.01–1.2 pixels; the seventeenth lost to a third, w1snr = 3.9 extraction farther still. The edge rule thus kept the displaced extraction.

**3. "One failure is a warning and two a rejection … none of the 697 control sources fails two tests … or use the aperture magnitudes".**
In the 506,437-row pull, 31,549 sources fail two of tests (1)–(3); 2MASS favours w1mpro for 16,749 and w1mag for 631. Replace with:

> Two failures reject the entry but do not say which magnitude is wrong: 31,549 clean sources fail two of tests (1)–(3), and where 2MASS decides it favors w1mpro for 16,749 and w1mag for 631. None of 697 control sources fails two (a limit of 0.4%).

End Section 4: "…should apply the test and, for entries that fail, decide between w1mag and w1mpro with 2MASS, the Reject Table or the images, before a star is called variable across 2011–2013."

**4. "631 sources (323 north, 308 south), or 1.5 × 10⁻⁵"** (and abstract).
A lower limit. Replace: "…or at least 1.5 × 10⁻⁵: the list recovers 31 of the 46, and 14,169 further two-test failures lack decisive 2MASS photometry". Abstract: "(at least 1.5 × 10⁻⁵)".

**5. "all fail (2) and 45 fail (4)".**
Test (4) is defined only without a close neighbour; 13 have one. Replace: "all fail (2) and all 33 with no close neighbor fail (4)".

**6. References.**
The 2010–2020 coadd is unWISE neo7 (`unwise_check.py`): Meisner, Lang, Schlafly & Schlegel 2022, RNAAS, 6, 62, not AJ 156, 69. Skrutskie et al. 2006 is listed but never cited; cite at "2MASS K magnitude". Add Cutri et al. 2012 (All-Sky Supplement). The five existing entries match ADS.

**7. Data files.**
`gaia_dr3_source_id` in dbf_48 is written as a float (6.531300936748132e+18); the IDs are corrupted. catalog_tiles_48.csv lacks J185650.54−483703.9. Fix the merge in reject_entries_48.csv.

## Overclaims

**8. "Unflagged" (title, abstract).** Add to Section 2: "Seven carry rel = 's' and 39 have W1 ph_qual = 'B'."

**9. Abstract: "aperture magnitudes, 2MASS, the unWISE images and NEOWISE agree with one another".** K − w1mag reaches 0.72; 32 of 46 pass the note's K criterion. Replace: "while the aperture magnitudes, the unWISE images and NEOWISE agree".

**10. "unWISE magnitude matches w1mag in 36".** Uncorrected 3-pixel aperture, 0.10–0.48 mag fainter than w1mag in all 40. Replace: "agrees with w1mag within 0.3 mag (median offset 0.14 mag) in 36".

**11. "early B stars whose … excess had gone".** Replace: "B stars (B0.5 III, B4e) whose 2010–11 excess, presumably circumstellar, had gone by 2014".

## Suggestions

12. Define "isolated" (legend). Say the control is one 1.5° field at b ≈ +80°. "0.23–2.5" is predicted R; measured R is 1.44 and 2.68.
13. Fifteen of the 19 duplicates lie in five Tiles.
14. claims.py: 4095, not 4096 (no effect).

## Checked and correct

All other counts, ranges and medians; Tile from cntr prefix; pixel edge distance as proxy. Abstract 146 words, file 1,357, one figure, AI statement present.

## Not completed

- Gaia positions of the 19 Reject entries not queried. Indirect only: Reject-to-catalog separation equals the catalog–Gaia offset within 0.13″ for 15 of 19.
- Prior art: Supplement pages, one ADS full-text query (0 hits), one web search. CatWISE/unWISE papers and known-anomalies pages not read.
- 42,759,991, 4.9 × 10⁷ and 19,818 not re-queried. RNAAS limits taken from the brief.

## Re-check of v5

**Verdict: FIX THEN SUBMIT (two sentences).**

re-checked-sha256: 30ce94dd6585f2f92f65c3d7b057e4d582bc5d2bb4a3cb2f4d23cd9a593c4fb8

Findings 1, 2, 4, 5, 6, 8, 9, 11 and 12 are resolved and verified against the rebuilt receipts and the original pulls. Section 3 matches the Supplements and the data: 17 unmarked pairs (largest separation 2.04″), 16 naming the catalog entry, 16 of 16 farther from the edge by 0.009–1.161 px, two rel = 'r'. Also confirmed: 39 ph_qual 'B', seven rel = 's', 33 of 33 without a neighbor fail (4), control field at b = 81.7–83.9°, references. Abstract 141 words; file 1,423 words (everything counted); one figure; AI statement present.

### Still wrong (both come from my own v4 replacement text)

**A. "agrees with w1mag within 0.3 mag in 36 and with w1mpro in none".**
Under that stated criterion the counts are 37 and 1: one source (cntr 3298050001351010095) is within 0.3 mag of both (0.14 and 0.28). The 36 is "w1mag only", which is what claims.py line 171 tests; the check passes while the sentence is false. Replace with:

> agrees within 0.3 mag with w1mag alone in 36 and with w1mpro alone in none

**B. "31,549 clean sources fail two of tests (1)–(3)".**
The count is within the 506,437-row pull (|w1mag − w1mpro| > 0.4 or w1snr < 20), not catalog-wide. A source with w1snr 20–23.7 and a difference of 0.3–0.4 mag fails two tests and is outside the pull. Replace with:

> 31,549 of the 506,437 fail at least two of tests (1)–(3)

### Recommended, not blocking

- Section 2, "Their AllWISE positions lie": after the control-sample sentence "Their" reads as the control sources. Use "The 46 lie 0.35–2.63″ (median 0.86″) from the Gaia positions".
- The two dropped clauses are not needed for accuracy. The text leaves the seventeenth unmarked pair unaccounted for; "; the seventeenth lost to a third extraction farther still" closes it if words allow.
- "catalogued" → "cataloged". "0.02 mag for the real stars" is 0.024 and 0.025.

### Outside the text

- `gaia_dr3_source_id` in dbf_48 is still a float; fix before the data are uploaded.

### Limits of this re-check

- My independent IRSA pull was no longer on disk. The rebuilt receipts were compared with the values that pull returned earlier in this review, not with a fresh pull.
- The items under "Not completed" above remain not completed.

## Re-check of v6

**Verdict: SUBMIT.** Nothing in the text must change.

document-sha256: e6bd00f23f0db48c3ced598086a3e08b170d7e41c58b9e817f14873a560b980b

### What I checked

- **Sentence A** ("agrees within 0.3 mag with w1mag alone in 36 and with w1mpro alone in none"): correct. 36 are within 0.3 mag of w1mag only, none of w1mpro only.
- **Sentence B** ("31,549 of the 506,437 fail at least two of tests (1)–(3)"): correct, and now scoped to the pull.
- **New Gaia sentence** ("18 lie within 0.5″ of the Gaia position (median 0.06″)"): correct. I queried Gaia DR3 at IRSA (`gaia_dr3_source`, 6″ cones) around each of the 19 Reject entries, 19 of 19 queries answered, and propagated to 2010.5. The nearest Gaia source is the star's own DR3 id in all 19; 18 lie within 0.5″; the median is 0.061″; my separations equal the receipt's `gaia_sep` to 0.001″. The one outside is J162011.24−172910.3 at 1.146″, which has a second star of equal brightness (G 14.72 against 14.62) 1.34″ away, so that extraction is a blend of the pair.
- **Other edits**: "The 46 lie 0.35–2.63″", "cataloged", and "(0.024 and 0.025 mag for the real stars)" are all correct.
- **Data file**: the Gaia ids in dbf_48 are now exact and match Gaia DR3 for the 19 I queried.
- **Limits**: abstract 141 words; file 1,440 words with everything counted; one figure; AI statement present.
- **paper-check**: 95 statements, 0 failures on this hash.

### Limits of this sign-off

- The same-star check listed under "Not completed" is now done. ESA and VizieR were unavailable (503 and timeout), so it ran on IRSA's copy of Gaia DR3.
- Prior art is still limited to the Explanatory Supplement pages, one ADS full-text query and one web search. The CatWISE and unWISE papers and the known-anomalies pages were not read.
- 42,759,991, 4.9 × 10⁷ and 19,818 were not re-queried. The RNAAS limits are those given in the brief.

## Re-check of v7

**Verdict: SUBMIT.** Nothing in the text must change.

document-sha256: 2c8572128956937376639c7266b7568373a405d4f7531d3ac10da6096c81ebb9

### What I checked

- **Scope of the change.** HEAD holds v6 (hash e6bd00f2…, confirmed). `git diff HEAD` shows two changes only: the DRAFT label on line 1 and the first sentence of the Acknowledgments. The body, abstract, caption and references are identical to v6.
- **DOIs.** Each was read on its IPAC landing page and in its DataCite record; the two agree in all four cases.
  - 10.26131/IRSA1: "AllWISE Source Catalog".
  - 10.26131/IRSA136: "AllWISE Reject Table".
  - 10.26131/IRSA134: "AllWISE Multiepoch Photometry Table".
  - 10.26131/IRSA144: "NEOWISE-R Single Exposure (L1b) Source Table". The note omits "(L1b)"; that is acceptable.
- **NEOWISE product.** It is the right one for "median of the first three NEOWISE visits". `hunts/H-0016/README.md` states the visit medians were built from the NEOWISE single-exposure table, and the step table carries that table's AllWISE-association columns (`allwise_cntr`, `w1mpro_allwise`, …).
- **Words.** Abstract 141 (limit 150). Everything else in the file, counting the draft label, title, author, headers, caption, acknowledgments and references, is 1,307 (limit 1,350). Whole file 1,448.
- **paper-check.** 95 statements, 0 failures on this hash.

### Limits of this sign-off

- The code that built the visit medians (`infra/gcp/neowise_pixel_v2.py`) is not in this checkout. The NEOWISE product was confirmed from the README and the column names, not from the code.
- The limits listed under "Re-check of v6" still apply.
