# Referee report: Gaia20fgk (Gaia DR3 523457286761045120)

Referee: claude-referee, 2026-10-28. Mandate: docs/REFEREE.md. This is not an Oddsky case, so there are no claim or call ids. Every number below comes from my own queries. Scripts and downloads are in `fgk/referee/`. Anything done outside the Oddsky tools is marked [ext].

## 1. Verdict

The dimmings are real and belong to the target. Eight independent datasets put them at the Gaia position, including Gaia DR3 epoch photometry, which the investigators did not use. The probability that this is an artefact or a mis-identification is below 2%.

The framing does not survive: "a Sun-like dwarf hidden by an external, optically thick, nearly grey occulter". The star is a strong Hα emitter. It varies by 0.1–0.25 mag on hour timescales and by about 0.3 mag on a quasi-period of about 20 days in the bright state. Its GSP-Phot fit failed. Those are the marks of an accreting object.

The mundane explanation is that this is a known class of variable whose multi-year fades come from its own circumstellar or accretion behaviour:
- most likely a T Tauri or UXor-type "fader" with an edge-on disk (KH 15D is a special case of this);
- less likely a VY Scl nova-like cataclysmic variable (CV) in its low states.

**Probability that this mundane explanation is correct: about 0.7.**

## 2. Attacks and results

**1. Period and durations.** The proposed 9–10 yr quasi-period and the "shrinking durations" both fail.
- Every epoch sampled between 1991.7 and 2015.5 shows the star faint:
  - POSS-II F 1991.7: not detected.
  - POSS-II J 1994.7: +2.85 mag.
  - POSS-II N 1995.7: +1.75 mag.
  - 2MASS 1999.0: not detected.
  - WISE Feb and Aug 2010, PS1 2010.57–2014.63, NEOWISE 2014.1, 2014.6 and 2015.1, Gaia DR3 2014.75–2015.47: all faint.
  - There is no data at all for 1999–2010.
- The only bright-state measurements are 1954.7, 2015.6–2020.4 and 2024.0–2026.
- So the start of the "2010–2014" eclipse is unconstrained. The 1991–1999 faint phase lasted at least 7.3 yr if it was one event. "≥5.5 yr then ~3.7 yr, shrinking" has no basis.
- The low state covers most of the sampled time since 1991. No period can be tested.
- The 2010 eclipse ends at 2015.6, not 2014.9. Gaia DR3 epoch G (rejected_by_photometry = False): 19.61 (2014.75), 18.10–18.25 (2015.16), 17.70–17.92 (2015.27), 16.75–16.85 (2015.47), 16.50 (2015.55), 16.23 (2015.63).
- New: in the bright state, ZTF g and r both show a quasi-periodic modulation of about 20 days with about 0.3 mag peak-to-peak [ext, astropy LombScargle]:
  - r 2019 season: P = 19.87 d, white-noise false-alarm probability (FAP) 2e-16;
  - g 2019 season: P = 19.49 d, FAP 4e-16;
  - g 2018 season: P = 20.86 d, FAP 0.002;
  - it appears in separate ZTF fields (1839 and 807 at 19.2–20.2 d; 1840 at 15 d);
  - after 2024: P = 38.5 d, which is about twice 19.2 d;
  - the window-function peak is at 30 d, so the signal is not an artefact of the sampling.
- The 20-day signal could be rotation, dipper-type modulation or a binary period. Red noise means the true FAP is higher than these values.

**2. Instrument artefacts.** None found.
- PS1: all 26 detections that pass the investigators' cut (psfQfPerfect > 0.85) lie within 0.81" of the Gaia position (median 0.08"; the 0.81" one is a split objID in y, 2012.60), with psfQf ≥ 0.87.
  - The text cites "2012.86 g 22.1" and "2013.64 z 20.8". Both fail the investigators' own cut (psfQfPerfect 0.70 and 0.60; the g point has apFlux ≤ 0) and are absent from the CSV. Drop them from the text.
- DSS: I reproduced dss_phot.py exactly: O −0.16, E +0.14, J +2.85, N +1.75, F +6.42.
  - Proper motion is (−0.81, −2.35) mas/yr, which is 0.15" over 62 yr, so the plates cannot have the wrong star.
  - The G=14.87 giant 16.5" away is a compact image on all plates, with no halo at the target.
  - Three POSS-II plates from three different years agree, which rules out plate flaws.
- Gaia DR3 epoch photometry (0.1" resolution; not used by the investigators) independently shows the 2014–2015 egress.

**3. Blends and neighbours.**
- Optical: no contamination, for the reasons in attack 2.
- WISE: the G=18.5 star 8.8" W has W1 ≈ 15.0 (2010 single exposures; NEOWISE W1 14.9–15.1).
  - While the target is bright, NEOWISE separates that neighbour in only 1–5 of about 20 frames per visit. So the W1 baseline of 13.87 includes up to about 0.3 mag of neighbour light.
  - During eclipses the neighbour is separated in 13–21 frames per visit, so W1 depths taken against 13.87 are overstated by up to 0.3 mag.
- WISE in-eclipse W1 values are biased bright. The target is detected in only:
  - 4/21 frames (2014.6, median 15.09);
  - 1/21 (2022.6, 15.96);
  - 3/18 (2023.6, 15.12);
  - 7/14 (Aug 2010, 15.32).
  These are the upper envelope of the true brightness, not visit means.
- TESS: the G=14.87 giant is 0.8 px away and supplies about 85% of the flux in the aperture.

**4. "No X" claims.** All of them survive, with corrections.
- WISE Feb 2010: the 8.8" neighbour is detected in 16/16 frames at W1 15.0 ± 0.1. The target is detected in 0/16, so W1 ≳ 15.5 is a real limit.
- NEOWISE: the target is detected in 0/19, 0/20, 0/17 and 0/14 frames at 2021.0, 2021.5, 2022.0 and 2023.0. It is also undetected in 0/19 (2014.1) and 0/10 (2015.1), which the investigators did not report. The neighbour is detected in each of those visits.
- 2MASS: the target is in neither the point source catalogue (PSC) nor the reject table. Field stars are detected to J 16.8–17.0, including the 9" neighbour at J 16.16. Forced aperture photometry on the atlas image gives J S/N 2.2 (J ≈ 18.5) and Ks S/N 2.6 [ext]. Taking a conservative J ≳ 17.5 against an expected 14.8, the star was at least 2.7 mag deep.

**5. Physical self-consistency.** "Sun-like dwarf" fails.
- GSP-Phot gives [M/H] = −4.09. Only 0.1% of 3,738 field stars with G 15.5–17 within 0.6° get [M/H] < −4.0, so the BP/RP spectrum does not fit a normal photosphere.
- Gaia ESP-ELS Hα pseudo-EW is −0.72 nm, i.e. emission. The same field sample has median +0.17 and 1st percentile −0.23; the target is the most extreme 0.1%.
- My own calibration of the XP spectrum [ext, gaiaxpy in a temporary venv, since removed] shows a clear Hα emission peak about 1.4× the same-colour field stars at 656 nm (`referee/xp_compare.png`). There are possible Hβ and Hγ bumps.
- Absolute magnitude: M_G = 16.25 − 10.07 − 0.86 = 5.32. That is 0.6–0.9 mag below the main sequence (MS) for 5967 K (0.6 if AG = 1.2, the value for neighbours at 0.9 kpc).
- The bright state is not flat:
  - ZTF g rms 0.155 (errors 0.020);
  - Gaia transit pairs 1.8–6 h apart differ by up to 0.24 mag (median 0.077; errors 0.006);
  - Gaia alerts show 0.8 mag between 2020-05-14 and 2020-05-24.
- The dimming is not uniform:
  - ZTF r jumps 21.32 → 19.84 in 12 days inside the deep phase (2022.88–2022.91);
  - in egress, g swings by 0.7–1 mag within 1–2 days and r goes 17.78 → 16.80 in one day;
  - Gaia alerts drop back to 20.69 at 2023.37, between 18.8 (2023.30) and 18.1 (2023.60);
  - PS1 i changes by 1 mag between 2011.688 and 2011.691.
  That looks like clumpy material or accretion variability, not a sharp ring edge.
- "Nearly grey" holds in the optical but not as "optically thick":
  - at 2014.75, A_BP/A_RP = 3.98/3.38 = 1.18 (interstellar medium (ISM) ≈ 1.7);
  - ZTF A_i/A_g = 0.75 (ISM 0.53);
  - W1 depth is about 1/3 of the optical depth even after the biases above;
  - BP−RP is 1.82 at the deepest Gaia point, against 1.22 baseline.
  This fits partial covering plus scattered light.
- Classes excluded:
  - giants, RCB stars and symbiotics: parallax is 20σ and M_G ≈ 5;
  - an eclipsing binary with a luminous companion: the depth is more than 5 mag.
- Classes that fit:
  - YSO fader (UXor or AA Tau-like; analogues V1184 Tau, AA Tau after 2011, KH 15D, RW Aur). This is favoured: grey-ish fades, Hα, Galactic plane at b = +1.3°, and the 20-day modulation.
  - VY Scl nova-like. Hα, hour-scale flickering, M_G ≈ 5, and the Gaia DR3 classifier's best class is "CV" (score 0.31). Against it: the bright-state g−r, r−i and r−W1 fit a G0V reddened by E(B−V) ≈ 0.35, and deep-state colours are not M-donor red (BP−RP 1.82, not about 3).
  - GALEX AIS would have told CV from G star apart, but its only visit (2011-11-05) fell in the deep phase.

**6. Novelty.** Nothing found, but the checks are incomplete.
- Gaia20fgk = TNS AT2020zvx. Alert comment "~1 mag dimming in Gaia source", class unknown, no ATels or AstroNotes.
- Gaia DR3 flags it VARIABLE. vari_summary gives a G range of 3.8 mag (15.81–19.61); the classifier gives CV, 0.31.
- Web searches for Gaia20fgk, AT2020zvx, the source_id and J0108+6408 returned nothing.
- It is not in arXiv 2601.16828.
- arXiv 2508.03964 (Tzanidakis+ 2025, 81 main-sequence ZTF dippers): the target is not among the 31 Gaia IDs visible in the HTML, but the full machine-readable table was not checked.
- **SIMBAD, VizieR and VSX were still unreachable today.** All CDS mirrors (Strasbourg, CfA, IUCAA, NAOJ, China-VO) timed out; VSX returned 403 (Cloudflare). HEASARC cone search returned nothing even for a control field.
- Unchecked: VSX, SIMBAD, IPHAS DR2 r−Hα and the IPHAS emission-line list, Gaia/WISE YSO-candidate catalogues, ADS full text.

**7. Untapped data.**
- Gaia DR3 epoch photometry and XP spectra: fetched; the results drive attacks 1 and 5.
- TESS: sectors 18, 24, 25, 78 and 85 exist. None falls in the deep phase (2020.9–2023.5); S24–25 only catch the very start of ingress. The target is blended with the giant, and simple-aperture rms is 6–15%, dominated by systematics. No constraint [ext, TESScut].
- Not checked: ATLAS (forbidden today), ASAS-SN (too faint), APASS, IPHAS, LAMOST, other plate archives (DASCH and APPLAUSE are mostly too shallow for B ≈ 17.5).

## 3. Most plausible mundane explanation remaining

The source is an accreting, Hα-emitting young star (a T Tauri or UXor-type fader, seen nearly edge-on) whose own disk material covers it for years at a time. The probable underluminosity in the bright state (about 0.6–0.9 mag) fits the same picture.

KH 15D-like geometry is a sub-case. It would need a strict binary period during the partial phases, which nobody has shown. A VY Scl nova-like in long low states is the main alternative and is not excluded. In neither case is this a quiet Sun-like main-sequence dwarf eclipsed by an external body.

## 4. Required wording changes

**Title and figure.**
- "a Sun-like star hidden for years at a time" becomes "an Hα-emitting variable star at 1 kpc that fades by 3–5+ mag for years at a time".
- The "eclipse 2010–2014" shading becomes "≤2010.1–2015.6".
- Add the Gaia DR3 epoch points to the figure.
- Mark NEOWISE in-eclipse points with their detection fractions.

**Retract:**
- "Sun-like dwarf" and "reddened Sun-like dwarf". GSP-Phot is invalid here ([M/H] −4.09, Hα emission). Say "FGK-like colours, M_G ≈ 5.3".
- "durations shrinking (≥5.5 yr then ~3.7 yr)".
- "flat out of eclipse 2015.5–2020.3".
- "optically thick" (not demonstrated).

**Correct:**
- 2010 eclipse: start ≤ 2010.1, end 2015.6.
- History: "faint at every sampled epoch 1991.7–2015.5; bright 1954.7, 2015.6–2020.4, 2024–2026".
- NEOWISE: give n_det/n_frames per visit, and say that the in-eclipse W1 values are bright-biased and the baseline includes up to 0.3 mag from the 8.8" neighbour.
- PS1: drop 2012.86 g and 2013.64 z.

**Hypotheses.**
- Make "YSO fader / circumstellar disk extinction (KH 15D as special case)" H1.
- Add "VY Scl nova-like low states" as H2.
- Demote "long-period external disk occulter of a main-sequence star" to H3. A duty cycle of 50% or more in the low state is very hard for a disk around a companion.

**Novelty.** Add AT2020zvx, the Gaia DR3 VARIABLE flag and CV classification, and say that VSX, SIMBAD and VizieR were not checked.

**Ladder status.** "Confirmed real variable; nature unclassified; candidate". Not a discovery.

## 5. Decisive follow-up

Take one optical spectrum now, while the star is bright (g ≈ 17; 4000–7000 Å, R ≳ 2000, on a 2–4 m telescope). It settles the question:
- G-type metal lines plus Li I 6708 absorption, with Hα and [O I] 6300 emission, mean a YSO.
- Broad Balmer plus He I or He II emission with weak photospheric lines means a CV.
- Repeat radial velocities at a cadence of about 20 days to test KH 15D-type binarity.

Archival checks to run first, once CDS is back:
- IPHAS DR2 r−Hα (the field is inside IPHAS coverage);
- VSX and SIMBAD;
- the full machine-readable table of Tzanidakis+ 2025.

## 6. Tool fixes

- `oddsky.data.neowise` visit medians should report detection fraction (n_det/n_frames covering) and any other detections within 10" in the same frames. Visit medians built from 1–4 of about 20 frames are biased bright.
- Any "Sun-like" or "dwarf" label taken from GSP-Phot should be gated on mh_gspphot > −2.5, and ew_espels_halpha should be shown next to it.
- The Gaia DR3 epoch-photometry tool (`oddsky.data.gaia_epoch`) already exists. Make it part of the default fetch for every Gaia-alert candidate; here it moves the end of an eclipse and provides an independent confirmation.
- Before anyone writes "flat", "out of eclipse" or "baseline", require the out-of-eclipse rms to be compared with the photometric errors.
