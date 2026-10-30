# Hunt H-0009: the long lenses

**Question.** H-0008 searched every star NEOWISE measured for a one-visit, colour-neutral brightening and recovered 64 known
microlensing events. Its referee measured two blind spots: saturated peaks, and long events (tE > 100 d) that brighten more than
one visit. Black-hole lenses live there. What does a search without those blind spots find?

**Status: survey done (2026-10-30); candidates not yet followed up; not refereed.** Google Cloud Batch run `sky4long`.

## Method

`infra/gcp/neowise_lens.py --mode long` reads the same NEOWISE-R single exposures as H-0008 and changes four things:

| | H-0008 (strict) | H-0009 (long) |
|---|---|---|
| saturated frames (w?sat ≥ 0.05, W1 < 8, W2 < 7) | dropped | kept; `satfrac` per visit |
| frames flagged h or d (lowercase: a real source with a bright neighbour's halo or spike) | dropped | kept; `hdfrac` per visit. Latents and ghosts (p, o) and all uppercase flags still dropped |
| frames fitted with 2-3 components (nb 2-3) | dropped | kept; `nbfrac` per visit |
| event shape | 1-3 consecutive hits, every other visit quiet | one block of up to 6 non-quiet visits, all brighter and colour-neutral, rising to a single peak that is a hit; baseline from the quiet visits only |

The second and third rows are new blind spots, found while testing. A star next to a bright one carries a lowercase `h` on every
frame, and in dense fields most frames are deblended, so H-0008 never searched those stars at all.

**Test on seven pixels** (known events the strict pass missed, plus OS-0017 as a control): the long pass searches 40-70% more stars
per Galactic-plane pixel and recovers ZTF19abagvae (×10 in W1, saturated), ZTF21aawqeqn (×8, halo-flagged), ZTF21abrgqfr (×2.5,
deblended), ZTF21abmnkml (×1.7, deblended) and OS-0017. It still misses ZTF21acqomnw (only 8 NEOWISE visits) and ZTF18absrimp (no
NEOWISE detection associated with its AllWISE source).

Configs: `infra/gcp/sky4long.json` (12,261 pixels), `sky4long_lmc.json` (the 27 densest, on 64 GB machines) and
`sky4long_dense.json` (257 inner-plane pixels that ran out of memory on 7 GB machines, rerun on 32 GB).
Downstream: `scripts/hunt_h0008_events.py` (reads both runs), `scripts/hunt_h0009_efficiency.py` (strict vs long on the same
reference events).

## The survey

| | |
|---|---|
| sky | all 12,288 HEALPix pixels |
| data | 108.3 billion NEOWISE detections |
| stars searched | 211.7 million with ≥ 10 visits (H-0008: 194.7 million) |
| raw events | 3,757 single-peaked brightenings (H-0008 counted 2,465 one-to-three-visit events of both signs) |

**Funnel** (`scripts/hunt_h0008_events.py`, `hunt_h0007_xmatch.py`, `hunt_h0007_vsx.py`, `hunt_h0008_classify.py`,
`hunt_h0008_vet.py`; `work/sky4_*.csv`):

| step | n |
|---|---|
| brightenings not at the first or last visit | 2,638 |
| clean (artifact share, PSF-fit χ², stellar colour, as in H-0008) | 1,308 |
| **known microlensing events** | **118** (114 by position and time) |
| dwarf novae and CVs / young stars / other catalogued variables | 50 / 36 / 212 |
| unclassified | 892 (576 one-visit, 316 two-to-six-visit) |
| strong (≥ 0.4 mag, achromatic to 0.08 mag) and unexplained | 122, 56 of them not in H-0008 |

## What the new rules buy

**Known lenses: 118, against H-0008's 64.** 58 of them are new to this pass. Of those, 31 have halo- or spike-flagged frames
at the event, 25 have deblended frames, 19 brighten on two or more visits and 4 have saturated frames (an event can have
several). The search also finds OS-0018 and the H-0008 candidate J173150 again, now as two-visit events.

**Detection rate on catchable known events** (`scripts/hunt_h0009_efficiency.py`, `work/efficiency.csv`). The reference set
and the magnification at the real NEOWISE visit dates are the H-0008 referee's. Catchable means magnified ≥ 1.6× at a visit
that is not the first or last.

| sample | n | H-0008 (strict) | H-0009 (long) |
|---|---|---|---|
| all catchable | 353 | 18 | 43 |
| outside the inner bulge | 112 | 12 | 22 |
| inner bulge | 241 | 6 | 21 |
| Zhai et al. disk events on stars with AllWISE W1 ≤ 15 | 15 | 6 | 10 |
| tE > 100 d | 126 | 5 | 11 |
| tE ≤ 100 d | 227 | 13 | 32 |

The rate rises about 2.4× overall. Most of the gain is not the long-event rule but the stars the strict pass never searched:
stars beside bright ones and blended ones, which crowd the bulge and the plane.

## Candidates (not followed up)

The 122 strong unexplained events are in `work/sky4_strong.csv`. TNS rate-limited 60 of the lookups again (recorded as errors,
not as "nothing"), so novelty is unchecked for half of them. 102 lie within 5° of the plane and 112 have no ZTF window
and ATLAS is the next check. Two families deserve follow-up first:

- **Long, colour-neutral events** (two to six visits, achromatic): the black-hole-lens search proper. Examples: J160706.90-533729.5
  (×8 over two visits in 2017), J025145.03+602012.5 (×2.5, 2021, beside a bright star), J190857.59+080922.1 (three visits in
  2017-18), J170153.51-425620.0 (two visits in 2015-16). Many two-to-six-visit events are chromatic by 0.1-0.25 mag, which
  points to young stars rather than lenses.
- **Single-visit events on stars the strict pass could not search** (fitted with two or three components on nearly every visit), e.g.
  J194519.88+274002.7 (×3.5, 2016), J182621.38-175812.7 (×2.8, 2020) and J181035.29-105156.9 (×2.5, 2015).

The pass also catches non-stellar transients: J101348.30+180734.9 is the host of SN 2022ffg (Gaia22bxs, a Type II supernova).

## Next

- ATLAS forced photometry for the strongest long, colour-neutral events, and a referee before anything is called a lens.
- Re-query TNS slowly for the 60 failed lookups.
- Gaia DR4 (December 2026) for every event in 2014.7-2020.1.
