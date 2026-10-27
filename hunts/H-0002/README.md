# Hunt H-0002: infrared afterglows on Sun-like stars

ASASSN-21qj was found because its debris cloud crossed our line of sight. Most collisions won't
be aligned that way, but their hot dust glows in the infrared from every direction. So the
infrared-first signature should be more common than the dimming that found ASASSN-21qj, and an
optical search cannot find it.

Method: upload Gaia DR3 FGK main-sequence stars to IRSA TAP, once per NEOWISE time window, and
let the server average W1/W2 per star per window. Look for stars whose W2 brightened by > 0.2 mag
and reddened in W1-W2 while staying photospheric before, then vet each one.

## Status (2026-10-27): parked

The server-side approach works (IRSA TAP accepts an uploaded table joined to `neowiser_p1bs_psd` with
comma-join + `GROUP BY`; `CASE` and grouping on expressions are rejected, so time windows are
encoded as one upload row per star per window). But a 300-star pilot sat in IRSA's async queue for more
than 20 minutes. ASASSN-21qj-like events are plausibly rarer than 1 in 10^5 stars per decade, so the
search needs ~10^6 stars: a bulk catalogue route (unTimely / NEOWISE-R per-epoch coadds, or a CatWISE
vs AllWISE comparison) rather than per-star joins. Pilot script: `.context`-era `irsa_pilot.py`, to
be promoted to `scripts/` when the bulk route is chosen.
