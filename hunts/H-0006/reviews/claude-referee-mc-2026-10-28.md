# Referee report: H-0006 Magellanic Cloud "vanishing dust" pair

Referee: claude-referee (independent). Date: 2026-10-28.
Targets: **J053700.12-712445.9** (LMC) and **J010347.02-723643.0** (SMC). J160708.51-320101.1 is out of scope here; another referee is reviewing it.
There is no case yet, so there are no claim ids to cite. "Call" below refers to scratch scripts and downloads in `/tmp/referee_h0005_mc/` (data in `data/`). All of that work ran outside the Oddsky tools (direct IRSA Gator/TAP, the VizieR mirror at vizier.idia.ac.za, the OGLE archive, Gaia TAP through `oddsky.data.gaia`, and BigQuery).

## 1. Verdict

**J053700.12-712445.9 (LMC): mundane, P(mundane) = 0.90.** The star is a catalogued carbon-rich semi-regular AGB variable: OGLE-LMC-LPV-74526 = SHV 0537442 = MACHO 14.9219.38, Boyer+2011 class C-AGB, Gaia DR3 LPV with `is_cstar`. OGLE-III already shows a 4525 d (~12 yr) trend in this star with an I-band amplitude of 0.59 mag, and its Spitzer colour in 2005 was already lower than in 2010-16. So the 2016-22 decline is one swing of the well-known episodic dust variability of C stars, not a star losing long-held dust.

**J010347.02-723643.0 (SMC): mundane, P(mundane) = 0.95.** This is also a catalogued carbon-rich SR variable: OGLE-SMC-LPV-15813, P = 1159 d, Boyer C-AGB, Srinivasan+2016 C-AGB, Gaia DR3 LPV with `is_cstar` and ESP-HS class CSTAR. Its full history is a textbook carbon-star dust-obscuration episode. W1-W2 was about 0.0-0.1 in 2008-2010, rose to 0.34 by 2014, then fell back to 0.0. Over the same period Gaia shows the optical recovering by +0.8 mag in G between 2014.8 and 2016.5 as the colour excess fell (Spearman 0.81 between G and W1-W2).

**Novelty.** For both stars the identity and the mid-IR variability are already catalogued:
- OGLE, Gaia DR3 LPV, SAGE evolved-star classes, Riebel+2012 and Srinivasan+2016 dust-production fits.
- **VarWISE Pure (Paz+2026)**: LMC star as `lpv` with confidence 1.00, W2 amplitude 0.52; SMC star as `cv` (a misclassification), W2 amplitude 0.42.
- SIMBAD types, as relayed by VarWISE: LongPeriodV* and C*.

I found no paper that describes these two stars' 2016-22 colour decline specifically. That is a fact about one paper about one star, not a discovery.

## 2. Attacks and results

**1. Period and aliases (pulsation).** OGLE-III periods (Soszyński+2009, 2011):
- LMC: 452 d (I amplitude 0.67), 4525 d (0.59), 441 d.
- SMC: 1159 d (0.32), 134 d (0.07), 214 d (0.07).

Gaia DR3 LPV gives the LMC star 1/0.0273 = 36.6 d, which is spurious next to 452 d; the SMC star has no Gaia period. NEOWISE samples every ~182.6 d. A 452 d period falls close to the Nyquist frequency, so it should appear as visit-to-visit alternation inside a ~1900 d envelope, and 214 d aliases to ~1260 d. The NEOWISE colour tracks don't look like that:
- LMC: smooth from 0.32 (2016.3) to 0.03-0.07 (2022-24), with only ±0.02-0.04 alternation on top.
- SMC: falls monotonically over 18 visits, 0.34 (2014.8) to 0.00 (2023.3).

So aliasing does not create the trend, though it adds a few hundredths of jitter. **The trend is real stellar behaviour.** What it is (attacks 5 and 6) is the problem.

Two correctness points on the claim itself:
- **It was not a "~1 year collapse".** The colour declined over 6.4 yr (LMC, 2016.3-2022.7) and 8 yr (SMC, 2014.8-2022.8). Only the W2 brightness step was fast: 0.45-0.5 mag in ~1 yr in 2017-18, with W1 fading 0.3-0.35 mag alongside it.
- **The 2014-15 "baseline" is not when WISE first looked.** AllWISE per-epoch photometry (MEP) gives SMC W1-W2 = 0.09 (2010.3) and 0.125 (2010.8). Those are lower than the NEOWISE "baseline" of 0.26-0.34, so the SMC excess *appeared* after 2010 and then went away.

**2. Instrument artifacts.** I re-derived both light curves from 1245 (LMC) and 580 (SMC) `neowiser_p1bs_psd` single exposures with the standard cuts (`neo.py`). They reproduce the sky-pass trend to ≤0.01 mag.
- w1sat = 0 throughout; w2sat > 0 in 2 of 1245 LMC exposures; nb > 1 in 4 of 1245; cc_flags all 0000.
- W1 9.3-9.7 is >1 mag fainter than the NEOWISE W1 saturation onset (~8).
- Centroid is stable within 0.1". The small alternating offsets follow scan direction.

I re-ran the investigators' control and confirmed it: yearly median colour change among same-pixel stars is |Δ| ≤ 0.03, except +0.055 in SMC pixel 8326 in 2018. There is no instrument step.

Two sky-pass defects that don't affect the verdict:
- The sky pass dropped the 2014 visits: LMC MJD 56941 (W1-W2 = 0.354); SMC MJD 56784 (0.323).
- The sky-pass LMC point at MJD 58674.93 (n = 110, W1-W2 = -0.036) has **no exposure at all** in IRSA's single-exposure table within 10" between MJD 58600 and 58730. It is a phantom visit.

**3. Blends and neighbours.** CatWISE2020 shows no neighbour within 13.8" (LMC; nearest is 4.4 mag fainter in W1) or within 10.8" (SMC; nearest bright one is 3.6 mag fainter, at 12"). AllWISE nb = 1 for both, and Gaia RUWE is 1.03 for both. Confusion contributes <2%. Blending is not the explanation.

**4. "No X" claims.**
- **"Stayed near-photospheric since"**: true from 2021 to 2024.
- **"Lost long-held warm dust"**: false for the SMC star, whose excess first appeared after 2010 (attack 1). For the LMC star it is not established.

How I compared Spitzer colours with WISE colours:
- On 247 (LMC) and 261 (SMC) Boyer C-AGB stars within 40', W1-W2 (AllWISE) = [3.6]-[4.5] (SAGE) + 0.09 (NMAD 0.07-0.10).
- LMC star in 2005 (SAGE [3.6]-[4.5] = 0.12): this predicts W1-W2 ≈ 0.21, already between today's 0.05 and the 2010-16 value of 0.33-0.42.
- SMC star in 2008 (SAGE [3.6]-[4.5] = 0.003): this predicts W1-W2 ≈ 0.10, matching AllWISE 2010.

Both stars' excess therefore varied before NEOWISE.

**5. Physical self-consistency.**
- **These are not RSGs, R CrB stars or post-AGB stars.** They are ordinary C-AGB stars: J-Ks = 2.03 (LMC) and 1.48 (SMC).
- LMC: Lbol = 10,232 Lsun, Teff 3400 K, dust mass-loss rate 2.1e-10 Msun/yr (Riebel+2012, at the LMC distance).
- SMC: L ≈ 5,750 Lsun, Teff 3300 K (Srinivasan+2016).
- In Mbol that is about -5.3 and -4.7, typical for C-AGB stars and below the AGB tip.
- The 452 d period with 0.67 mag I amplitude rules out R CrB for the LMC star.
- The "luminous" in the claim should be read as "normal AGB".

**Is the timescale sensible?**
- R* ≈ 1.35 AU (LMC) and 1.1 AU (SMC).
- Carbon dust condenses at ~3 R* ≈ 3-4 AU.
- At 10-20 km/s (2-4 AU/yr), dust leaves the >800 K zone that sets W1-W2 (out to ~15-25 AU, with T ∝ r^-0.4) in ~3-8 yr.

The observed 6-8 yr colour decline is exactly the drain time of hot dust once production slows. Nothing exotic is required.

**Is the end state photospheric?** Today's colours are typical of a C-AGB star:
- LMC 0.03-0.07 against a local C-AGB median of -0.03 (84th percentile 0.10).
- SMC 0.00-0.03 against a median of -0.01 (84th percentile 0.14).

For C stars, "photospheric" W1-W2 is not 0. It depends on C2H2/HCN/C3 band strength, which changes with pulsation phase.

For the LMC star, W1 faded 0.37 mag and W2 0.6 mag. That fits removing dust that supplied ~28% of W1 and ~55% of W2 (1000 K dust), but a drop in stellar luminosity is equally possible (see the 4525 d term). The data cannot separate the two.

**6. Novelty.** Coverage of this check:
- **CDS SIMBAD/VizieR**: unreachable again, as were the CfA, NAO, IUCAA and Strasbourg mirrors.
- **vizier.idia.ac.za**: worked.
- **Matches found:**
  - 2MASS and IRSF.
  - SAGE IRAC (II/305).
  - Boyer+2011 (C-AGB, both).
  - Riebel+2012 (LMC: C type, Per 444 d, Amp 1.17).
  - Srinivasan+2016 (SMC: C-AGB, OGLE-SMC-LPV-15813).
  - OGLE-III LPV (both: SRV, spectral type C).
  - EROS-2 Spano+2011 (LMC: C-rich).
  - Gaia DR3 vari_long_period_variable (both `is_cstar` = True; best class LPV).
  - VarWISE Pure (both).
- **No match:** Jones+2017 SAGE-Spec, Groenewegen & Sloan 2018, Tisserand+2009 R CrB, Kontizas+2001, MACHO variables (II/247), Vijh+2009 SAGE variables.
- **Literature:** a web search finds no paper naming either star. Suh (2025, arXiv:2506.22100) analysed WISE/NEOWISE light curves of ~11,000 LMC C stars. I could not confirm whether the LMC star is in its tables or whether it discusses long-term colour trends.
- **Not checked:** SIMBAD bibliography, ADS full text, and the Suh 2025 tables.

**Base rate (BigQuery, `sky1_features`; LMC pixels 8256-8291, SMC pixels 8320-8335):**
- Population: n_visits ≥ 12, W1 8.5-11.5, colour_base 0.2-0.6, base_scatter_w2 < 0.05.
- 6 of 188 (3.2%) pass the hunt's exact fade cut. These two are not unique even within the MCs.
- Without the scatter cut, colour drops > 0.2 (35) and rises > 0.2 (44) are about equally common among 1004 sources.

Dust excess comes and goes in these stars about equally often in both directions. That is variability, not one-way dust loss.

**7. Untapped data.**
- **OGLE-III I/V, 1997/2001-2009:**
  - LMC I: 15.58 (2001) → 14.55 (2003) → 14.45-14.66 (2008-09). This is a ~1 mag recovery from an earlier faint state, which is the 4525 d term.
  - SMC I: steady at ~14.3 apart from the LSP, fainter in 2009 (14.81).
- **Gaia DR3 epochs (2014.6-2017.4):**
  - SMC: G 16.41 → 15.59, with BP brighter by ~1 mag and RP by ~0.7 mag. The star got bluer while W1-W2 fell from 0.34 to 0.19 and W1 held at 10.6. That is dust clearing from the line of sight, i.e. the end of an obscuration event.
  - LMC: only pulsation (G 15.5-15.9), no trend.
- **OGLE-IV:** light curves for MC LPVs are not public; OCVS ogle4 covers Cepheids, RR Lyrae and eclipsing binaries only.
- **ASAS-SN:** the client returned "unavailable".
- **ATLAS:** cannot see Dec -72 before the 2022 southern units, so it misses the 2017-18 step.
- **TESS:** not fetched. Both stars are I ≈ 14.4-14.7 in crowded 21" pixels, and FFI systematics wipe out multi-year trends.
- **MACHO:** not fetched.

## 3. Most plausible mundane explanation remaining

Episodic dust formation in carbon-rich semi-regular AGB stars: an obscuration event, then the shell drifting out and cooling.
- **SMC:** dust formed 2010-14. W1-W2 rose 0.1 → 0.34 while the optical dimmed by ~0.8 mag. Production then stopped. The optical recovered by 2016, and the hot dust drained over 2015-22.
- **LMC:** the same behaviour on the ~12 yr cycle OGLE already measured. The 2017-18 IR fade may also include a drop in stellar luminosity.

The phenomenon is well known for C Miras and SRs (Whitelock et al. 1997, 2006: obscuration events). Here it was simply seen in its declining half.

## 4. Required wording changes

- **Title/hook:** drop "lost their warm dust" and anything implying a rare one-way switch-off. At most: "two known Magellanic carbon-star LPVs show the decline phase of dust-obscuration cycles in NEOWISE".
- **"Luminous dusty evolved stars":** replace with "carbon-rich semi-regular AGB variables (OGLE-LMC-LPV-74526 / SHV 0537442; OGLE-SMC-LPV-15813)". Drop any RSG wording.
- **"Over ~1 year around 2017-2018":** retract. The colour fell over 6-8 yr; only the W2 flux step took ~1 yr.
- **"Long-held excess" / "excess when WISE first looked":** retract for the SMC star (W1-W2 = 0.09-0.12 in 2010, ~0.10-equivalent in 2008). For the LMC star, state that the 2005 colour was already intermediate.
- **"Photospheric":** say "typical C-AGB colour"; for C stars photospheric W1-W2 is not 0.
- **Ladder status:** both are **rejected as discovery candidates**. Optionally keep them as a worked example of the C-star false positive.

## 5. Decisive follow-ups

- **SMC:** already settled by Gaia DR3 epochs combined with AllWISE MEP and SAGE. Gaia DR4 epoch photometry (to 2020.0) would show whether the optical stayed bright through the 2017-18 W2 step; that would complete the obscuration picture, not rescue the claim.
- **LMC:** Gaia DR4 epoch photometry (2014.6-2020.0), with OGLE-IV photometry on request from the OGLE team. A brightening (dust clearing) or fading (luminosity cycle) in 2017-19 would decide the mechanism. Either outcome is mundane.

## 6. Tool fixes

1. **Veto LPVs and carbon stars before calling a fade "dust lost".** Join Gaia DR3 `vari_long_period_variable` (`is_cstar`), `vari_classifier_result` and OGLE LPV membership. Both stars would have been flagged in one query.
2. **Check the pre-baseline history.** Before any vanishing-dust claim, require the AllWISE MEP per-epoch colours (2010) and, in the MCs and other SAGE fields, the Spitzer IRAC colour with the +0.09 C-star offset. The 2014-15 NEOWISE baseline is not "first looked".
3. **Report the symmetric base rate.** Pair every "fade" query with the mirror "rise" query in the same population. Here they come out about 1:1, which means variability, not one-way loss.
4. **Fix two sky-pass visit defects:**
   - The phantom LMC visit at MJD 58674.93 (n = 110) has no counterpart in IRSA single exposures. Check `_read_release` for duplicate or misassigned rows across release partitions.
   - The 2014 visits are missing for both stars (LMC MJD 56941, SMC MJD 56784).
5. **Look the source up in VarWISE (IRSA `varwisepure`) automatically.** It is a 2-second TAP query and answers the "known mid-IR variable" question even when CDS is down.
6. **Make "colour" mean the colour change.** Phrases like "collapse over ~1 year" came from the W2 step, not the colour. Report the colour decline time separately from the flux step.
