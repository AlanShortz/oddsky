# Gaia DR4 day: five forecasts for Oddsky's searches

Author: claude (H-0014 forecasts), 2026-11-02; revised the same day after the referee's report ("seal after changes"; every
blocking and recommended item applied). **A pre-registration, drafted for sealing. Not yet sealed.** It is sealed by the commit
that merges it into `main`, which must happen before Gaia DR4 is released (scheduled 2026-12-02, about 11:00 UTC). After that
commit nothing here may change, except the adaptations listed in section 6. Computed with numpy 2.5.4, pandas 2.3.3 and Python
3.12.16 (the grader prints the versions it runs with).

Machine-readable sample: [`dr4_search_sample.csv`](dr4_search_sample.csv), one row per item, with a `forecast` column (F1, F3,
F4, F5; F2 uses the F1 rows with `f2_member` true). Grader: [`dr4_search_grade.py`](dr4_search_grade.py). Forecast numbers:
[`work/forecast.json`](work/forecast.json), made by [`work/forecast.py`](work/forecast.py) (log: `work/forecast.log`). Hunt:
[H-0014](../README.md).

## The forecasts

| | what is counted (all from Gaia DR4 products and Oddsky's committed lists) | model | graded statement (fixed) | P(hit) | resolve by |
|---|---|---|---|---|---|
| **F1** | of H-0010's 67 classifier-only MICROLENSING sources, how many are in DR4's microlensing catalogue | median 21, mean 20.6 | **13 ≤ count ≤ 36** | **0.67** | 2027-01-31 |
| **F2** | among the 39 of those 67 that no survey catalogued, does Oddsky's sealed P(lens) rank catalogue membership the way the catalogue's selection does | AUC median 0.62 (80%: 0.44-0.77) | **AUC > 0.60** | **0.54** (0.20 if the catalogue ignored Oddsky's P) | 2027-01-31 |
| **F3** | of H-0010's 21 first-pass lens candidates, how many fail DR4's single-event test (DR3 event not reproduced, or a new brightening of ≥ 0.3 mag after DR3's span) | median 4, mean 3.6 | **2 ≤ count ≤ 6** | **0.82** | 2027-03-31 |
| **F4** | of the 61 strong NEOWISE events in DR4's span not already confirmed by Gaia DR3, how many DR4's microlensing catalogue lists at the NEOWISE time | median 2, mean 2.7 | **2 ≤ count ≤ 6** | **0.64** | 2027-01-31 |
| **F5** | 444 unclassified NEOWISE brightenings (blind): excess of Gaia DR4 brightenings at the NEOWISE time over control times one and two years away | excess median 0.043 (80%: 0.009-0.099) | **excess > 0 with p < 0.05** (signs flipped per Gaia star) | **0.80** | 2027-03-31 |

**Named sources.** Each has a probability of being in DR4's microlensing catalogue (at the NEOWISE time for F4 events). They are
members of F1/F2 or F4 and are scored individually with the Brier score. They are not separate bets.

| source | P(lens) (case file or H-0010 referee) | P(in DR4's catalogue) | in |
|---|---|---|---|
| OS-0016 (J040025.77+323527.4, Gaia DR3 170329679884731008) | 0.95 | 0.43 | F4 |
| OS-0020 (J163539.69-355208.3) | 0.75 | 0.35 | F4 |
| OS-0021 (J173150.73-444549.3) | 0.55 | 0.28 | F4 |
| OS-0026 (Gaia DR3 5959812622743175552) | 0.65 | 0.31 | F1 |
| OS-0027 (Gaia DR3 4143495279954502016) | 0.60 | 0.30 | F1 |
| OS-0029 (Gaia DR3 4145977633638478336) | 0.50 | 0.29 | F1 |
| J174618.09-253631.3 (4067152339419332992) | 0.75 | 0.33 | F1 |
| J173332.42-421445.1 (5958944416543307648) | 0.75 | 0.33 | F1 |
| J072830.43-204112.5 (5620272814897694848) | 0.60 | 0.30 | F1 |

All nine are near or below one half. Oddsky expects Gaia's DR4 catalogue to miss a substantial fraction of the lenses Oddsky
finds, as DR3's catalogue missed OS-0026, OS-0027, OS-0029 and 28 known lenses that its own classifier had found (H-0010).

**What the five test.**

- F1 and F4 measure how far Gaia's independent lens catalogue reaches into Oddsky's lists.
- F2 tests whether Oddsky's P(lens) ranks sources the way Gaia's catalogue selection does. Both reward clean, lens-like light
  curves, so agreement is not proof that either is right.
- F3 tests Oddsky's strongest lens criterion, "a single event", with 2.6 more years of Gaia data.
- F5 tests whether Oddsky's weaker NEOWISE brightenings have optical counterparts in Gaia at the same time, against a built-in
  control.

**What they do not duplicate.**

- The 15 sealed case predictions on GAIA:G grade light-curve thresholds of individual case stars (OS-0016, OS-0018 to OS-0025).
  None is about catalogue membership, H-0010's candidates or the unclassified events.
- The sealed H-0009 ensemble (`hunts/H-0009/predictions/dr4_ensemble.md`) counts how many of its 47 testable strong events pass
  the ±30 d two-transit rule and what colour they are.
- F4 uses **the same 50 ensemble events plus 11** and asks a different question: does Gaia's catalogue, built by Gaia's own
  pipeline and inspection, list the event? F4 inherits the ensemble's per-event lens probabilities, so the two are correlated
  (section 7).
- F5 applies the ensemble's rule, unchanged, to a disjoint sample with controls.
- The ensemble's lens-fraction test is not repeated here.

## 1. Data, the catalogue and identities

- **Release products.** Everything is read from the outputs of the DR4-day pipeline (`scripts/dr4_day.py --release dr4`, code in
  `src/oddsky/dr4day/`, sealed with H-0014):
  - `catalogue/lens_catalogue.csv`, the catalogue joined to `gaiadr4.gaia_source` for positions;
  - `catalogue/target_flags.csv`, the archive's answer for each of our ids, from `gaiadr4.all_source_flags`;
  - `idmap.csv`, `epoch_status.csv` and `search/metrics.csv`;
  - the epoch-photometry cache `epoch/<DR4 id>.csv`.
- **Which catalogue (pinned now).**
  - The catalogue is the table `gaiadr4.vari_microlensing`.
  - If DR4 has no table of that name, it is the union (by source) of all DR4 tables whose documentation describes them as
    catalogues of microlensing events. The pipeline writes that union to `lens_catalogue.csv`, a retrieval step under section 6.
  - If DR4 has no such table, F1, F2 and F4 are **unresolvable**.
  - A "candidates" table and a "confirmed" table, if both exist and both are so described, are both in the union. No choice is
    made after the data.
- **Our ids are Gaia DR3 ids.** They are mapped to DR4 ids only by the pipeline's `idmap` stage: the nearest DR4 source in
  `gaiadr4.dr3_neighbourhood` within 0.5″ whose G differs by at most 0.3 mag. With no such source, the DR3 id is used as it is
  (the rule sealed in `dr4_ensemble.md` §2.5 item 4).
- **DR4 identity.** A source has a DR4 identity if the id used for it (mapped, or DR3) appears in `target_flags.csv`, or if it is
  matched to the catalogue by id or position.
- **Catalogue membership** (F1, F2) means either of:
  - the DR4 id or the DR3 id equals a catalogue `source_id`;
  - a catalogue row with a position lies within 0.5″ of the source's DR3 position.

  Repeated rows for one source count once.
- **Columns** are found only through the look-up lists `COLUMNS` in the grader:

  | quantity | look-up list |
  |---|---|
  | source id | `source_id` |
  | ra, dec | `ra`, `dec` |
  | peak time | `paczynski0_tmax`, `paczynski1_tmax` |
  | tE | `paczynski0_te`, `paczynski1_te` |

  Section 6 item 1 allows names to be appended to these lists and nothing else.
- **Time.** The peak time is always taken from the raw catalogue column and converted to MJD. A value below 20,000 is read as
  Gaia's BJD(TCB) − 2455197.5 (the DR3 convention), above 2,000,000 as a JD, otherwise as an MJD. The pipeline's own derived
  `tmax_mjd` is never used.

## 2. The forecasts in detail

### 2.1 F1: H-0010's 67 in DR4's microlensing catalogue

**Sample.** The 67 sources that Gaia DR3's classifier labelled MICROLENSING and that are not in DR3 `vari_microlensing`
(`hunts/H-0010/work/gaia_ml_unpub.csv`). The list is Rimoldini et al. 2023's; H-0010 and its referee vetted it one by one.
After the referee it holds:
- 28 catalogued OGLE/KMTNet lenses;
- 3 Oddsky cases (OS-0026, OS-0027, OS-0029);
- 21 first-pass candidates: 9 still at P ≥ 0.4, 1 published by Mróz et al. 2020, 10 inconclusive, 1 rejected;
- 8 inconclusive;
- 7 not lenses, 2 of them artifacts.

**Statistic.** The number of the 67 in the catalogue (section 1), whatever the catalogued peak time.

**Identity floor.** If fewer than 60 of the 67 have a DR4 identity, F1 and F2 are **not yet resolvable**: the catalogue stage is
rerun. If that is still so 60 days after the resolve-by date, they are unresolvable. Sources without an identity are never
dropped to shrink the sample. With 60 or more identities, the count runs over all 67 against the fixed bounds.

**Forecast.** Median 21, mean 20.6. **Hit if 13 ≤ count ≤ 36** (probability 0.67). P(count ≤ 12) = 0.26,
P(count ≥ 37) = 0.07.

| group | n | expected in the catalogue |
|---|---|---|
| catalogued lenses | 28 | 11.8 |
| Oddsky cases | 3 | 0.9 |
| first-pass candidates | 21 | 5.3 |
| inconclusive | 8 | 2.0 |
| not lenses | 7 | 0.6 |

**Reasoning (section 3 gives the model).**

- **Two scenarios for DR4's selection.**
  - DR4's catalogue has 1,360 rows over 66 months; DR3's had 363 over 34. That is about twice as many events per year, so DR4's
    selection is probably broader. If the rate is uniform, about 700 DR4 events peak inside DR3's span, some 340 more than DR3
    listed.
  - The 67 are a natural pool for those extra events. Gaia's classifier gave each a single-event label, though 7 of them are not
    lenses and 2 are artifacts.
  - But DR4 may also repeat DR3's cuts, in which case few of the 67 enter. The prior gives that scenario 25% weight (section 3):
    the completeness is below 0.15 with probability 0.21.
  - That honest width is why P(hit) is only 0.67, and why a count of 12 or fewer has probability 0.26.
- **What DR3 lost them to.** It is only partly known (H-0010 §"The 28 catalogued lenses", corrected by its referee).
  - 24 of the 28 known lenses were never in DR3's survey-matched input list (Sample B). They failed the unpublished automated
    cuts of Sample A (G0 < 19, 20 < tE < 300 d, …).
  - Three have OGLE tE ≤ 20 d, below Sample B's cut.
  - If DR4 matches against the full OGLE and KMTNet alert lists, most of the 28 enter.
- **Modifiers.**
  - Nine of the known lenses peaked within 120 days of DR3's end, so DR3 saw only their rise or peak. DR4 sees the whole event
    (×1.3).
  - Sources fainter than G = 19 are less likely to pass a G0 < 19 style cut (×0.7).
- **Non-lenses** enter only if they look like lenses. DR3's catalogue did take in contaminants (10 LPVs and 1 YSO among its
  363). Non-lenses with lens-like light curves get a mean inclusion probability of 0.2, refuted non-lenses 0.1, and the two
  artifacts 0.025.

### 2.2 F2: does Oddsky's P(lens) rank sources the way Gaia's catalogue does?

**Sample.** The 39 F1 sources that no survey catalogued: the 3 cases, the 21 first-pass candidates, the 8 inconclusive and the 7
non-lenses (`f2_member`), restricted to those with a DR4 identity.

**Score.** Each source's P(lens) as sealed in `p_lens`. It contains no model of the catalogue.

| sources | P(lens) used |
|---|---|
| 21 first-pass candidates | the referee's P, or the later ATLAS P where ATLAS revised it (J200958 0.45, J184922 0.10, J182811 0.25) |
| 3 cases | the case files' P: OS-0026 0.65, OS-0027 0.60, OS-0029 0.50 |
| the other 15 | H-0010's P |

**Statistic.** The AUC of the score for F1's membership outcome. Ties count one half. It equals the Mann-Whitney U divided by
the number of (in-catalogue, out-of-catalogue) pairs.

**Forecast.**
- AUC median 0.62 (80%: 0.44-0.77). **Hit if AUC > 0.60** (probability 0.54).
- If catalogue membership were unrelated to the score, P(AUC > 0.60) would be 0.20. A hit is therefore about 2.7 times likelier
  under the model than under "unrelated".
- Reported but not graded: whether the AUC exceeds 0.5 (model probability 0.80), and the one-sided Mann-Whitney p-value (normal
  approximation with tie and continuity corrections; P(p < 0.05) = 0.25).

**Not graded** if none or all of the identified members are in the catalogue (probability 0.014).

**What it can and cannot say.**
- Oddsky's P(lens) and Gaia's selection both reward clean, lens-like light curves. In the model, that alone gives P(AUC > 0.5)
  of about 0.6 even if lens truth were unrelated to the score.
- So a hit says Oddsky ranks sources as Gaia's catalogue selection does, not that Oddsky's vetting is right.
- A miss with AUC near or below 0.5 would mean Oddsky's P values and Gaia's catalogue disagree about which of these sources are
  lenses. Oddsky would then re-examine its P values before quoting them again.
- **Power is low.** About 9 of the 39 are expected in the catalogue, and most scores lie between 0.25 and 0.75.

### 2.3 F3: the single-event test of H-0010's 21 candidates

**Sample.** H-0010's 21 first-pass lens candidates (its table "New lens candidates"), whatever the referee later decided. The
DR3 Gaia peak time is fixed in the sample (`t_peak_dr3`).

**Transits.** A valid G transit has no `rejected_by_photometry` flag and a finite time and magnitude. Variability-flagged
transits are kept. A transit id listed more than once counts once.

**Untestable** (counted neither way) if any of these holds:
- the archive says the source has no DR4 epoch photometry (`epoch_status` "absent");
- the pipeline's analysis label is missing or empty, starts with "too few" (fewer than 10 G transits), or starts with "analysis
  error";
- DR4 has no valid G transit within 45 days of the DR3 peak;
- DR4 has fewer than 10 valid G transits after MJD 57931 (2017-06-27, 30 days after DR3's last transit).

**Fails** if either:
- **not reproduced:** no DR4 brightening episode peaks within 45 days of the DR3 peak with its peak transit at least 0.15 mag
  brighter than baseline;
- **repeats:** a DR4 episode made of at least 3 transits beyond the episode threshold, with its peak transit at least 0.30 mag
  brighter than baseline, peaks after MJD 57931 and at least 200 days from the DR3 peak.

Episodes are the pipeline's sealed `lightcurves.episodes`: clusters of at least 2 G transits brighter than max(4σ, 0.08 mag),
split by a quiet transit and a gap of more than 30 days. They are read from `bright_eps` in `metrics.csv`
("t_peak:dG_peak:n"; n counts the transits beyond the threshold).

**Statistic.** The number of testable candidates that fail.
- **Void if fewer than 15 of the 21 are testable.**
- With 15-20 testable, the hit is still decided by the fixed bounds. The grader also reports the model's probability of those
  bounds for the testable subset.

**Forecast.** Median 4, mean 3.6. **Hit if 2 ≤ count ≤ 6** (probability 0.82). P(count ≤ 1) = 0.11, P(count ≥ 7) = 0.07.
Expected: about 1.6 not reproduced and 2.2 repeats (a candidate can do both).

**Reasoning.**

- **Lenses do not repeat.** A real lens fails only through a spurious second episode in crowded photometry: 2% per source at
  G ≤ 19, 4% fainter. DR3 shows the scale: among the 67 over 2014-2017, the one second episode brighter than 0.3 mag was an
  artifact.
- **Non-lenses repeat.** They are Be stars, young stars, other outbursters and artifacts that showed one event in DR3's 2.8
  years.
  - The chance that one shows another qualifying episode in the next 2.6 years is put at 10-35% (uniform, shared).
  - That allows for Gaia's sampling (a month-long burst gets ≥ 3 transits about half the time) and for intrinsic recurrence
    times of a few years.
  - H-0010 had already checked some candidates for repeats, which lowers the chance. NEOWISE 2014-2024 was checked for 5 and
    catches a month-long repeat about a third of the time (×0.75). ZTF 2018-2025 was checked for 11 and catches one about 60% of
    the time (×0.4).
- **Not reproduced.** DR4 reprocesses the same 2014-2017 transits with better crowding treatment. A real event survives it. A
  crowding artifact might not.
  - 2% at G ≤ 19 and 5% fainter.
  - 8 points more for the events seen on only two scan dates (J175414, J182656, J182811).
  - 35% for J190032, whose "event" is two single transits in one field of view.
  - A shared multiplier, uniform from 0.5 to 2, is applied.
- **A known risk of false repeats.** For the two long events, J072830 (DR3 fits allow tE up to 188-456 d) and J173332 (tE about
  140 d), a long wing broken by one quiet transit could read as a second episode. The DR3 self-test could not check this,
  because DR3 ends before their late wings. The 200-day separation, the 0.30 mag depth and the 3-transit requirement make it
  unlikely. If either fails F3 by "repeat", its light curve is published so readers can judge.
- **What the counts would mean.**
  - A count of 0 or 1 (probability 0.11) would mean almost every candidate is a clean single event in 2014-2020. That is good
    news for H-0010, but a miss for this forecast.
  - A count of 7 or more would mean H-0010's list is materially contaminated by recurrent variables.
  - In every case, the verdict of each failing candidate is withdrawn in public.

### 2.4 F4: strong NEOWISE events in DR4's microlensing catalogue

**Sample (61 events).**
- The same 50 events as the sealed ensemble sample (`dr4_ensemble_sample.csv`), including the three it calls untestable by
  design, with the same tested Gaia DR3 star and centroid neighbour (`alt_source_id`).
- The 11 strong events in DR4's span with no Gaia DR3 source within 4″.

Together these are the 64 strong events of H-0008/H-0009 whose NEOWISE peak lies in DR4's span, less the three Gaia DR3 already
confirmed (OS-0026, OS-0027, OS-0029). Those three are counted in F1 instead.

**Catalogued** if a catalogue row satisfies both conditions:
1. **Same object:**
   - its `source_id` equals the DR4 id (through `idmap.csv`) or the DR3 id of the tested star or of its neighbour; or
   - it lies within 3.0″ of the event's AllWISE position (the survey matched stars within 3″).
2. **Same time:** its peak time is within max(60 d, min(2 tE, 365 d)) of the NEOWISE peak-visit time, with tE from the same
   row. If tE is missing, the window is 60 d. A row without a peak time cannot satisfy this condition. The grader reports how
   many rows lack one.

**Time check.** If the catalogue has no peak-time column, or its median peak time is not inside MJD 56,000-59,500, F4 is **not
yet resolvable** until a section 6 item 4 change fixes the zero point.

**Statistic.** The number of catalogued events. An event counts once however many rows match.

**Forecast.** Median 2, mean 2.7. **Hit if 2 ≤ count ≤ 6** (probability 0.64). P(0) = 0.14, P(1) = 0.18, P(≥ 7) = 0.04. The
model correlates it with F1's count at 0.65 (one catalogue).

**Reasoning.**

- **Where the expected count comes from.**
  - About 1.1 of the expected 2.7 comes from the three large, ATLAS-confirmed events (OS-0016, OS-0020, OS-0021).
  - About 1.6 comes from 58 low-probability events (about 0.03 each). Their lens probabilities are the ensemble model's,
    mostly blind priors.
- **The named three** use their case files' P(lens): OS-0016 0.95, OS-0020 0.75, OS-0021 0.55. The ensemble's weights were 0.17
  (blind, because its sample row carries no case link), 0.80 and 0.60.
- **Catalogue completeness** for these events is the shared completeness of section 3 times 0.8. They were unknown to every
  survey and alert stream, so they can enter only through Gaia's own automated selection. It is further multiplied:
  - by 0.7 at G > 19;
  - by 0.6 for events inside DR3's span, which DR3 did not flag as variable (a lens it missed was probably poorly sampled);
  - by 1.5 for the three ATLAS-confirmed events (large and well sampled);
  - by the chance that Gaia sampled the event: 1.0 with ≥ 3 GOST transits within ±30 d, 0.7 with 2, 0.3 with fewer.
- **No Gaia DR3 star.** The 11 events without one need a new, faint DR4 source to be catalogued: about 0.6% each.
- **The cautionary base rate.** DR3's catalogue listed none of the three strong-event lenses DR3 saw (0 of 3), though its
  classifier labelled all three.

### 2.5 F5: do the unclassified NEOWISE brightenings have optical counterparts in Gaia?

**Sample (444 events on 421 Gaia stars).** NEOWISE brightenings that H-0008 (`sky3_classified.csv`) or H-0009
(`sky4_classified.csv`) classed `unclassified`, with a Gaia DR3 star and a NEOWISE time inside DR4's span (H-0014 target set
`unclassified`). Of 503 such events, 59 are dropped and nothing else:
- 58 that are strong events, H-0010 sources or case stars (not blind, or already in F1-F4 and the ensemble);
- 1 whose light curve Gaia DR3 published (its answer is partly known).

46 of the 444 events lie on 23 stars that carry more than one event.

**Per event.**
- The sealed ensemble rule (`grade_series` in `hunts/H-0009/predictions/dr4_ensemble_grade.py`, `dr4_ensemble.md` §2.2,
  unchanged) is applied at the NEOWISE time t.
- It is applied again at each control time t − 730.5, t − 365.25, t + 365.25 and t + 730.5 d that lies inside DR4's span.
  Every event has 2-4 control times.
- The rule passes if at least 2 transits within ±30 d are brighter than the median of the transits more than 150 d away by
  max(15%, 5 × their scatter).

**Statistic.**
- Paired events are those testable (pass or fail) at t with at least one testable control.
- For each paired event, d = (1 if pass at t, else 0) − (passes at control times / testable control times).
- The **excess** is the mean of d.
- Its significance is a one-sided sign-flip permutation test: 20,000 random flips, seed 20261202, **one sign per Gaia star**
  (all events on a star share it). p = (1 + number of flipped means ≥ the observed mean) / 20,001.

**Forecast.**
- Excess median 0.043, mean 0.050, 80% interval 0.009-0.099. **Hit if the excess is > 0 with p < 0.05** (probability 0.80).
- The interval is reported, not graded; the graded statement is the significance.
- About 370 paired events are expected. **Void if fewer than 150.**

**What the excess measures.**
- A star whose variability is unrelated to the NEOWISE time passes at control times as often as at t, so on average it adds
  nothing.
- A star that brightens at the NEOWISE time adds to the excess. That includes a transient, and also a variable that the NEOWISE
  selection caught near maximum.
- The excess therefore measures **optical brightenings coincident with the NEOWISE ones**, not transient events as such.

**Reasoning.**
- **On-star brightenings.** The fraction of events with a real brightening of the Gaia star at the NEOWISE time is Beta(2, 18),
  mean 0.10. That is about half the strong events' on-star fraction (lens 0.14 plus non-lens optical 0.075 in the ensemble
  calibration). These events are weaker (median ΔW1 −0.33 mag against ≥ 0.4) and more often chromatic, which points to
  infrared-only or neighbour events.
- **Pass rates.**
  - A real brightening passes 35-70% of the time: weaker events give smaller G amplitudes.
  - A flat star passes 0.5-3% of the time at any epoch.
  - About 3% of the stars (Beta(1.5, 48.5)) are strongly variable and pass 10-40% of the time at any epoch. The calibration:
    DR3 published light curves, which it did for variables only, for 1 of the 445 candidate events and for about 1% of all 902
    unclassified events. DR3's variability detection misses perhaps half of such stars, hence 3% rather than 1%.
- **Variables caught at maximum** add to the excess, as they should under the definition above. The model treats them as
  unrelated, which makes its excess slightly conservative.
- **The test is conservative.** The referee simulated the sign-flip test under realistic nulls: false-positive rates of
  0.014-0.038 at α = 0.05.

**What a result would mean.**
- A miss with an excess near 0 says the weaker unclassified NEOWISE events are almost all artifacts, infrared-only or on a
  neighbour. Search #6 of H-0014 would then be a low-yield search.
- A large excess (above 0.10) would make the passing events a discovery list worth refereeing one by one.

## 3. The model

All five numbers come from Monte Carlos in `dr4_search_grade.py` (`model_f1`, `model_f3`, `model_f4`, `model_f5`; 20,000
realisations, 4,000 for F5; seeds fixed in the file). `work/forecast.py` calls them and writes the sample and
`work/forecast.json`. The graded bounds are fixed (`GRADED` in the grader) and are never recomputed.

| parameter | prior | used by |
|---|---|---|
| c0: completeness of DR4's catalogue for a real single-lens event that DR3's classifier labelled MICROLENSING | a mixture: with weight 0.75 Beta(3, 3.5) (mean 0.46, DR4's broader selection), with weight 0.25 Beta(1, 8) (mean 0.11, "DR4 repeats DR3's cuts"). P(c0 < 0.15) = 0.21. **Shared by every source and by F1, F2 and F4** | F1, F2, F4 |
| per-source completeness | c = min(0.95, c0 × the multipliers in `cat_mult`, listed per row in `notes`) | F1, F4 |
| f0: inclusion of a non-lens with a lens-like DR3 light curve | Beta(1.5, 13.5), mean 0.10. ×2 for candidates, inconclusive sources and cases (they look like lenses), ×1 for refuted non-lenses, ×0.25 for the two artifacts | F1, F2, F4 |
| P(lens) | `p_lens` per row (sections 2.1-2.4) | all but F5 |
| r0: repeat chance of a non-lens one-off brightener in 2017.5-2020.0 | uniform 0.10-0.35, shared. ×0.75 if NEOWISE checked, ×0.4 if ZTF checked | F3 |
| not-reproduced chances | `p_norepro` per row, × a shared uniform 0.5-2 | F3 |
| F5 fractions and pass rates | section 2.5. 85% of epochs testable | F5 |

Per-item probabilities (`p_in` for F1/F4, `p_fail` for F3) are the model's means. They are in the sample for Brier scoring.

## 4. Grading, missing data and resolve-by dates

**Running the grade.**
- Run `uv run python -I hunts/H-0014/predictions/dr4_search_grade.py` from the repo root.
- It prints each forecast's statistic, hit or miss, and the Brier score of the per-item probabilities.
- It writes them to `<run>/forecast_grade/` (`summary.json`, `f1_f2.csv`, `f3.csv`, `f4.csv`, `f5.csv`), never into this
  directory.

**The first complete run is the grade, forecast by forecast.** A run is complete for a forecast when:
- **F1, F2:** the catalogue stage succeeded and at least 60 of the 67 have a DR4 identity.
- **F4:** the catalogue stage succeeded and the time check passes.
- **F3, F5:** every sample source appears in `epoch_status.csv`, none has status `error` or `missing (archive says it has epoch
  photometry)`, and every source with status `ok` has a cached light curve and (F3) a metrics row.

Until then the forecast is "not yet resolvable", and the pipeline stage is rerun. A source is untestable only for the reasons
listed under each forecast; a failed or partial request is never one. The first run that is complete for a forecast grades
it. A later run counts only if it applies the section 6 changes, and it is published with them.

| case | what happens |
|---|---|
| DR4 is released as planned | F1, F2 and F4 resolve by **2027-01-31**; F3 and F5 by **2027-03-31** (DataLink light curves for about 3,300 sources may be slow) |
| DR4 slips | each resolve-by date becomes the actual release date + 60 days (F1, F2, F4) or + 120 days (F3, F5). The forecasts stand as written |
| no catalogue table (section 1) | F1, F2, F4 **unresolvable** |
| the catalogue stage fails, fewer than 60 identities, or F4's time check fails | "not yet resolvable". If still so 60 days after the resolve-by date: **unresolvable** (recorded as such, not as a miss) |
| an incomplete epochs run for F3 or F5 | "not yet resolvable", the same 60-day rule |
| the catalogue has a different size from the announced 1,360 | no change: the forecasts are about the catalogue DR4 actually publishes |
| catalogue rows without a position (sources outside `gaia_source`) | matched by id only. The grader reports how many. Section 6 item 3 allows fetching positions from `all_source_astrometry` |
| several DR4 sources map to one of ours, or one DR4 source to several of ours | the id map's nearest-match rule decides; the positional rule can add a match, never remove one |
| F3: fewer than 15 testable | **void** |
| F5: fewer than 150 paired events | **void** |
| F2: none or all identified members catalogued | not graded |
| DR4 publishes epoch photometry under new column names | handled by `gaia_epoch.to_series` (section 6 item 2), as for the ensemble |

Where this text and the grader differ, the grader governs.

## 5. Self-test on Gaia DR3 (the stand-in)

`uv run python -I hunts/H-0014/predictions/dr4_search_grade.py --self-test` grades the DR3 dry run (`~/oddsky-runs/h0014/dr3`),
treating DR3 as if it were DR4. It writes only to `<run>/forecast_grade_selftest/`. Result on 2026-11-02, after the revision:
**PASS**.

| check | expected | got |
|---|---|---|
| F1 on DR3 (the 67 are classifier-only by definition) | 0 of 67 (with 67 identities) | 0 (67) |
| F2 on DR3 | not graded (nothing catalogued) | not graded |
| F4 on DR3 (strong events are unmatched to DR3's catalogue by definition) | 0 of 61; time check passes | 0; median peak MJD 57473 |
| id matcher: classifier MICROLENSING sources in DR3's catalogue (an independent number, from H-0010) | 187 of 254 | 187 |
| position + time matcher: H-0008/H-0009 known-lens NEOWISE events in DR3's span that DR3 catalogued | 25 of 40 (a regression value taken from this matcher's first run; the referee confirmed all 25 by hand) | 25 |
| the same with the NEOWISE time moved by +400 d | ≤ 1 | 0 |
| F3 rule on the 21 (the "new" interval taken as after MJD 57382, the middle of DR3's span; self-test only) | all reproduced | 21 of 21, 0 repeats |
| F3 rule on the 30 catalogued lenses and cases (lenses do not repeat) | all reproduced, 0 repeats | 30 of 30, 0 repeats |
| F5 machinery on OS-0026, OS-0027, OS-0029 at their NEOWISE times | pass at t, no control pass | 3 of 3; control rate 0 |

The F5 sample itself cannot be tested on DR3: by construction, DR3 published none of its light curves.

Offline unit tests: `tests/test_dr4_search_grade.py` (28 tests, synthetic catalogues and light curves). They include one test
for each defect the referee found:
- an analysis error or empty label counted as "not reproduced";
- the identity floor;
- incomplete epoch runs;
- the peak-time zero point and the time check;
- the 365-day window cap;
- sign flips per star;
- the F2 threshold.

## 6. What may change after DR4 (and nothing else)

The grade uses these files as they are at the sealing commit:
- `dr4_search_grade.py`, `dr4_search_sample.csv` and `work/forecast.json`;
- `src/oddsky/dr4day/` and `src/oddsky/data/gaia_epoch.py`;
- **`hunts/H-0009/predictions/dr4_ensemble_grade.py`** (F5 imports its `grade_series`; the pipeline uses it too).

Only these changes are allowed:

1. **Retrieval and names.**
   - The release settings of `src/oddsky/dr4day/config.py` (`--set`: table names, the classifier label, the neighbourhood table
     and its columns).
   - Retrieval-only changes to `archive.py`, `probe.py` or `readiness.py`.
   - Writing the section 1 union of microlensing tables to `lens_catalogue.csv`.
   - Names appended to the grader's `COLUMNS` look-up lists. No threshold may change.
2. **Epoch-photometry columns:** the `COLUMN_MAPS` of `gaia_epoch.to_series`, exactly as `dr4_ensemble.md` §2.5 items 2-3 allow.
3. **Positions** of catalogue rows may be taken from `all_source_astrometry` (or any DR4 table) when `gaia_source` lacks them.
4. **The peak-time zero point.** If DR4 states one that `to_mjd` does not read correctly, the conversion is changed to DR4's
   stated one.
5. **The DR3 → DR4 id map**, produced by the pipeline's `idmap` stage with the rule of section 1.

Any other change voids forecasts according to this map:

| change | voids |
|---|---|
| `lightcurves.py` (episodes, baseline, cleaning, labels), or `grade_series` in the ensemble grader | F3, F5 |
| `catalogue.idmap_rule` | F1, F2, F3, F4, F5 |
| the matching code of `catalogue_frame` or of the grader (radii, time window, membership, identity) | F1, F2, F4 |
| any other line of the grader that changes an outcome | the forecasts that line touches |

The grade is published with
`git diff <sealing commit> -- hunts/H-0014/predictions src/oddsky/dr4day src/oddsky/data/gaia_epoch.py hunts/H-0009/predictions/dr4_ensemble_grade.py`
and the versions the grader printed.

## 7. Caveats and correlations

- **The catalogue's selection is the main unknown.** DR4's microlensing paper and selection are not public (the DR4 page lists
  only "Microlensing events", 1,360 rows, "under development"). F1's, F2's and F4's widths are mostly that ignorance, carried by
  one shared parameter that includes a 25% "DR3's cuts repeated" scenario.
- **The forecasts are correlated.** Read them as three questions: catalogue reach (F1, F4), ranking agreement (F2), and Oddsky's
  light-curve claims (F3, F5).
  - F1 and F2 use the same outcomes.
  - F4 shares F1's catalogue (model correlation 0.65).
  - F3 and F1/F2 share the 21 candidates. A candidate that fails F3 is more likely a non-lens and less likely catalogued.
  - F4 and the sealed ensemble share per-event lens probabilities: if the ensemble's lens fraction is too high, both miss.
  - F5 and the ensemble use the same `grade_series`: a DR4 photometry quirk affects both.
  - The named sources are members of F1 or F4.
- **Judgement priors.** The multipliers and priors of section 3 are judgement, anchored on DR3 base rates:
  - 187 of 254 classifier sources catalogued;
  - 0 of 3 strong-event lenses catalogued;
  - 25 of 40 NEOWISE-detected known lenses in DR3's span catalogued. This figure is inflated: the reference list includes DR3's
    catalogue itself.

  The priors were fixed before DR4 and are in the sample row by row.
- **F2 has little power** (section 2.2), and its hit means agreement, not correctness.
- **F3 depends on the pipeline's episode finder**; see the long-wing risk for J072830 and J173332 (section 2.3).
- **Catalogue membership is not truth.** A known lens missing from DR4's catalogue is still a lens. F1 and F4 measure Gaia's
  catalogue, not nature.

**Considered and left out.**
- OS-0015's eclipses in 2015-2019. A strong test, but whether Gaia sampled any 2-week eclipse window needs GOST times first.
- First declines among H-0004's R CrB candidates. They need a sealed list of the candidates already known as R CrB stars.
- The strong events' lens fraction, which the sealed ensemble already tests.

## 8. Files

| file | what |
|---|---|
| `dr4_search_forecast.md` | this document |
| `dr4_search_sample.csv` | every item: F1 (67), F3 (21), F4 (61), F5 (444) rows, with ids, positions, times, priors, multipliers and per-item probabilities |
| `dr4_search_grade.py` | the rules (`GRADED`, `RULES`, `COLUMNS`), the Monte Carlos, the grader (`--self-test`, `--run`, `--release`) |
| `work/forecast.py`, `work/forecast.log`, `work/forecast.json` | builds the sample and the numbers |
| `tests/test_dr4_search_grade.py` | offline tests |
