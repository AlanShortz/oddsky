# Hunt H-0005: the Gaia alerts nobody finished

**Question.** Gaia's photometric alert stream (2016-2025, now closed) flagged thousands of stars that changed
and then moved on. Which of the *fading* alerts on ordinary-looking stars were never explained, and what did
those stars do before and after Gaia looked?

**Why this hunt.** An alert is a snapshot taken mid-event. The archives kept recording around it: Pan-STARRS
(2010-2014), WISE/NEOWISE (2010-2024), ZTF (2018-2025), TESS (2018-2026), ATLAS (2015-today), and, further back,
2MASS (1998-2001) and the Palomar sky surveys (1950s, 1990s). A fade that looked like "~1 mag dimming in Gaia
source" can turn out to be one frame of something that has been happening for decades.

## Funnel (2026-10-28; scripts in `scripts/hunt_h0005*.py`, inputs in this directory)

| step | n | what fell out |
|---|---|---|
| Gaia Science Alerts, final list (`alerts.csv`) | 27,076 | |
| fading by > 0.5 mag, historic G < 16.5, class "unknown" | 173 | |
| comment not naming a known class or a young star | 79 | 61 YSO-like, 40 named classes (CV, carbon star, LPV, AGN...) |
| Gaia DR3 parallax/error > 5 and abs G > 4 (dwarfs) | 12 | giants, bulge and Magellanic Cloud sources |
| followed up (alert LC + NEOWISE + ZTF + AllWISE/2MASS + web literature) | 12 | Gaia16bnz: a published CV; Gaia19anb, Gaia19elx: blue, VY Scl-like low states; Gaia18bwg, Gaia19bnf, Gaia22edw: DR3-classified young-star dippers; Gaia21agx: +2 mag since 2021 while the infrared faded, extinction clearing in a Class II young star; Gaia20dhm: slow 1-mag fade, unexplained but not pursued |
| **candidates** | **4** | see below |

## Candidates

- **Gaia20fgk, an Hα-emitting star at 1 kpc that has spent most of 35 years 3-5 mag fainter** (Gaia DR3
  523457286761045120). See [`Gaia20fgk.md`](Gaia20fgk.md). Faint at every sampled epoch 1991.7-2015.5 (absent on a 1991
  Palomar plate, faint in 1994-95, missing from 2MASS 1999, 2010-2015 low in Pan-STARRS, WISE and Gaia DR3 epochs),
  bright 2015.6-2020.4, low again 2020.4-2023.9, bright since; normal in 1954. The referee confirmed the fades are real
  and on the star, and retracted our "Sun-like dwarf behind an external occulter" framing: Gaia sees strong Hα
  emission and a failed GSP-Phot fit, so a young-star fader or a nova-like in low states is likely (~0.7).
- **Gaia20cdd, an old K dwarf with warm dust that keeps going dark** (Gaia DR3 1624711296862985472). See
  [`Gaia20cdd.md`](Gaia20cdd.md). At least ten dimming events 2007-2025 (and a shallow one in early 2026), up to 3.5 mag, hours to ~300 days, seen by
  CRTS, Pan-STARRS, Gaia, ZTF, ATLAS, NEOWISE and TESS; a thick-disk dwarf 1 kpc above the plane with a 500 K infrared excess.
  VSX lists it as a nova-like (NL/VY:); the UV, Hα and colours say otherwise. Our 392.2-day clock was retracted by the
  referee.
- **Gaia20fmb, a dipper with a cold disk far from any star-forming region** (Gaia DR3 2900506558769385088):
  K7-M0 dwarf at 321 pc, 28 deg below the plane; aperiodic dips to 3.2 mag in Gaia (2020-2024) with W1 dimming only
  0.1-0.25 mag (small grains); W1-W2 photospheric but W1-W4 = 3.7. ATLAS shows the dimming still going in October 2026
  (0.4-0.9 mag below its 2019 level). In VSX as an unclassified variable. Not refereed.
- **Gaia20cmg, an outburst recognised from its ending** (Gaia DR3 5332042022123062144): in Vela, 860 pc; W1
  rose from 14.07 (2010) to 11.0 (2017) and fell back to 14.0 (2021-2024), with the optical following (G 15.5 to
  18.8). VSX already types it YSO:; the multi-year infrared outburst behind the alerted fade is not described in any source
  we reached. Not refereed.

## What did not work (kept so nobody repeats it)

Two pilots on the H-0002 sky table preceded this hunt and failed for an instructive reason: a bug in
`oddsky.sky.neowise_pixel.visits()` (see [`../H-0002/BUG-2026-10-28.md`](../H-0002/BUG-2026-10-28.md)) merged one
star's first NEOWISE visit into its neighbour's last. "Vanishing infrared excesses" (1,746 flags) and "grey
single-visit infrared dips" (46,760 flags, 98% of the clean ones in Feb-Oct 2019) were dominated by it, by halos of
bright Miras (o Cet, R Cas, R Dor, L2 Pup, R Hya, theta Aps), and by young stars. The vanishing-dust question was
then taken up properly, in parallel, as [H-0006](../H-0006/).

## Novelty searches (2026-10-28)

Web search (designations, coordinates, TNS/ZTF names), the Gaia alert pages, BHTOM, arXiv 2601.16828 (ZTF
circumbinary occultation candidates), arXiv 2508.03964 (ZTF main-sequence dippers; text and source, not the full table),
**VSX via vsx.aavso.org** (www.aavso.org sits behind Cloudflare): all four candidates are in VSX, entered from the Gaia
alerts (Gaia20fgk NL/VY:, Gaia20cdd NL/VY:, Gaia20cmg YSO:, Gaia20fmb VAR). The variability is catalogued; what is new
here is the history and the nature. **SIMBAD was unreachable all day** (both CDS hosts); VizieR answers at
vizier.china-vo.org. "Not found" means not found in these searches, nothing more.
