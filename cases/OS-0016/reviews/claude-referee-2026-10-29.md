# Referee report: H-0007 candidate J040025.77+323527.4 (Gaia DR3 170329679884731008)

Author: claude-referee, 2026-10-29. Scope: the README section "The candidate" and `figures/J040025.png`.
Every number below was re-derived; scripts are in `reviews/claude-referee-2026-10-29/` (a1-a6.py; they run outside
the Oddsky tools, using pandas on the IRSA parquet plus my own Gator, Gaia TAP and GOST queries; a1 writes `/tmp/h7ref/ex.parquet`, which a2 and a5 read).

## 1. Verdict

The brightening is real NEOWISE photometry of this star. It survives every instrumental, association and
physics attack I could make, and no mundane explanation fits it: no artifact, blend, flare or companion outburst
reproduces a ×2.73, colour-neutral, centroid-locked brightening lasting ≥ 1 day. **Probability that a mundane
explanation is correct: 0.15.** Two things make up that 0.15. First, the prior is low: about 7% that this hunt would
find any A ≥ 2.7 event on an anticentre star (attack 4). Second, the event is unconfirmed outside NEOWISE. Two README
statements are wrong and must change: "tE ≳ 20 d" and "ZTF r rms 0.05" (section 4).

## 2. Attacks and results

**1. Instrumental (exposure level; a1, a2, a3, a4).**
- Event visit (visit 16, MJD 57992.559-57993.541): 13 exposures in 11 scans (85442a-85472a), frames 50-122. All have
  nb = 1, na = 0, cc_flags 0000, ph_qual AA, moon_masked 00 and sso_flg 0. qual_frame is 10 in 9 exposures and 5 in 4; the
  baseline visits have qual_frame = 5 in a similar fraction (0-64%).
- W1 = 10.034 (exposure scatter 0.015) against a 20-visit baseline of 11.126 (visit-to-visit scatter 0.008), so ΔW1 = −1.092 and the flux ratio is **2.733**.
  W2 = 10.132 against 11.219, so ΔW2 = −1.087 and the flux ratio is **2.721**. This confirms the README (2.731 / 2.716).
- Reduced χ² in the event visit has median 2.55 (W1), inside the 1.2-4.3 range of the baseline visit medians. The highest
  values are in the last exposure (8.9 W1, 6.0 W2), which is also the brightest W1 point.
- No second detection within 20" in any event exposure. There are 199 unassociated detections in the 90" cone during the visit,
  against 127-254 in other visits. All of them have W1 > 14.6 and none is within 20".
- **The 90" controls are weak:** 15 of the 18 controls have W1 > 14, and only three are brighter (ΔW1 −0.002, +0.016,
  −0.026). I replaced them with a 20' cone restricted to the event visit and the adjacent visits (Feb 2017, Feb 2018), using 34
  event frames. 211 stars with W1 < 12.5 were measured in all three visits. Median ΔW1 is +0.002 (MAD 0.005) for 26 stars at W1 6-10,
  and +0.002 (MAD 0.007) for 30 stars at W1 10-11, the target's own range. **The target is the only one of 211 stars with |ΔW1| > 0.3.**
  So there is no frame-level or magnitude-dependent calibration error.
- Latent or ghost: the brightest source within 20' is W1 = 5.8. A latent cannot land on the same sky position in 11 different
  scans and keep a stellar W1-W2. Excluded.
- Moving object: excluded. A solar-system body moves ≥ 1'/day at 90° elongation (even a 40 AU object moves about 70"/day
  from parallax), but the centroid stayed fixed to 0.03" over 0.98 d. Thermal emission would also make W2 ≫ W1. No sso_flg was set.
  The Moon was 4-5 days old (new Moon 2017 Aug 21) and far from 4h RA.
- The artifact mode that does exist at this position looks different. In visit 14 (2016 Sep), one exposure has nb = 2,
  W1 = 10.22, W2 = 11.27 and rχ² = 238: a deblend failure, one frame only, and strongly chromatic. Nothing like it occurs in visit 16.
- Across the hunt's whole brightening list (36 stellar events), J040025 is the only uncatalogued brightening of ≥ 0.5 mag on a
  normal cool star. That gives no sign of a population of similar artifacts, but it also caps any unknown artifact rate at about one per 3.5×10⁸ star-visits.

**2. Association (a1).** Gaia DR3 proper motion is (−1.22, −1.58) mas/yr, a negligible correction. After propagating it,
the event-visit mean centroid is (+0.013, −0.012)" ± (0.022, 0.011)", against a baseline-visit mean of (+0.006, −0.021)" ±
(0.019, 0.017)". The shift is < 0.06" (2σ). The extra light is 63% of the event flux, so its source must lie within **≈ 0.1"
of the giant**. The only Gaia neighbour within 15" is G = 19.6 at 6.35"; it would need a ~9 mag outburst and would have
moved the centroid by 4". Excluded.

**3. Physics (a1; Gaia TAP).**
- Colour. The star's own W1−W2 is −0.093 (the visit-to-visit scatter is 0.014, with a slow drift from −0.08 in 2014 to −0.10 in 2024).
  Colour change in the event visit: −0.001 against the all-visit median, −0.020 against the adjacent visits.
  Extra light with W1−W2 = 0, which covers any Rayleigh-Jeans source (hot flare, accretion disk, early supernova), would give Δ(W1−W2) = **+0.060**.
  Free-free emission (a nova or symbiotic outburst, W1−W2 ≳ +0.5) would give far more. The Rayleigh-Jeans case is excluded at ≥ 4σ. Only light with the giant's own colour fits, and lensing supplies exactly that.
- Luminosity. Parallax is 0.3295 ± 0.021 mas (about 2.9-3.0 kpc after the zero-point correction; GSP-Phot gives 3.39 kpc), A_V ≈ 1.08. The extra light
  is W1 = 10.53, i.e. M_W1 ≈ −1.8. A dwarf nova at peak has M_W1 ≈ +2 to +4, so it falls short by 4-6 mag. A flare would need about 0.6 of the giant's
  surface at 10⁴ K for ≥ 1 day, roughly 400 L☉ and ~10⁴¹ erg. A classical nova would be about V ≈ 6 and red in W1−W2. Excluded.
- Binarity and accretion. RUWE 0.99. ipd_frac_multi_peak 0, ipd_gof_harmonic_amplitude 0.03, astrometric_excess_noise 0, non_single_star 0,
  classprob_dsc binary 3×10⁻⁶. RV −22.0 ± 1.64 km/s over 23 transits. rv_chisq_pvalue and rv_renormalised_gof are null
  (G_RVS > 12), **so Gaia offers no RV-variability test here.** ESP-ELS Hα pEW is +0.015 nm (no emission). FLAME gives R = 8.0 R☉,
  L = 32.6 L☉, M = 2.7 M☉. **One flag:** the MSC two-star fit returns distance_msc = 382 pc with two K dwarfs, which is
  inconsistent with the parallax at 15σ; this is the expected MSC failure for a single giant, not evidence of a pair. There is nothing to suggest a symbiotic or a CV.
- Optical quiescence. ZTF catflags = 0 gives r rms **0.011** (869 points), g 0.017 and i 0.011. The README's 0.05 is the rms
  with flagged points included. That is good news for the claim: there is no quiescent flickering.

**4. Microlensing plausibility (a5, a6).**
- Point-lens fit to the 26 event-visit points plus the flat visits of Feb 2017 and Feb 2018 (χ²_min = 14.8 for 28 points).
  tE 95% range is **6-53 d** (median 22 d, log-flat prior). t0 is between −1 and +12 d after the visit, u0 is 0.28-0.39, and A_peak is ≤ 3.6.
  The README's "tE ≳ 20 d" is wrong. Near peak the slope constrains how far t0 is from the visit, not a lower limit on tE; tE = 6-10 d is allowed.
  W1 slope is −0.037 ± 0.011 mag/d (confirmed), but W2 is +0.002 ± 0.020 and the combined slope is −0.028 ± 0.010. The rise is a 2.8σ result.
- Rate. A double-exponential disk (thin + thick, ρ₀ = 0.043 M☉ pc⁻³) gives τ = **1.1×10⁻⁸** for Ds = 3.0 kpc at (162.8°, −15.3°).
  With tE = 20-40 d, Γ = 0.6-1.2×10⁻⁷ per star per year. The chance that one snapshot shows A ≥ 2.73 is τu² = 1.6×10⁻⁹, or 3.4×10⁻⁸ for this star over 21 visits.
  - For the hunt: 17.5 M quiet stars × 21 visits × 0.147 × τ̄. With τ̄ = 0.5-1×10⁻⁸, that is **0.3-0.5 expected A ≥ 2.7 events over the
    whole |b| ≥ 10° sample.** Restricted to anticentre-hemisphere stars at 1-5 kpc (about 3 M stars, τ̄ ≈ 8×10⁻⁹), it is about **0.07**.
  - So one event here is a 1-in-15 outcome: unlikely but not alarming.
- Comparison. Gaia DR3 4084984459435880064 (l = 14.9°, b = −10.6°, ~6 kpc) has τ ≈ 1.25×10⁻⁷, 12× higher, and was the expected kind of
  recovery. Gaia20fnr (A = 1.38) is below this threshold. It is also not a new NEOWISE result: the Gaia20fnr paper (arXiv:2601.15969) already uses
  NEOWISE.
- Anticentre events this bright do happen (Kojima-1 / TCP J05074264+2447555, Oct 2017, τ ≈ 2×10⁻⁹ by the same model).

**5. Novelty.**
- VSX (vizier.idia.ac.za, 120"): only Gaia DR3 170329508086043392, a ROT star at 59.6". TNS (60"): no objects.
- Gaia alerts (`../H-0005/alerts.csv`, 27,076 rows): the nearest alert is 45' away (Gaia23ahr, a YSO). There are 109 alerts within 10°, many of them YSOs in the Perseus/California clouds.
- Web search for the Gaia id and designation: no hits.
- ASAS-SN catalogue: asas_sn_id 17180188199 ([stellar_main, tic]). Its light-curve service is down for maintenance (notice dated 2026-10-13).
- Absent from all of these, but ASAS-SN and ATLAS, the two surveys that would have seen a 2017 event, are unread.

**6. Untapped data.**
- **Gaia scanned the star 5.3 days before the NEOWISE visit.** GOST transits: 2017-07-27 (FoVP+FoVF), **2017-08-22 04:47 and 06:34 UTC**
  (MJD 57987.20 / 57987.27), and 2017-09-18 16:35 (`reviews/claude-referee-2026-10-29/gost_2017jun-oct.csv`).
  - Point-lens predictions: Aug 22 **ΔG = −0.83** (68%: −0.95 to −0.52; P(ΔG ≤ −0.5) = 0.87), Sep 18 ΔG = −0.33, Jul 27 ΔG = −0.13.
  - P(any transit ≤ −1 mag) is only 0.12-0.18, so the lack of a Gaia alert (2017 threshold ~1 mag) is weak evidence against lensing (likelihood ratio ~0.85), not a refutation.
  - These transits fall after the DR3 cut-off (2017 May 28) and inside DR4 (to 2020 Jan).
- ATLAS task 5270459 was still at queue position 244 when I finished, so there is no ATLAS file to analyse.
- ZTF did not exist yet (it starts in 2018-03), and TESS, OGLE, KMTNet and K2 did not cover this position.

## 3. Most plausible mundane explanation remaining

None of the mundane explanations tested fits the data. What remains is an unknown NEOWISE single-exposure processing fault. It would have to hit one source
in 13 frames from 11 scans, scale W1 and W2 by the same factor, keep the centroid and leave 210 neighbours alone. No such
fault is known, and the hunt's own 3.5×10⁸ star-visits show no other example. I hold most of the 0.15 for this, plus a small share for a
same-colour, co-located transient I cannot think of.

## 4. Required wording changes

- Title: "a microlensing event toward the Galactic anticentre" should be "**a candidate** microlensing event …".
- "tE ≳ 20 d from the in-visit slope" should be: "a point-lens fit gives tE 6-53 d (95%) and peak within −1 to +12 d of the
  visit; the in-visit rise is 2.8σ (W1 −0.037 ± 0.011, W2 +0.002 ± 0.020 mag/d)."
- "ZTF (2018-2025, r rms 0.05)" should be "r rms 0.011 (catflags = 0)".
- "18 control stars in the same frames were unchanged" should become: "211 stars with W1 < 12.5 within 20', in the same frames, changed by
  +0.002 ± 0.007 mag (W1 10-11); the target is the only one beyond 0.3 mag."
- "Not in VSX, TNS or the Gaia alerts" should add: "ASAS-SN and ATLAS 2017 data not yet examined; Gaia observed it on 2017 Aug 22
  (no alert; predicted ΔG ≈ −0.8, below the alert threshold)."
- Add the expected-rate statement: about 0.07 such events were expected among anticentre stars in this hunt.
- The link `J040025.md` points to a file that does not exist. Write it or remove the link.
- Ladder status: **candidate**, which is correct. Not "discovery" until optical confirmation.

## 5. Decisive follow-ups

1. **Gaia DR4 epoch photometry (due Dec 2026)** for source 170329679884731008 on 2017-08-22 (MJD 57987.2). Point-lens models predict
   ΔG ≈ −0.8 (A ≈ 2.1), identical in BP and RP; flat would kill it. The Sep 18 point (predicted −0.33) then fixes tE.
2. Before DR4: ATLAS task 5270459 (2017 Aug-Sep, c/o, cadence ~2 d) and ASAS-SN Sky Patrol id 17180188199 once the service returns.
   A×2.7 at G = 14 means about 13 mag in V/g, far above the ASAS-SN limit. The light-curve shape over tE settles it.

## 6. Tool fixes

- `scripts/hunt_h0007_exposures.py`: controls drawn from a 90" cone are mostly 3-5 mag fainter than the target. Use a ≥ 15' cone restricted
  to the event visit and the adjacent visits (Gator `constraints="mjd between …"`), and report magnitude-matched controls (as in a3/a4.py).
- Replace slope-based tE claims with a point-lens grid fit that includes the flat neighbouring visits (a5.py).
- Add a GOST transit lookup (`gaia.esac.esa.int/gost`: POST GostServlet with a session cookie, then export.jsp csv) to `oddsky.data.gaia`. Then
  "Gaia didn't alert" can be checked against whether Gaia actually looked.
- `oddsky.data.asassn` needs `pyasassn`, which is not installed (`uv run --with skypatrol` works). The service also announces maintenance
  in its banner; put that text in provenance.
- Hunt READMEs should quote ZTF scatter after the catflags = 0 cut.
