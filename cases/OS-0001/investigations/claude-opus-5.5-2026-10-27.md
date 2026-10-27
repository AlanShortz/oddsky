# OS-0001 / ASASSN-21qj: the star that glowed before it dimmed

Investigator: claude-opus-5.5, 2026-10-27. Every number below comes from a tool call recorded in `cases/OS-0001/ledger.jsonl` (call ids K1 to K95). Claim ids (C1 to C17) refer to the case record.

## The short version

About 1,850 light-years away there is a star much like the Sun. For three and a half years it was perfectly ordinary in the infrared. Then, sometime in the winter of 2017-18, it suddenly started glowing at 3-5 microns, as though something next to it had been heated to about 1000 K (roughly 700 C, the temperature of a red-hot stove element). Three years later, after that glow had already begun to fade, the star itself started flickering: it lost up to almost 90% of its blue light for days or weeks at a time, more in blue than in red, which is what small dust grains do. By 2023 the glow was gone and the flickering had stopped. Since early 2025 the star has been steady to half a percent. Something made a lot of hot dust very quickly, some of that dust drifted across our view, and then it went away. The leading suspect is the wreckage of a collision between planets. I could not rule out the boring explanations by wishing, so I tried to rule them out with data. The full list of what was tried is below.

## What the data show

- **Infrared, before.** Eight NEOWISE visits from 2014-05 to 2017-11 are flat (W1 = 11.654) with photospheric W1-W2 of about -0.07 [C1] (K3, K4, K14).
- **Infrared turn-on.** Between the visits on 2017-11-15 and 2018-04-19, W1 brightened by 0.34 mag and W2 by 0.78 mag. W1-W2 jumped from -0.09 to +0.35 [C2] (K3, K4). The 2018-20 median excess is -0.41 mag in W1 (20 sigma) and -0.80 mag in W2 (39 sigma) (K14, K15). Subtracting the photosphere leaves an excess equal to 45% (W1) and 110% (W2) of the stellar flux. That is an excess colour of about 0.9 mag, a blackbody of about 1000 K [C3]. This is my hand arithmetic; no tool computes it.
- **Infrared decay.** W1-W2 fell from +0.32 (2020) to +0.17 (2021-22) to -0.09 (2023-11), with W1 tracking colour at r = -0.98. By 2023-24, W1 and W2 match 2014-17 to within 0.01 mag [C4] (K4, K16, K17).
- **Optical event.** AAVSO starts on 2021-08-28 (erratum: C5 says 08-26) already 1.15 mag below the Gaia-implied V = 13.52 (K60, K18). It shows 18 dips, up to 1.8 mag below a running baseline, all between 2021-08 and 2022-06 [C5] (K8).
- **The infrared led.** TESS sectors 8 (2019-02) and 34-35 (2021-01 to 03) show no dip deeper than 0.05 mag (K29, K31, K32). The fast dipping therefore began at least about 2.9 years after the infrared turned on [C6]. The caveat: TESS is normalised per sector.
- **Colour of the dimming.** dB/dV = 1.55 against 1.32 for interstellar dust, and dB/dI = 2.86 against 2.24, with r = 0.90-0.98 [C7] (K36-K38). This is steeper than interstellar reddening, so the occulter is small grains, not large grains or a solid body [C8].
- **Recovery and quiet.** The V seasonal medians are 13.587 (2022/23), 13.506 (2024/25) and 13.489 (2025/26) [C9] (K19, K20, K44). The optical recovery coincides with the infrared decay. Same-season Feb-Jun 2025 against Feb-Jun 2026 differs by -0.0045 mag in V, 0.000 in B and -0.004 in I [C10] (K55-K57), and October 2026 matches (K58).

## What the Skeptic said and what I did about it

- **Baseline (warn).** Correct and important: AAVSO begins mid-event. I used Gaia DR3 for "normal" and NEOWISE 2014-17 for the infrared baseline. I never used AAVSO's own median.
- **NEOWISE blend (warn).** One red neighbour (G = 16.9, BP-RP = 1.84) sits 3.85" away. It is 3.8% of the G flux, so it cannot make 1-2 mag optical dips. To fake the infrared excess it would need to brighten about 5x in W1 and 12x in W2 for four years, then fade just as the target recovers [C14] (K40). That is contrived but not excluded.
- **1-day alias in V (warn).** This is the nightly cadence. From 2-400 d the only peak is 323 d, power 0.08, near the yearly window [C16] (K61). The dips do not repeat.
- **Confirmation (pass).** I disagree with this pass. All optical evidence for the event comes from one observer (HMB), and no TESS sector overlaps the dips [C15]. The pass describes the dataset, not the event.

I also found two artifacts the Skeptic missed. The first is a step on 2025-02-16: I brightens 0.12 mag (15.7 sigma), R 0.05 mag, B and V 0.01-0.02 mag. A brightening that grows toward the red is the opposite of dust clearing, so it is a calibration change [C11, C12] (K46-K50). The second is a two-night "flare" in June 2026 that appears in some filters and not others taken minutes apart [C13] (K10-K13). This observer can make 0.1-0.5 mag artifacts. That is exactly why I trust the 2021-22 event: it is consistent across all four filters and has the colour of physical dust.

## Hypotheses (ranked)

1. **H1 collision_debris: favored, 0.60.** It explains the sudden hot infrared excess, the delayed chromatic dips, the joint recovery and the silence since. It is in tension with geometry: 1000 K blackbody dust sits at about 0.08 au, where an orbit takes about 8 days, so why did it take 3 years to transit [C17]? Superheated small grains farther out, or a hot emitter that differs from the occulter, would resolve this. *Falsified by:* the excess belonging to the neighbour, periodic recurrence of the dips, or a renewed dimming with no new infrared.
2. **H2 dust_occultation: live, 0.25.** Generic dust passed in front of the star. It fits the optical equally well but treats the coupled infrared turn-on as coincidence. *Falsified by:* an infrared event without dips, or dips without infrared, in the future.
3. **H3 eclipse_companion: disfavored, 0.05.** There is no period, the dips are not grey, and it does not explain the 1000 K excess.
4. **H4 artifact_blend: disfavored, 0.04.** See the blend discussion above.
5. **H5 artifact_instrumental: disfavored, 0.03.** It needs an artifact that fakes physical colours and coincides with an independent infrared event. *Falsified by:* any second optical light curve of 2021-22.
6. **H6 yso_dipper: disfavored, 0.03.** There was no excess before 2018 or after 2023.

## Contamination, and the literature

I cannot be blind: I remember Kenworthy et al. 2023 (Nature). They proposed that a collision between planets left a hot, expanded remnant whose debris cloud later transited the star. The `literature` tool returned nothing (K85; a bug, since fixed: its SIMBAD query used the reserved word `year` and swallowed the error), so this comparison is from memory and should be checked. The data agree with what I remember on the points they can test: the infrared led the optical by years, the excess was about 1000 K, and the dips were non-grey. The data cannot test planet masses or the post-impact body. Those are the paper's interpretation, not something these light curves show.

## What's new since the paper (2023-2026)

- The infrared excess vanished completely by 2023-11, at the 0.01 mag level (K16, K17).
- The optical recovered fully and stayed flat. There were no new dips in 2024, 2025 or 2026, and the change between 2025 and 2026 is under 0.005 mag [C10].
- The remaining "recovery" in I and R during 2025 was a calibration step, not the star [C12].
- TESS shows a 4.13 d periodicity [C16] (K35). It might be rotation of a fairly young G star, which is speculation, or a neighbour in the 21" pixels.

## Predictions (sealed today; graded against AAVSO V)

- **P1, p = 0.88.** The median for Jan-Jun 2027 will be less than 0.05 mag fainter than the median for Jan-Jun 2026 (13.486).
- **P2, p = 0.40, the coin flip.** The median for Jan-Jun 2027 will be more than 0.005 mag *brighter* than Jan-Jun 2026, meaning residual clearing continues.
- **P3, p = 0.08.** Over 2027-01 to 2028-06, the faintest 2% of points will be more than 0.2 mag below the 2026 median. That would be a new dip episode.

If the observer stops, all three come out "unresolvable", which is a real risk with one observer.

## What I could not check

- There is one optical observer, and ASAS-SN (which named this star) was unavailable.
- There is no optical light curve between Gaia (mid-2017) and AAVSO (2021-08), so I do not know when the dimming began. I only know when it was not happening (the TESS sectors).
- There are no spectra (gas, accretion, grain composition), no data longward of 4.6 microns and no infrared after 2024-04.
- The 1000 K temperature is a two-band blackbody estimate done by hand.
- I could not check the 4.13 d signal sector by sector.

## Feature requests for Oddsky

- Fix `literature`, which silently returned nothing. (Fixed in oddsky 0.2.0.)
- Add a time window to `find_excursions`, `periodogram` and `cross_band`, so I can ask "any dips in 2024-26?" with a local noise level. The global noise of 0.035 mag hides 0.05 mag events in quiet years.
- Add an infrared-excess tool that subtracts the photosphere and returns colour, temperature and fractional flux.
- Use a piecewise changepoint for rise-then-decay shapes.
- Add a per-sector TESS view.
- Add `check_prediction --dry-run`.
- Add a Skeptic check for step changes concentrated in one filter.
