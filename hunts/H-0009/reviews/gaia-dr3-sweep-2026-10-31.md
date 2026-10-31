# Gaia DR3 as a second instrument for every strong NEOWISE event

Author: claude (Gaia DR3 sweep), 2026-10-31. Scripts, logs and data are in `reviews/gaia-dr3-sweep-2026-10-31/` (s1-s8, run from
the repo root with `uv run python -I`). The table is `work/gaia_dr3_sweep.csv`, one row per event. Nothing was committed or posted.

## Result in one paragraph

Across all 118 deduplicated strong events, only **three Gaia DR3 sources within 4″ have epoch photometry**, and all three
brighten at the NEOWISE time, equally in BP and RP (or G and RP). They are the three the H-0009 ATLAS referee already found:
**J172057, J180402 and J180839**. The DR3 classifier labels all three MICROLENSING, and none is in `vari_microlensing`. No other
source within 4″ of any strong event is flagged VARIABLE or classified, and no event has a source in `vari_microlensing`. The other
32 events inside the DR3 span are untested: DR3 published no epoch photometry for their stars. The missing VARIABLE flags still
carry information as a population, though. Among known lenses that NEOWISE caught inside the DR3 span (not selected through Gaia),
61% (14/23) have a VARIABLE Gaia source within 4″. Among the strong events with a Gaia source, 11% (3/28) do. That puts the lens
fraction among in-span strong events on Gaia-visible stars at about **0.2 (95%: 0.06-0.5)**.

## Method

1. **Events (s1).** `H-0008/work/sky3_strong.csv` (66) and `H-0009/work/sky4_strong.csv` (122). I dropped the 10 events with
   `frame_artifact`, none of which is among the 66, and deduplicated on `allwise_cntr`. That leaves **118 events**: 60 in both
   hunts, 52 in H-0009 only and 6 in H-0008 only. For the 60 shared events I used the H-0009 peak time. They agree to < 1 d except
   J185035, whose dates (2018-04 / 2018-09) both fall outside DR3. I joined the H-0009 referee's centroid test (`r9b_flags.csv`) for
   the 112 H-0009 events, 22 of them off-target.
2. **Gaia sources (s1).** VizieR idia mirror, I/355/gaiadr3, 4″ cones: 210 sources around 99 events. 19 events have no Gaia DR3
   source within 4″. Source ids are kept as strings throughout, and the script asserts this.
3. **Variability tables (s2).** I ran 4″ cones on VizieR's copies of `vari_summary` (I/358/varisum), `vari_classifier_result`
   (I/358/vclassre) and `vari_microlensing` (I/358/vmicro). The ESA TAP never answered the scripted queries (see the
   caveats). An ad-hoc TAP query at the start returned the same three classifier rows (MICROLENSING 0.60, 0.26, 0.21).
4. **Epoch photometry (s3).** `gaia_epoch.fetch_report(ids, releases=("Gaia DR3",))` for **all 210** sources, not only the flagged
   ones, so the `has_epoch_photometry` flag was checked empirically. Exactly the 3 VARIABLE sources came back.
5. **Source choice and measurements (s4).** Source choice, in order:
   - a source whose epoch photometry brightens ≥ 5σ within ±90 d;
   - for off-target events, the Gaia source whose position best reproduces the NEOWISE event-centroid shift (the r9_bulk test,
     applied to every source within 4″);
   - the survey's matched star.

   Measurements:
   - Transits rejected by photometry are dropped; variability-outlier transits are kept.
   - The baseline is the median of transits more than 150 d from the event.
   - Ratios are taken at the nearest epoch within ±30 d and at the largest within ±90 d. Errors combine the transit error with the
     baseline scatter.
   - The colour test is ΔBP − ΔRP at every ≥ 5σ epoch within ±90 d, or ΔG − ΔRP when the BP median is fainter than 20.5.
   - A repeat is an epoch more than 150 d away with at least half the event excess and ≥ 5σ.
6. **Scanning law (s6, s8).** GOST predicted transits for every event. The predictions match the published DR3 transits of the
   three sources: 86%, 100% and 100% of predicted transits are published.
7. **Calibration (s5, s7).** The VARIABLE-flag rate among the 37 known lenses H-0009 recovered inside the DR3 span. 14 of them are
   excluded because they are in the reference list only through Gaia DR3's own catalogue.

## Counts by verdict

| verdict | events |
|---|---|
| **Gaia-confirmed achromatic brightening (lens candidate)** | **3** |
| Gaia: chromatic or repeating variable (not a lens) | 0 |
| Gaia flat at the NEOWISE time (no optical counterpart on that source) | 0 |
| no Gaia epoch photometry, in the DR3 span (untested): no source within 4″ flagged VARIABLE | 25 |
| no Gaia epoch photometry, in the DR3 span (untested): no Gaia DR3 source within 4″ | 7 |
| outside the DR3 span, inside DR4 (2017-05-28 to 2020-01-20): waits for DR4 | 29 |
| after the DR4 span: waits for DR5 | 54 |
| **total** | **118** |

Inside the DR3 span there are 35 events: 3 confirmed and 32 untested. The verdicts "flat" and "chromatic/repeating" cannot occur in
this sample. DR3 published epoch photometry only for sources it flagged VARIABLE, and the only flagged sources near these events are
the three that brightened. DR4 publishes epoch photometry for every source, so it can test 61 events: the 32 untested in-span events
and the 29 later ones. GOST predicts 2-5 transits within ±30 d for 30 of the 32 in-span events; J044653 and J180730 have none.
Nineteen events (all spans) have no Gaia DR3 source within 4″ at all. Gaia will not test those unless DR4 detects a fainter source.

## Gaia-confirmed lens candidates

| event | Gaia DR3 source (sep, G, BP−RP) | NEOWISE W1 | Gaia at the transit nearest the visit | later transits | colour | repeats 2014-17 | DR3 classifier |
|---|---|---|---|---|---|---|---|
| **J172057.02-414201.2** (2015-09-07) | **5959812622743175552** (0.59″, 17.87, 2.57); the survey matched …175808 at 2.2″ | ×4.50 | G ×6.12 ± 0.02, BP ×6.10 ± 0.13, RP ×6.23 ± 0.03 at −7 d | ×2.83 (+25 d), ×1.83 (+44 d); flat at −140 d and +139 d | ΔBP − ΔRP = +0.02 ± 0.02 (3 epochs): **achromatic** | none (max ×1.07 elsewhere, 39 transits) | MICROLENSING 0.60 |
| **J180402.28-181847.5** (2015-09-15) | **4143495279954502016** (0.43″, 18.66, 4.25) | ×2.69 | G ×2.60 ± 0.03, RP ×2.69 ± 0.05 at −9 d | ×2.58 (+20 d), ×1.78 (+42 d) | BP too faint (median 21.1); ΔG − ΔRP = +0.04: **achromatic G to RP** | none (max ×1.05, 28 transits) | MICROLENSING 0.26 |
| **J180839.93-151910.5** (2016-03-21) | **4145977633638478336** (0.28″, 16.04, 2.92) | ×1.62 | G ×1.52 ± 0.01 (−16 d); ×1.39 ± 0.01 with BP ×1.38 ± 0.04, RP ×1.39 ± 0.01 at +15 d | ×1.15 (+35 d) | ΔBP − ΔRP = −0.00 ± 0.02 (3 epochs): **achromatic** | none (max ×1.01, 28 transits) | MICROLENSING 0.21 |

None of the three is in `gaiadr3.vari_microlensing` (VizieR I/358/vmicro: no row within 4″ of any event). In each case Gaia's
ratio is at least the NEOWISE one, allowing for the time offset, which is what a lens on that star predicts given the WISE beam's
dilution. Gaia's ratios here use a baseline of transits more than 150 d away. The referee divided by the median of all transits,
which gives ratios about 4% lower for J172057 (×5.87, ×2.71, ×1.76).

## Off-target events

Off-target events (re-association, s4): 22, 8 of them inside the DR3 span.
- **7 are reassigned to a neighbour that explains the centroid shift.** J172057 is confirmed on its neighbour. The others are
  J173525, J180255, J184240, J173341, J145817 and J171543. J184240's neighbour, 1.15″ away at G 19.3, matches the referee's
  2MASS source.
- **For 11, no Gaia DR3 source within 4″ reproduces the shift** (misses 0.35-3.6″, 7-77σ). The brightening source is either not in
  Gaia DR3 or a red IR source. Examples: J185846 (implied source 0.6″ from AllWISE; the Gaia star is 2.8″ away), J123522, J164900,
  J161946, J180949.
- **4 have no Gaia source within 4″.**

None of the reassigned in-span sources (J173525, J180255) has epoch photometry.

## What the missing flags say (s5, s7)

| sample | VARIABLE source within 4″ |
|---|---|
| known lenses, in the DR3 span, not Gaia-selected | 14/23 = 0.61 (0.39-0.80) |
| the same, ≥ 2 GOST transits within ±30 d | 14/20 = 0.70 |
| strong events in the DR3 span with a Gaia source within 4″ | 3/28 = 0.11 (0.02-0.28) |
| the same, ≥ 2 GOST transits | 3/27 |
| matched star G < 17: known / strong | 11/19 / 1/12 |
| matched star G ≥ 17: known / strong | 3/4 / 2/15 |

- **For a single event**, a missing flag multiplies the lens odds by about 0.4 (0.3 with ≥ 2 transits). That is weak evidence, not
  a test.
- **For the population**, the gap is large. If all 28 were lenses on their Gaia stars, about 17 would be flagged. Three are, which
  implies a lens fraction of about 0.2 (Monte Carlo 0.06-0.5). That agrees with H-0008's "10-25% look like lenses".
- **Two consequences:**
  - most strong events either have no optical counterpart on the Gaia star (IR-only variables, sources hidden behind dust) or
    brightened on something Gaia DR3 does not list;
  - when a strong event's Gaia star is flagged VARIABLE, it has so far always been the lens (3/3).

## Caveats

- **This sweep confirms nothing new.** The three candidates are the referee's. What it adds:
  - completeness: no other flagged, classified or `vari_microlensing` source sits within 4″ of any of the 118 events;
  - the BP/RP numbers and the repeat test;
  - GOST counts;
  - the population constraint.
- **The calibration set is not a perfect match.** Its lenses are bulge events found by OGLE/KMTNet, which selects optically bright
  events (matched-star G median 16.1, against 17.2 for the strong events). An IR-only event on a dust-hidden source would show no
  Gaia variability whatever its nature. So the 0.2 applies to "lenses on the Gaia-visible star".
- **The DR3 VARIABLE selection is not a clean detector.** 9 of 23 known lenses (OGLE-2014-BLG-1356 at ×4.8 among them) were not
  flagged, although GOST puts at least two transits within ±30 d of the event for 6 of those 9. For any single event, the absence of a flag is weak evidence.
- **gaia_source mean photometry rejects outliers.** J172057's lens star has an amplitude proxy sqrt(n_obs)/(flux/error) of only
  0.04 despite ×6, so that proxy cannot test non-VARIABLE sources.
- **Timing.** Gaia ratios are at transits 7-16 d from the NEOWISE visit, not at it. Gaia's windows (G 0.7″ × 2.1″) also differ
  from WISE's beam, so the G and W1 amplitudes need not match.
- **J180402's BP is unusable** (median 21.1, transits scattered by several mag), so its colour test is G against RP only.
- **The 6 H-0008-only events have no centroid test.** Their source is the survey match. Three of them are in the DR3 span (J175844,
  J101423, J201542), and all three are untested.
- **ESA TAP.** Two scripted runs hung on their first query, for about 40 and about 45 minutes, and were killed. The only TAP
  answer is one ad-hoc query for the three classified sources, which matches VizieR to every digit (logged in
  `s2_vari_tables.log`). VizieR's I/358 copies are the source of record here. Both sources are drawn from the same DR3 tables,
  and the I/355 VarFlag/EpochPh columns agree with `varisum` and with what the datalink returned (asserted in s4).

## Files

| script | what it does |
|---|---|
| `lib.py` | paths, TAP helper |
| `s1_events_cones` | deduplicated events (`data/events.csv`), Gaia DR3 4″ cones (`data/cones.csv`) |
| `s2_vari_tables` | `vari_summary` / classifier / microlensing (VizieR I/358; TAP cross-check) → `data/vari_*.csv` |
| `s3_epoch` | DR3 epoch photometry for all 210 sources → `data/epoch/`, `data/epoch_report.json` |
| `s4_analyse` | source choice, ratios, colour and repeat tests, verdicts → `work/gaia_dr3_sweep.csv` |
| `s5_calibration` | VARIABLE-flag rate among in-span known lenses → `data/calib_known.csv` |
| `s6_gost` | GOST predicted transits for all events and calibration lenses → `data/gost_transits.csv` |
| `s7_population` | flag-rate comparison and implied lens fraction |
| `s8_gost_check` | GOST predictions against published DR3 transits |
