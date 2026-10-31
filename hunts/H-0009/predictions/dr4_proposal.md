# Gaia DR4 sealed predictions: proposal (H-0009 follow-up)

Author: claude (prediction design), 2026-10-30. Nothing is registered yet. This is a proposal for the six targets below.
The machine-readable list is `dr4_proposal.json`. Scripts, logs and GOST forecasts are in `work/` (p1-p10, run from the
repo root with `uv run python hunts/H-0009/predictions/work/pN_*.py`).

Gaia DR4 (scheduled 2026-12-02) publishes per-transit G photometry for every source, 2014-07-25 to 2020-01-20. All six
NEOWISE events fall inside that span, and Gaia's scanning law puts transits within 2-27 days of every event visit. Every
target therefore gets a gradeable prediction, and none has to be dropped (see the last section).

## Summary

The `probability` column is the stake: P(true | resolved). "Unresolvable" means fewer than 3 points in the window. Times
are MJD, and the baseline is subtracted from the window statistic. Every check has series `GAIA:G` and op `<`, so a
check is true when the window is brighter than the baseline by more than |value|.

| # | target | window (MJD) | statistic | baseline (MJD) | value | stake | P(unres) | tests |
|---|---|---|---|---|---|---|---|---|
| 1a | J163539.69-355208.3 | 57949-58042 (2017 Jul 15-Oct 16) | median | 56863.5-57570 | −1.2 | **0.93** | 0.03 | the ATLAS lens is seen at full strength in G |
| 1b | J163539 | 57770-57840 (2017 Jan 17-Mar 28) | median | 56863.5-57570 | −0.10 | **0.90** | 0.01 | slow rise in G 5-7 months before peak |
| 1c | J163539 | 58140-58215 (2018 Jan 22-Apr 7) | median | 56863.5-57570 | −0.07 | **0.90** | 0.01 | slow decline 5-7 months after peak |
| 2a | J173150.73-444549.3 | 58150-58400 (2018 Feb 1-Oct 9) | brightest | 56863.5-57935 | −1.0 | **0.90** | 0.00 | the ATLAS lens is seen in G at +27 d |
| 2b | J173150 | 58150-58215 (2018 Feb 1-Apr 7) | median | 56863.5-57935 | −0.10 | **0.92** | 0.00 | slow rise in G |
| 3a | J124517.35-630125.0 | 58255-58340 (2018 May 17-Aug 10) | brightest | 56863.5-57935 | −0.3 | **0.57** | 0.01 | real brightening of the Gaia star vs artifact / other star |
| 3b | J124517 | 58255-58340 | median | 56863.5-57935 | −0.15 | **0.50** | 0.01 | event lasting weeks or more (lens) vs short outburst / artifact |
| 4a | J160706.90-533729.5 | 57945-58025 (2017 Jul 11-Sep 29) | median | 56863.5-57570 | −0.5 | **0.74** | 0.03 | real slow event on the Gaia star vs artifact / other star |
| 4b | J160706 | 57945-58025 | brightest | 56863.5-57570 | −1.5 | **0.71** | 0.03 | achromatic lens with fs_G ≥ fs_W1 vs a weaker G response |
| 5a | J131026.53-612259.2 | 57185-57300 (2015 Jun 12-Oct 5) | median | 57600-58868 | −0.2 | **0.70** | 0.02 | real months-long event on the Gaia star vs artifact / flare |
| 5b | J131026 | 57185-57300 | brightest | 57600-58868 | −0.6 | **0.69** | 0.02 | achromatic lens with fs_G ≥ fs_W1 |
| 6a | J154239.48-572601.4 | 57945-58020 (2017 Jul 11-Sep 24) | brightest | 56863.5-57630 | −0.4 | **0.48** | 0.02 | real brightening of the Gaia star vs artifact / neighbour |
| 6b | J154239 | 57945-58020 | median | 56863.5-57630 | −0.15 | **0.45** | 0.02 | event lasting more than ~2 weeks (lens) vs short outburst / artifact |

Suggested resolve_by for all of them: **2027-06-30**, which allows for a DR4 slip.

## Method

### Gaia's scanning (p2, p3, p4)
- **GOST forecasts.** Fetched today for each Gaia DR3 position (`work/gost/gost_<k>.csv`, raw export) over 2014-07-25
  10:32 to 2020-01-21. GOST rejects start times before 2014-07-25T10:31:26 TCB.
- **Time system.** Times are taken from the barycentric column (BJD_TCB − 2400000.5). That is the time system of Gaia
  epoch photometry: `g_transit_time` + 55197 in `oddsky.data.gaia_epoch`.
- **Delivery against the forecast.** GOST vs delivered photometry, using DR3 `matched_transits` against GOST transits
  before 2017-05-28: 96%, 100%, 93%, 95%, 94% and 94% for the six targets. The Monte Carlo therefore uses 10% random
  loss, and every probability is repeated with 20% loss (logged in `p9_mc.log` and `p10_final.log`). The stakes move by
  ≤ 0.01; P(unres) rises by at most 0.05.

### The grader Monte Carlo (gaialib.py, p9)
- **Grader.** A line-for-line replica of `oddsky.tools.evaluate`:
  - window inclusive; fewer than 3 points gives "unresolvable";
  - brightest = the minimum nightly median, with nights binned on floor(MJD);
  - the baseline median is subtracted, and fewer than 3 baseline points also gives "unresolvable".
- **Observed series in each realisation:**
  - the GOST transits, 10% lost;
  - per-transit noise. This is the DR3 noise floor at the transit's own magnitude ×1.5 for crowding: 0.02 mag at G 18,
    0.005 at G 15;
  - **2% outliers** of ±0.2-1.0 mag. Variability-flagged transits are kept by the grader, so these are real.
- **Pessimistic branch (3% weight).** Every transit more than 0.5 mag above the series median is dropped, as if Gaia had
  flagged it `rejected_by_photometry`. The grader drops those points.
- **That branch is a tail risk.** p7 fetched the DR3 epoch photometry of 25 Gaia DR3 microlensing events: 918 G transits,
  32 of them more than 1 mag above baseline. None is `rejected_by_photometry`. 5 of the 32 bright ones are
  variability-flagged, which the old grader would have dropped.
- **Sample sizes.** 600 model draws × 4 noise draws per scenario.

### Pre-DR4 evidence already in DR3 (p5, p6)
Gaia DR3 publishes mean photometry for all six stars, which already says whether Gaia saw anything before 2017-05-28.
- **The calibration case is J163539**, whose ATLAS rise began in early 2017. It has 7.19 CCD observations per matched
  transit against a field median of 8.54. That is the 2.3rd percentile, and ≈ 4.3 transits' worth of CCD fluxes are
  missing. Its G scatter is at the 95th percentile.
- **Interpretation.** That matches its 5 rising-wing transits (Jan-Mar 2017, model ΔG −0.2 to −0.37) being rejected from
  the DR3 *mean* photometry. So "missing CCD observations" is a fingerprint of brightened transits.
- **Comparison stars** are within 2′ and ±0.5 mag.

| target | event inside DR3 span? | CCD obs / transit (pct) | missing transits | DR3 G scatter pct | reading |
|---|---|---|---|---|---|
| J163539 | rise only | 7.19 (2.3) | 4.3 | 95 | Gaia saw the rise (calibrator) |
| J173150 | no | 8.45 (28) | 0.3 | 47 | uninformative, as expected |
| J124517 | no | 8.50 (25) | 0.6 | 44 | uninformative |
| J160706 | rise (×1.75 in W1 in Mar 2017) | 7.90 (12) | 4.4 | 77 | mildly supports Gaia seeing the rise (3 transits Jan-Mar 2017) |
| J131026 | yes (2015) | **7.12 (1.4)** | **9.4** | **95** | **supports a months-long event seen by Gaia**: ~12 transits within ±100 d of the visit; RUWE 2.17 also fits a variable blend |
| J154239 | no | 8.44 (23) | 0.8 | 73 | uninformative |

I used this only to move the scenario priors for J131026, J160706 and J163539 (below). It is aggregate, so the DR4
per-transit test stays blind.

### Gaia G vs NEOWISE W1 amplitude (assumption)
- **Same source magnification.** A lens magnifies the source by the same factor in every band. The observed ratio is
  1 + fs(A − 1), where fs is the source's share of the light in that instrument's beam.
- **Different blending.** WISE's W1 beam is ≈ 6″, while Gaia resolves ≈ 0.2-0.4″.
- **Assumption for targets 3-6.** If the lensed source is the Gaia star, Gaia's blend fraction is fs_G = fs_W1 +
  (1 − fs_W1)·U(0, 1). In other words fs_G ≥ fs_W1: Gaia removes some or all of the WISE blend. **G amplitude ≥ W1
  amplitude** is therefore expected for a lens on the Gaia star. Predictions 4b and 5b test exactly this.
- **Assumption for targets 1-2.** G sees the ATLAS-o ratio scaled by k ~ U(0.65, 1.10):
  - k < 1 if the ATLAS forced-photometry baseline is biased low. The referee found ATLAS baselines 0.7-1.0× the o flux
    expected from Gaia.
  - k > 1 if ATLAS's baseline includes neighbours Gaia resolves.

### Scenarios for the NEOWISE-only targets (models.py)
- **L: lens on the Gaia star.**
  - Point lens, with draws weighted by the likelihood of *all* NEOWISE W1 visits (error ⊕ 0.03 mag).
  - t0 between the bracketing quiet visits; tE log-uniform 20-200 d; u0 uniform 0-1.2; fs_W1 uniform 0.1-1.
  - J160706 is an exception, described in its section.
- **R: real non-lens event on the Gaia star.** Same time profile as L, but chromatic: G amplitude (mag) = W1 amplitude
  × U(0.3, 2).
- **F: short outburst.**
  - e-fold decay τ log-uniform 1-20 d, rise τ/3.
  - The NEOWISE visit falls anywhere from the peak to 3τ after it.
  - G amplitude = W1 amplitude × U(0.5, 2.5) in mag.
  - Must keep the neighbouring visits quiet.
- **N: Gaia sees nothing.** Covers an artifact, or an event on another star in the WISE beam, including a G-invisible
  dusty star.
- **Priors are judgement.** They are set from the H-0008/H-0009 follow-up record: of 7 strong events followed with ATLAS,
  4 are lens candidates, 1 is inconclusive and 2 are non-lenses. Each target's section gives P(true | scenario), so
  anyone can reweight.

## Per target

### 1. J163539.69-355208.3 (Gaia DR3 6020322385418675200, G 18.31)
**Facts.**
- ATLAS sees a smooth ×6-9 event peaking 2017 Aug 15-18.
- Referee parallax-lens fits over 14 reduction variants: tE 121-189 d.
- NEOWISE: W1 −2.26 on 57982; −0.31 at −167 d; −0.21 at +197 d.
- The DR3 CCD deficit (above) shows Gaia already saw the rise.
- One DR3 neighbour within 6″ (G 19.66 at 4.9″).

**Gaia transits.** 55 in DR4.
- Near the event: Jan 26, Feb 13 (2), Mar 17 (2) 2017; **Jul 29 (2), Aug 20 (2), Sep 19 (2) 2017**; Feb 4, Feb 28 (2),
  Mar 27 (2) 2018.
- **The referee's open question is answered:** Gaia did *not* have a scanning gap. It transited 19 d before, 3 d after
  and 33 d after the peak, at a modelled G ≈ 16, and issued no alert.

**Model** (`p8_atlas_models.log`). ΔG by night, across all 14 variants and k = 0.65-1.10:

| night | ΔG |
|---|---|
| Jul 29 2017 | −1.56 to −2.06 |
| Aug 20 2017 | −1.96 to −2.49 |
| Sep 19 2017 | −1.28 to −1.76 |
| Jan-Mar 2017 | −0.17 to −0.37 |
| Feb-Mar 2018 | −0.10 to −0.30 |

| # | statement | Check | MC P(true\|res) | stake | P(unres) | scenario |
|---|---|---|---|---|---|---|
| 1a | Gaia G in 2017 Jul 15-Oct 16 (6 transits) has a median ≥ 1.2 mag brighter than the 2014-07..2016-06 baseline | GAIA:G, 57949-58042, median, baseline 56863.5-57570, < −1.2 | 0.97 | 0.93 | 0.03 | lens at full amplitude vs Gaia flat |
| 1b | Gaia G in 2017 Jan 17-Mar 28 (5 transits) has a median ≥ 0.10 mag brighter than baseline | 57770-57840, median, same baseline, < −0.10 | 0.97 | 0.90 | 0.01 | slow rise |
| 1c | Gaia G in 2018 Jan 22-Apr 7 (5 transits) has a median ≥ 0.07 mag brighter than baseline | 58140-58215, median, same baseline, < −0.07 | 0.97 | 0.90 | 0.01 | slow decline |

**Why the stakes are below the MC.**
- The MC value is P(ATLAS model) × P(true | model), plus the 3% "Gaia sees nothing" branch.
- I shaded 1a by 0.04 and the wings by 0.07 for systematics the MC does not hold: G vs o passband for a blend of
  different colours, and unknown DR4 processing.
- **Lens vs symmetric bump:** these checks do not discriminate. The ATLAS PV7 bump also fits the same wings, because
  ATLAS data constrain those epochs.
- **What they do discriminate:** whether Gaia, at 0.2″ resolution, sees the same event on this star at ≥ 0.65× the
  ATLAS ratio.
- **Peak amplitude as a blend test.** It is not used as a threshold, but G at the Aug 20 transit near −2.5 rather than
  −2.0 would mean fs_G > fs_ATLAS.

### 2. J173150.73-444549.3 (Gaia DR3 5952322268527918208, G 15.07)
**Facts.**
- ATLAS ×7.7, peak 2018 Jul 11-14.
- A static lens is excluded; the parallax-lens tE runs over 123-493 d.
- Possible ATLAS saturation at the peak (o 12.6).
- NEOWISE: W1 −0.35 on 58193 and −1.21 on 58357.
- DR3 neighbours: G 17.68, 19.76 and 16.86 at 4.4-5.6″ (the Gaia star has 0.77 of the G flux within 6″).

**Gaia transits.** 82 in DR4.
- Near the event: Feb 8 (2), Feb 27 (2), Mar 31 (2), **Aug 9 (2)**, Sep 1, Oct 1 2018; then Feb-Apr 2019.
- **No Gaia transit between Mar 31 and Aug 9 2018**, so Gaia missed the peak. It did see +27 d (model G ≈ 13.3), +50 d
  and +80 d. No alert was issued.

**Model.** The excess at Gaia's epochs is pinned by ATLAS, so the tE degeneracy hardly matters. Values for k =
0.65-1.10, all variants:

| night | ΔG |
|---|---|
| Aug 9 2018 | −1.39 to −1.86 |
| Sep 1 2018 | −0.90 to −1.28 |
| Oct 1 2018 | −0.45 to −0.70 |
| Feb-Mar 2018 | −0.11 to −0.60 |
| 2019 Feb-Apr | −0.01 to −0.05 |

Peak compression from ATLAS saturation could only make Gaia brighter than modelled, which helps 2a.

| # | statement | Check | MC P(true\|res) | stake | P(unres) | scenario |
|---|---|---|---|---|---|---|
| 2a | The brightest Gaia night in 2018 Feb 1-Oct 9 (10 transits, 6 nights) is ≥ 1.0 mag brighter than the 2014-07..2017-06 baseline | 58150-58400, brightest, baseline 56863.5-57935, < −1.0 | 0.92 | 0.90 | 0.00 | lens vs Gaia flat; G amplitude at +27 d |
| 2b | Gaia G in 2018 Feb 1-Apr 7 (6 transits) has a median ≥ 0.10 mag brighter than baseline | 58150-58215, median, same baseline, < −0.10 | 0.95 | 0.92 | 0.00 | slow rise (NEOWISE W1 −0.35 on Mar 15) |

**Rejected candidates for J173150.**
- *Brightest over Jul 31-Oct 8 only*: 4 transits, P(unres) 0.08-0.20.
- *2019 median back to baseline*: true under every scenario, including "Gaia flat", so it carries no information.
- *Decline wing as a tE test*: the model gives −0.01 to −0.05 for every variant, so it discriminates nothing.

**Gaia's 2a outlier immunity.** The brightest night (Aug 9) has 2 transits. A single 1-mag outlier cannot fake a night
1 mag up: the nightly median of two points halves it.

### 3. J124517.35-630125.0 (Gaia DR3 5862971688685406976, G 17.76)
**Facts.**
- A single NEOWISE visit at 58313.4, ×6.9 in both W1 and W2.
- Quiet visits 162 d before (W1 −0.06) and 205 d after (+0.01).
- The Gaia star is alone within 6″ (share 1.00), so an event on any star Gaia sees here would be on this one.
- Strong mid-IR excess (W1−W4 5.6; W3 9.2, W4 6.2), which keeps a YSO-type outburst a live alternative.
- NEOWISE intra-visit rχ² is 20-36 at every quiet visit but 5 at the event visit; unexplained.
- No DR3 hint (the event is after the DR3 span).

**Lens posterior.** tE 42-90 d (16-84%), t0 within ±6 d of the visit, fs_W1 ≈ 0.75. The quiet visits limit tE.

**Gaia transits near the visit.**

| date | offset | transits | model ΔG (lens) |
|---|---|---|---|
| May 26 | −49 d | 3 | −0.46 [−0.74, −0.19] |
| Jun 19 | −25 d | 2 | −0.95 [−1.43, −0.57] |
| Jul 27 | +13 d | 1 | −1.48 [−2.13, −1.11] |
| Sep 1 | +49 d | 1 | – |
| Sep 21 | +69 d | 2 | – |

| # | statement | Check | stake | P(unres) | P(true) by scenario: L / R / F / N |
|---|---|---|---|---|---|
| 3a | The brightest Gaia night in 2018 May 17-Aug 10 (6 transits, 3 nights) is ≥ 0.3 mag brighter than the 2014-07..2017-06 baseline | 58255-58340, brightest, baseline 56863.5-57935, < −0.3 | 0.57 | 0.01 | 0.97 / 0.96 / 0.51 / 0.02 |
| 3b | Gaia G in 2018 May 17-Aug 10 has a median ≥ 0.15 mag brighter than baseline | same window, median, same baseline, < −0.15 | 0.50 | 0.01 | 0.94 / 0.91 / 0.22 / 0.00 |

**Priors and outlier risk.**
- Priors: L 0.35, R 0.15, F 0.15, N 0.35.
- 3a's 2% false-pass under N comes from single-transit outliers. 3b is outlier-proof.
- An outcome of 3a true with 3b false would point to a short outburst.

### 4. J160706.90-533729.5 (Gaia DR3 5932843350525331968, G 18.00, BP−RP 3.96)
- **NEOWISE light curve:** W1 −0.05 (57620), −0.61 (57813.6, ×1.75), **−2.29 (57980.6, ×8.3)**, −0.11 (58178), −0.01
  (58341).
- **The light curve is asymmetric.** The rise is slower than the decline, and a symmetric point lens misses the 58178
  visit by 4σ (χ² 35 for 21 visits).
- **So L here uses separate rise and fall timescales** as a proxy for annual parallax, in a focused prior box.
  Posterior: rise tE ≈ 236-283 d, fall ≈ 140 d, peak 0-15 d before the visit, fs_W1 ≈ 0.9 (ESS 41, χ²min 13.5).
- **This exceeds the 20-200 d range in the brief**, because the visits demand it.
- **Blending:** the Gaia star holds 0.72 of the G flux within 6″ (four G 20-21 neighbours, one at 1.9″). NEOWISE frames
  are halo-flagged at every epoch.
- **DR3 hint:** a mild CCD deficit (4.4 transits; 12th percentile) matching the 3 rise transits of Jan-Mar 2017.

**Gaia transits near the visit, with model ΔG (lens):**

| date | transits | model ΔG |
|---|---|---|
| Jul 23 2017 | 2 | −2.6 [−3.3, −2.1] |
| Aug 17 2017 | 2 | −2.3 [−2.4, −2.2] |
| Sep 16 2017 | 1 | −1.3 [−1.5, −1.1] |

| # | statement | Check | stake | P(unres) | L / R / N |
|---|---|---|---|---|---|
| 4a | Gaia G in 2017 Jul 11-Sep 29 (5 transits, 3 nights) has a median ≥ 0.5 mag brighter than the 2014-07..2016-06 baseline | 57945-58025, median, baseline 56863.5-57570, < −0.5 | 0.74 | 0.03 | 0.96 / 0.96 / 0.00 |
| 4b | The brightest Gaia night in the same window is ≥ 1.5 mag brighter than baseline | same window, brightest, same baseline, < −1.5 | 0.71 | 0.03 | 0.96 / 0.81 / 0.00 |

**Priors and rejected candidates.**
- Priors: L 0.55, R 0.20, N 0.25 (F excluded: two event visits 167 d apart). These were raised from 0.50 / 0.20 / 0.30
  for the DR3 deficit.
- 4b is the "G amplitude ≥ W1 amplitude" test.
- *Rejected:* the decline wing (2018 Feb-Mar), which has only 3 transits (P(unres) 0.27).

### 5. J131026.53-612259.2 (Gaia DR3 5863586423081438848, G 17.75, RUWE 2.17)
**Facts.**
- A single NEOWISE visit at 57235.8, ×2.5 in W1/W2.
- Neighbouring visits W1 −0.08 (−178 d) and −0.12 (+189 d) against a later baseline. The early 2014-15 visits sit
  0.02-0.06 bright, so the wings may be real.
- Alone within 6″.
- **The strongest pre-DR4 hint of the set:** a CCD deficit of 9.4 transits (1.4th percentile) and DR3 G scatter at the
  95th percentile, both from the epoch that contains the event.

**Lens posterior.** tE 112-162 d, t0 5-33 d after the visit, fs_W1 ≈ 0.67.

**Gaia transits near the visit, with model ΔG (lens):**

| date | offset | transits | model ΔG |
|---|---|---|---|
| Jun 22 | −40 d | 2 | −0.69 |
| Jul 20 | −12 d | 1 | −1.0 |
| Aug 20 | +19 d | 1 | −1.4 |
| Sep 28 | +58 d | 2 | −1.0 |

The baseline is 2016-08 to 2020-01 (83 transits), more than a year after the event.

| # | statement | Check | stake | P(unres) | L / R / F / N |
|---|---|---|---|---|---|
| 5a | Gaia G in 2015 Jun 12-Oct 5 (6 transits, 4 nights) has a median ≥ 0.2 mag brighter than the 2016-08..2020-01 baseline | 57185-57300, median, baseline 57600-58868, < −0.2 | 0.70 | 0.02 | 0.97 / 0.97 / 0.11 / 0.00 |
| 5b | The brightest Gaia night in the same window is ≥ 0.6 mag brighter than baseline | same window, brightest, same baseline, < −0.6 | 0.69 | 0.02 | 0.97 / 0.83 / 0.37 / 0.02 |

Priors: L 0.50, R 0.20, F 0.05, N 0.25, raised from 0.40 / 0.15 / 0.10 / 0.35 for the DR3 deficit.

### 6. J154239.48-572601.4 (Gaia DR3 5882495205642608896, G 17.24)
**Facts.**
- A single NEOWISE visit at 57977.9, ×2.3.
- Quiet visits at −167 d (−0.03) and +197 d (0.00).
- **A DR3 neighbour, 5882495205563616128 (G 17.58, BP−RP 1.90, ϖ 1.03 mas, RUWE 1.87), lies 3.2″ away.** The target
  holds only 0.48 of the G flux within 6″.
- The neighbour is much bluer and nearer. The red target (BP−RP 3.23) is the likelier W1 source, but the event could be
  on the neighbour. Hence the largest N prior.

**Lens posterior.** tE 31-77 d, t0 within ±15 d of the visit.

**Gaia transits near the visit, with model ΔG (lens):**

| date | offset | transits | model ΔG |
|---|---|---|---|
| Jul 21 | −22 d | 2 | −0.6 [−1.3, −0.3] |
| Aug 17 | +4.5 d | 2 | −1.0 [−1.3, −0.8] |
| Sep 15 | +34 d | 1 | −0.4 [−0.9, −0.2] |
| Oct 28-Nov 1 | +77 d | 14 transits on 4 nights | – |

| # | statement | Check | stake | P(unres) | L / R / F / N |
|---|---|---|---|---|---|
| 6a | The brightest Gaia night in 2017 Jul 11-Sep 24 (5 transits, 3 nights) is ≥ 0.4 mag brighter than the 2014-07..2016-08 baseline | 57945-58020, brightest, baseline 56863.5-57630, < −0.4 | 0.48 | 0.02 | 0.96 / 0.89 / 0.57 / 0.01 |
| 6b | Gaia G in the same window has a median ≥ 0.15 mag brighter than baseline | same window, median, same baseline, < −0.15 | 0.45 | 0.02 | 0.97 / 0.93 / 0.38 / 0.00 |

**Priors and options.**
- Priors: L 0.30, R 0.10, F 0.15, N 0.45.
- **Optional:** if the case can hold a second Gaia id, register 6a on the neighbour 5882495205563616128 as well. Exactly
  one of the two should brighten if the event is real.
- *Rejected:* "Oct-Nov 2017 median < −0.1" (stake 0.21; a tE test). It is informative, but nobody would stake it.

## Risks not in the Monte Carlo

- **No Gaia Science Alert for J163539 or J173150.** Gaia transited both well inside their events, at ΔG ≈ −2 and −1.6
  for stars at G ≈ 16 and 13. Neither was alerted.
  - Alert incompleteness in the plane is common, and the J163539 DR3 deficit shows Gaia's photometry did register that
    star.
  - Still, it is the one fact that argues for "Gaia sees less than ATLAS". That is why the stakes for 1-2 sit below the
    MC.
- **DR4 processing is unknown.**
  - The flag semantics could change.
  - Transits rejected from DR3 mean photometry (the CCD deficit) could be flagged in DR4 epoch photometry. The 3%
    pessimistic branch models this; p7 says it did not happen in DR3.
  - If DR4 drops them, the event checks (1a, 2a, 4a/b, 5a/b, 3a, 6a) fail or become unresolvable together.
- **Correlation.** The checks on one target are strongly correlated. Score them as one bet per target, not as independent
  bets.
- **Scenario priors for 3-6 are judgement.** The per-scenario P(true) values are given so they can be reweighted.

## Targets to drop?

None. Every target has a Gaia transit within 2-13 d of its NEOWISE event visit (J173150: 27 d after the ATLAS peak).
Every proposed window holds 5-10 forecast transits on 3-6 nights, so every check above is resolvable with ≥ 97%
probability.

**J124517 and J154239 carry near-even stakes (0.45-0.57).** That is not for want of Gaia data: whether those NEOWISE
events are on the Gaia star at all is genuinely uncertain. They are still worth sealing. A "true" would turn a
one-visit NEOWISE blip into a confirmed optical event; a "false" would rule out a lens on the Gaia star at ≥ 95%
confidence. If only high-confidence predictions are wanted, register 1a-c, 2a-b, 4a and 5a.

## Files (`work/`)

**Setup and the per-target checks:**
- `targets.py`, `gaialib.py` (GOST loader, grader replica, noise model), `models.py` (scenario models).
- `p1_neowise` (visit light curves), `p2_gost` (GOST fetch → `gost/`), `p3_transits`.
- `p4_dr3` (`dr3_stats.csv`), `p5_dr3_scatter` (`dr3_scatter.csv`), `p6_nobs_per_transit` (`dr3_ccd_per_transit.csv`).

**Tests, Monte Carlo and outputs:**
- `p7_flag_test` (DR3 microlensing flag test; `dr3_ml_sample.csv`, `p7_flag_test.csv`).
- `p8_atlas_models` (targets 1-2 at every transit).
- `p9_mc` (grader Monte Carlo; `p9_results.json`).
- `p10_final` (writes `../dr4_proposal.json`).
