# Referee report: H-0016 (the WISE gap)

Author: claude-referee (independent session, no stake in the result). Date: 2026-11-03.
README version read: `hunts/H-0016/README.md` of 2026-11-03 00:00 (20,541 bytes). Budget used: ~40 min.
My code and outputs live outside the repo in `/tmp/h0016ref/` (`unwise_remeasure.py`, `irsa_seq.py`, their `.csv`/`.log`);
nothing in the repo was modified except the creation of this file.

**Verdict in two sentences.** The catalogue-artifact diagnosis (46 of 48 clean stellar steps are AllWISE profile-fit
failures) survives every attack I could mount and is in fact stronger than the README states: the failure is also visible in
the AllWISE astrometry (0.35-2.6" offsets from Gaia), the per-frame uncertainties and the apparent-motion columns. The
novelty claims for the two Be stars are wrong (BD+28 4177 is a Hipparcos "unsolved variable", JL 62 is NSV 25308), the Be
classification of BD+28 4177 is an inference with no emission-line record behind it, and the ZTF test in section 6 is
invalid as built: when ZTF actually has a point inside the NEOWISE dip, two of the three cases I checked show the *same* dip
in the optical, i.e. ordinary grey eclipses.

## Findings

### 1. unwise.me `version=allwise` is the 2010-11 coadd; `neo7` is a 2010-2020 mix. CONFIRMED (empirically)

The unwise.me landing page does not document the versions (fetched 2026-11-03; it only names the coadd papers, whose titles
say the neoN "full-depth" coadds combine WISE and NEOWISE-R frames). I tested the semantics on the data instead. For
BD+28 4177, my own 5-pixel aperture on the `allwise` cutout gives W1 = 8.97, W2 = 8.75 (AllWISE catalogue 8.91/8.68; the
~0.06 mag difference is aperture loss), and on `neo7` W1 = 10.03, W2 = 9.86, between the 2010 value and the NEOWISE baseline
(10.20/10.21). The implied flux weight of the 2010-11 frames in neo7 is f = 0.10 (W1) to 0.17 (W2), i.e. 1:5 to 1:9. If the
version flag were ignored the two cutouts would give identical magnitudes; they do not. KT Eri gives R = 4.28 (W1), 3.61 (W2).

### 2. The prediction R = 7a/(a+6). CONFIRMED as adequate; the exact weight does not matter

neo7 covers 2010-11 (2 visits) plus NEOWISE-R years 1-7 (14 visits), so 1:7 (R = 8a/(a+7)) is the better nominal weight;
the measured f above is 1:5 to 1:9. For the steps in question (|d1| ≤ 1.3) the 1:6 vs 1:7 predictions differ by < 4%
(BD+28 4177: 2.48 vs 2.56; observed 2.68). No weighting puts a real 0.4-1.7 mag step at R = 1.00 ± 0.03, which is what the
46 artifacts give, so the test's discriminating power does not depend on the weight. KT Eri (4.28 vs 5.6-6.2 predicted)
falls short because it was still fading through 2010-11 and the catalogue ratio is not a flux-weighted mean; it is not
evidence about the weighting.

### 3. Re-measurement of R with my own aperture code. CONFIRMED

`/tmp/h0016ref/unwise_remeasure.py`: 60-pixel cutouts, flux-weighted recentring, three apertures (r = 2, 3, 5 px with
annuli 8-14, 6-10, 10-18 px), plus a peak-pixel ratio. Results (W1 R at r = 2/3/5 px; W2 R at r = 5 px):

| object | d1 (cat) | W1 R (2/3/5 px) | W2 R (5 px) | peak ratio | 2010 image W1 (5 px) | w1mag | w1_base | w1mpro |
|---|---|---|---|---|---|---|---|---|
| J234829.46-440418.4 | −1.73 | 0.96 / 1.00 / 1.00 | 1.02 | 1.14 | 11.07 | 11.05 | 10.99 | 12.72 |
| J224539.27+302150.6 | −1.26 | 1.04 / 1.03 / 1.03 | 1.01 | 1.04 | 12.36 | 12.34 | 12.30 | 13.55 |
| J081749.91+374608.8 | −0.76 | 1.08 / 1.03 / 1.03 | 1.01 | 1.05 | 11.10 | 11.07 | 11.05 | 11.81 |
| J162011.24-172910.3 | −0.71 | 1.03 / 1.01 / 1.00 | 1.02 | 1.10 | 12.06 | 12.03 | 12.01 | 12.71 |
| J180859.57-564520.7 | +0.96 | 1.04 / 1.02 / 1.01 | 1.00 | 1.13 | 11.99 | 11.97 | 11.96 | 11.00 |
| J062354.25+462845.2 | +0.99 | 1.02 / 1.00 / 1.00 | 1.01 | 1.05 | 11.54 | 11.51 | 11.50 | 10.51 |
| JL 62 | +0.43 | 1.46 / 1.44 / 1.43 | 1.55 | 1.51 | 11.20 | 11.15 | 11.56 | 11.14 |
| BD+28 4177 | +1.29 | 2.69 / 2.68 / 2.68 | 2.78 | 2.75 | 8.97 | 8.93 | 10.20 | 8.91 |

Every artifact is at R = 1.00-1.04 in every aperture, in the peak pixel, and in both bands; the absolute 2010 image
magnitude agrees with the AllWISE *aperture* magnitude and with NEOWISE to ≤ 0.08 mag and disagrees with w1mpro by
0.7-1.7 mag. The two real steps reproduce the author's R to 0.01. The small r = 2 px departures (0.96-1.08) are PSF
differences between the Lang and Meisner coadds (the peak ratio of 1.04-1.14 shows the `allwise` coadd is slightly sharper)
and are the same for artifacts and real stars.

### 4. Could the error be in NEOWISE or 2MASS instead? INVALIDATED (the alternative, that is)

Three independent 2010-11 measurements agree with NEOWISE and with 2MASS: the AllWISE aperture magnitude on the Atlas
coadd, my aperture on the unWISE 2010-11 coadd, and the per-frame fluxes being *inconsistent with each other* (below).
Only the AllWISE profile fit disagrees. The artifact is on the AllWISE profile-fit side.

### 5. The failure is wider than "two columns"; the MEP does not simply "inherit" a clean error. CONFIRMED and sharpened

From `~/oddsky-runs/h0016/steps_mep.csv` and `work/steps_master.csv`, 46 artifacts vs the 2 real stars:

| statistic | artifacts (min / median / max) | BD+28 4177, JL 62 |
|---|---|---|
| per-frame w1sigmpro_ep at W1 ≈ 11-13 | 0.085 / 0.174 / 0.265 mag | 0.024, 0.025 |
| fraction of frames with null uncertainty | 0 / 0.15 / 0.29 | 0, 0 |
| fraction of frames with *negative* W1 flux | 0 / 0.05 / 0.22 | 0, 0 |
| MAD of frame W1 magnitudes | 0.07 / 0.20 / 0.35 | 0.021, 0.021 |
| median per-frame w1rchi2_ep | 0.8 / 3.2 / 8.7 | 1.25, 1.63 |
| AllWISE−Gaia position offset (g_sep) | 0.35" / 0.86" / 2.63" | 0.053", 0.050" |
| AllWISE sigra | 0.10" / 0.20" / 0.40" | 0.034", 0.038" |
| AllWISE apparent motion |pm| | 0 / 847 / 2380 mas/yr | 0, 55 mas/yr |

So the per-frame profile fits are themselves wrong (median frame magnitude is 0.2-1.5 mag from the truth, in the same
direction as the catalogue), their uncertainties are 5-10× too large, several frames return negative flux, and the
multi-frame astrometric solution is off by up to 2.6" with spurious motions of ~1"/yr. This is the signature of a
profile-fit that converged badly (wrong centroid and/or PSF), not of a clean photometric offset. Practical consequence:
`g_sep > 0.3"` for an isolated W1 < 13 star, or `sigra > 0.1"`, are additional one-column flags, and the README sentence
"the multi-epoch table inherits the error at every 2010 frame" should say the frames are individually bad, which *is* a
way the MEP can validate (or not) a catalogue value.

### 6. Neighbours inside the 8.25" aperture as a mundane cause. INVALIDATED

32 of 46 artifacts have no Gaia source within 6". The strongest neighbour case, J162011.24-172910.3 (companion at 1.55",
ΔG = 0.10), gives R = 1.00-1.03 and an image magnitude equal to the NEOWISE one: the unresolved pair is measured identically
by the AllWISE aperture, the 2010 unWISE image, and NEOWISE, and only the AllWISE single-component (nb = 1) profile fit
loses 0.7 mag, which a single-PSF fit to an unresolved 1.5" pair cannot do. Neighbours do not explain the sample.

### 7. The 0.52% / 0.053% catalogue rates (IRSA job 27091585). CONFIRMED at the 1-cone level; UNTESTED at full scale

A sync cone of 1.5° at (200°, +30°) with the same cuts (`/tmp/h0016ref/allwise_cone.csv`): 3,069 sources, 3 with
|w1mag − w1mpro| > 0.4 (0.10%), 2 of them with w1snr < 15 (0.065%, vs 0.053% all-sky). One of the two is
J132458.04+294909.7, already in the author's 46; the other, J131558.26+294324.9 (w1mpro 14.41, w1mag 11.37, |pm| = 1023
mas/yr), is a new instance with the same signature. In this cone w1snr < 15 and |w1mag − w1mpro| ≤ 0.4 is empty, and the
median w1snr is 47 at W1 = 8-12, 41 at W1 = 14. The all-sky numbers could not be re-run in the time available.

### 8. Novelty of BD+28 4177 and JL 62 as variables. INVALIDATED

- BD+28 4177 = HIP 107387. Hipparcos (VizieR I/239/hip_main): Hp = 9.855, 190 transits, Hpscat = 0.031 mag,
  **HvarType = U** ("unsolved variable"), SpType B1IV. It has a published variability flag since 1997.
- JL 62 = **NSV 25308** (VizieR B/gcvs/nsv_cat and VSX OID 63743): suspected variable, amplitude 0.04 V, "Be".
- VSX within 30" of both: nothing else (endpoint validated on KT Eri, type NR). Gaia DR3 vari (I/358): nothing.
  ASAS-SN variables (II/366): nothing. SIMBAD CfA mirror: 18 refs for BD+28 4177, none in the title list I could pull.

"No variability record anywhere" and "None of these objects is in the literature as variable" must go. The records are
small-amplitude optical flags, consistent with a Be star, but they exist.

### 9. BD+28 4177 as a Be star that lost a disk. WEAKENED (the event is real; the interpretation is under-determined)

What is solid: the 2010-11 excess is real in the images (R = 2.68/2.78, my measurement), present at both AllWISE epochs
(MEP frames 8.87-8.98 over 29 frames, Jun and Dec 2010, MAD 0.02 mag), the source is isolated in Gaia to 6" and in AllWISE
(nb = 1, cc_flags 0000), the AllWISE astrometry matches Gaia to 0.05", and 2MASS (2000) and NEOWISE (2014-24) both show a
bare photosphere (J−K = −0.15; K − W1 = +0.03). A moving object, latent, ghost or blend cannot produce a 6-month, two-epoch,
four-band excess at a fixed Gaia position. Microlensing is excluded by the colour (the excess rises from 2.3× at 3.4 µm to
14× at 22 µm) and the duration.

What is not solid:
- No spectral record shows emission lines. SIMBAD: B0.5IIIk (Morgan 1951, "peculiar"); Hipparcos: B1IV. The "Be" label is
  the author's inference from the IR excess alone. The README table header "Two Be stars" and the hook "a B giant that lost
  its disk" overstate this.
- The excess SED does not discriminate free-free from hot dust. Relative to the Rayleigh-Jeans photosphere the excess is
  Fν ∝ ν^+1.0 from 3.4 to 22 µm (excess factors 2.3, 3.1, 6.9, 14 at W1-W4 using K = 10.25 as the photosphere); a Be disk
  (α ≈ 0.6-1) fits, but so does a ~1300-1500 K blackbody (predicted Fν(22)/Fν(3.4) = 0.11 vs 0.14 observed). A dust episode
  (B[e]-like, or dust from a companion) is not excluded by the WISE colours.
- The only optical constraint from the gap is absent (ASAS-3 ends at Dec +28; the star is at +29.6). A Be star building a
  disk dense enough to triple the 3.4 µm flux typically brightens by 0.1-0.5 mag in V and reddens; KELT-North (2007-2013,
  V 8-11, covers this field) and the Hipparcos/Tycho epoch photometry are the places to look, and were not looked at.
- Distance: parallax 0.19 ± 0.05 mas gives 4-7 kpc; at b = −17.9° that is 1.3-2.1 kpc below the plane. Fine for a runaway;
  not evidence for or against a disk.

### 10. LEDA 1815030 and the eight "red-fading nuclei". WEAKENED

- LEDA 1815030 is not a G ≈ 20 host: SDSS DR16 (V/154) has it at r = 16.52, class = galaxy, no spectrum; PGC D25 ≈ 15"
  (logD25 = 0.39). Gaia's G = 19.87 is the compact-core measurement. Gaia DR3 (IRSA copy): DSC galaxy = 1.00, quasar = 0.00,
  `in_galaxy_candidates` = 1, no parallax. Spectroscopy is cheap, not "feasible but not cheap".
- No RASS source within 60" (IX/29); not in the Assef et al. R90 AGN catalogue (J/ApJS/234/23) at 5"; not in Gaia QSO
  candidates. SIMBAD type G, one reference.
- The 2010 colours are AGN-like (W1−W2 = 1.14, W2−W3 = 2.57) and the MEP shows the decline already under way inside 2010
  (W1 11.95 → 12.23, W2 10.79 → 11.07 between the Jun and Dec epochs, i.e. ~0.5 mag/yr), reaching 13.08/12.49 by 2014 and
  flat since. This is a fading hot-dust component. It is equally the signature of a changing-look/turn-off AGN (Sheng et al.
  2017 found ~1% of WISE AGN with |ΔW1| > 0.5 mag over the gap; dozens of such among the parent sample's AGN-coloured
  sources are expected) and of a dust echo. The sample statistics support nothing more: among the 62 clean non-stellar steps
  the fainter-now colour change has median 0.03 mag and only 8 exceed ~0.25 mag; "quiet after" is the selection, not a
  discriminant.
- Before the words "tidal disruption" are used: an optical spectrum of the nucleus (persistent narrow-line AGN or not; broad
  lines), 2008-2012 optical photometry of the r = 16.5 nucleus (CRTS covered Dec +27.7 continuously; the data exist even if
  the author's endpoint 404'd), a literature search in the WISE changing-look/fading-AGN catalogues (Sheng 2017, Stern 2018,
  Yang 2018, Jiang 2021 MIRONG, Wang 2018), and an energy budget (the 2010 excess luminosity vs host mass).

### 11. The ZTF test of the one-visit fades (section 6). INVALIDATED as a test; the frame test itself CONFIRMED

The count reproduces (94 with a ±10 d ZTF window; 6 fainter, 84 unchanged, 4 brighter, `work/fades_ztf_ok.csv`). But the
statistic is the median of all ZTF points within ±10 d, and the NEOWISE events are ~1-day dips. I re-ran the frame logic
with `oddsky.data.neowise.exposures` and re-fetched ZTF for five fades, three of them "unchanged" ones chosen by depth and
not in the author's 14 (`/tmp/h0016ref/fades_recheck.csv`):

| fade | W1 dip (all frames / span) | ZTF r inside ±1 d | ZTF r, other points in ±10 d | author's verdict |
|---|---|---|---|---|
| J051053.20+285351.6 | 11 frames, smooth +0.02 → +0.67 → +0.14 over 0.98 d; W2 the same | none (nearest −5.5 d, +2.5 d) | 0.00 ± 0.01 | unchanged |
| J213232.27+481424.0 | 16 frames, +0.14 → +0.72 → +0.17 over 1.64 d | **+0.42 at −0.4 d** (g: +0.16 at +0.7 d) | 15 points at 0.00 ± 0.02 | unchanged (window median +0.007) |
| J185349.89+164754.6 | 12 frames, +0.12 → +0.53 → +0.01 over 1.24 d | **+0.36 at +0.2 d** (g: +0.32 at +0.3 d) | 0.00 ± 0.01 | unchanged (window median −0.001) |
| J070747.24-103052.7 | 11 frames all +0.68 to +0.82 over 1.11 d; W2 +0.90 to +1.20 | none in r (g: −0.14 at +0.8 d) | r ranges −0.16 to +0.15 over 7 nights | "unchanged to 0.05 mag, IR-only dip" |
| J203548.57+455927.6 | 1 frame of 17 at +1.96; the rest −0.04 to +0.06 | none | 0.00 ± 0.05 | not supported by frames |

So: (a) of the three "unchanged" fades with a ZTF point inside the dip, two show the same-depth dip in the optical
(0.42 and 0.36 mag against 0.43 and 0.41 mag in W1): grey, i.e. ordinary eclipses or occultations by a stellar body, which
the ±10 d median erased; (b) the author's showcase J070747.24-103052.7 has no ZTF r point inside its 1.1-day dip and its
r scatter within ±10 d is ±0.15 mag, so "unchanged to 0.05 mag" and "infrared-only" are not established (the one g point at
+0.8 d is −0.14, i.e. brighter, inside a YSO's normal flicker); (c) the frame-level findings for J203548 and J070747
reproduce exactly; the ingress/egress shapes seen in the three new objects are real within the visit. "84 of 94 unchanged"
and "the optical counterpart does not fade in 89% of the cases" must be withdrawn; the fair statistic is the ZTF point(s)
inside the span of the deep frames, available for a minority of fades.

### 12. Internal consistency of numbers. CONFIRMED with small gaps

- 110 clean = 57 brighter-now + 53 fainter-now; 48 with parallax/error > 3; 62 without; 33 + 13 artifacts by direction:
  all reproduce from `steps_master.csv` and `steps_unwise_verdict.csv`.
- Artifact ranges in section 4 (w1snr 5.4-13.7; |w1mag − w1mpro| 0.44-1.67; real ≤ 0.13) reproduce (stellar real: 0.010,
  0.019).
- `steps_master.csv` has 261 rows (57 brighter-now, 204 fainter-now) but the funnel quotes 19,546 / 272; the README says
  "261 flagged-or-clean candidates" without saying which flagged ones were kept. State the rule.
- Section 2 says KT Eri's image R is "4.3/3.6 against 5.6 predicted"; with the 1:7 weight the prediction is 6.2. Either way
  it under-predicts by 25-30%, for the reason in finding 2; say so rather than "the test sees it".
- The wide pull: 3 artifacts of 14 reproduce from `steps_wide_unwise_verdict.csv` (R = 1.02-1.07); "10 (+1 partial)" ✓.

### 13. Untested within the budget

The all-sky 20.6 M / 106,933 / 10,995 counts; the identities of the ten wide-pull stars; the other seven red faders beyond
the catalogue checks above; CRTS/KELT/Tycho epoch photometry for BD+28 4177; the Hipparcos epoch photometry itself.

## Required changes before this hunt is merged

1. Delete "no variability record anywhere" (BD+28 4177) and "None of these objects is in the literature as variable";
   add HIP 107387 HvarType U (Hpscat 0.031, 190 transits) and NSV 25308 to the table and the novelty section.
2. Retitle 5.1 from "Two Be stars that lost their disks" to something like "Two B stars whose 2010-11 mid-infrared excess
   vanished"; state that no emission-line observation of BD+28 4177 exists and that the excess SED (Fν ∝ ν^1.0) is
   consistent with both free-free and ~1400 K dust. Any case title must not say "disk" until an Hα spectrum or a 2010
   optical light curve supports it.
3. Section 6: withdraw "84 of 94 unchanged" and "89%"; replace with the in-dip statistic (ZTF points within the span of the
   deep frames) and report J213232.27+481424.0 and J185349.89+164754.6 as grey dips seen by ZTF. Rewrite the J070747
   paragraph: no ZTF r point inside the dip, r scatter ±0.15 mag; "infrared-only" is untested.
4. Section 5.3: replace "Hosts are G ≈ 19-21, so spectroscopy is feasible but not cheap" with the SDSS r = 16.5 value for
   LEDA 1815030 (and check the others in SDSS/PS1); state that a turn-off AGN is the null and that the colour-change sample
   of eight is not statistically distinguishable from AGN variability.
5. Section 4/README summary: replace "the AllWISE multi-epoch table inherits the error at every 2010 frame" with the actual
   frame-level picture (frame uncertainties 0.09-0.27 mag, 15% null, 5% negative fluxes, rchi2 3-9, astrometric offset
   0.35-2.6" from Gaia, spurious |pm| ~ 1"/yr). Add `g_sep`/`sigra`/`pmra,pmdec` as diagnostics beside w1snr and
   |w1mag − w1mpro|.
6. Section 2: state the unwise.me version semantics as an empirical result (finding 1) rather than as documentation, and
   quote the nominal weight as 1:7 with the measured 1:5-1:9.

## Recommended changes

- Run the two-column (now five-column) diagnostic on the whole catalogue through the image test, as planned, but seed it with
  the cone result that w1snr < 15 alone appears sufficient at W1 < 14.5 and with the new case J131558.26+294324.9.
- For BD+28 4177: KELT-North and Tycho/Hipparcos epoch photometry, an Hα spectrum, TESS (TIC 452720691) for present-day
  Be-type activity, and a check of the "peculiar O star" remark in Morgan 1951 for emission.
- For the fades: re-run the ZTF check with the in-dip window for all 214, and keep only fades with a ZTF point inside the
  deep-frame span as the "optical-tested" subsample; grey vs IR-only is then a measurement, not a window median.
- For LEDA 1815030: CRTS 2005-2013 light curve of the nucleus (the data exist), a spectrum, and the fading-AGN literature.
- Oddsky tooling: add a `skeptic` check that any AllWISE magnitude used in a case has w1snr consistent with its magnitude
  (median 47 at W1 ≤ 12, 41 at W1 = 14 in my cone), |w1mag − w1mpro| < 0.3, and an AllWISE−Gaia offset < 0.3" for isolated
  stars; and a `ztf_check` that only counts points inside the event's frame span.

## My probabilities

- (a) Catalogue-artifact diagnosis for the 46 stellar steps: P(correct) = 0.97. Four independent 2010-11 measurements
  agree against the profile fit, every artifact sits at R = 1.00-1.04 in every aperture I tried, and the failure is visible
  in six catalogue columns at once.
- (b) BD+28 4177 as a Be decretion-disk loss event: P = 0.45. The 2010-11 excess is real and transient (P ≈ 0.97); that it
  was a gaseous decretion disk rather than a dust episode or a companion-driven event is not established by any observation
  in hand, and the star has no emission-line record.
- (c) LEDA 1815030 as a nuclear flare (TDE/echo) rather than ordinary AGN fading: P = 0.25. The decline is real and steep in
  2010, but a turn-off AGN is the null and the host has never been spectroscopically classified.
