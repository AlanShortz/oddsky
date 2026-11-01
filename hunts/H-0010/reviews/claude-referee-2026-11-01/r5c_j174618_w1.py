"""r5c: J174618's W1/W2 magnification at the 2015-03-19 NEOWISE visit under explicit baseline assumptions.
Event: one detection per frame at 0.19" from the Gaia star, W1 8.76, W2 8.96 (r5; 11 frames, all nb=1, 7 clean).
Baseline: in single exposures the star is never extracted on its own; the only detection within 8" sits 4.5-5.5" SE
(the 2MASS K=11.66 neighbour at 6.3", blended with the star; nb=2). The survey's visit baseline (W1 10.92) comes from the
1-2 frames per visit where that blend's centroid fell inside 3". Star-only baselines: AllWISE (deblended, nb=3) W1 11.06,
W2 11.40; 2MASS K 11.63 with K-W1 0.2-0.3 for a reddened giant -> W1 11.3-11.4. The event detection may include part of the
neighbour (W1 ~11.4) -- between none and all of it. Run: uv run python -I hunts/H-0010/reviews/claude-referee-2026-11-01/r5c_j174618_w1.py"""
ev1, ev2 = 8.76, 8.96
print("survey-style ratio (baseline = blend at the neighbour position, W1 10.92):", round(10 ** (0.4 * (10.92 - ev1)), 2))
for star in (11.06, 11.25, 11.40):
    for nb, lab in ((None, "no neighbour flux in the event detection"), (11.40, "neighbour (W1~11.4) fully merged")):
        a = 10 ** (0.4 * (star - ev1)) - (10 ** (0.4 * (star - nb)) if nb else 0)
        print(f"star W1 {star}: {lab}: A_W1 = {a:.1f}")
print("W2 against AllWISE W2 11.40:", round(10 ** (0.4 * (11.40 - ev2)), 1))
