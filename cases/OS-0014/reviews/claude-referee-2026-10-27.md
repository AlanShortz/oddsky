# Referee report: OS-0014 (Gaia DR3 6733428488637673984 / AllWISE 2779036401351050434), "a Sun-like star with a new warm glow"

Referee: claude-referee, 2026-10-27.

**Claims in force:** C1, C3, C6, C7, C9, C11–C15.

**Retracted claims:**
- C2, replaced by C9.
- C4, replaced by C12.
- C5, replaced by C13 (the retraction note says C14 in error).
- C8 and C10, replaced by C14 (C10's note says C13 in error).

Call IDs refer to `ledger.jsonl`; my calls are K10–K42. Checks marked "outside the tools" used IRSA Gator, Gaia TAP, VizieR, ASAS-SN Sky Patrol or SkyMapper DR4 directly. Light curves are in `/tmp/osref`.

## Verdict

**The case survives, and the hunt undersold it.**

- **The IR step is real and on the star.**
- **The "odd visit" at MJD 57840 is the most important datum in the case.** It is NEOWISE catching the ingress of a ~95–100-day, near-total (≥99.5%) occultation of the star in March–June 2017. ASAS-SN and SkyMapper see the same event independently.
- **A warm excess (~650 K) appeared 6–12 months after the occultation ended** and has persisted to 2024.
- **The star is not demonstrably Sun-like.** It is a G0 dwarf, possibly a binary.

Confidence that both phenomena are astrophysical and belong to this system: ≥97%.

## Attacks and results

1. **NEOWISE systematics** (C1). Eighteen field stars within 150″ change by +0.010 (W1) and +0.018 (W2) mag across the onset (robust scatter 0.007). Per-visit zero-points are within ±0.02 mag. Not a field or calibration effect.
2. **Blends and confusion** (C9).
   - Centroid shift 0.011 ± 0.011″, so any culprit must lie within ~0.3″.
   - CatWISE has no other source within 15″.
   - unWISE has only a 0.4%-flux W1-only source at 12.6″.
   - Gaia neighbours within 6″ total 0.5% of G.
   - SkyMapper measured the faded star at its own Gaia position (within 0.17″), so it was the star that disappeared, not a neighbour.
3. **Saturation and flags.** None.
   - The 35% exposure loss is SAA proximity (70 of 299) and moon masking (36).
   - VarWISE's latent-artifact likelihood of 0.55 (C15) is overridden by the checks in item 4.
4. **The 57840 visit** (C3, C11, C12).
   - Over 14 exposures spanning 0.98 d, W1 falls monotonically from 1.15 to 3.65 mag below baseline and W2 from 0.41 to 2.03 mag below.
   - The star lands on different detector positions in successive scans, and field stars in the same frames are steady.
   - ASAS-SN V: normal to 57828, −0.11 at 57831, −2.76 at 57837, then undetected (>3.5 mag) from 57839 to 57911, back to 14.6 at 57923 and normal by 57933. All eight comparison stars are normal on the same nights.
   - SkyMapper (2017-05-25): 5.4–6.0 mag faint in v, g, r and i.
   - The ingress was chromatic (V deeper than W1, dW1/dW2 = 1.8–2.8). The depth at maximum is grey in the optical, which fits an optically thick core with a small-grain edge.
   - **This visit does not undermine the case. It turns it into a different and stronger one.**
5. **Geometry** (C12, inferred).
   - The ~6-d ingress implies ~3 km/s transverse speed. That is a lower limit for a soft or oblique edge.
   - The 95-d chord implies an occulter ≳0.15 AU across, orbiting at ≳1 AU (tens of AU if the edge is sharp). An eclipse in a 1.8-d binary is impossible.
6. **Stellar explanations** (C13).
   - Gaia RV: 4.7 ± 8.5 km/s, robust amplitude 51 km/s, p = 0 from 7 transits. Probably a spectroscopic binary, but duplicated_source = True and 7 transits leave room for a processing cause.
   - The 1.8-d TESS modulation is not securely on the target (TIC contamination ratio 0.41).
   - Dereddened, the star is on the F9–G0 main sequence.
   - Photospheric 2010–2017: AllWISE epochs match NEOWISE, W1−W3 = −0.18 ± 0.16, Ks−W1 = 0.02. No pre-existing disk, so not an ordinary YSO dipper, though youth is not excluded without lithium.
   - Not a Be star. A background AGN cannot occult.
7. **Excess** (C6; K19, K20).
   - Onset between MJD 58008 and 58204.
   - W2 excess 20% → 23%; T_BB 690 → 610 K; L_IR/L* ~ 0.005; variable.
   - A blackbody at that temperature sits at ~0.24 AU, inside the occulter's orbit. Small grains could sit farther out.
8. **Novelty** (C15).
   - Nothing in SIMBAD, VSX or the literature.
   - The 2017 occultation appears to be unreported. A >3.5-mag, 3-month disappearance of a V = 12.7 star is notable on its own.

## Most plausible explanation

A long-duration occultation by an extended, partly optically thick dusty structure, most likely a circumsecondary disk or dust envelope around an unseen companion. Analogues: ε Aur, EE Cep, Gaia17bpp and ASASSN-24fw. The warm excess that followed is probably related: material from the same system, a disturbed companion disk, or debris. The connection is not shown.

| Explanation | Probability |
|---|---|
| Companion-disk / dust-structure occultation, excess from the same system | ~45% |
| Collision-produced dust cloud transit, then warm debris (ASASSN-21qj-like) | ~20% |
| Binary-driven dusty outflow | ~10% |
| Occultation and excess unrelated, or unanticipated | ~23% |
| Instrumental or background | ≤2% |

## Wording requirements

- **Title and hook:** lead with the occultation. Suggested: "A G dwarf that vanished for three months in 2017, then began to glow in the infrared."
- Drop "Sun-like". Use "G0 dwarf, possibly binary".
- Never call 57840 an "odd visit" or glitch.
- Say "dust in the system". Temperatures are two-band colour temperatures (±200 K).
- Make no causal claim linking the occultation and the excess.
- Say "no TESS dips 2019–2025 in four sectors", not "no dips".
- The 1.82-d period is not attributable to the star yet.

## Decisive follow-ups

1. **Full archival optical record**, to measure eclipse depth vs colour and to look for recurrence or precursor dips:
   - ASAS-SN g (2018–2026);
   - ATLAS forced photometry (2015–);
   - DECam/SkyMapper images;
   - DASCH/APPLAUSE plates for historical eclipses (period estimate).
2. **Gaia DR4** (Dec 2026): epoch photometry during the event, epoch RVs, and an astrometric orbit if there is a wide companion.
3. **Spectroscopy:**
   - multi-epoch high-resolution RVs (SB1/SB2);
   - Li 6708 (age);
   - Hα (accretion or activity);
   - Na D and K I for circumstellar gas.
4. **SPHEREx** 0.75–5 µm spectra and mid-IR (VISIR, or JWST MIRI) to determine the excess temperature, silicate features and dust mass.
5. **Register predictions:**
   - no repeat within ~10 yr if the occulter is at tens of AU;
   - the excess stays on-source and continues to vary.
