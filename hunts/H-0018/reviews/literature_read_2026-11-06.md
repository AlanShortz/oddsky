# H-0018 literature read, 2026-11-06

Finding under test: Gaia DR3 astrometric orbits (`Orbital`, `AstroSpectroSB1`) lack orbits turning in Earth's sense; `parallax_error`
depends on orbital sense (near 1 yr and 2 yr; 1.30 at 700-800 d, about 1 at 200-250 d, below 1 near half a year); the two-year feature
vanishes for pseudo-circular solutions; the cut `parallax_over_error > 20000/P` converts this into missing orbits. Separately, a direct
test of a mean Galactic dipole of binary orbital angular momentum (limit about 1.9%).

Reading depth is stated per paper. "Grep" means the full PDF text was searched for: clockwise, counter-clockwise, anticlockwise,
retrograde, prograde, direct, sense, handed, chiral, ecliptic, hemisphere, cos i, signed, degenerate, degeneracy, parallax, one year,
1 yr, two year, 2 yr, and hits were read in context. Not every paper was read end to end. PDFs and text are in `/tmp/lit_h18/`.
Comments marked **[my note]** are my inference, not the paper's. No Gaia data were queried for this note.

---

## 1. The four required papers

### 1.1 Perryman 2026, Phys. Rep. 1150, 1 (arXiv:2509.10883)
First and only author is Michael Perryman; bibcode confirmed. 271 pp, about 241,000 words.
**Read:** whole text grepped; read in context §4.3.2, §7.24 intro, §7.24.1 Processing, §7.24.2 Resolved binaries (start), the stellar-masses
passage before §7.5, §7.26.4 Orbit inclination, the DR4 outlook. **Not** read end to end.
**On sense or degeneracy:** nothing on astrometric orbit sense. Zero hits: clockwise, cos i, handed, chiral, "1 yr", "2 yr". The 21
retrograde, 9 prograde and 6 "sense" hits concern asteroids, streams and halo dynamics, or are ordinary usage. The 18 ecliptic hits concern
scanning, parallax zero point, transits, asteroids or coordinates. It does not cite Butkevich 2018 (only Butkevich & Lindegren 2014 and Butkevich+ 2017).
§7.24.1 describes the solutions as "yielding the system's parallax and proper motion, the orbit inclination and its standard error".
§7.26.4 gives inclinations of individual systems only. This 271-page 2026 review does not mention the effect.

### 1.2 Lammers & Winn 2026, AJ 171, 18 (arXiv:2511.04673)
The brief says "et al."; there are two authors. Found by the ADS query given (1 hit). 27 pp.
**Read:** grep; read §3 intro and the mock-catalogue bias passage in §4.
**On sense or degeneracy:** none. The one ecliptic hit (§3): number of data points "depends on the star's ecliptic latitude (see Holl et
al. 2023b)". Orbit biases are unsigned: "a mild deficit of detected planets with nearly edge-on orbits (i ≈ 90°)", and "most planets with
e ≈ 0 end up with best-fit eccentricities of e ≈ 0.2 due to noise". Gaiamock is used, with cos i sampled uniformly; no hemisphere split.

### 1.3 Yahalomi et al. 2026, arXiv:2611.06915 (v1, 4 Nov 2026)
24 pp. **Read:** grep; read §1, §3.1.2, §3.2.1 (part), the reflex-motion section.
**On sense or degeneracy:** none. Both "sense" hits are node convention ("Reading the injected elements in the classical sense"). Both
"degeneracy" hits are the resoeccentric degeneracy. Orbits injected with "cos i ∼ U(−1, 1), so i ∈ [0°, 180°]" and GOST along-scan
parallax factors (§3.1.2). **[my note]** The catalogue keeps signed i and real parallax factors, so a hemisphere split of recovered orbits
would be a test, but only for substellar companions and at the DR4 baseline. Useful dates: "expected 2 December 2026"; baseline "2014 July
25 10:30 UTC to 2020 January 20 22:00".

### 1.4 Makarov 2025, ApJL 981, L23 (arXiv:2502.20553)
8 pp. **Read in full.**
**On sense:** sign is used only as a label: "0 and π (counterclockwise and clockwise face-on orbits)" (§2). His condition cos i + sec i = u/v
carries the sign of cos i. The all-sky distribution is reported as symmetric: "two symmetric bumps at 40° and 140°" (§3). No ecliptic or
hemisphere content (0 hits).
**On period:** "the large deficit of periods around 1 yr and a smaller deficit around 2 yr caused by the poor conditioning of the
12-parameter model (essentially, a positive correlation between parallax and orbital excursion)" (§3). This is the closest published
statement of a two-year feature in the actual DR3 catalogue. No link to sense or eccentricity.
**[my note]** All-sky symmetry does not conflict with the finding, because an Earth-sense deficit flips sign between ecliptic hemispheres.

---

## 2. Technical and pipeline sources

### 2.1 Butkevich 2018, MNRAS 476, 5658 (arXiv:1709.00290): closest prior art
10 pp. **Read in full** through §5 and App. A start (App. B-C not read closely). Theory only; predates DR3; no data.
- §3.1: "The orbital motion is direct, i.e. the host star and Earth revolve in the same direction, if iE < π/2, while the star proceeds in a
  reverse direction if iE > π/2."
- Eq. 22 links ecliptic inclination to catalogue elements: cos iE = −sin β cos i − cos β sin i cos(Ω − θ). Eqs. 25-26: iE = 0 requires
  i = β + π/2, Ω = θ + π. **[my note]** So Earth-sense means i > 90° (clockwise) in the north ecliptic hemisphere and i < 90° in the south.
  This is the hemisphere prediction in formula form, though he never states it, never tabulates it and never tests it.
- Eq. 29 is explicitly sense-dependent for circular orbits: a sin[πT(1−1/P)]/[πT(1−1/P)] term weighted by cos²(iE/2), and a
  sin[πT(1+1/P)]/[πT(1+1/P)] term weighted by sin²(iE/2).
- §4.3: "for iE > 90° the correlation decreases since the star and Earth revolve in opposite directions."
- §5: "These effects are significant for orbits with low eccentricity (e ≲ 0.5) and period 0.8 ≲ P ≲ 1.2 yr."
- Abstract: "the Earth's motion has no effect on detectability for e ≳ 0.5"; "Selection effects against one-year period systems is therefore
  expected."
- Treats parallax **bias** and detectability via χ², with position and proper motion assumed known and continuous sampling. No covariance
  of a 12-parameter fit, no `parallax_error`, no two-year term, no half-year term. App. A: the tangent-plane factor sin²ν "is omitted".

**[my note]** Evaluating Eq. 29's two envelopes (not in the paper): at T = 34 months, 730 d gives 0.22 direct against 0.05 retrograde; 183 d gives
0.06 against 0.04; 365 d gives 1.0 against 0.05. So a circular orbit carries a small finite-baseline sense term at two years (|ρ| ≈ 0.2 implies
about 2% in error), and his formula has no half-year sign reversal. Also, Eq. 22 needs the true node; astrometry alone leaves Ω ambiguous by
180°, so hemisphere-signed cos i is the −sin β cos i piece only.

### 2.2 Halbwachs+ 2023, A&A 674, A9 (arXiv:2206.05726)
16 pp. **Read:** §5.2, §5.3, §7, Table 1, App. A definitions; rest grepped.

**§5.2, exact sentences verified:**
- "Preliminary calculations showed that the eccentricities below 0.006 were all at least three times smaller than their uncertainties."
- "In order to limit these effects, orbits with eccentricity less than 0.0005 have been "pseudo-circularised" in the following way: The
  Campbell elements were derived, and the periastron longitude, ω, was set to 0 in order to place the periastron on the ascending node."
- "After these transformations, the solution is based on only 10 unknowns: e and T0 are fixed, and only 3 of the 4 TI elements remain,
  since ω = 0 implies that G = −AF/B, or F = −BG/A."
- "Thus, the solution variance-covariance matrix was recalculated for the 10 selected unknowns. This 10 × 10 matrix was inserted into the
  12 × 12 matrix of orbital solutions, setting the unnecessary terms to 0."

The brief's description is **verified**, with two refinements. (i) e is fixed at its fitted value, not zero. DR3 docs §7.2.5: "not by
circularising them, but only by fixing the eccentricity and by shifting the periastron to the ascending node"; "e is considered as fixed to
its initial value"; "in reality, the uncertainties and correlations of e and G are not zero nor NaN"; identify them by "eccentricity_error
is NaN". (ii) It is a post hoc transformation of the same fit, not a refit.

**Cuts, exact wording:**
- §5.3 Eq. 16 is printed with an equals sign: "This filter consists of selecting only the solutions that satisfy the following condition:
  ϖ/σϖ = 20 000/Pd" and "it allowed to keep 179 234 astrometric orbits as a result of the main processing". Table 1 and the DR3 docs (Eq. 7.22)
  give it as ">".
- "A filter based on the quality of the eccentricity: σe < 0.079 ln P − 0.244, where P is in days."
- "A filter based on the significance: s = a0/σa0 > 158/√P, where P is again in days."
- Table 1 "Other" column: σe cut for eccentric solutions, **"-" for circular or pseudo-circular**. Significance floor is max(5, 158/√P).
- Table 1 footnote: "These selection conditions do not apply to orbital solutions from main processing when they have been confirmed by a
  SB1 spectrocopic solution, as explained in Gosset et al. (2022)."
- §5.3: "nearly 30 950 combined orbits, of which about 2470 were recovered after having been rejected by the post-processing."
- Gaia Collaboration 2023a §2.3 (checked on the rendered page, since text extraction misplaces the root): parallax S/N > 20000/period, s > 5 and
  s > 158/√period, eccentricity_error < 0.182 log10(period) − 0.244. Consistent, since 0.182/ln 10 = 0.079.

**Sense:** App. A: "i ∈ [0, π/2] when the orbital motion is in the direct sense, and i ∈ [π/2, π] when the photocentre is revolving around the
barycentre in a clockwise direction." **Degeneracy:** §7: "the lack of one-year periods, which comes from a degeneracy between parallactic
and orbital motion, is expected to remain." Motive for the cut is removing false solutions at scan-law periods; no mention of sense or hemisphere.

### 2.3 Holl+ 2023, A&A 674, A10 (arXiv:2206.05439): eccentricity floor
32 pp. **Read:** grep; §4 priors, §6.1, §6.2.4. **No eccentricity floor stated.** DE-MCMC: "starting values for e are drawn from a Beta
distribution". GA prior: "a truncated normal distribution for the eccentricity (with µ = 0, σ = 0.3, truncated over [0, 0.985])" (§4.2). This pipeline
is the `OrbitalAlternative*`/`OrbitalTargetedSearch*` chain, not the Halbwachs one that made `Orbital`. Unsigned remark only: cos i "rather flat"
(§6.1.4). §6.2.4: "period aliases corresponding to e.g. 1 year, 6 months, the 63-days precession period". No sense content.

### 2.4 Holl+ 2023, A&A 674, A25 (arXiv:2212.11971)
53 pp. **Read:** grep; §2.1, §5.4.2. §2.1: "Depending on the ecliptic hemisphere, this gives a negative or positive slope" (scan-angle rotation with time,
a hemisphere-signed scan-law property, not about orbits). §5.4.2: a constant offset "effectively traces out a circle on the sky and always results in
orbits with a period of 1 yr with an extremely high orbital significance (> 10⁶) and eccentricity of about 0.033. This is twice that of the Earth's
orbit". No orbit-sense statement.

### 2.5 Gaia Collaboration (Arenou+) 2023a, A&A 674, A34 (arXiv:2206.05595)
57 pp. **Read:** §2.3, §3 intro, §3.1-3.2, §4.1, App. D; figure 11 inspected; rest grepped.
- §3: "the period distribution of astrometric orbits shows a prominent lack of solutions around one year, which was expected for long due to the
  difficulty to decouple the orbital from the parallactic effect." Footnote 5: "crosstalk with parallax or scan-angle dependent effects".
- Fig. 11 plots **signed** cos i from −1 to 1, but all-sky; it looks symmetric by eye. No hemisphere split anywhere (the single "hemisphere" hit is
  an ESO acknowledgement).
- App. D.1: "The apparent dearth of face-on configurations for Orbital solutions (Fig. 11) is therefore the consequence of extracting the
  Thiele-Innes parameters A, B, F, G from noisy data." Their simulation uses real time sampling and scan angles but the orbit signal alone ("neglecting proper and
  parallactic motion", §3.2), fitting only A, B, F, G. **[my note]** So it cannot contain the effect.
- App. D.2: the ω modulation comes from "the application of an ω-independent significance threshold", a published cut-as-selection result but for ω, not sense.

### 2.6 Babusiaux+ 2023, A&A 674, A32 (arXiv:2206.05989)
**Read:** §6 NSS; rest grepped. Zero hits for ecliptic, sense, clockwise, cos i. §6.1: "The covariance matrix for very low eccentricity solutions may be problematic.
In these cases, the eccentricity and periastron time should be set to zero." §6.2: "proper motion and accelerations may both have absorbed the orbital motion."

### 2.7 Selection-function papers
- **El-Badry+ 2024, OJAp (arXiv:2411.00088), gaiamock.** **Read:** §4 cuts, §5.1, §5.4; grep. "binaries with periods near one year have large parallax
  uncertainties – because their orbital motion is degenerate with parallactic motion – and are almost all eliminated by Equation 20"; "eccentricity breaks the
  degeneracy between parallax and orbital motion". Fig. 5 compares signed cos i all-sky. Footnote 6: "33467 of the astrometric orbital solutions published
  in DR3 are AstroSpectroSB1" and an accepted Orbital solution "was a necessary prerequisite". §5.4: "a reversal in Gaia's precession during 2019-2020
  (including the last 6 months of data included in DR4...)"; "The "hole" near Porb ≈ 1 year is also predicted to become progressively narrower in DR4 and DR5."
  **This is the parallax-cut channel, published, for period only.**
- **Lam+ 2025, ApJ 987, 215 (arXiv:2411.00654).** **Read:** §4.4, §5.2.3, §5.3; grep. §5.2.3: the cut "preferentially removes solutions with Porb ≈ 1 year because these
  sources have a very low ϖ/σϖ, due to the large errors from the degeneracy between parallax and orbital motion." Inclinations "uniform in |cos i|", so unsigned.
- **Andrews+ 2019, ApJ 886, 68 (arXiv:1909.05606).** **Read:** §3-4; grep. "a decreased sensitivity around orbital periods of a year and two years... This is due to a
  partial degeneracy between parallax and orbital motion close to these periods (see also Butkevich 2018)." **The simulated orbits have e = 0.01** with fixed I = Ω = ω = π/3, one sky field, and a
  full MCMC fit. **[my note]** So a two-year dip is published at near-zero true e with e free in the fit. That points to the floating parameter rather than large true eccentricity. No sense test possible with fixed geometry.
- **Penoyre+ 2022, MNRAS 513, 2437 (arXiv:2111.10380).** **Read:** §4.3; grep. "periods close to 1 year (or harmonics thereof), orientations aligned such that their motion
  mimics the parallax ellipse (itself set by the position of the source in ecliptic coordinates) and eccentricities close to zero". Sense implied, not stated. Cites Butkevich.
- **Penoyre+ 2020, MNRAS 495, 321 (arXiv:2003.05456).** Passages only: binaries near one year "can mimic parallax". No sense.
- **Yamaguchi+ 2018 (arXiv:1710.09839).** §4.2: degenerate "when the orbit is circular (the same as Earth orbit) and the inclination angle is equal to the ecliptic latitude". No sense; "such case must be rare".
- **Perryman+ 2014, ApJ 797, 14 (arXiv:1411.1173).** App. A: "orbital motion with a period close to 1 yr may be absorbed by the parallax parameter."
- **Holl+ 2022, A&A 661, A151 (arXiv:2109.02647).** Footnote 3 cites Lattanzi+ 2000, Butkevich 2018, Sozzetti+ 2010 for the 1 yr exception.
- **Liao+ 2026, A&A 710, A398 (arXiv:2605.25482).** Fig. 2 caption: "degeneracies caused by orbital periods of half a year and one year". No sense.
- **El-Badry+ 2024, OJAp (arXiv:2405.00089).** §5.1 "Inclination sign degeneracy": +i against −i, "A, B, F, and G depend only on cos i, an even function". **[my note]** This is the node/line-of-sight flip, not the sign of cos i; do not confuse the two.
- **An+ 2025, ApJS 280, 61 (arXiv:2508.08374).** "inability to distinguish prograde from retrograde orbits" in Hipparcos-Gaia plus RV fits. Fitting ambiguity, not a catalogue asymmetry.
- **Müller-Horn+ 2026 (arXiv:2510.05982), El-Badry 2025 (arXiv:2504.11528), Stevenson+ 2023, Wen+ 2026 (arXiv:2609.09631), Sandave & Garani 2026 (arXiv:2609.24321), Marcussen & Albrecht 2023:** grep only.
  The first two state the one-year degeneracy; none has sense or hemisphere content.

### 2.8 Hipparcos
No Hipparcos paper found that discusses orbit sense or one-year degeneracy by sense.
- **Pourbaix & Arenou 2001** (astro-ph/0104412) and **the Reprocessing Hipparcos IAD II paper** (astro-ph/0211483): grep only; no sense or one-year content. The second's arXiv listing is by title; authors not confirmed from the text I read.
- **Goldin & Makarov** (astro-ph/0611885, the 2006 ADASS proceeding only): grep; nothing relevant.
- **Glebocki 2000** §2.1 (read pp. 1-3) on the Hipparcos DMSA/O sample: "There is an obvious deficit of binaries with |cos i| ≅ 1", citing ESA 1997 Fig. 3.2.118. Also "for retrograde (clockwise) apparent motion 90° < i ≤ 180°". No ecliptic split.

### 2.9 Other
- **Hogg research blog, 27 Jul 2025** (WebFetch summary, not a paper): El-Badry seminar noted no sensitivity near one year; Hogg sees an exact degeneracy for one specific one-year orbit and asks whether the missing binaries should be sought. The fetch summary says it does not discuss orbit direction.
- **Gaia DR3 known issue, "NSS: False-positive astrometric binary solutions"** (5 May 2023, updated 27 May 2024; via WebFetch summary): a software bug found during DR4 validation made four orbits false positives. Not related to sense on the evidence read.

---

## 3. Verdict

"Published" requires an actual statement, not an implication. Absence is limited to what I searched: ADS full text and arXiv, not journals' paywalled text or very recent preprints.

| Item | Verdict | Nearest source |
|---|---|---|
| (a) Signed asymmetry by ecliptic hemisphere measured in Gaia data | **Not found** in data. Mechanism and geometry partially published | Butkevich 2018 Eqs. 22, 25-26 (theory). Signed cos i only all-sky: Gaia Collab 2023a Fig. 11; Makarov 2025 Fig. 2; El-Badry+ 2024 Fig. 5 |
| (b) Sense-dependent published parallax errors | **Not found.** Period-only errors published; sense-dependent parallax *bias* in theory | El-Badry+ 2024 §4; Lam+ 2025 §5.2.3 (errors, no sense). Butkevich 2018 (bias, no errors) |
| (c) Two-year feature / e link | **Partially.** Two-year deficit published; link to e not found; sense at two years not found | Makarov 2025 §3; Andrews+ 2019 §4; Penoyre+ 2022 §4.3 "(or harmonics thereof)" |
| (d) Pseudo-circular comparison | **Not found.** The definition is published; nobody uses it as a test | Halbwachs+ 2023 §5.2; Gaia docs §7.2.5 |
| (e) Parallax cut as selection channel | **Partially.** Published for the one-year period hole; not as a sense or hemisphere channel | El-Badry+ 2024 §4; Lam+ 2025 §5.2.3 |
| (f) Galactic dipole of binaries measured | **Partially / not found.** Pole-isotropy tests on small samples; all-sky sign test with no Galactic split; no Gaia dipole found | Glebocki 2000 (252); Agati+ 2015 (51); Makarov 2026 §3 |

**On (f):** Makarov 2026 (AJ 171, 79; arXiv:2512.25002) §3, on 103,169 Gaia DR3 pairs: "The values on ν have sign, which only reflects the sense of orbital motion in the sky plane"; "As expected, there is no asymmetry in the sense of rotation for this sample." The word "Galactic" does not occur in the paper. **[my note]** A Galactic dipole flips sign across the Galactic plane, so all-sky symmetry says nothing about it. This is the same observable as the H-0018 test, so it should be cited. He assumes isotropy rather than testing it.

---

## 4. Points that qualify or cut against the finding

1. **`AstroSpectroSB1` may be exempt from the cut.** Halbwachs Table 1 footnote says the selection conditions "do not apply" to solutions confirmed by SB1, and §5.3 says about 2470 were "recovered after having been rejected by the post-processing". The two passages are not clearly consistent about whether Eq. 16, applied in main processing, is waived or only the σe and significance post-filters. If waived, the `AstroSpectroSB1` deficit (README objections table) would not be driven by the cut in the way `Orbital` is. **Checkable:** count `AstroSpectroSB1` rows with ϖ/σϖ < 20000/P. Not done here.
2. **The pseudo-circular comparison is not a clean test of true eccentricity.** These are the same fits with e and T0 conditioned out of the covariance; true e is not established ("always much greater than 0.0005" for σe, docs). They also skip the σe filter (Table 1), so their selection differs. "Vanishes" supports "floating e and T drive it" but cannot separate that from selection. Andrews+ 2019 (e = 0.01, dip at two years) favours floating parameters over true e.
3. **Near one year, the literature has eccentricity *reducing* the effect** (Butkevich §4.3; El-Badry+ 2024; Penoyre+ 2022 "eccentricities close to zero"). **[my note]** No contradiction with an e-linked two-year term, since the mechanisms differ, but anyone reading those lines will ask.
4. **Half-year reversal: no support found.** Liao+ 2026 and El-Badry+ 2024 note a half-year feature, unsigned. Butkevich's Eq. 29 has no such reversal. Unconfirmed by literature, not contradicted.
5. **Other named causes of inclination structure:** Gaia Collab 2023a App. D and Makarov 2025 explain the face-on deficit by noise in Thiele-Innes parameters, which is symmetric in sign. It does not produce a hemisphere sign, but any hemisphere analysis sits on top of it.
6. **Motive of the cut.** Halbwachs, Gaia Collab 2023a and DR3 docs all present it as removing scan-law false solutions. Holl A25 attributes most spurious periods to close pairs at fixed position angle. Near the cut, fakes remain the alternative reading (already flagged in the README).

Nothing read contradicts the sign of the effect or the geometry. Butkevich's Eq. 25 gives the same hemisphere mapping.

---

## 5. DR4 facts

| Question | Answer | Source |
|---|---|---|
| Release date | 2 December 2026 | cosmos.esa.int/web/gaia/release; Yahalomi+ 2026 |
| Time span | "between 25 July 2014 (10:30 UTC) and 20 January 2020 (22:00 UTC) spanning a period of 66 months"; reference epoch J2017.5 | cosmos.esa.int/web/gaia/dr4 |
| Reversed precession | 16 July 2019 to 29 July 2020 (2019.536-2020.576); data segments DS6 and DS7 | Lindegren+ 2021 (arXiv:2012.03380) §6.4, App. B; Gaia Collab 2021 (arXiv:2012.01533) |
| Reversed time inside DR4 | About 6.2 months (my arithmetic); "the first 6 months of the reverse precession period" | Gaia Collab 2021; Halbwachs §7 |
| `nss_two_body_orbit` rows | 5,901,111 ("under development", last update 14 Sep 2026) | dr4 page table |
| Epoch astrometry | `epoch_astrometry` for all main-processing sources, 129,625,750,708 records by DataLink; `nss_epoch_flags` new | dr4 page table |
| NSS parallax errors | **Yes**: `parallax`, `parallax_error` columns | Draft data model (26 Jun 2026) §10.8 |
| Thiele-Innes | **Yes**: `a/b/f/g_thiele_innes` with errors, plus `correlations` and `bit_index` | same |
| Campbell elements | Columns in the draft: `inclination`, `arg_periastron`, `pos_ascending_node`, `semi_major_axis` with errors; the `inclination_error` text mentions astrometric binaries. I did not check which are filled per solution type | same |
| Pseudo-circular | Kept: "For orbits with small eccentricities (eccentricity < 0.0005 and eccentricity_error is absent, the standard error will be null to indicate that the orbit has been made pseudo-circular." | same |
| New low-significance type | "OrbitalPoorlyConstrained: Orbital model for an astrometric binary but with low significance (< 5)" | same |
| NSS cuts | **Not stated.** No 20000/P or equivalent in the 1231-page draft (grepped) or on the DR4 page. "Gaia Data Release 4: Astrometric binaries" is listed on the papers page, with no link that I could find | cosmos.esa.int/web/gaia/dr4-papers |
| One-year hole in DR4 | Halbwachs: "expected to remain". El-Badry+ 2024: "progressively narrower" | |

**[my note]** Evaluating Butkevich Eq. 29 at T = 5.5 yr: the 730-d direct envelope falls from 0.22 to 0.08. Whether the two-year term shrinks depends on the e-linked mechanism, which no paper treats. A forecast needs the actual cut, which DR4 documents do not yet give.

---

## 6. Numeric facts

| Fact | Value | Status | Source |
|---|---|---|---|
| Bovy 2017 Oort B | −11.9 ± 0.4 km/s/kpc (A = 15.3 ± 0.4; C = −3.2 ± 0.4; K = −3.3 ± 0.6) | Verified, full text | MNRAS 468, L63; arXiv:1610.07610 |
| Li+ 2019 Oort B | −13.4 ± 0.1 km/s/kpc (A = 15.1 ± 0.1; C = −2.7 ± 0.1; K = −1.7 ± 0.2) | Verified from **ADS abstract only** | ApJ 872, 205 |
| Glebocki 2000 | 252 visual binaries | Verified, p. 1 abstract scan | AcA 50, 211. "orbital planes do not show any trend to be parallel to the Galactic plane"; asymmetry "only for a subgroup of 19 binaries lying closer than 10 pc" |
| Agati+ 2015 | 51 systems with resolved node, of 95 | Verified | A&A 574, A6: "the pole ambiguity could be resolved for 51 systems". False-alarm 0.5% for 20 systems within 8.1 pc, vanishing to 18% for all 51. Abstract says 95 "closer than 18 pc"; its Table 1 caption says 20 pc |
| DR3 `Orbital` | 134,598 | Verified | Gaia Collab 2023a Table 1 |
| DR3 `AstroSpectroSB1` | 33,467 | Verified | same; El-Badry+ 2024 fn. 6 |
| Sum check | 168,065; adding `OrbitalAlternative*` 629 and `OrbitalTargetedSearch*` 533 gives 169,227, the number Perryman 2026 §7.24.1 quotes | Verified | arithmetic |
| El-Badry+ 2021 rows | 1,817,594 pairs (candidates, including chance alignments) | Verified | MNRAS 506, 2269, Table 1; Zenodo 4435257 ("1,817,594 rows and 217 columns") |
| El-Badry+ 2021 R cut | R < 0.1 defines "high bound probability"; 1,256,400 pairs; "approximately to > 90% probability of being bound" | Verified; the paper *defines* this subset rather than using the word "recommend" | §3 and Table 1. R < 0.01: 1.15 M. Column name `R_chance_align` |

---

## 7. What I could not read

- **Holl 2011 technical note** (GAIA-C3-TN-LU-BH-003, "Astrometric planet detectability with Gaia, a short AGISLab study"). Found at dms.cosmos.esa.int/COSMOS/doc_fetch.php?id=3097428 but the server returned "This function is currently unavailable". I know only that Butkevich 2018 credits it, and a search snippet saying it studied circular orbits. Whether it splits by sense is unknown.
- **Holl, Lindegren & Hobbs on parallax-orbit:** I found no such paper. Holl+ 2012 papers (A&A 543, A14/A15, MNRAS 422, 2786) are error-covariance and CCD-damage work by title; not read. Holl's 2012 thesis not obtained.
- **Exoplanet Handbook (Perryman 2018):** not accessible; publisher and bookshop pages only. ADS confirms it cites Butkevich 2018; the section is unread.
- **Pourbaix 2000, A&AS 145, 215:** ADS abstract only (scan and A&A fetches blocked). **It is not a Hipparcos orbit paper**: its title is "Resolved double-lined spectroscopic binaries: A neglected source of hypothesis-free parallaxes and stellar masses". The brief's description looks like a different paper; Pourbaix & Jorissen 2000 (A&AS 145, 161) may be meant, also blocked.
- **Li+ 2019 full text:** IOP blocked; abstract only.
- **Gosset+ 2025** (arXiv:2410.14372): grepped for combination rules only; did not resolve point 4.1. DR3 docs §7.7 fetch did not return usable text.
- **DR4 processing papers:** titles only. Draft data model has column definitions, not selection rules.
- **Lattanzi+ 2000, Sozzetti+ 2010, ESA 1997 Vol. 3 Fig. 3.2.118:** cited by others, not read.
- **Not read end to end:** Perryman 2026, Halbwachs, Holl A10 and A25, Gaia Collab 2023a, Babusiaux, Lammers & Winn, Yahalomi; see each entry.

## 8. Searches run

ADS (full-text and abstract, 2018-2026 unless noted), about 30 queries, including: `full:("Gaia" "astrometric orbits" "ecliptic" "inclination") full:(clockwise OR retrograde OR prograde)`; `full:("nss_two_body_orbit" "ecliptic" "hemisphere")`; `full:("nss_two_body_orbit" "ecliptic latitude" "inclination")`; `full:("Gaia" "orbital motion" "parallactic" "same sense")`; `full:("Gaia" "binary" "absorbed by the parallax")`; `full:("orbital sense" Gaia astrometric)`; `full:("Earth-sense" OR "same sense as the Earth")`; `full:("hemisphere" "cos i" "Gaia" "Thiele-Innes")`; `full:("sign of cos i" OR "sign of the inclination" ...)`; `full:("two years" "parallax" "orbital period" "eccentric" ...)`; `full:("DR4" "nss_two_body_orbit" "parallax" "cut" "selection")`; `citations(2018MNRAS.476.5658B)` (7 papers); `citations(2025ApJ...981L..23M)` (4 papers); wide-binary and orbital-pole queries; Hipparcos one-year queries. Web: 6 searches (orbit sense, DR4 NSS twice, Handbook, Holl 2011, wide-binary dipole). None returned a report of (a), (b) or (d). ADS phrase queries are blunt, so this is evidence of absence only at the level of these searches.
