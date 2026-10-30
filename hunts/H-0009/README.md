# Hunt H-0009: the long lenses

**Question.** H-0008 searched every star NEOWISE measured for a one-visit, colour-neutral brightening and recovered 64 known
microlensing events. Its referee measured two blind spots: saturated peaks, and long events (tE > 100 d) that brighten more than
one visit. Black-hole lenses live there. What does a search without those blind spots find?

**Status: running** (Google Cloud Batch run `sky4long`, started 2026-10-30).

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

Configs: `infra/gcp/sky4long.json` (12,261 pixels), `sky4long_lmc.json` (the 27 densest, on 64 GB machines).
Downstream: `scripts/hunt_h0008_events.py` (reads both runs), `scripts/hunt_h0009_efficiency.py` (strict vs long on the same
reference events).
