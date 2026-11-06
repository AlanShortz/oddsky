# H-0018 assumption register

Every assumption the dossier rests on, how it was tested and what happened. All tests here are exploratory, run after the held-out
data were opened. Status: **holds** (tested, no problem at the stated level), **partly** (tested, with a limit that matters), **fails**
(the assumption was wrong and the text was changed), **untested**.

Outputs: `work/assumptions.txt`, `work/assumptions2.txt`, `work/variants.txt`, `work/post_referee.txt`, `work/gm_dr3.txt`, `work/gm_long.txt`,
`work/gm_dr4.txt`, `work/gm_channel.txt`, `work/knockout.txt`, `work/knockout_Te.txt`. "Referee" and "reproducer" are `reviews/claude-referee-2026-11-06.md`
and `reviews/independent_reproduction/REPORT.md`. Literature: `reviews/literature_read_2026-11-06.md`.

## Statistic and conventions

| # | assumption | test | result | status |
|---|---|---|---|---|
| 1 | sign(BF − AG) is the sign of L·n | algebra; time-domain Kepler; Sixth Orbit Catalog; Gaia BH1, BH2 | 2000/2000; 61 of 63 independent orbits | holds |
| 2 | L along +NEP is the sense of the parallactic ellipse, so a deficit reads A < 0 | geometry; Butkevich 2018 Eqs. 25–26 give the same mapping; reversing Earth's orbit inverts the simulated ratio (reproducer) | agrees | holds |
| 3 | scan angle ψ: along-scan = Δα* sin ψ + Δδ cos ψ | heading measured from the scan law's own track (referee) | median 6×10⁻⁵°; mirrored convention spreads ±174° | holds |
| 4 | `ecl_lat` is right | recomputed from ra, dec (reproducer) | ≤ 0.03″, no sign mismatch | holds |
| 5 | C and H are in mas | P·Q orthogonality (referee) | **Wrong: they are in au.** Median \|cos\| 0.227 raw, 0.057 corrected. 3D ⟨L̂⟩ corrected; no registered decision used it | fails, fixed |
| 6 | the split is independent of everything else | χ² of the dev flag against ecliptic latitude, G, period; declination for pairs | p = 0.64, 0.87, 0.70, 0.79 | holds |
| 7 | the preregistration was fixed before the data | sha256 of the text through Addendum A matches the hash recorded before opening. Only a local record until commit e162015 | matches | partly |

## Wide pairs and the Galactic limit

| # | assumption | test | result | status |
|---|---|---|---|---|
| 8 | the instrument adds no Galactic dipole at small scales (the shift catalogue had no power) | unrelated stars 1–10′ apart, same statistic, N ≈ 690,000 | D_Z = −0.15 ± 0.36%. 1–10′ differing in distance +0.23 ± 0.41%; 10–30′ +0.77 ± 0.36% (2.1σ). Errors naive, stars recur | holds to about 0.8% |
| 9 | perspective does not bias y | comoving mock on real pair geometry, Δd up to 5 pc | −0.56 ± 0.82, +0.32 ± 0.33; with solar reflex −0.62 ± 0.32%. Errors naive (six draws of the same pairs). Δd 5 pc is far beyond a bound pair | holds |
| 10 | meridian convergence is handled | 3D against tangent-plane formula | negligible on dev | holds |
| 11 | magnitude-dependent frame spin does not fake a dipole | spin regression (referee) | spin detected at about 13σ; D_Z moves −1.56 to −1.55 | holds |
| 12 | the result does not hang on the cuts | R_chance 0.01, 0.5; RUWE 1.2, none; \|z\|/σ 2, 5; PM errors × 1.5; parallax agreement | D_Z from −0.72 ± 0.91 to −1.63 ± 0.70% | holds for the limit |
| 13 | close separations are clean | sep > 5″, > 10″ | −1.06 ± 0.86, −0.95 ± 1.21% (from −1.56 ± 0.69, nested). Consistent, and no support for a real signal | holds for the limit |
| 14 | higher multipoles don't leak into D_Z | add l = 2 terms | −1.61 ± 0.69%; l = 2 χ²(5) = 5.7 | holds |
| 15 | the errors are right | bootstrap; permutation of y over the sky | 0.71%, 0.70%; permutation p = 0.024 for this one component, before any trials correction | holds |
| 16 | pairs are bound Kepler orbits | referee's mock with real errors: gain 1.87–1.90; 13% of selected pairs exceed √2 v_c; effective gain about 1.5–1.75 | (2/3)D is about right, not "conservative" | partly |
| 17 | unresolved triples don't matter | RUWE < 1.2 unchanged; parity argument. No direct test with a triple catalogue | −1.58 ± 0.74% | partly |
| 18 | ⟨L̂⟩ = (2/3)D assumes a dipole-shaped pdf of L̂ | none. D itself is model-free | | untested |
| 19 | tides would show near the Jacobi radius | only 23 pairs above 10⁵ au | the sample cannot address it | untested |
| 20 | plain shear is negligible in bound pairs | order-of-magnitude only | B·s about 6×10⁻⁴ km/s at 10⁴ au | holds roughly |

## The orbit handedness

| # | assumption | test | result | status |
|---|---|---|---|---|
| 21 | the table is complete and the types are right | counts against Gaia Collab 2023 Table 1 | 134,598; 33,467; 169,227 | holds |
| 22 | the cuts are as stated | hard edges in the data; Halbwachs Eqs. and Table 1 read | `Orbital` min margin 1.000 | holds |
| 23 | `AstroSpectroSB1` passed the same cut | Table 1 footnote says conditions "do not apply" to SB1-confirmed solutions; counted | 0.30% below the parallax line, 1.49% below a₀ (referee); `Orbital` was a prerequisite (El-Badry+ 2024) | holds, mostly |
| 24 | the ratio is not a G or sky artefact | narrow sky bands at fixed \|sin β\|, G | 1.41, 1.38, 1.42 at \|b\| < 10, 10–30, > 30; control 200–300 d 1.009 | holds |
| 25 | the pattern is tied to the ecliptic, not one sky region | A by ecliptic longitude; hemispheres | −0.069 to −0.088; mean y −0.074, +0.082 | holds |
| 26 | the excess orbits are real | RVS variability and amplitude by sense; `AstroSpectroSB1` shows the deficit; proxies | no evidence of fakes. Reaches 8.8% of the excess at 600–900 d | **partly: nothing direct above G 13** |
| 27 | catalogue P and sense can be trusted | blind cascade on known truth | fitted sense right 98.9%; P within 10% for 97.9% of accepted orbits, but 26–46% wrong for true P > 1100 d | holds below 1100 d |

## The explanation

| # | assumption | test | result | status |
|---|---|---|---|---|
| 28 | a Fisher matrix stands in for a real fit | gaiamock's full blind cascade, with period search and acceleration models, 12,000 stars × 60 mirror pairs (`work/gm_dr3.txt`) | same sign and shape: A −0.032 ± 0.007 overall (data −0.078), −0.19 at 340–390 d (−0.25), +0.04 ± 0.03 at 150–200 d (+0.06). Amplitude 35–75% of data | holds in shape |
| 29 | errors differ in fact, not only formally | scatter of fitted parallax in real fits; companion parallaxes | scatter ratio 4.2 at 365 d, 2.26 at 730 d, matching formal errors. Companions at 600–900 d: 1.18 ± 0.14, underpowered | partly |
| 30 | free e and T carry the two-year term | model with e, T fixed: 1.026, 1.010, 1.011 at 600–900 d. Gaia pseudo-circular: 1.034, 1.008, 1.020 | agree. But pseudo-circular errors are the same fit conditioned, so this tests Gaia's covariance, not new data. They also skip the σ_e filter, so A's vanishing can't be separated from selection | partly |
| 31 | **the parallax cut is the main channel** | blind cascade with and without the cut, by parallax (`work/gm_channel.txt`) | Near 1 yr yes: 340–390 d −0.19 with, −0.07 without. At 600–900 d the cut is sense-dependent (at ϖ 1–1.5: 15.9% vs 8.0% removed) but A exists before it: −0.095 without, −0.139 with. **Text changed: one channel of several** | fails as stated |
| 32 | P > 1100 d needs something outside the cut | deep cascade, 15,000 stars (`work/gm_long.txt`) | A = −0.035 ± 0.010 at the step that decides orbit against acceleration solution, where 7/9-parameter solutions are symmetric. About half the observed −0.07. So the referee's guess is supported; half is still missing | partly |
| 33 | the parent population does not matter | variants: q, M₁, thinning. Eccentricity distribution | ratio barely moves, but 700–800 d goes 1.21 (thermal), 1.35 (uniform), 1.52 (low e) | partly |
| 34 | parents cover the data | parallax distribution | data 10% at ϖ < 0.7, where A = −0.37; cascade 0.7% (M₁ = 1 M☉ can't make their large orbits). Likely the main reason for the low amplitude; untested directly | partly |
| 35 | `field_parent` is a random sample | second `random_index` slice | \|b\| < 10 fraction 0.505 vs 0.527 (KS p < 0.001). TOP without ORDER BY isn't strictly random. Small, and affects amplitude only | partly |
| 36 | transit counts and noise are realistic | against `astrometric_matched_transits`, catalogue σ_ϖ at fixed G, and thinning | model has 1.21× the transits; catalogue/model σ_ϖ 1.00–1.25; thinning 18% changes ratios by up to 0.08, mostly under 0.03 | holds |
| 37 | half-year reversal is understood | data, Fisher, cascade agree in sign | no mechanism identified, no literature support | untested |
| 38 | 50–100 d is understood | A +0.164 ± 0.037; cascade +0.02 ± 0.06. Also in `AstroSpectroSB1` (referee) | unexplained | fails |

## The DR4 forecast

| # | assumption | test | result | status |
|---|---|---|---|---|
| 39 | DR4 publishes what the grader needs | draft data model read | `parallax_error`, Thiele-Innes and pseudo-circular marking kept. 5.9 M rows, new `OrbitalPoorlyConstrained`, **cuts not stated** | partly |
| 40 | a repeated scan law stands in for the unpublished one | on DR3, replace the law with its first year repeated | 700–800 d 1.33 vs 1.35; 340–390 d 1.21 vs 1.18; half-year 0.97 vs 0.92 | holds, except half-year |
| 41 | reversed precession can be approximated | cascade with the last 188 d reflected in the ecliptic plane (`work/gm_dr4.txt`). Real `epoch_astrometry` arrives only with DR4 | see the forecast | partly |

## Prior art

| # | assumption | test | result | status |
|---|---|---|---|---|
| 42 | nobody has measured this | Perryman 2026, Lammers & Winn 2026, Yahalomi+ 2026, Makarov 2025 and others read or grepped; about 75 ADS queries in all | not found. Unread: Holl 2011, Exoplanet Handbook, Hipparcos papers mostly, DR4 NSS paper. ADS phrase search is blunt | partly |
| 43 | the mechanism is ours | Butkevich 2018 Eqs. 22, 25–26, 29 imply the hemisphere mapping and a finite-baseline sense term; Makarov 2025 and Andrews+ 2019 report a two-year dip; El-Badry+ 2024 and Lam+ 2025 report the cut's one-year hole; Makarov 2026 finds no all-sky asymmetry in 103,169 pairs | credit given in the dossier | fails, fixed |
