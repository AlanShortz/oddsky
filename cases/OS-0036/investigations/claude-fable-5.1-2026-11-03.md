# HM Sge, fifty years on: the fade that Goldman et al. (2022) caught starting

Investigator: Claude Fable 5.1 through the Oddsky tools, 2026-11-03. Asked by the advisor via Alan: "anything interesting on
HM Sagittae?" Case opened by coordinates (SIMBAD at CDS was down); data: AAVSO (B, V, R, I, visual, 1977-2026), Gaia DR3 epoch
photometry (2014-17), ZTF g (saturated in r), NEOWISE (saturated, useless), AllWISE (saturated); ATLAS and TESS were still
queued when this was written. Every number below has a ledger receipt (K-ids); `oddsky replay OS-0036` reproduces them.

## What the archives say (claims C1-C12; C5 retracted)

1. **HM Sge has faded in every band since 2021-22 and is still fading.** Between 2019.0-2021.5 and 2026.0-2026.9 the AAVSO
   medians moved: V 12.22 → 13.18 (+0.95 mag), B +0.90 (one observer, DFS; a second observer's 2026 B is 0.45 fainter still),
   visual +0.90, R 11.00 → 12.65 (+1.65, five observers at each end agreeing to ±0.2) (K12-K16, K42-K43). The V levels at
   both ends are set by five or more observers agreeing to 0.1 mag (C10). The V changepoint is 2023 Jan 27 (+0.54 mag step,
   K20); yearly medians fall 0.2-0.3 mag/yr through November 2026 with no flattening (`figures/aavso_2008_2026.png`).
2. **The star is at its faintest since the 1975 outburst**: visual 13.1 against 10.6 in 1977-85 (K21). The 1977-2021 record is a
   smooth decline to 12.2; nothing like the present fade occurred before.
3. **The fade is red-heavy.** Same-night pairs from one observer: R moves 1.73× V (1,528 pairs, r = 0.986) and B 1.04× V
   (K44, K45); V−R went from 1.3 (2018-2021) to 0.53 (2026) while B−V stayed at 0.45-0.5. For dust in front of a single source
   the slopes would be 0.81 and 1.32; the opposite ordering means the light being lost is redder than what remains: the
   Mira's light is leaving the sum faster than the nebula's.
4. **The Mira's clock is untouched, and its maxima are sinking.** I-band maxima: 10.19 (2021.51), 10.69 (2023.15), 11.50
   (2026.11), each from an observer with dozens of points: 1.3 mag in 4.6 yr at the same phase (C11). Lomb-Scargle on I gives
   530 d for 2008-2021.5 (K17; literature 527-534 d) and the detrended 2022.5-2026.9 data still pulsate at ~540 d with 0.9 mag
   amplitude. The I band is otherwise unreliable across observers (2026 levels differ by 1.2 mag between observers), which is
   why the earlier "1.8 mag below trend" statement (C5) is retracted.
5. **The 2018-2021 "high-activity episode" of Ikonnikova et al. (2026) is in AAVSO V**: +0.24 mag over 2014-17 (K22).
6. Gaia DR3 2014-17: G 11.57-12.10 over 70 transits, the pulsation; RUWE 5.74 (a photocentre moving with the pulsating,
   nebula-embedded Mira; the Skeptic warns). NEOWISE: five saturated visits, nothing usable (K23).
7. **TESS sees no flickering** (C9, K40): five sectors from 2019 to 2024, including 2021 Jul-Aug at the onset of the fade,
   with sub-day scatter of 1-2 mmag and no periodic signal above a few mmag. Whatever the white dwarf is doing, it does not
   show on hours timescales in the optical at this level (the nebula and the Mira dilute it; SPOC contamination 25-33%).

## What is already known (novelty, honestly)

Ikonnikova et al. 2026 (Astron. Rep. 70, 561; arXiv:2603.11777): UBV 2003-2025 fading at ~0.05 mag/yr to 2018, a 0.3 mag
brightening peaking in 2021, then "a decline by 2025 to the faintest level in five decades"; JHKLM 2009-2025 with P = 532 d and
"long-term variability driven by changes in the optical depth of the dust shell"; first [Fe X] detection; a 46-yr periastron
hypothesis linking 1975 and 2018-21. Goldman et al. 2024 (ApJ 961, 14): SOFIA/HST, dust output unchanged over 39 years, hot
component hotter than 250,000 K. Hack et al. 2025 (HST GO 18051): a jet in the April 2021 HST images, and the late-2021 dimming
read as "a new powerful mass ejection and dust formation". Toalá et al. 2023: an extremely soft X-ray component, periodic
ejections suggested.

So the fade itself is reported. **What this investigation adds:** the record to November 2026 (one year past the published
data, still falling at 0.2-0.3 mag/yr); the wavelength dependence (R and I lose twice what B and V lose), which separates the
Mira's light from the nebula's; the untouched 540-d pulsation through the fade; and three sealed-style predictions.

## Hypotheses (H1-H3), after reading Ikonnikova et al. (2026)

Their paper (UBV + JHKLM to 2025; no AAVSO, no R or I) says the near-infrared fell to early-1990s levels, that J−H went
*bluer* while K−L and L−M did not change, that "the expected reddening of colour indices was not observed", and that the Raman
O VI and Hβ behaviour point to the hot component. They set a dust-formation episode aside on those grounds. Our optical
colour result (R fades 1.73× V, B 1.04× V) is in neither paper, but it does not settle the question by itself, because the R
band also carries the nebula's Hα.

- **H1 (0.40): new dust from the 2018-21 ejection obscuring the Mira** (the HST GO 18051 reading). Fits the red-heavy fade and
  the sinking I-band maxima; would need large grains or an optically thick, grey screen to leave J−H bluer. Test: the
  3-20 µm dust emission (new warm dust should add flux; JWST or a ground N-band point).
- **H2 (0.35): the hot component and the nebula it ionizes are declining** (Ikonnikova's reading). Explains B, V and part of R
  (Hα); has to explain the I-band maxima sinking 1.3 mag while Hβ fell by only ~0.4 mag. Test: Hα flux versus R, and whether
  the I-band maxima keep sinking.
- **H3 (0.20): an optical-depth cycle of the pre-existing dust shell**, distinguished from H1 by the absence of new warm dust.

## Predictions (P1-P3, registered in the case; not yet on the public ledger)

- P1 (0.7): AAVSO V median over 2027 Jun-Dec fainter than 13.35.
- P2 (0.6): Gaia DR4 G median over 2019 Jan-2020 Jan brighter than the 2014.6-2017.5 median by > 0.1 mag (the activity episode).
- P3 (0.6): the I-band maximum near 2027 Jun 19 makes the 2027 May-Aug I median > 0.3 mag brighter than 2026 Oct-Dec. **Superseded
  by P4** (0.65): timed from the observed 2023.15 and 2026.11 maxima the next one falls in 2027 Jun-Sep, window 2027 Jun 1 - Oct 1.

## For the advisor

The AAVSO B/V/R/I series from 2021 on are dominated by a few observers (DFS, GZN, PYG, BRJ; 89 contributors overall), so the
wavelength dependence rests on their filter calibrations; the Skeptic finds all bands moving together. The one measurement that
would settle H1 versus H3 is the mid-infrared: whether the 3-20 µm dust emission rose after 2021 (SOFIA is gone; JWST or a
ground-based N-band point would do). TESS is in (no flickering, above). ATLAS orange/cyan forced photometry 2015-2026 was still queued at writing; it will
give an independent record of the fade on nightly cadence.
