# Referee inputs, 2026-10-27 (archived 2026-10-28)

The referee's field-star, centroid and AllWISE checks for OS-0014 ran outside the Oddsky tools, on files that only
existed in a temporary directory. They are kept here so those checks can be reproduced.

- `f14.tbl.steps.csv`: per-star W1/W2 visit-median change across the step (or event) for every AllWISE field star
  in the 150" NEOWISE cone (`d_w1`, `d_w2`, pre-step medians, separation in arcsec). Made by `scripts/field.py`.
- `f14.tbl.target.csv`: the target's NEOWISE single exposures from the same cone (centroids, rchi2, flags).
- `aw14.tbl`, `mep14.tbl`: AllWISE source and multi-epoch photometry at the target (IRSA Gator).
- `scripts/`: `fetch_field.py` (IRSA Gator cone; re-creates the 14 MB raw table `f14.tbl`, not kept here),
  `field.py`, `target.py`, `viz.py`.
