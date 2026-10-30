# Hunt H-0008: the lensing sky

**Question.** H-0007 found two gravitational microlensing events by accident, among the stars NEOWISE happened to catch on one of
its day-long visits. What happens if every star in the sky is searched that way, the Galactic plane included?

**Why this hunt.** Microlensing surveys (OGLE, KMTNet, MOA) stare at the bulge, and ZTF and Gaia cover the rest of the sky in the
optical. NEOWISE looked at every star twice a year for ten years at 3.4 and 4.6 µm. That is too sparse to *find* most lensing events,
but a magnified star brightens equally in both bands, which almost nothing else does. The sky2 pass had skipped the plane; this one
does not.

**Data.** NEOWISE-R single exposures 2014-2024 from IRSA's Parquet on AWS, read on Google Cloud (run `sky3lens`,
`infra/gcp/neowise_lens.py`). The Large Magellanic Cloud adds 5 clean brightenings and no lens: its strongest is a hot LMC star
brightening by 1.1 mag in 2021, most likely a Be-star outburst.

Reference events, built into `ext/reference_lenses.csv` by `scripts/hunt_h0008_reference.py`:
- KMTNet (2016-2024) and OGLE EWS (2014-2025);
- OGLE GVS Galactic-disk events (Mróz et al. 2020);
- Gaia DR3 `vari_microlensing` and the Gaia Science Alerts;
- the ZTF catalogues of Zhai et al. 2024 (all 177, from the journal's machine-readable tables), Rodriguez et al. 2022 and
  Medford et al. 2023;
- two TNS microlensing candidates found during refereeing.

Follow-up: AllWISE, Gaia DR3, VSX (VizieR mirror), ZTF DR (IRSA), TNS, ALeRCE, SIMBAD (CfA mirror).

## The survey

| | |
|---|---|
| sky | all 12,288 HEALPix pixels. The 27 densest, almost all of them the Large Magellanic Cloud, needed 64 GB machines (`infra/gcp/sky3lens_lmc.json`) |
| data | 106.7 billion NEOWISE detections |
| stars searched | 194.7 million with ≥ 10 NEOWISE visits |
| compute | Google Cloud Batch, spot VMs, about 3 hours |
| event | 1-3 consecutive visits brighter in both W1 and W2 by ≥ max(0.2 mag, 6σ), equal in the two bands to 0.1 + 15%, every other visit quiet |

**Funnel** (`scripts/hunt_h0008_events.py`, `hunt_h0008_classify.py`; every number is reproducible):

| step | n | what fell out |
|---|---|---|
| one-visit events in both bands | 2,465 | |
| isolated brightenings, not at the first or last visit | 1,022 | 821 isolated fades (not followed up), 622 events at the first or last visit |
| clean | 666 | 356 whose event visit is full of artifact-flagged frames (latents, ghosts, halos), whose PSF fit got 3× worse, or with quasar colours |
| **known microlensing events** (within 6" and in time, or typed Microlens in VSX) | **64** | |
| this project's own events (OS-0016, OS-0017) | 2 | |
| cataclysmic variables in outburst / young stars / other catalogued variables | 41 / 26 / 105 | |
| unclassified | 428 | see below |

## Known events, found blind

The search was never told where the known events are, and it recovered **64**.
- **The matches are secure:** none in 200 position-shifted trials, and at most 2 expected from time coincidences (referee).
- **60 are position-and-time matches.** The other 4 (Gaia23bay, Gaia23cpd, Gaia19bsy, Gaia19dqj) rest on VSX typing them
  Microlens.
- **Most are bright disk and plane events:** 45 lie within 5° of the plane, and the median brightening is 0.49 mag.
- **They include H-0007's hand-found event,** Gaia DR3 4084984459435880064 (×12 in NEOWISE, 2015 Sep 29). The search also
  recovers this project's own two events, OS-0016 and OS-0017, which are not in any catalogue and so are not counted among the 64.
- **Catalogue labels disagree with the lensing interpretation** for ASASSN-21ak (VSX "UG") and two ASAS-SN/VSX "YSO" entries that
  Gaia DR3 lists as lenses.

**How much NEOWISE can see** (referee, with real NEOWISE visit dates):
- **Inner bulge** (|l| < 10°, |b| < 5°): 2.5% of catalogued events magnified at a NEOWISE visit (6/239). WISE's 6" beam holds dozens
  of stars, so a magnified one is diluted to a few hundredths of a magnitude.
- **Elsewhere:** 14% (4/29), or 7% (6/85) of the full Zhai disk list. But 59 of those 85 have no AllWISE source at all, and the
  pipeline only searches AllWISE-matched stars.
- **Disk events on stars NEOWISE can measure** (AllWISE W1 ≤ 15): **6 of 15, about 40% (16-68%)**.
- **Two blind spots:**
  - peaks brighter than W1 ≈ 8, whose saturated frames are dropped (ZTF19abagvae brightened 2.5 mag in W1 and is missing);
  - long events: the "every other visit quiet" rule rejects about a third of events with tE > 100 d.

So NEOWISE is a useful independent detector for bright disk events, not yet a survey with a known selection function. The efficiency
figures in the first draft (KMT 3/167, OGLE 4/118, Gaia 4/7) used a visibility model that misplaced half of the NEOWISE visits by
about three weeks. They are withdrawn.

## Events with ZTF light curves (`figures/ztf_events.png`)

| event | identity | peak | tE | status |
|---|---|---|---|---|
| **J180624.78-090411.4** (l 19.7, b +5.7) = **[OS-0018](../../cases/OS-0018)** | ZTF22abjkknd (an alert object with no positive transient) | 2022 Sep 19-20 | 115-150 d | **an apparently unreported microlensing event.** ATLAS samples the peak (×5.4) and both wings; a point lens fits from c to W2 and beats any flexible bump. P(microlensing) 0.95 (ATLAS referee). Reproduced |
| **J183040.98-220950.3** (l 10.9, b −5.6) = **[OS-0019](../../cases/OS-0019)** | ZTF22aalviwh (ALeRCE class LPV/YSO; its classifier has no microlensing class) | 2022 Aug 15-20 | unconstrained (effective timescale ~35 d) | an apparently unreported **microlensing candidate**: achromatic from g to W2, single, on the M giant itself, but a point lens needs 80-90% blend light Gaia does not see. P(microlensing) 0.65. Candidate |
| J173342.30-205204.5 (l 5.4, b +6.6) | ZTF21abahtfi = AT 2021aicc, posted to TNS by ALeRCE as a microlensing candidate (2024) | 2021 Jul 21 | 51 d | known as a candidate; **first fit, and first infrared confirmation of achromaticity** (fs 0.97-1.05 from g to W2). Reproduced |
| J204610.56+514104.9 (l 89.8, b +5.3) | ZTF22aagdkla (Zhai et al. 2024, high confidence) = AT 2022aexe / XOSS KATS22J002 | 2022 May 26 | 45 d | known; recovered blind. A static lens is rejected (Δχ² ≈ 220 to parallax) |
| J190512.73+145135.7 (l 47.7, b +3.7) | ZTF21aaowecs (Zhai et al. 2024) = Gaia21bde = AT 2021dzr | 2021 Mar 31 | 35-44 d | known; recovered blind |
| J180441.77-182728.7 (l 11.3, b +1.5) | ZTF22abcfjfp (Zhai et al. 2024, possible) | 2022 Sep | 15 d (Zhai: 14.1 d) | known; a check on the method |

**What went wrong first.** The first draft of this README called four of these "new". Three were not. Zhai et al.'s full list sits
in an online-only table that the investigators had not reached, and TNS was rate-limiting. The referee found both. The correction is
in "what we got wrong" on the site.

## ATLAS: one event, one candidate (`figures/candidates_atlas.png`)

ATLAS forced photometry (tasks 5272650-1, `work/atlas/`) arrived on 30 Oct. Fits: `scripts/hunt_h0008_atlas_fit.py`
(`work/atlas_fits.json`); second referee: [`reviews/claude-referee-atlas-2026-10-30.md`](reviews/claude-referee-atlas-2026-10-30.md).

- **J180624 (OS-0018) is a microlensing event.** One smooth, symmetric brightening in 2015-2026: ×1.1 in March 2022, ×5.4 at the
  peak on Sep 19-20 (24-26 ATLAS nights near it), ×1.2 by February 2023. Point lens with annual parallax and blending per series,
  ATLAS + ZTF + NEOWISE: tE 112-131 d (95%), 113-153 d across 18 reduction choices, so **tE ≈ 115-150 d**; u0 0.16-0.23; source
  fraction 0.8-1.0 in the optical and 0.7 in W1/W2 (red neighbours in WISE's beam). It beats a free symmetric bump with lens-like
  wings (Pearson VII) by Δχ² 26-88 and a fast-rise/exponential-decay pulse by ~4,000. c and o peak within 0.3 d with the same
  timescale. Parallax is a one-dimensional hint (Δχ² 4-36), and **no lens mass is measured** (allowed: ~0.3 to 10 M☉).
  Before 2019 ATLAS reads it 10-40% faint, stepping with each unit's PSF width; NEOWISE is flat, so that is instrumental.
- **J183040 (OS-0019) stays a candidate.** The brightening (×1.55-1.6, 2022 Aug 15-20) is real, single and achromatic, and the ZTF
  difference-image centroid sits 0.09" from the Gaia star. But tE runs from 77 to over 700 d with reduction choices, a lens fits only
  with an 80-90% blend in every band that Gaia does not resolve, and a symmetric bump fits better. Its fitted parameters are
  withdrawn; the figure shows it without a model.
- **What the referee corrected in our first fit:** a chi/N < 10 cut that removed the peak (chi/N grows with flux), a baseline inside
  the lens wings (|Δt| > 250 d; now 400 d, through 2026), ZTF r field 1428 dropped (the only ZTF data on J180624's rise), the baseline
  scatter counted twice in the errors, and a Gaussian as the only rival shape (its wings are too thin to be fair).
- **Sealed predictions** (registered in the cases, on the Sky Ledger after merge), worded with Gaia's scanning law (GOST): DR4 shows
  no repeat (OS-0018 brightest night > −0.5 mag, p 0.85; OS-0019 > −0.3, p 0.80); DR4 shows ATLAS's 2015-16 dip is instrumental
  (|ΔG| < 0.1, p 0.90 and 0.95); DR5 sees the events (OS-0018 brightest night in 2022 Feb - 2023 May < −1.2 mag, p 0.85, and both wings;
  OS-0019 < −0.3, p 0.85). A Sep-Oct 2022 window would hold only 2 Gaia transits, too few to grade.
- **The grader now keeps Gaia's variability-outlier transits** when grading (it still drops photometry rejections). Gaia flags
  transits that depart from a star's usual brightness, which during a lens peak are the peak itself. This also affects OS-0016 P1,
  sealed on 29 Oct for the same kind of window; the change was made before any DR4 data exist.

## The 428 unclassified

They cluster in the Galactic plane (`figures/lensing_sky.png`). In the referee's sample about 80% behave like ordinary variable stars:
chromatic in the infrared, flat in the optical. Roughly 10-25% look like lenses, and most of those are in the south, where there is no
ZTF to check them. 66 are strong (achromatic to 0.08 mag, ≥ 0.4 mag; `work/sky3_strong.csv`; TNS was rate-limiting again for 32 of them, recorded as
errors; the referee's paced TNS pass, `reviews/claude-referee-2026-10-30/r16_tns_strong.csv`, covers the same events). Four still coincide with Gaia alerts
that Gaia never classified (Gaia21atr, Gaia23boj, Gaia23bnj, Gaia23crp = AT 2023tvg); for an alert with no spectrum, a brightening equal at 3.4 and 4.6 µm is
a classification hint.

## A tool came out of it

`lens_fit` is now an Oddsky tool (25 in all). It fits a point lens to any set of a case's series, with annual parallax beside the
static model, chi-square profile ranges instead of covariance errors, and warnings when the peak is unsampled or the light curve is
asymmetric. It reproduces both H-0007 referees' hand fits in seconds (OS-0016: tE 47-52 d; OS-0017: t0 2020 Mar 19-22, tE 39-48 d).

## Next

- ATLAS for the ten strongest lens-like unclassified events that ZTF cannot check (south of ZTF, or before 2018): queued
  2026-10-30, `work/atlas/queue.csv` (`scripts/hunt_h0008_atlas_queue.py`).
- A TNS report for OS-0018 (needs the project's TNS account; not filed).
- **Literature (done 2026-10-30, `scripts/hunt_h0008_ads.py`):** ADS full text has no hit for either candidate's ZTF name
  (ZTF22abjkknd, ZTF22aalviwh), WISE designation, 2MASS-style name, short name or sexagesimal coordinates (the two coordinate
  hits are unrelated papers). ADS full text is only a partial net, though: of seven names of published events used as positive
  controls, it found five and missed two that appear only in journal tables (e.g. ZTF20abwxmep in Zhai et al. 2024). A web search
  on the ZTF names finds nothing; XOSS's candidate pages were unreachable, but XOSS reports to TNS, which has nothing within 60".
  So: not in any catalogue, alert stream or text we can search, which is the strongest "apparently unreported" we can state.
- The long-lens rerun is hunt [H-0009](../H-0009): saturated frames kept, the quiet-elsewhere rule relaxed for tE > 100 d, and two
  blind spots this survey never measured (stars beside a bright one, and deblended stars) closed.

## Lessons

- Catalogue completeness is the hard part. The reference list was scattered across HTML pages, LaTeX sources and online-only
  journal tables. Missing one (Zhai's full list) turned three recoveries into false discoveries until the referee found it.
- An HTTP 429 from TNS is not "nothing found". The vetting script now records it as an error.
- The plane is where both the lenses and the impostors are. Artifact share per visit and a χ² test removed a third of the raw events.
- 19-digit ids lost precision as float64 again, twice: concatenating empty per-pixel tables made `allwise_cntr` float, and the VSX
  step re-read the cross-match table without fixing the Gaia id column's type, so exact Gaia ids came back as `4.08e+18`. The
  second bug silently emptied the id-based Gaia DR3 microlensing check, and it had also re-corrupted the H-0007 tables 'fixed' a day
  earlier. Every table is regenerated and checked (0 float-looking ids). Counts are unchanged: all 14 Gaia DR3 lenses had already
  been found by position.
- TNS has objects at 7 of the 70 strong events of the first pass: the five Gaia alerts above (as ATs) and two microlensing candidates (J173342 from
  ALeRCE, J204610 from XOSS). The first vetting pass saw none, because TNS was rate-limiting.

Referees: [`reviews/claude-referee-2026-10-30.md`](reviews/claude-referee-2026-10-30.md) (the survey) and
[`reviews/claude-referee-atlas-2026-10-30.md`](reviews/claude-referee-atlas-2026-10-30.md) (the ATLAS light curves). Files: `scripts/hunt_h0008_*.py`,
`infra/gcp/neowise_lens.py`, `infra/gcp/sky3lens*.json`, `work/` (event tables, efficiencies), `ext/` (reference catalogues),
`figures/`. Per-pixel outputs: `gs://oddsky-sky-br3c3-data/runs/sky3lens/`.
