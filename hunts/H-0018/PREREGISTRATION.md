# H-0018 preregistration: do binary stars know which way the Galaxy turns?

Written 2026-11-06 before any pair or orbit data were opened (the catalogue download had started; no row had been read).
The sha256 of this file is recorded with a UTC timestamp in `~/oddsky-runs/h0018/prereg.sha256`. Changes after that are
listed at the bottom of this file and mark whatever they touch as exploratory.

## Question

The Galaxy has a preferred rotation axis, and stars form from gas that shears around it. Is any of that handedness kept in
binary stars, from orbits of about a year out to about a parsec? Equivalently: is the mean direction of binary orbital
angular momentum zero?

Best prior tests found: 252 visual binaries (Glebocki 2000) and 51 binaries with resolved nodes (Agati+ 2015), neither of
which has statistical power at the percent level. LISA forecasts treat the dipole around the Galactic axis as an unknown
(Seto 2024; Seto & Liu 2026). Makarov 2026 uses projected orbital momentum of Gaia pairs but assumes isotropy.

## The statistic

For any Keplerian orbit, (r × v)·n = L·n, where n is the outward line of sight, at every orbital phase. So the sign of the
sky-projected rotation is the sign of L·n, whatever the eccentricity and phase:

- Resolved pair: `y = sign(Δα* Δμ_δ − Δδ Δμ_α*)`, unchanged if the two stars swap.
- Gaia astrometric orbit: `y = sign(B F − A G)` from the Thiele-Innes constants.

Fit by least squares over all objects, with `n` in Galactic Cartesian coordinates:

    E[y | n] = m + D·n

If L̂ has a dipole distribution, then ⟨L̂⟩ = (2/3) D. Prograde means L along −Z (the Galaxy turns clockwise seen from the
north Galactic pole), so **D_Z < 0 = prograde excess; D_Z > 0 = retrograde excess**. Uncertainties come from a bootstrap
over objects (1000 draws) and agree-or-explain with the OLS standard error.

Selection that depends on |cos i|, or on anything else even under L → −L, cannot create D. Only a chiral effect can.

## Samples

**WB (wide pairs).** El-Badry, Rix & Heintz 2021 catalogue (Zenodo 4435257). Cuts: `R_chance < 0.1`, `ruwe < 1.4` for both
stars, angular separation > 3″, and the projected rotation measured: `|z| / σ_z > 3` with PM covariances ignored and PM
errors from the catalogue. The cut is even under y → −y.

Bins by projected separation in AU: [10², 10³), [10³, 10⁴), [10⁴, 3×10⁴), [3×10⁴, 10⁵), [10⁵, 2.1×10⁵].

**Split.** A pair is dev if a multiplicative hash of `source_id1` modulo 10 is below 3 (30%). The remaining 70% is held out
and is opened once, by a frozen script, after the method is fixed on dev.

**NSS (year-scale orbits).** `gaiadr3.nss_two_body_orbit`, solution types `Orbital`, `OrbitalTargetedSearch*`,
`AstroSpectroSB1`, `OrbitalAlternative*` (the last two groups as sensitivity checks). The same 30/70 split by `source_id`.
Bins by period: < 100 d, 100–300 d, 300–450 d (contains 1 yr), 450–800 d, > 800 d. For `AstroSpectroSB1`, where the
Thiele-Innes C and H resolve the node, also the 3D mean of L̂ = (P × Q)/|P × Q|.

## Controls, fixed in advance

1. **Injection.** Flip signs on dev to inject D = 0.5% along +Z and along the north ecliptic pole. Recover within 2σ.
2. **Geometry mock.** Random Kepler orbits with known ⟨L̂⟩, projected with catalogue errors. Must return D = (3/2)⟨L̂⟩.
3. **Known physics, field pairs: the Oort test.** Random pairs of unrelated field stars at similar distance share no orbit
   but do share the Galaxy's vorticity. Mean sky-plane rotation scales with Oort B. The method must return D_Z < 0 with a
   size consistent with B ≈ −12 km/s/kpc given the pairs' velocity dispersion.
4. **Known instrument physics, parallax degeneracy.** The parallactic ellipse has the sense of the Earth's orbit, L along
   the north ecliptic pole. A one-year orbit of that sense is partly degenerate with parallax, so the NSS sample near 1 yr
   may show a chiral deficit along the ecliptic pole. Exploratory expectation, not a pass/fail control.
5. **Negative control.** The El-Badry shifted chance-alignment catalogue, same cuts. Expect D = 0 at scales where the shear
   term is negligible.
6. **Monopole.** m is unphysical: a real L field averages to zero over the sky. |m| > 3σ flags a systematic, not a signal.
7. **Frame test.** Fit D with the direction free. Compare with the Galactic pole and the ecliptic pole (60.2° apart).
8. **Gaia frame spin.** The PM frame spin depends on magnitude (Cantat-Gaudin & Brandt 2021) and adds Δμ·t̂ = −Δω·ŝ, which
   averages to zero only if pair position angles are isotropic. Compare the sample with both stars G > 13 and |ΔG| < 1
   against the rest.

## Decision rule on held-out data

**Detection** of a Galactic handedness requires all of:

1. |D_Z| > 4σ in WB overall or in NSS overall, or p < 0.05/15 in one WB bin (5 bins, 3 components);
2. |m| < 3σ in that sample;
3. consistent with zero in the shift control, or an excess that a shear calculation does not explain;
4. the free-direction D lies closer to the Galactic pole than the ecliptic pole;
5. the two Galactic hemispheres agree (y flips sign across b = 0);
6. the same sign in near/far (parallax split at the median) and bright/faint (median G) splits, within 2σ of each other.

Otherwise the result is an **upper limit**: 95% limit on |⟨L̂_Z⟩| per bin. A limit counts as a result only when the
injection control shows the method would have detected that size.

## Signs that would mean different things

- **Prograde (D_Z < 0) at all separations, including year-scale orbits:** natal memory of Galactic vorticity.
- **Retrograde (D_Z > 0) rising towards the Jacobi radius (≈1.7 pc for 1 M☉):** tidal stripping, which removes prograde
  wide orbits faster than retrograde ones (the Hill-problem asymmetry).
- **Prograde only at the widest separations, in proportion to separation:** unbound or weakly bound pairs carrying plain
  shear, not stored angular momentum. Calculated before calling it anything: shear gives ⟨L_Z⟩ = −|B| s² per unit mass.
- **Along the ecliptic pole, or a non-zero monopole:** instrument.

## What would make me drop it

Any Galactic signal that vanishes when pairs are restricted to G > 13 and |ΔG| < 1; moves with the ecliptic pole; or
appears at the same size in the shift catalogue.

## Not claimed in advance

No size of effect is predicted. The prior for a detection at the 1% level is low: a null is the likely outcome, and a tight
null is itself a first measurement.

## Changes after registration

(none yet)

### Addendum A, 2026-11-06, written before the held-out split was opened

Everything in this addendum came from looking at the development split. Part A1 changes method; A2 adds tests of an idea
the original registration did not contain (only control 4 anticipated it, as a one-year effect). Tests A2 are prospective
for the held-out 70% and exploratory for the 30% that suggested them.

**A1. Changes to the registered method**

- `z` is computed from 3D vectors, not the tangent-plane formula. The formula above lets meridian convergence into `z`
  when PMs are expressed in each star's own east/north basis. Effect on dev: negligible (both printed).
- Geometry: `D = (3/2)⟨L̂⟩` holds without a cut on `|z|/σ`. With the cut the gain lies between 3/2 and 3 (Kepler mock), so
  `⟨L̂_Z⟩ = (2/3) D_Z` is an upper bound on the true mean, which keeps the limits conservative.
- The shift catalogue undoes a 0.5° on-sky RA shift to recover each pair's selected separation. Under the |z| cut it has
  very few pairs (176 on dev), so it has almost no power; that is reported rather than treated as a pass.

**A2. New tests on held-out orbits**, all in `scripts/final.py`, whose sha256 is recorded with this file.

Sense: `A = ⟨y sign β⟩`; A < 0 means orbits with L along the north ecliptic pole, the sense of Earth's orbit, are missing.
Forward model: `scripts/chiral_sim.py`, predictions frozen in `work/sim_prediction.csv` (no parameter fitted to orbit data).

- **T1, parallax error.** Ratio of median `parallax_error`, +NEP over −NEP, Orbital, 12 ≤ G < 16, by period: Pearson r ≥ 0.8
  against the model and median |difference| ≤ 0.05.
- **T2, handedness.** A(P) against the model: Spearman ρ ≥ 0.7. A > 0 at 2σ in 150–200 d. Residual for P ≥ 450 d reported.
- **T3, are the missing or extra orbits fake?** Orbital, P 600–900 d, predicted K > 5 km/s, RVS constant-velocity p < 0.001.
  If the −NEP excess were fake, −NEP would be less often RV-variable by a calculable amount; the fake-excess reading is
  rejected if observed −NEP lies more than 3σ above that. RV amplitude over 2K_pred is compared between senses.
- **T5, channel.** A against the margin over `parallax/σ_ϖ > 20000/P`, using a sense-blind σ_ϖ (median for −NEP at that G).
  P 600–900 d: |A| at margin ≥ 5 is under half of |A| at margin < 1.5.
- **T4, Galactic pole in orbits.** D_Z with sign(β) × period-bin nuisance terms. Reported as a limit. It does not enter the
  detection decision unless |D_Z| > 4σ, and then only with the other registered conditions.

The registered WB decision rule is unchanged.

### Addendum B, 2026-11-06, written after the held-out run, disclosing departures found by the referee

- "No row had been read" (line 3 above) is not strictly true. Row counts by type and a partial first row of the orbit table
  (no orbital constants) were printed in the same step as this file was written. No statistic had been computed.
- Control 1 registered a 0.5% injection. That is below dev noise, so a 5% label-flipping injection on dev was run as well. It is a
  linearity check, not the sensitivity test the registration describes.
- Control 2 as first run was not a Kepler mock: it had no orbits and no catalogue errors. A proper one was run by the referee.
- `chiral_sim.py` was edited after the held-out run to add `--dr4` and `--fix`, so its recorded hash no longer matches. With those
  options off, the edited code reproduces the frozen `sim_nss` and `sim_field` tables exactly (`DataFrame.equals`).
- `final.py`, kept frozen, treats Thiele-Innes C and H as mas; they are au. The 3D ⟨L̂⟩ in `work/final_heldout.txt` is wrong and
  is corrected in `scripts/post_referee.py`. No registered decision used it.
