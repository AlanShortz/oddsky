# Gaia DR4 ensemble forecast: how many strong NEOWISE events does Gaia see brighten?

Author: claude (ensemble design), 2026-10-31. **A pre-registration.** The git commit that adds this file is the seal; nothing
here may change after Gaia DR4 is released (scheduled 2026-12-02) except the adaptations listed in section 2.5. Sealed with
numpy 2.5.4, pandas 2.3.3 and Python 3.12.16 (the grader prints the versions it runs with).

Machine-readable sample: [`dr4_ensemble_sample.csv`](dr4_ensemble_sample.csv), one row per event. Grader:
[`dr4_ensemble_grade.py`](dr4_ensemble_grade.py). Work files: [`work/ensemble/`](work/ensemble/) (e1-e6, run from the repo root
with `uv run python -I`; logs beside each script). Forecast numbers: `work/ensemble/forecast.json`.

## The forecast

| | |
|---|---|
| sample | 50 strong NEOWISE events in the DR4 span that have a Gaia DR3 star within 4″ |
| untestable by design | 3: GOST predicts fewer than 2 Gaia transits within ±30 d (J044653, J170002, J164442) |
| **testable** | **47** |
| **expected PASS count** | **8.9 (median 8; 80% interval 5-14; 90% interval 4-15)** |
| of which lens-like brightenings of the tested star (model) | 5.7 |
| expected resolved (enough DR4 data in the window) | 43.3 of 47 |
| **"~20% of strong events are lens-like brightenings of the matched Gaia star" is falsified if** | the PASS count is in a 5% tail of the forecast's Monte Carlo with f_L held at 0.20, recomputed by the grader for the events that resolve (for orientation, if all 47 resolve: **≤ 5 or ≥ 17**; at the expected resolution of 43: ≤ 5 or ≥ 16). The verdict is **firm** if it also holds at the pre-registered nuisance bounds (**≤ 3 or ≥ 20** if all 47 resolve; ≤ 2 or ≥ 19 at the expected resolution); otherwise it is **conditional on the non-lens priors**. |
| secondary test (achromatic passes) | expected 3.4 (80% 1-6); the same claim is falsified if ≤ 1 or ≥ 8 if all 47 resolve (≤ 0 or ≥ 8 at the expected resolution) |
| colour | of passing events whose colour can be measured, **62% achromatic** (80%: 33-100%). The colour forecast is hit if at least 40% are (probability 0.83). About 38% of passing events will have an undetermined colour |

A PASS means: Gaia saw the fixed star at least 15% brighter (and at least 5 times its own scatter) on at least two transits within
30 days of the NEOWISE event. It does not by itself mean a lens; a lens also passes the colour test (BP and RP rise equally).

## 1. The sample

### 1.1 From 118 strong events to 47 testable ones

The Gaia DR3 sweep (`hunts/H-0009/work/gaia_dr3_sweep.csv`, report `reviews/gaia-dr3-sweep-2026-10-31.md`) lists the 118
deduplicated strong events of H-0008 and H-0009 (≥ 0.4 mag in W1 and W2, achromatic to 0.08 mag, unexplained, frame artifacts
removed).

| step | events | |
|---|---|---|
| strong events | 118 | |
| NEOWISE event visit inside DR4's epoch-photometry span (2014-07-25 to 2020-01-20) | 64 | 54 later events wait for DR5 |
| already confirmed by Gaia DR3 epoch photometry | −3 | J172057 (OS-0026), J180402 (OS-0027), J180839 (OS-0029): not blind; they are the grader's test set (section 5) |
| no Gaia DR3 source within 4″ of the AllWISE position | −11 | nothing to test (list below) |
| **sample** | **50** | the "61 DR4 can test" of the sweep, less these 11 |
| fewer than 2 GOST transits within ±30 d: **untestable by design** | −3 | listed below; never counted, whatever DR4 shows |
| **testable** | **47** | 24 inside the DR3 span (2014.6-2017.4), 23 after it |

**Excluded for having no Gaia DR3 source within 4″** (Gaia cannot measure a star it does not list; DR4 may add faint sources,
but a pre-registration cannot name them): J180730.57-220016.2 (off-target), J131900.24-371433.7, J180559.66-215319.2,
J184700.06-002702.7, J173845.19-321346.1, J172214.29-364055.7 (off-target), J181331.72-171333.9 (all inside the DR3 span);
J175120.35-271621.8 (off-target), J190857.59+080922.1, J182109.55-163557.5, J182333.07-135416.2 (after it).
(`work/ensemble/excluded.csv`.)

**Untestable by design** (Gaia's scanning law, GOST, puts fewer than 2 field-of-view transits within ±30 d of the NEOWISE visit):

| event | Gaia DR3 source_id | transits within ±30 d | nearest transits |
|---|---|---|---|
| J044653.95+425943.5 | 204505284418239872 | 0 | 38.2 d (and G = 8.3, near Gaia's bright limit) |
| J170002.26-421902.3 | 5966258475262316032 | 1 | 19.5 d, 31.5 d |
| J164442.56-464619.2 | 5942679070471273216 | 0 | 33.3 d, 159 d |

### 1.2 Which star is tested

The tested star is the **survey's matched Gaia DR3 star** (`source_id`, the brightest Gaia DR3 source within 3″ of the AllWISE
source, as H-0009 matched it). It is fixed here and is not re-chosen after DR4.

- **Off-target events.** For 7 testable events the H-0009 referee's centroid test says the brightening was not on the matched
  star (`off_target` True). They keep the matched star. The forecast treats them as less likely to pass (section 3.3).
- **Neighbour sources.** For two of the 7, the centroid shift points at a different Gaia DR3 source: J173525 → 4053635935507980800
  (0.35″ from AllWISE) and J180255 → 4145148082128337664 (2.28″). The grader grades those sources too and reports them as
  `alt_status (not counted)`. They never enter the count. (J172057 showed why this matters: its lens was on the neighbour, not on
  the star the survey matched.)
- **No centroid test.** The four H-0008-only events (J175844, J101423, J201542, J163808) never had one.

### 1.3 Overlap with sealed cases

Five events in the sample already have individual sealed DR4 predictions. The ensemble does not replace them. Its rule and its
statement differ from theirs, so the two must not be scored as the same bet. (The `P(pass)` column is defined in 3.4.)

| case | event | sealed statement (P) | ensemble P(pass) |
|---|---|---|---|
| OS-0020 | J163539 | median G in 2017 Jul 15-Oct 16 > 1.2 mag brighter (0.93) | 0.93 |
| OS-0021 | J173150 | brightest night in 2018 Feb 1-Oct 9 > 1.0 mag brighter (0.90) | 0.89 |
| OS-0022 | J124517 | median G in 2018 May 17-Aug 10 > 0.15 mag brighter (0.50) | 0.24 |
| OS-0024 | J131026 | median G in 2015 Jun 12-Oct 5 > 0.2 mag brighter (0.70) | 0.29 |
| OS-0025 | J154239 | median G in 2017 Jul 11-Sep 24 > 0.15 mag brighter (0.45) | 0.28 |

- **These are different bets.** Each sealed case has its own window, statistic and threshold. The ensemble's P(pass) is for
  the ±30 d two-transit rule of section 2, so the two columns are not directly comparable.
- **Why the ensemble's numbers are lower.**
  - The sealed priors (lens 0.30-0.55) came from the ATLAS follow-up record, a lens-selected sample. The ensemble uses the Gaia
    DR3 population calibration (section 3.2).
  - That calibration was computed after the cases were sealed (sweep of 2026-10-31; seals registered 2026-10-31 03:31 UTC).
  - For J131026 the ensemble also applies the missing DR3 VARIABLE flag. It weights the DR3 CCD deficit at ×7, the sealed-case
    referee's calibration (`dr4_referee.md` §3.3). How much an event with that deficit should also be depleted for the missing
    flag is a modelling choice; without the depletion, J131026's P(pass) would be higher.
  - The ensemble does not use J154239's neighbour (OS-0025).
- **What this means for the record.** On present evidence the ensemble model would stake less on J124517 and J154239 (and,
  depending on how the J131026 CCD deficit is weighted, on J131026). That compares two models. It does not correct the sealed
  cases. The sealed stakes stand and are scored as registered. After DR4, each case is scored on its own statement, and the
  ensemble's per-event probabilities are scored on the ensemble rule. Neither is rescored against the other.
- **Not in the sample.**
  - OS-0023 (J160706) is not a strong event: its W1 and W2 brightenings differ by 0.086 mag, just over the 0.08 cut.
  - OS-0028 (J175634) peaked in 2022, after DR4.

### 1.4 The sample

`abs dW1`: the NEOWISE W1 brightening at the event visit (mag). `visits`: the number of NEOWISE visits in the event block.
`centroid`: the H-0009 referee's test (on / off-target / no test). `DR3 span`: event before 2017-05-28; all of these stars were
**not** flagged VARIABLE in DR3. `P(pass)`: this forecast's probability that the event passes (it includes the ~8% chance that
DR4 has too few transits there). Event times are the NEOWISE peak-visit MJD (`t_event_mjd` in the CSV).

| # | event | case | NEOWISE visit (MJD, date) | abs dW1 | visits | tested Gaia DR3 source_id | sep (") | G | BP-RP | centroid | DR3 span | GOST transits within 30 d (nearest, d) | optical info | P(pass) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | J172246.71-403331.7 |  | 56913.392 (2014-09-13) | 0.47 | 1 | 5960257061625105024 | 0.14 | 17.97 | 3.59 | on | yes | 4 (5.6) |  | 0.13 |
| 2 | J172729.10-323917.2 |  | 56913.723 (2014-09-13) | 0.47 | 1 | 4054748744344748544 | 0.11 | 18.89 | 4.11 | on | yes | 4 (4.4) |  | 0.11 |
| 3 | J173525.98-335850.5 |  | 56915.465 (2014-09-15) | 0.76 | 1 | 4053635939839764608 | 1.78 | 20.28 |  | off-target; points at 4053635935507980800 (0.35") | yes | 4 (6.2) |  | 0.04 |
| 4 | J180744.93-222226.3 |  | 56922.078 (2014-09-22) | 0.41 | 1 | 4069725604546345472 | 0.15 | 19.95 | 3.58 | on | yes | 2 (9.5) |  | 0.01 |
| 5 | J211957.84+572625.7 |  | 57012.326 (2014-12-21) | 0.43 | 1 | 2178980910929234944 | 1.09 | 20.45 | 2.36 | on | yes | 2 (12.3) |  | 0.00 |
| 6 | J123522.62-622827.0 |  | 57054.538 (2015-02-01) | 0.92 | 1 | 6053935349230889344 | 0.67 | 12.49 | 2.43 | off-target | yes | 3 (4.3) |  | 0.05 |
| 7 | J181035.29-105156.9 |  | 57105.130 (2015-03-24) | 0.99 | 1 | 4157149599451570944 | 0.27 | 17.10 | 3.15 | on | yes | 5 (2.4) |  | 0.17 |
| 8 | J131026.53-612259.2 | OS-0024 | 57235.815 (2015-08-01) | 1.01 | 1 | 5863586423081438848 | 0.12 | 17.75 | 3.54 | on | yes | 2 (12.2) |  | 0.29 |
| 9 | J130153.27-655628.5 |  | 57238.667 (2015-08-04) | 0.49 | 2 | 5858515677297526656 | 0.27 | 15.55 | 1.28 | on | yes | 3 (15.5) |  | 0.09 |
| 10 | J171723.15-403337.1 |  | 57271.440 (2015-09-06) | 0.41 | 1 | 5971935666113330048 | 0.83 | 18.82 | 3.43 | on | yes | 3 (6.5) |  | 0.09 |
| 11 | J172130.29-372518.3 |  | 57272.097 (2015-09-07) | 0.56 | 3 | 5972880279747996160 | 0.90 | 19.11 | 3.10 | on | yes | 3 (6.4) |  | 0.08 |
| 12 | J173349.59-264330.5 |  | 57273.673 (2015-09-08) | 0.59 | 2 | 4061588260756165632 | 0.30 | 16.22 | 4.18 | on | yes | 4 (5.7) | no ATLAS; no OGLE alert | 0.10 |
| 13 | J175844.62-263022.5 |  | 57279.151 (2015-09-14) | 0.62 | 1 | 4064033505903753728 | 1.67 | 17.24 | 4.88 | no test | yes | 2 (10.0) |  | 0.06 |
| 14 | J192602.96+134138.7 |  | 57305.919 (2015-10-10) | 0.50 | 1 | 4319553612961496192 | 0.59 | 20.60 | 2.56 | on | yes | 2 (4.7) |  | 0.01 |
| 15 | J101423.62-603507.1 |  | 57397.273 (2016-01-10) | 0.78 | 1 | 5254932176492837376 | 0.12 | 14.45 | 1.17 | no test | yes | 2 (4.3) |  | 0.11 |
| 16 | J170153.51-425620.0 |  | 57456.819 (2016-03-09) | 0.85 | 2 | 5966156701720599680 | 0.50 | 15.71 | 1.66 | on | yes | 2 (1.3) | ATLAS flat: IR-only | 0.03 |
| 17 | J182120.84-143232.7 |  | 57471.790 (2016-03-24) | 1.27 | 1 | 4146309720455045504 | 0.14 | 16.29 | 3.78 | on | yes | 4 (10.9) | ATLAS: IR variable (YSO?) | 0.21 |
| 18 | J184017.78-134852.3 |  | 57475.984 (2016-03-28) | 0.48 | 1 | 4103821395764717440 | 0.17 | 16.30 | 2.69 | on | yes | 4 (5.9) |  | 0.09 |
| 19 | J185846.27+033028.5 |  | 57484.894 (2016-04-06) | 1.87 | 1 | 4280846616059642368 | 2.83 | 17.85 | 3.07 | off-target | yes | 4 (6.9) | ATLAS: Gaia star not the variable | 0.03 |
| 20 | J201542.68+382806.1 |  | 57520.109 (2016-05-12) | 0.57 | 1 | 2060942088532024704 | 0.29 | 16.55 | 2.31 | no test | yes | 2 (15.7) |  | 0.05 |
| 21 | J033351.36+561412.5 |  | 57630.015 (2016-08-30) | 0.77 | 1 | 448377646353031040 | 0.08 | 18.83 | 2.66 | on | yes | 4 (5.3) |  | 0.13 |
| 22 | J044653.95+425943.5 |  | 57639.386 (2016-09-08) | 0.46 | 3 | 204505284418239872 | 0.12 | 8.34 | 0.32 | on | yes | 0 (38.2) |  | untestable by design |
| 23 | J075928.63-221055.1 |  | 57692.982 (2016-10-31) | 1.01 | 1 | 5711343503294249856 | 0.08 | 16.98 | 1.19 | on | yes | 2 (12.8) | ATLAS unusable | 0.08 |
| 24 | J164900.93-433618.0 |  | 57819.059 (2017-03-07) | 0.47 | 1 | 5967450719527687168 | 2.02 | 16.23 | 1.83 | off-target | yes | 3 (12.0) |  | 0.05 |
| 25 | J180255.46-160745.2 |  | 57834.836 (2017-03-22) | 0.73 | 1 | 4145148086414772864 | 1.32 | 16.72 | 2.76 | off-target; points at 4145148082128337664 (2.28") | yes | 3 (6.3) |  | 0.04 |
| 26 | J154239.48-572601.4 | OS-0025 | 57977.922 (2017-08-12) | 0.91 | 1 | 5882495205642608896 | 0.24 | 17.24 | 3.23 | on | no | 4 (4.5) |  | 0.28 |
| 27 | J163539.69-355208.3 | OS-0020 | 57982.411 (2017-08-17) | 2.26 | 1 | 6020322385418675200 | 0.77 | 18.31 | 2.13 | on | no | 4 (2.9) | ATLAS: achromatic x6-9 | 0.93 |
| 28 | J170655.82-373839.7 |  | 57988.466 (2017-08-23) | 0.44 | 1 | 5976421806697577600 | 0.17 | 16.89 | 3.76 | on | no | 5 (4.8) |  | 0.26 |
| 29 | J040025.77+323527.4 |  | 57993.083 (2017-08-28) | 1.09 | 1 | 170329679884731008 | 0.04 | 14.01 | 1.56 | on | no | 3 (5.8) |  | 0.27 |
| 30 | J013600.31+612130.4 |  | 58137.210 (2018-01-19) | 0.48 | 2 | 510002700418972416 | 0.02 | 12.77 | 0.62 | on | no | 3 (17.4) |  | 0.22 |
| 31 | J161946.51-492721.6 |  | 58179.096 (2018-03-02) | 2.26 | 2 | 5935607763281500800 | 1.17 | 20.61 | 2.54 | off-target | no | 4 (0.5) |  | 0.13 |
| 32 | J163808.41-414832.7 |  | 58180.862 (2018-03-03) | 0.75 | 1 | 5968618405199767296 | 0.10 | 17.32 | 3.17 | no test | no | 5 (2.9) |  | 0.26 |
| 33 | J170002.26-421902.3 |  | 58187.374 (2018-03-10) | 0.41 | 1 | 5966258475262316032 | 0.11 | 16.51 | 5.34 | on | no | 1 (19.5) |  | untestable by design |
| 34 | J071033.70-021828.0 |  | 58194.795 (2018-03-17) | 0.42 | 2 | 3108434511210306048 | 0.33 | 11.64 | 0.04 | on | no | 2 (9.4) |  | 0.18 |
| 35 | J075219.97-325515.6 |  | 58216.648 (2018-04-08) | 1.89 | 1 | 5594032591941367424 | 0.05 | 19.38 | 3.11 | on | no | 4 (12.8) | ATLAS: real month-long rise | 0.68 |
| 36 | J124517.35-630125.0 | OS-0022 | 58313.432 (2018-07-14) | 2.10 | 1 | 5862971688685406976 | 0.47 | 17.76 | 3.22 | on | no | 3 (12.8) |  | 0.24 |
| 37 | J131433.70-604212.0 |  | 58315.461 (2018-07-16) | 0.41 | 3 | 5869622806317427072 | 0.30 | 17.77 | 5.09 | on | no | 4 (11.9) |  | 0.23 |
| 38 | J173150.73-444549.3 | OS-0021 | 58357.181 (2018-08-27) | 1.21 | 2 | 5952322268527918208 | 0.27 | 15.07 | 1.85 | on | no | 3 (5.0) | ATLAS: x7.7, months | 0.89 |
| 39 | J175905.00-174624.2 |  | 58362.061 (2018-09-01) | 0.62 | 1 | 4143806609213044608 | 0.43 | 15.37 | 2.49 | on | no | 4 (3.9) |  | 0.27 |
| 40 | J180010.34-243417.6 |  | 58362.289 (2018-09-01) | 0.86 | 1 | 4069002813088944128 | 2.32 | 17.68 | 2.59 | off-target | no | 4 (2.3) |  | 0.16 |
| 41 | J185035.91-014014.4 |  | 58374.694 (2018-09-13) | 1.33 | 2 | 4259246224801979776 | 0.14 | 18.98 | 2.48 | on | no | 5 (8.0) | ATLAS flat: IR-only | 0.06 |
| 42 | J222915.37+560017.4 |  | 58465.723 (2018-12-13) | 0.55 | 1 | 2006722799327487744 | 0.39 | 17.33 | 1.47 | on | no | 2 (8.5) |  | 0.15 |
| 43 | J051237.90-060835.8 |  | 58526.689 (2019-02-12) | 0.48 | 1 | 3208562675757595904 | 0.09 | 18.90 | 3.56 | on | no | 4 (5.1) |  | 0.25 |
| 44 | J161048.56-514754.1 |  | 58545.149 (2019-03-03) | 0.61 | 2 | 5933460593167064192 | 0.40 | 19.48 | 2.19 | on | no | 4 (14.2) |  | 0.22 |
| 45 | J164442.56-464619.2 |  | 58549.826 (2019-03-07) | 0.64 | 1 | 5942679070471273216 | 2.68 | 16.85 | 1.34 | on | no | 0 (33.3) |  | untestable by design |
| 46 | J170958.77-413848.6 |  | 58553.587 (2019-03-11) | 0.98 | 1 | 5965817983469250048 | 0.37 | 20.34 | 3.48 | on | no | 5 (2.8) |  | 0.23 |
| 47 | J172247.87-324616.4 |  | 58555.254 (2019-03-13) | 0.57 | 1 | 5979317993343609600 | 0.12 | 17.97 | 5.12 | on | no | 3 (0.6) |  | 0.21 |
| 48 | J172244.98-363407.6 |  | 58555.647 (2019-03-13) | 0.43 | 2 | 5975194889158606464 | 0.32 | 16.91 | 4.43 | on | no | 5 (0.4) |  | 0.24 |
| 49 | J081611.24-335034.8 |  | 58591.289 (2019-04-18) | 0.40 | 1 | 5546617183791572736 | 0.06 | 15.49 | 0.90 | on | no | 4 (13.8) |  | 0.24 |
| 50 | J174350.48-375311.7 |  | 58723.368 (2019-08-28) | 0.47 | 1 | 5961558745953829504 | 0.47 | 15.68 | 2.17 | on | no | 3 (5.5) |  | 0.24 |

## 2. The per-event test (the rule)

`RULE` and `judge` / `colour` in `dr4_ensemble_grade.py` are the machine form of this section; where the text and the code
differ, the code governs.

### 2.1 Data

- **Photometry.** Gaia DR4 per-transit epoch photometry (G, BP, RP) of the tested source, fetched with
  `oddsky.data.gaia_epoch.fetch_report(ids, releases=("Gaia DR4",))`. That module requests `VALID_DATA=false`, so flagged
  transits come back and are dropped explicitly.
- **Which transits count.**
  - Transits flagged `rejected_by_photometry` and non-finite magnitudes or times are dropped.
  - Transits flagged only as variability outliers are **kept**: during an event they are the event.
  - **A transit** is one field-of-view crossing: one `transit_id` in the DR4 per-transit table (GOST counts the same thing). If a
    `transit_id` appears more than once in a band, it counts once, with the median of its magnitudes. Window and baseline counts,
    and the "at least 2 above threshold", are counts of distinct transits.
- **Time.** Gaia transit time (BJD_TCB − 2400000.5) against the NEOWISE visit's MJD. The difference (minutes) is irrelevant at
  these windows.

### 2.2 G test

For an event with NEOWISE peak-visit time t:

1. **Baseline.** The transits with |t_transit − t| > 150 d. At least 10 are needed, else the event is "untestable (data)".
2. **Flux ratio** per transit: r = 10^(−0.4 (G − median baseline G)).
3. **Scatter.** s = 1.4826 × median absolute deviation of the baseline ratios.
4. **Threshold.** T = 1 + max(0.15, 5 s).
5. **Window.** The transits with |t_transit − t| ≤ 30 d. At least 2 are needed, else the event is "untestable (data)".
   Transits between 30 and 150 d from t are used for neither the window nor the baseline.
6. **Verdict.** **PASS** if at least 2 window transits have r ≥ T; otherwise **FAIL**.

Why this form:

- **Two transits above threshold, not one.** A single outlier transit cannot make a pass. The two fields of view usually give a
  pair of transits 106 minutes apart, so a real event lasting days is seen twice.
- **±30 d.** It makes 47 events testable, against 36 at ±20 d (`e1_sample.log`). The three DR3-confirmed events were seen at
  −7, −9 and −16 d, with later transits at +15 to +25 d still bright.
- **The 15% floor and 5 s.** Together they keep a flat star's chance of passing at about 1% (section 3.2).
- **A fixed floor, not one scaled to the W1 amplitude.** Gaia's window and WISE's 6″ beam blend differently, so the G amplitude
  of a real event can be larger or smaller than W1's. The colour test (2.3), not the amplitude, is what separates lenses.

### 2.3 Colour test (PASS events only)

1. **Pairs.** At each passing transit that has both a valid BP and a valid RP measurement (matched by transit id), take
   ΔBP − ΔRP. Each band is measured against its own baseline median: same 150 d rule, at least 5 transits.
2. **Per-band error.** The larger of the formal error and the baseline's robust scatter (in mag) divided by that band's flux
   ratio at the transit, combined in quadrature with scatter / √(n baseline).
3. **Mean.** D is the inverse-variance mean over the pairs, with error e_D.
4. **Verdict.**
   - **undetermined** if there are fewer than 5 BP or fewer than 5 RP baseline transits, if the BP baseline median is fainter
     than 20.5, if no passing transit has both BP and RP, or if e_D > 0.05;
   - **achromatic** if |D| ≤ 0.10;
   - **chromatic** otherwise.

### 2.4 The ensemble statistic

- **Primary.** The number of PASS events among the 47 testable-by-design events.
- **Secondary.** The number of PASS events whose colour is achromatic.
- **What does not count.** Untestable-by-design events never count. "Untestable (data)" events (too few DR4 transits, or no DR4
  epoch photometry for the source) count as neither pass nor fail. The falsification thresholds are then recomputed for the events
  that did resolve (2.6).

### 2.5 What may change after DR4 (and nothing else)

The grade uses `dr4_ensemble_grade.py`, `src/oddsky/data/gaia_epoch.py` and `src/oddsky/data/series.py` **as they are at the
commit that seals this file**, with only these changes allowed:

1. **Retrieval.** The release label passed to `--release`, the endpoint and the request parameters of
   `gaia_epoch._fetch_release`, or reading DR4's bulk files instead, provided the per-transit values are DR4's as published.
   (Today the DR4 label is rejected with HTTP 500, and the grader prints "fetch failed" and stops.)
2. **Column mapping** in `gaia_epoch.to_series`: the names of the time, magnitude (or flux), error, transit-id and flag
   columns.
   - Time is converted to BJD(TCB) − 2400000.5 with whatever zero-point DR4 states.
   - If DR4 gives only flux, G = −2.5 log10(flux) + DR4's published zero point.
   - "rejected_by_photometry" means DR4's transit-level photometric rejection flag. All other DR4 flags are ignored.
3. **Per-CCD data.** If DR4 publishes only per-CCD G, the transit's G is −2.5 log10 of the median of its valid (unflagged,
   finite) per-CCD fluxes, with DR4's zero point. A transit with no valid CCD is dropped.
4. **The DR3 → DR4 source-id map** `work/ensemble/dr4_idmap.csv` (`dr3_source_id,dr4_source_id`), built from DR4's
   DR3-neighbourhood table.
   - It takes the **nearest** DR4 source within 0.5″ whose G differs by at most 0.3 mag.
   - With no such source, the DR3 id is used as is.

The grade is published together with `git diff <seal commit> -- src/oddsky/data/gaia_epoch.py src/oddsky/data/series.py
hunts/H-0009/predictions/dr4_ensemble_grade.py`. Any change outside items 1-4 voids the grade.

The grader prints the numpy, pandas and Python versions it runs with. The forecast was sealed with numpy 2.5.4, pandas 2.3.3 and
Python 3.12.16. `pyproject.toml` allows numpy ≥ 1.26 and NumPy does not promise identical random streams across versions, so a
re-run under other versions can move the Monte Carlo thresholds by sampling noise.

### 2.6 The verdicts the grader prints

Run `uv run python -I hunts/H-0009/predictions/dr4_ensemble_grade.py`. It prints and saves (`work/ensemble/grade_dr4.csv`,
`grade_dr4_summary.json`):

- **Per event:** PASS / FAIL / untestable (data), with the ratio and colour numbers.
- **The PASS count.** The forecast interval is hit if 5 ≤ count ≤ 14 (inclusive), however many events resolve; it is not
  recomputed.
- **"~20% of strong events are lens-like brightenings of the survey-matched Gaia star".**
  - The lens fraction is held at 0.20 and the Monte Carlo of section 3 is rerun for the events that resolved, as if all of them
    resolved.
  - The claim is **falsified** if P(count ≤ observed) < 0.05 ("too few") or P(count ≥ observed) < 0.05 ("too many").
  - The verdict is **firm** if the same tail also holds at the pre-registered nuisance bounds (section 3.5). Otherwise it is
    **conditional on the non-lens priors**.
  - The same test (without the tier) is applied to the achromatic-pass count.
- **The colour forecast** is hit if at least 40% (inclusive) of the passes with a determined colour are achromatic. With no
  determined colour it is not graded.
- **The lens fraction DR4 implies:** flat prior on 0-0.8, from the same Monte Carlo.

## 3. The ensemble forecast

### 3.1 Scenarios

What can the tested Gaia star be doing at the NEOWISE time?

| scenario | what Gaia sees | model (e3) |
|---|---|---|
| **L**: lens, or lens-like, on the tested star | a smooth achromatic brightening | point lens with t0 between the bracketing quiet NEOWISE visits, tE log-uniform 20-200 d (20-400 d for multi-visit blocks), u0 0-1.2, W1 source fraction 0.1-1. Draws are weighted by the NEOWISE visits (event visits = their dW1 ± 0.05; the two bracketing quiet visits and one more on each side = 0 ± 0.07). Gaia resolves part of the WISE blend: fs_G = fs_W1 + (1 − fs_W1)·U(0,1). BP and RP blend fractions scatter around fs_G by (1 − fs_G)·N(0, 0.15) |
| **R**: real non-lens brightening of the tested star | slow, usually bluer when brighter | same time profiles as L. G excess = q × W1 excess, q log-uniform 0.1-1.5. ΔBP − ΔRP = κ ΔG, κ 0.3-1.0 |
| **F**: short outburst on the tested star (dwarf-nova-like) | days | decay e-fold τ log-uniform 1-20 d, rise τ/3, the visit 0-3τ after the peak. ΔG = g × ΔW1, g 0.5-2.5; κ 0.5-1.5. Not allowed for multi-visit blocks |
| **N**: nothing on the tested star | flat | IR-only event, event on a neighbour, or a NEOWISE artifact that survived the exposure-level cut |

**Observation model.** For each event, scenario and realisation (1,200 realisations; 3,000 for N), DR4 photometry is simulated at
the event's GOST transits (fetched 2026-10-31 for the DR3 sweep, `work/ensemble/gost_sample.csv`) and graded by the grader's own
`judge` and `colour`.

- **Transit losses.**
  - 10% of transits are lost (DR3 delivered 86-100% of GOST's transits for the three confirmed sources).
  - 2% of sources have no DR4 epoch photometry at all.
  - In 3% of realisations DR4 rejects every transit more than 0.5 mag above the median (the earlier proposal's pessimistic
    branch).
- **Noise.**
  - G per-transit noise is the DR3 floor ×1.5. It predicts 0.035, 0.019 and 0.008 mag for the three DR3-confirmed sources'
    baselines; DR3 measured 0.028, 0.019 and 0.007.
  - BP and RP noise are calibrated on the same three sources.
  - Intrinsic stellar jitter: log-uniform 0.003-0.05 mag.
- **Outliers.**
  - 2% of transits: ±0.2-1.0 mag.
  - 1% of epochs: a brightward offset of 0.15-0.6 mag on both fields of view (a neighbour drifting into the window).

**Mean pass probability over the 47 events, given resolved:**

| scenario | mean P(pass) |
|---|---|
| L | 0.93 |
| R | 0.62 |
| F | 0.47 |
| N | 0.009 (an earlier estimate was ~2%; this model gives ~1%) |

- **Lenses rarely fail.** Every testable event has transits within ±30 d, and a lens bright enough for NEOWISE stays magnified for
  weeks. Lenses fail mainly on the faintest stars (G ≈ 20-20.6) with only two transits (J180744, J211957, J192602: P(pass | L)
  0.14-0.35).
- **Missing data.** Events with only two predicted transits (11 of 47) have a 21% chance that DR4 lacks one of them.

### 3.2 Calibrating the scenario fractions

| evidence | sample | lens-like (achromatic) optical brightening on a Gaia star | non-lens optical brightening | no optical brightening on the tested star | unconstrained |
|---|---|---|---|---|---|
| Gaia DR3 sweep: VARIABLE flags of in-span events with a Gaia source (complete, not selected) | 28 (27 with ≥ 2 transits within ±30 d) | 3 flagged, all achromatic: 2 on the matched star (J180402, J180839), 1 on a neighbour (J172057) | 0 flagged and chromatic | 25 unflagged | – |
| H-0009 ATLAS referee (10 events chosen as the most promising) | 10 | 3 (J174401; J180402; J172057, on the neighbouring Gaia star) | 1 (J064439, chromatic); also 1 optical *dimming* (J025145, a young star) | 4 (J170153 and J185035 IR-only; J184240 and J182621 on a neighbour) | 1 (J173349) |
| H-0008 ATLAS referees (the 10 strongest lens-like southern events, two of them Gaia alerts) | 10 | 6 (J163539, J173150, J174440, J191120, J175634, J174744) | 1 (J075219, real, unclassified) | 2 (J185846: the matched star is not the variable; J182120: IR variable) | 1 (J075928) |
| follow-ups combined | 18 constrained | 9 (50%) | 2 (11%), plus 1 dimming | 6 (33%) | |

How these fix the fractions:

- **Lens fraction f_L.**
  - The follow-ups were chosen for looking like lenses, and two were Gaia alerts, so their 50% is an upper bound for the
    population.
  - **The only complete sample is the DR3 sweep.** Among in-span strong events with ≥ 2 Gaia transits within ±30 d, 2 of 27
    have their **matched** Gaia star flagged VARIABLE (J180402, J180839).
    - The third Gaia-confirmed event, J172057, was a lens on a neighbour 2.8″ from the matched star, which this test would grade
      as "not counted".
    - Among known lenses with ≥ 2 transits, 14 of 20 have the matched star flagged.
    - That gives f_L ≈ 0.14 (80% 0.06-0.27; 95% 0.03-0.37) for **a lens-like brightening of the matched star**, the quantity DR4
      tests here (`draw_fL`, flat priors).
    - The sweep's "≈ 0.2" counts any Gaia source within 4″ and is about 1.4× larger. Holding f_L at 0.20 in the falsification
      test (3.5) is a test value inside the matched-star interval, not the sweep's estimate.
  - **A non-lens achromatic event** such as J174401 counts as L here, both in the calibration and in DR4. The claim DR4 tests is
    therefore "**~20% of strong events are lens-like brightenings of the survey-matched Gaia star**".
- **Non-lens optical brightening f_R ~ Beta(1.5, 18.5)** (mean 0.075, 95% 0.005-0.21).
  - The follow-ups give 2 non-lens optical brightenings per 9 lens-like ones.
  - DR3 flagged no chromatic variable among 28 in-span events. That caps f_R at about 0.25 for a flag efficiency near 0.4.
- **Short outbursts f_F ~ Beta(1, 19)** (mean 0.05, 95% 0.001-0.17). There is no clear case in 20 follow-ups; J182621 (a
  one-day rise on a neighbour) might be one. Catalogued dwarf novae were already removed by the funnel.
- **N** is the rest, about 0.72 on average. The follow-ups' 39% (no brightening plus dimming) comes from a lens-biased sample.
- **Shared fractions.** All four fractions are drawn once per Monte Carlo realisation and shared by all events. That correlation
  is most of the forecast's width.

### 3.3 Per-event evidence (fixed now)

- **Centroid test (H-0009 referee).**
  - The on-star scenarios L, R and F are multiplied by 0.48 for off-target events and by 1.16 for on-target ones. The four
    H-0008-only events, which have no test, get 1.
  - Derivation: P(off | event on the star) ≤ 13/117 (known lenses) and P(off) = 22/112 for strong events once the frame
    artifacts (9 of which were off-target) are removed. With about 30% of strong events on the star, P(off | not on the star) =
    0.233, so the likelihood ratios are 0.111/0.233 = 0.48 (off-target) and 0.889/0.767 = 1.16 (on-target).
- **Missing DR3 VARIABLE flag (the 24 in-span events).**
  - Each on-star scenario is multiplied by (1 − its DR3 flag efficiency). The efficiencies are:
    - L: P(VARIABLE matched star | known lens with ≥ 2 transits), the same draw that sets f_L, ~0.7;
    - R: 0.2-0.6;
    - F: 0.05-0.3.
  - The DR4 pass probability of an unflagged event is then lowered to ρ·max(0, (q − e)/(1 − e)) + (1 − ρ)·q, with ρ ~ U(0.5, 1).
    ρ = 1 means DR3 flagged exactly those events that DR4 would pass. A lens DR3 missed is more likely to be one whose transits
    caught little of it.
  - This is the largest single effect in the forecast (section 3.6).
- **Optical follow-up (fixed weights L / R / F / N replace the population fractions).**

  | event | L | R | F | N | basis |
  |---|---|---|---|---|---|
  | J163539 | 0.80 | 0.17 | 0 | 0.03 | ATLAS achromatic ×6-9 at the NEOWISE time |
  | J173150 | 0.60 | 0.35 | 0 | 0.05 | ATLAS ×7.7 for months; rise mildly chromatic |
  | J075219 | 0.35 | 0.35 | 0.15 | 0.15 | ATLAS real month-long brightening, unclassified |
  | J185846 | 0 | 0.03 | 0 | 0.97 | the matched star is not the variable |
  | J182120 | 0.03 | 0.30 | 0.02 | 0.65 | IR variable / young-star candidate; ATLAS 2016 unusable |
  | J170153 | 0.02 | 0.05 | 0 | 0.93 | ATLAS flat at +9 and +21 d where a lens needs ×2 |
  | J185035 | 0.01 | 0.04 | 0 | 0.95 | IR-only; the IR source is too red for the Gaia star |

- **Other event-specific evidence.**
  - J131026 (OS-0024): DR3 CCD-level scatter at the 95th percentile of its field, about 9 missing transits. L and R ×7, the
    likelihood ratio the sealed-case referee calibrated for that deficit on 47 DR3 lenses (`dr4_referee.md` §3.3).
  - J173349: OGLE observed its field in 2015 without an alert. L ×0.5.
- **The blind core.** The 39 testable events with no optical information at all (all but the 7 above and J173349; J075928's ATLAS
  data were unusable, so it stays).

### 3.4 Results (`e4_ensemble.log`)

| subsample | events | expected PASS | median | 80% | 90% | achromatic passes (80%) |
|---|---|---|---|---|---|---|
| **all testable** | **47** | **8.9** | **8** | **5-14** | **4-15** | **3.4 (1-6)** |
| blind core | 39 | 6.0 | 6 | 2-10 | 1-12 | 2.2 (0-5) |
| inside the DR3 span (unflagged) | 24 | 2.1 | 2 | 0-4 | 0-5 | 0.6 (0-2) |
| after the DR3 span | 23 | 6.8 | 7 | 4-10 | 3-11 | 2.8 (1-5) |
| with optical follow-up | 8 | 2.9 | 3 | 2-4 | 2-4 | 1.3 (0-2) |

- **Per event.** `P(pass)` in the table and `p_pass_forecast` in the CSV; `p_lens_onstar` is the model's probability of a lens on
  the tested star.
- **Where the expected passes come from.** About 5.7 of the 8.9 are lens-like brightenings of the tested star. The rest are mostly the two ATLAS-confirmed events'
  non-lens share, R events and noise.
- **The split by DR3 span is the forecast's sharpest feature.** Events after the DR3 span should pass about 3.5 times as often
  per event as events inside it (0.30 against 0.09), because DR3 already looked at the in-span stars and flagged none of them.
  In the blind core alone the ratio is about 2.6 (0.23 against 0.09); the follow-up events inflate the overall figure.

### 3.5 What the count says about the lens fraction

The whole forecast is rerun with f_L held fixed. R, F, the flag efficiencies and ρ are still drawn.

| f_L | expected PASS | 80% | 90% | expected achromatic passes |
|---|---|---|---|---|
| 0 | 4.9 | 3-7 | 2-8 | 1.3 |
| 0.05 | 6.2 | 4-9 | 3-10 | 2.0 |
| 0.10 | 7.4 | 5-11 | 4-12 | 2.6 |
| **0.20** | **10.0** | **7-13** | **6-15** | **4.0** |
| 0.30 | 12.5 | 9-16 | 8-18 | 5.3 |
| 0.40 | 15.2 | 11-19 | 10-21 | 6.7 |
| 0.50 | 18.1 | 14-22 | 13-24 | 8.2 |

Lens fraction implied by a pass count (all 47 resolved; flat prior; median and 90% interval):

| pass count | implied f_L |
|---|---|
| 3 | 0.01 (0-0.10) |
| 5 | 0.04 (0-0.16) |
| 7 | 0.09 (0-0.24) |
| 10 | 0.18 (0.04-0.36) |
| 13 | 0.29 (0.12-0.46) |
| 16 | 0.39 (0.20-0.56) |
| 20 | 0.51 (0.33-0.67) |

**Falsification of "~20% of strong events are lens-like brightenings of the survey-matched Gaia star".**

- **The criterion.** The count is compared with the Monte Carlo at f_L = 0.20, rerun by the grader for the events that resolve.
  - A count in a 5% tail falsifies the claim: P(count ≤ observed) < 0.05 or P(count ≥ observed) < 0.05.
  - For orientation: **≤ 5 or ≥ 17** if all 47 resolve. At the expected resolution (43 events) it is ≤ 5 or ≥ 16, with tail
    probabilities 0.039 and 0.031.
- **Firm or conditional.** The non-lens part of the count is set by judgement priors (f_R, f_F, the pass probabilities, the
  flat-star rate). So the grader repeats the tail test at two **pre-registered nuisance bounds** (`nuisance_bounds` in the
  grader):
  - *low side*, fewest non-lens passes: f_R = f_F = 0 and on-star pass probabilities ×0.85;
  - *high side*, most non-lens passes: f_R mean 0.15, f_F mean 0.10, flat-star pass rate ≥ 3%.

  A falsification that also holds at the bound on its side is **firm**: **≤ 3 or ≥ 20** if all 47 resolve (≤ 2 or ≥ 19 at the
  expected resolution). Otherwise it is **conditional on the non-lens priors**.
- **The secondary test.** For achromatic passes the thresholds are ≤ 1 and ≥ 8 if all 47 resolve (≤ 0 and ≥ 8 at the expected
  resolution). They barely move with f_R and f_F, because R and F events rarely read achromatic, but the test has less power.
- **What it can and cannot tell.**
  - Under the stated priors, a true f_L of 0 would put the count in the "too few" region about three times in five (0.61), and
    f_L = 0.4 would put it in the "too many" region about half the time (0.46).
  - For a firm verdict those chances fall to about one in five (0.19) and one in six (0.16). A firm verdict needs an extreme count.
  - A conditional verdict means "20% is inconsistent with the count, given our judgement of how often non-lens brightenings
    occur".
  - The count cannot tell 0.15 from 0.25.
  - The two tails are tested separately at 5% each. The combined false-alarm rate at f_L = 0.20 is about 5% (0.049 if all 47
    resolve), because the count is discrete.

### 3.6 Sensitivity (all 47)

| change | expected PASS | 80% | 90% |
|---|---|---|---|
| as forecast | 8.9 | 5-14 | 4-15 |
| no DR3 non-flag conditioning (ignore that DR3 flagged none of the in-span stars) | 11.1 | 6-17 | 5-19 |
| no centroid evidence | 8.8 | 5-13 | 4-15 |
| ρ ~ U(0, 1) (DR3 flag and DR4 pass less correlated) | 9.0 | 5-14 | 4-16 |
| f_R mean 0.15, f_F mean 0.10 | 10.8 | 6-16 | 5-18 |
| f_R = f_F = 0 | 7.1 | 4-11 | 3-13 |
| on-star pass probabilities ×0.85 (DR4 worse than modelled) | 7.3 | 4-11 | 3-13 |

The forecast is most sensitive to how much non-lens optical variability there is (f_R, f_F) and to the DR3 non-flag
conditioning. Those are also what make "too many passes" hard to interpret: a high count could mean more lenses or more non-lens
brightenings. The colour test is what separates the two (section 4).

## 4. Colour forecast

| | expected |
|---|---|
| passing events whose colour is determined (BP baseline ≤ 20.5 and e_D ≤ 0.05) | about 62% of passes |
| **achromatic among those (BP and RP rise equally, within 0.10 mag)** | **62% (80%: 33-100%)** |
| achromatic / chromatic / undetermined passes | 3.4 / 2.1 / 3.4 |
| **hit condition** | at least 40% (inclusive) of the passes with a determined colour are achromatic; probability 0.83. With no determined colour it is not graded |

- **By scenario.** Given a determined colour, a lens reads achromatic about 90% of the time; the misses are blends of another
  colour inside Gaia's BP/RP windows. R and F events read achromatic 5-15% of the time, mostly the smallest ones, where
  κ·|ΔG| < 0.1. Noise passes on stars with a measurable BP read achromatic about half the time (a flat star has no colour
  change).
- **Against f_L.** The achromatic fraction rises from 46% at f_L = 0 to 76% at f_L = 0.5. On its own it is a weak test of f_L.
  Its job is to say whether the passes are lens-like. The achromatic-pass *count* (3.5) is the more prior-robust lens statistic.
- **The two ways to read the result.**
  - Fewer than 40% achromatic among determined passes: most of what Gaia sees is non-lens variability, whatever the count.
  - More than 90%: the passes are lenses.
- **Undetermined colour.** About 38% of passes will have an undetermined colour. Most are red bulge giants (BP − RP 3-5) whose
  BP is fainter than 20.5; undetermined also covers e_D > 0.05, missing BP/RP pairs and too few BP or RP baseline transits.

## 5. The grader and its tests

`dr4_ensemble_grade.py` holds the rule (`judge`, `colour`, `grade_series`) and the forecast's Monte Carlo (`ensemble_mc`,
`fL_posterior`). The forecast script e4 imports both, so the grading percentiles are computed by the code that made the forecast.

- **Self-test on real data** (`--test-dr3`, log `work/ensemble/grade_dr3_test.log`): the three events Gaia DR3 already confirmed,
  fetched live with `releases=("Gaia DR3",)`. **All three pass.**

  | event | source | transits in window | above threshold | max ratio | colour |
  |---|---|---|---|---|---|
  | J172057 | 5959812622743175552 | 2 | 2 | ×6.12 at −7 d | achromatic (D = +0.02 ± 0.03) |
  | J180402 | 4143495279954502016 | 2 | 2 | ×2.60 at −9 d | undetermined (BP baseline 21.7) |
  | J180839 | 4145977633638478336 | 3 | 3 | ×1.52 at −16 d | achromatic (D = +0.01 ± 0.02) |

  J172057 is graded here on 5959812622743175552, the neighbour where DR3 saw the lens. The survey matched 5959812622743175808
  (2.2″ from the AllWISE position, 2.8″ from the lens star). Under this forecast's rule J172057 would be graded on …175808,
  with …175552 reported as `alt_status (not counted)`. The test shows the rule detects a real event on the star it is given. It
  does not show that the matched-star rule catches every lens (section 3.2).

  Negative controls:
  - The same three stars with the event time moved ±400 d. None passes; four controls fail and two are untestable (no transits
    there).
  - Sliding the event time over the three stars' DR3 span (one fake time every 5 d, ≥ 180 d from the event): 0 passes in 181
    testable trials (227 others had too few transits).
- **Synthetic end-to-end check** (`work/ensemble/e5_grader_check.py`). The full grading path (fetch → per-event verdicts →
  counts → falsification test → lens-fraction posterior) runs on synthetic photometry at the GOST times. 10 achromatic ×1.6 and 2
  chromatic injections all pass, with the right colours or undetermined, and no flat star passes. A single bright transit
  listed twice still counts once (FAIL).
- **Dry run against DR3** (`--release "Gaia DR3"`): every sample star comes back "no epoch photometry", as expected (DR3
  published none for them). The grader stops cleanly.

**On DR4 day**, in order:

1. Run `fetch_report([...], releases=("Gaia DR4",))` on one sample star and read the report. A failure there means the release
   name or schema changed (section 2.5).
2. Build `work/ensemble/dr4_idmap.csv` if DR4 renumbered sources.
3. Run the grader. Do not change anything outside section 2.5.
4. Publish the grade with `git diff <seal commit> -- src/oddsky/data/gaia_epoch.py src/oddsky/data/series.py
   hunts/H-0009/predictions/dr4_ensemble_grade.py` and the versions the grader printed.

## 6. Caveats

- **A PASS is not a lens.** The G test asks whether the tested star brightened at the NEOWISE time. The colour test is the lens
  check, and it is undetermined for about a third of passes.
- **The scenario fractions and amplitude ranges for R and F are judgement**, constrained only loosely by the follow-ups and DR3
  (3.2). Section 3.6 shows how much they matter. The falsification test holds f_L fixed but still draws f_R and f_F from these
  priors. The grader therefore labels a "falsified" verdict firm or conditional (3.5).
- **The calibration population.** f_L comes from in-span events and is applied unchanged to the 23 later events. The two groups
  were found the same way but are not identical: 15 of the 23 later events were also found by H-0008's strict pass, against 12
  of the 24 in-span ones.
- **Off-target events test the matched star**, which the brightening probably did not happen on. That is deliberate (no choice
  after the data) and is priced in (3.3). The neighbour sources are graded but not counted.
- **Block events.** Only ±30 d around the peak visit is tested.
- **GOST and the time system.** GOST transit times are UTC at the AllWISE position, and DR4 may deliver fewer transits than GOST
  predicts. 10% random loss is modelled; a systematic DR4 gap near an event is not.
- **Crowding.** Correlated crowding noise in the inner bulge may exceed the model. Raising the flat-star pass rate from 1% to 3%
  adds about 0.65 expected passes.
  - Two tested stars have a catalogued Gaia neighbour within 2″ and 2 mag: J172130 (1.1″, +1.1 mag) and J161048 (1.6″, +1.2).
  - Three have RUWE > 1.4: J130153 (4.2), J170153 (8.3) and J131026 (2.2).
  - Scan-angle contamination is a risk for those five, not for the sample.
- **Not every event is blind.** 8 events have optical follow-up (their weights are fixed above). The blind core (39) is the clean
  test.
- **A DR4 slip.** If DR4 slips, the forecast stands as written. If DR4 publishes epoch photometry for only some sources, those
  without it are "untestable (data)".

## 7. Files

| file | what |
|---|---|
| `dr4_ensemble_sample.csv` | the 50 events: fixed source, event time, GOST transits within ±30 d (`gost_times_30`), status, per-event evidence, scenario pass probabilities (`q_*`, `a_*`, `u_*`, `p_res`), forecast (`p_pass_forecast`, `p_pass_fL20`, `p_lens_onstar`) |
| `dr4_ensemble_grade.py` | the rule, the Monte Carlo, the grader (`--test-dr3`, `--release`) |
| `work/ensemble/e1_sample.py` | builds the sample from the DR3 sweep; `excluded.csv`, `gost_sample.csv` |
| `work/ensemble/e3_scenarios.py` | per-event scenario pass probabilities by simulation (`scenario_pass.csv`) |
| `work/ensemble/e4_ensemble.py` | per-event evidence, the ensemble forecast, the f_L grid, sensitivity (`forecast.json`) |
| `work/ensemble/e5_grader_check.py` | synthetic end-to-end check of the grading path |
| `work/ensemble/dr3_test/` | the DR3 epoch photometry the self-test used, and its result |
| `work/ensemble/e6_table.py`, `sample_table.md` | the table in section 1.4 |
