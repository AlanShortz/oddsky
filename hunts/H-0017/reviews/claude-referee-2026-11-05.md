# H-0017 referee report (Claude, independent), 2026-11-05

Scratch code: `/tmp/h17ref/`. Line numbers: README at 86ce44c.

## Verdicts

1. **Section 4, fading in 2010: HOLDS WITH CAVEAT.** The fade is real and not instrumental; "no arrow of time" is wrong; not new.
2. **Section 5, J142401.66+295028.4: DOES NOT HOLD.** Published, and not free of AGN lines in 2006.
3. **Population claim: DOES NOT HOLD as new.** Wang et al. 2018; four of the 96 are in their sample.
4. **Sections 2-3: HOLDS WITH CAVEAT.** Counts reproduce; the quiet-cut bullet uses the wrong populations.

## Must change

**1. J142401.66+295028.4 is a published dust-echo candidate with a composite spectrum.**
Checked: SIMBAD `has_ref` for all 109 (none failed); Wang et al. 2018 Table 1 (ar5iv 1802.05105); SkyServer DR18 `galSpecExtra`/`galSpecLine` for seven objects (classes match the CSV).
Found: it is Wang et al. object 12. MPA-JHU `bptclass` = 3 (log [N II]/Hα = −0.32, log [O III]/Hβ = −0.09), as for all three "star-forming" objects; J080026.92+101308.6 is a SIMBAD Sy1. It has three AllWISE visits (W2 11.72, 11.90, 12.23); 0.51 is uncorrected.
Replace lines 112-115:
> So none of the 13 is a clean non-AGN: 8 are SDSS AGN or broad-line objects, 4 are BPT composites (MPA-JHU bptclass 3; one is a SIMBAD Sy1) and 1 is unclassifiable (a SIMBAD Sy2). J142401.66+295028.4 (z = 0.086, composite in 2006) is already published: object 12 of Wang et al. 2018 (MNRAS 477, 2943), a candidate tidal-disruption dust echo. It fades 0.45 mag in W2 over three AllWISE visits (363 days) and is 1.31 mag fainter and 0.74 mag bluer by 2014.

**2. The "Reading" is Wang et al. 2018.**
They took AllWISE-variable (`var_flg` ≥ 7) SDSS galaxies and found 19 non-Seyferts with declining light curves, read as dust echoes. In the 96: J100933, J123715, J130819, J142401. Stern et al. 2018 searched for fading across the gap. `var_flg` ≥ 7 marks 23 of the 96, all among the 45. None is in MIRONG (137) or Flaires (823).
Replace lines 96-99:
> **Reading.** About 40% of the cooled sources were already declining in 2010-11. The population is known: Wang et al. 2018 selected AllWISE-variable SDSS galaxies with declining light curves (four are in this sample), after Dou et al. 2016. This selection adds objects without a spectrum. Rise-selected NEOWISE samples do not contain them (0 of 96 in MIRONG and Flaires). What they are is not settled by the fade.

**3. The selection has an arrow of time.**
Checked: stationary red noise (damped random walk, τ = 1-10 yr, and smooth kernels) through the README's cuts (`sim.py`): 55-100% fade. A straight line from 2010 to 2014 gives 0.74 × 0.52/3.75 = +0.10.
Replace lines 93-94:
> The selection does have an arrow of time: the later visit is nearer the 2014 baseline, and the quiet cut removes declines that began late. Stationary red noise through the same cuts gives +0.02 to +0.06 mag; straight interpolation gives +0.10. The observed +0.10 says the change was gradual and under way in 2010. It does not separate a flare from a shut-down; the heated nuclei show the mirror image.

**4. Rate argument (line 89).** Medians reproduce; per object they do not. Replace the second sentence:
> This holds for the medians only: 46 of the 96 show no 2010 change above 0.1 mag and dropped later, 33 would overshoot by more than half, and a decline still running at that rate would break the quiet cut.

**5. Quiet-cut bullet (lines 57-59).** The SQL reproduces, but 81% and 93% describe all red sources. Counting the state-change cuts instead (`q.sql`), replace:
> **The quiet cut decides the ratio.** Before any image test, 116 of 410 coolers (28%) and 186 of 772 heaters (24%) are quiet. Without the cut there are more heater candidates than coolers, unvalidated. 96 : 13 describes decade-quiet objects only.

Delete "The imbalance says…" (lines 64-65): hosts are steady and AGN are not.

**6. Significance and the offset (line 11).** 45/3 and 2/4 reproduce; heated is 0/1. The quoted σ is 1.4 times too small against the control's scatter. 37 of 96 fade by > 0.15 mag (the control's 99th percentile) and 2 brighten; control 1 and 3. The offset is instrumental: 1,906 field sources in the same frames as 50 of the nuclei (the first 50 in file order) give +0.044 (W2) and +0.027 (W1), 657 extended ones add 0.000, and a local correction moves those 50 from a median 0.18 to 0.16. The AllWISE Supplement does not document it. Replace "45 of 96 significantly, against 3" with:
> 37 of 96 by more than 0.15 mag, against 2

**7. PTF 10fgz and "nuclei" (line 48).** Offsets are from SIMBAD positions (host Z 273-16). Replace:
> Positive control: one of the 96 is **PTF 10fgz** itself, 0.6″ from the supernova and 4.5″ from its host's nucleus. "Nucleus" is untested for the others, and 59 are non-stellar only for want of Gaia astrometry or a SIMBAD entry.

## Not checked

TNS (login). Wang et al. Table 1 was read through an automated page reader, not the PDF. No machine tables for Masterson 2024, Yang 2018, Stern 2018, Dou 2016 or Assef 2018's variable list; SIMBAD bibliographies stood in, and 69 of the 96 are not in SIMBAD. The real fraction of the 410 and 772. Nuclear offsets for the other 95. The neighbour control for 46 nuclei (IRSA timed out).
