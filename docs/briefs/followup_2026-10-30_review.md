# Fact-check: followup_2026-10-30.md (note to the advisor)

Reviewer: adversarial fact-check, 2026-10-30. Sources: the 28 Oct brief, `cases/OS-0013/` (case.yaml C14, `reviews/spherex-2026-10-30.md` and its `phot/` outputs), `cases/OS-0018/case.yaml`, `hunts/H-0008/README.md`, `hunts/H-0008/reviews/claude-referee-atlas-2026-10-30.md` (and its r1/r6 logs), `hunts/H-0008/work/atlas_fits.json`, `hunts/H-0006/README.md`, `hunts/H-0006/reviews/claude-referee-2026-10-28.md`, `hunts/H-0006/reviews/literature-2026-10-30.md`, `hunts/H-0006/plots/J160708.51-320101.1.png`. I also checked the live site (`oddsky.ai/data/cases/OS-0013.json`, `OS-0018.json`, `hunts.json`), GitHub collaborators, and the MAST, IRSA (SOFIA, Spitzer) and ESO archives at J160708's position.

## Verdict

**Send after the fixes below.** Almost every number matches its source, and the tone is right: short, it says plainly what is outside his field, and the questions are clear. Three problems would embarrass Alan with a professional:

1. **The site claim is false today.** The live OS-0013 page has claims C1-C13 and no SPHEREx result (C14 exists only in the working tree). The note says everything except item 3 is on the site.
2. **Item 3's "did not dim (NEOWISE W1 …)" contradicts the attached figure.** In the figure, W1 falls from 9.3-9.9 before the step to 10.02 after it, the faintest value in the whole record. TESS has no data across the step.
3. **Item 2 overstates in several places:** "caught the whole event" (ATLAS has a 94-day conjunction gap on the decline), "the same from 0.5 to 4.6 µm" (only one NEOWISE epoch, with its own blend fraction), "no other change" (ATLAS reads 10-40% low before 2019, and that shows on the live light curve), "every non-lens shape I tried" (two shapes), "outside the … OGLE fields" (not verified), and the novelty sentence leaves out that ASAS-SN and MOA could not be checked.

Verified correct: the item 1 numbers (+35.8 ± 3.1% vs +40.7% expected; +13.0 ± 2.3% vs +16.3%; field maximum +7.6%; all three seasons; centroid shift 0.05" ± 0.03", which supports the stated ≤ 0.5"; H/K +5-6%; plausible range +30% to +37%). G = 17.00, l = 19.67°, b = +5.72°, tE 115-150 d, t0 2022 Sep 19-20, 64 known events recovered. The J160708 ids, W1-W2 values and dates, SPHEREx "still absent", and the PDS 70 / Gaidos et al. 2024 description (2024ApJ...966..167G: 3.4/4.6 µm emission gone "for up to one year" around MJD 57000, then back). The correction paragraph's first half is true: the repo is private, the only collaborator is AlanShortz, and no invitation is pending.

## Required fixes

**1. Site claim (correction paragraph).**
Draft: "Everything in this note is also on the case pages at oddsky.ai, except item 3, whose figure is attached."
Problem: `oddsky.ai/data/cases/OS-0013.json` has C1-C13 only. The word "SPHEREx" appears once, in the old follow-up suggestions, so the item 1 result is not live. OS-0018 is live, with claims C1-C10 and light curves.
Fix: either deploy the OS-0013 C14 change and confirm it is on the page before sending, or write:
> "Items 1 and 2 will be on the case pages at oddsky.ai (OS-0013, OS-0018) by the time you read this; item 3 is not a case yet, so its figure is attached."

Only use the first version if it is true when you press send. Safest: deploy first, then keep the original sentence.

**2. Item 3: "The star did not dim (NEOWISE W1, SPHEREx 1-2.4 µm, ATLAS and TESS agree)."**
Problems:
- The attached figure shows W1 dropping by about 0.27 mag at the step (referee: pre-step median 9.75, post-step 10.02). That drop is the excess leaving W1. What the referee showed is that post-step W1 sits on the photosphere (K − W1 = 0.12 against 0.136 expected), not that W1 stayed flat.
- TESS has no data across the step (S12 is 2019, S65 is 2023), and its sector-normalised fluxes cannot show a dimming between those years.

Replace with:
> "The star itself did not change: ATLAS stays within 0.04 mag across the drop, SPHEREx at 1-2.4 µm matches 2MASS, and after the drop W1 sits on the photosphere (K − W1 = 0.12). The fall in W1 in the figure is the excess leaving."

**3. Item 3: "W1-W2 = 0.05-0.11, a bare M-dwarf photosphere".**
Problem: the referee required "consistent with" (report §4). Field M dwarfs of this colour give 0.09 ± 0.04, so the data cannot say more than that.
Replace with:
> "W1-W2 = 0.05-0.11, consistent with a bare M-dwarf photosphere (0.09 ± 0.04 for field M dwarfs of the same colour)"

**4. Item 3: "I checked the step against raw single exposures, field stars in the same frames, …"**
Problem: the referee used one control star (Gaia DR3 6036595883378178432, 18.5" away).
Replace "field stars in the same frames" with:
> "a constant control star in the same frames"

**5. Item 3: "a 'full' disk in Luhman (2022)".**
Problem: Luhman published two 2022 papers. The disk class is in 2022b (2022AJ....163...25L, VizieR J/AJ/163/25). 2022a (AJ 163, 24) is the membership census and gives no spectral type. The class was also assigned from 2010 AllWISE data, before the change, which a reader should know.
Replace with:
> "a 'full' disk in Luhman (2022b, from 2010 AllWISE data)"

**6. Item 3: "This one has stayed off for 4.5 years."**
Problem: "stayed off" implies continuous coverage. There are five NEOWISE visits at six-month cadence to February 2024, then no 3-5 µm data until SPHEREx in August 2025, an 18-month gap. PDS 70's off phase lasted at most a year, so a return between looks cannot be excluded. The literature check says "at least 4.5 yr".
Replace with:
> "This one has been off at every look since (five NEOWISE visits and three SPHEREx seasons, over 4.5 years), though a short return between looks can't be excluded."

**7. Item 3 heading: "A young star whose hot dust went out in 2021".**
Problem: the window is August 2021 to February 2022.
Replace with:
> "A young star whose hot dust went out in 2021-22 (not yet a case)"

**8. Item 3: "Nothing has measured 10-24 µm since 2010".**
Problem: this is a universal negative that was only partly checked. What I could check supports it:
- MAST has no JWST, HST or Spitzer data within 36".
- IRSA's SOFIA collections (FORCAST included) and Spitzer collections are empty here.
- ESO has only SOFI near-IR frames from 2015-04-05 and no VISIR.
- Spitzer lost 10-24 µm capability in 2009.

Gemini refused the query, and Subaru/COMICS was not checked.
Replace with:
> "I can find no 10-24 µm measurement since WISE in 2010 (nothing in the JWST, SOFIA, Spitzer or ESO archives)"

**9. Item 2: "ATLAS caught the whole event".**
Problem: ATLAS has no data from 2022 Nov 9 to 2023 Feb 11 (solar conjunction; `r1_nightly_J180624.csv`). That is a 94-day gap on the decline, while the magnification falls from about ×2 to about ×1.2. The fit reports the largest gap within 1 tE as 64-75 d.
Replace with:
> "ATLAS sampled the rise, the peak (24-26 nights) and the decline to ×2 before the star went behind the Sun, and found it back near normal in February 2023"

**10. Item 2: "brightening to 5.4 times on 2022 September 19".**
Problem: 5.4 is the model's source magnification (Amax_source 5.42-5.48 in `atlas_fits.json`; 4.4-6.5 across the referee's variants). ATLAS observed ×4.9 (o) and ×5.0 (c) (C2). A microlensing reader separates magnification from the observed flux ratio.
Replace with:
> "brightening about fivefold, peaking on 2022 September 19-20"

**11. Item 2: "the same from 0.5 to 4.6 µm".**
Problem: what supports achromaticity is narrower than this:
- ATLAS c and o peak within 0.3 d with the same width.
- At the single in-event NEOWISE visit (Aug 31), W1 and W2 rose by the same 1.37/1.38 mag. Equal W1/W2 was also the selection criterion.
- Optical and infrared agree only after a separate blend fraction per band (about 0.7 in WISE against 0.85-1.0 in ATLAS). With one IR epoch, that is consistency, not a test.

Replace with:
> "the same in ATLAS's two optical bands, and equal at 3.4 and 4.6 µm in the one NEOWISE visit during it (×3.5 on Aug 31, lower than the optical because WISE's 6" beam includes red neighbours)"

**12. Item 2: "and no other change in 2015-2026".**
Problem: ATLAS reads the star 10-40% faint before 2019. The step follows each unit's PSF width and NEOWISE is flat, so it is instrumental (C7; referee §2.2), but it is visible in the ATLAS series on the live OS-0018 page. The source claim is "no other brightening" (C2: no other 20-day bin above ×1.10).
Replace with:
> "and no other brightening in 2015-2026"

Optionally add: "(ATLAS reads it 10-40% low before 2019, which tracks each unit's PSF width; NEOWISE is flat then)".

**13. Item 2: "beats every non-lens shape I tried".**
Problem: two shapes were tried (three counting the withdrawn Gaussian). "Every" implies a broad search, and Δχ² 26-88 against a flexible symmetric bump is solid but not overwhelming.
Replace with:
> "beats both alternatives I tried: a free symmetric bump with lens-like wings (Δχ² 26-88) and a fast-rise, slow-decay outburst (by far more)"

**14. Item 2: "outside the KMTNet and OGLE fields".**
Problem:
- KMTNet is verified: its footprint reaches only l ≤ 8.5°, and the nearest KMT event is 12.7° away.
- OGLE is not verified:
  - The nearest OGLE EWS event of any year is 6.6° away. OGLE now issues events out to l ≈ 13° at these latitudes and has a "DG" (disk) stream.
  - OGLE GVS (Mróz et al. 2020) had events 3.9° away (BLG847, l = 16.4°) and at b = +6.8° (BLG834, l = 15.1°).
  - Nobody checked a field map.

Replace with:
> "well away from where KMTNet and OGLE report events (the nearest either has reported is 6.6° away)"

**15. Item 2: "in no catalogue, alert stream or paper I could search".**
Problem: true as stated, but the two gaps that matter were not checked. ASAS-SN (API 500, Sky Patrol 404) is the bigger one: at G = 17.0 a fivefold peak reaches G ≈ 15.2, within ASAS-SN's reach. MOA's alert page was empty. A microlensing person will ask about ASAS-SN first.
Replace with:
> "in no catalogue, alert stream or paper I could search (TNS, Gaia alerts, the KMTNet, OGLE and ZTF lists, SIMBAD, VSX, ADS; ASAS-SN and MOA I could not reach)"

**16. Item 1: "So the excess now rests on two instruments, and it has lasted about eight years."**
Problems:
- SPHEREx starts in 2025, so it confirms the excess now, not the 2018 onset, which still rests on NEOWISE alone.
- "Lasted about eight years" implies continuous coverage across an 18-month gap (last NEOWISE visit early 2024, first SPHEREx August 2025).

The arithmetic is fine: an onset in Mar-Aug 2018 to Oct 2026 is 8.2-8.6 yr.
Replace with:
> "So the excess no longer rests on NEOWISE alone (the 2018 onset still does), and it has been there at every look for about eight years."

**17. Delete the line "DRAFT for Alan, not sent."** before sending.

## Checked and fine (no change needed)

- "+41% expected": the report gives +40.7%, a 1045 K blackbody scaled to the NEOWISE post-step W1/W2. Fair. SPHEREx sees 80-90% of it, which the plausible range (+30% to +37%) already conveys.
- "rests on two instruments": fair once fix 16 is made. The SPHEREx excess is measured against a photosphere built from 2MASS and pre-2018 WISE, which is standard. Both caveats (unexplained H/K offset, relative photometry) are in the draft.
- "4.6/3.4 µm ratio matches ~1000 K dust": +20.4% against +20.9% for 1045 K. "Is consistent with" would be slightly more careful, since this is one colour and the D5 window hints at a different shape.
- "centroid … to about 0.5" from 2 to 4.6 µm … not from a catalogued neighbour": the measured shift is 0.05" ± 0.03". The 7.9" and 13.4" neighbours would give 2.1" and 3.6".
- "487 SPHEREx images": the target was measured in 482 of them. Close enough for a note.
- "64 published events recovered blind": 60 are position-and-time matches and 4 rest on VSX typing; several come from alert lists rather than papers. "64 known events" would be more exact (optional).
- G = 17.0, l/b, "a reddened giant" (GSP-Phot gives a K giant/subgiant, logg 3.4), tE 115-150 d: all match.
- Repository access: correct, the advisor has neither access nor a pending invitation.
- PDS 70 sentence: accurate. "3-5 µm inner-disk emission … in 2014-15" would add precision (optional).

## Optional suggestions

- **Selection bug (item 3).** Not required: the note makes no claim about the search, and every number quoted comes from raw IRSA exposures, SPHEREx and ATLAS, independent of the sky pass. The 28 Oct brief did disclose a bug for the other cases, though, and if the advisor reads the H-0006 README later he will find that on the corrected run this star no longer passes the selection (its young-star variability fails the quiet-baseline cut). One clause pre-empts that: "(found by a search whose first run had a bug; everything here is re-measured from the raw exposures)".
- **OS-0016 and OS-0017.** On the site, the advisor will see two earlier apparently unreported lens events from this project, and OS-0019 as a candidate. Item 2 reads as if OS-0018 is the only one. Add: "Two earlier ones, OS-0016 and OS-0017, are the same kind; whatever you advise would apply to all three."
- **Gaia.** He may ask why Gaia did not alert. GOST puts Gaia transits on 2022 Sep 8 and Oct 7, when the model is about 1.6-1.8 mag bright, yet no Gaia alert exists within 60". That is not wrong, just a question to be ready for.
- **The figure for item 3.** The plotted dotted "photosphere" line at 0.2 and the axis label "photosphere ~0.1-0.2 for an M star" predate the referee's calibration (0.09 ± 0.04). Consider regenerating it with that band, plus the SPHEREx and ATLAS points, so the figure tells the same story as the text. At minimum, fix 2 explains the W1 drop.
- **Item 2 figure.** The live OS-0018 page shows the light curves without the point-lens model. Attaching `cases/OS-0018/figures/event.png` would answer his first question for him.
- **Opening sentence.** "No need to answer this before the brief from the 28th" reads oddly. Try: "This doesn't need an answer before the brief from the 28th does." Item 1 removes the weakness the brief gave for ranking OS-0013 last, so "nothing here changes the questions in it" is true, but you could add "though item 1 removes the weakness I gave for ranking OS-0013 last".
- **Length.** At 674 words it is a little over one page, and the fixes add about 60 words. Trims that cost nothing:
  - in item 1, drop "forced PSF photometry," and "It appears in all three SPHEREx seasons;" (keep "no field star exceeds +8%");
  - in item 3, drop "(Gaia DR3 6036595883378187008)", since the 2MASS name suffices.
- **ESO SOFI 2015.** Someone observed J160708 with SOFI (near-IR) on 2015-04-05, 16 frames. If those are spectra, they may give the spectral type that no paper has published. This is for Alan, not for the note.
