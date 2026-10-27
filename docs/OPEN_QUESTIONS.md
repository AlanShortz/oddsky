# For the advisor: decisions only an astronomer should make

Everything scientific in Oddsky v0.1 is a default chosen by a non-astronomer and an AI, written
down so you can overrule it quickly. In rough priority order:

1. **The seed cases.** `scripts/seed_cases.py` opens seven: ASASSN-21qj, Boyajian's Star, EE Cep,
   R CrB, R Cyg, SS Cyg, AA Tau. Chosen because the explanation is published, the AAVSO and
   NEOWISE coverage is good, and they span the taxonomy. Veto, replace, and above all add the
   ~20 odd/ordinary/misleading stars you would use to test a student.
2. **The taxonomy** (`src/oddsky/case/model.py: CLASSES`): dust_occultation, dust_formation,
   collision_debris, eclipse_companion, yso_dipper, pulsation, eruptive, rotation_spots,
   artifact_instrumental, artifact_blend, normal. Too coarse? Too fine? Is "collision_debris"
   distinct enough from "dust_occultation" to be fair in a blind trial?
3. **NEOWISE cuts** (`src/oddsky/data/neowise.py`): qual_frame>0, qi_fact>0, saa_sep>0,
   moon_masked=00, cc_flags=0 per band, ph_qual A/B, nb=1, SNR>=4, rchi2 < 5x the source's
   median, visits split at 30-day gaps, 4-MAD clip. Saturation flagged at W1<8, W2<7. Your DESK
   and NEOWISE experience trumps all of this.
4. **Skeptic thresholds** (`src/oddsky/skeptic/report.py`): beam radii (WISE 6.1", ASAS-SN 16",
   TESS 42", AAVSO 5"), blend warn at 10% of target flux / fail at 50%, the Gaia-baseline test
   (> 0.2 mag from the Riello+2021 G->V transformation), RUWE > 1.4.
5. **What counts as validated.** Draft in `docs/EPISTEMICS.md`: a sealed prediction coming true, or
   a professional review committed to the case. Should a single astronomer's review be enough?
6. **Trial design.** Hindsight cut dates, whether Gaia context should be shown in blind mode (it
   narrows the field a lot), and which famous stars are too recognisable to count.
7. **STScI.** Whether and how your name and affiliation appear, and any clearance needed before
   this is public. Nothing goes public until you say so.

## What Trial 001 taught us (decisions for you)

- **Famous stars leak through blinding.** Opus recognised 8 of 10. Trial 002 needs your ~20 stars,
  ideally including obscure ones with a known answer in a paper few people read, plus ordinary and
  misleading ones.
- **Our fake artifact was too fake.** Opus called out that the planted dips were smoother and
  longer than real momentum-dump glitches. If we keep "salted" packets, we should plant real
  artifacts cut from other stars' light curves, not synthetic Gaussians.
- **Is the taxonomy fair?** collision_debris vs dust_occultation was the hardest boundary for both
  models on ASASSN-21qj.
- **Hindsight trials are the strongest format.** The sky grades them, they can't be gamed by
  recognition alone (Opus still had to time the eclipse), and they reward calibration. Which of
  your stars have predictable futures?

## Data-source notes for you

- ASAS-SN Sky Patrol's light-curve service has been down for maintenance since 13 Oct 2026; the
  client degrades to "unavailable" and the optical record falls back to AAVSO, ZTF and TESS.
- For ASASSN-21qj the entire AAVSO record (7,115 B/V/R/I points, Aug 2021 to Oct 2026) is one
  observer, HMB (Franz-Josef Hambsch). The Skeptic flags the single-observer risk; TESS is the
  independent check.
