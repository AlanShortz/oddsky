"""Large galaxies whose single-cone query times out: fetch the same data in small tiles.

A hexagonal grid of 0.05-degree cones out to RMAX degrees from the centre (not complete coverage; it does not need to be).
Usage: 03b_fetch_tiled.py NAME [RMAX=0.2] [tiles.csv with ra,dec]
"""
import sys, math, time, pathlib
import pandas as pd
from oddsky.data import hsc

RUN = pathlib.Path.home() / "oddsky-runs/h0019"
HERE = pathlib.Path(__file__).resolve().parents[1]
M_TIP, AB_VEGA, APCOR = -4.05, 0.43, 0.25
SUMCOLS = ["MatchID", "MatchRA", "MatchDec", "NumVisits", "NumFilters", "CI", "CI_Sigma", "Extinction", "StartMJD", "StopMJD"]
COLOUR = ["A_F814W", "A_F606W", "A_F555W", "A_F475W", "A_F435W", "W3_F814W", "W3_F606W", "W3_F555W", "W3_F475W", "W3_F110W",
          "W3_F160W", "W2_F814W", "W2_F606W", "W2_F555W"]
name = sys.argv[1]; rmax = float(sys.argv[2]) if len(sys.argv) > 2 else 0.2
row = None
for ln in (RUN / "cat/ungc.tsv").read_text().splitlines():
    p = [x.strip() for x in ln.split("\t")]
    if p[0] == name:
        h, m, s = (float(x) for x in p[1].split()); d, dm, ds = (float(x) for x in p[2].replace("-", "").replace("+", "").split())
        ra = 15 * (h + m / 60 + s / 3600); dec = (-1 if p[2].startswith("-") else 1) * (d + dm / 60 + ds / 3600)
        row = dict(ra=ra, dec=dec, dist=float(p[4]), ab=float(p[9] or 0))
lim = 5 * math.log10(row["dist"] * 1e5) + M_TIP + 0.42 * row["ab"] + AB_VEGA + APCOR + 1.3
step, tiles = 0.085, []
n = int(rmax / step) + 1
for i in range(-n, n + 1):
    for j in range(-n, n + 1):
        x, y = step * (i + 0.5 * (j % 2)), step * j * 0.866
        if math.hypot(x, y) <= rmax:
            tiles.append((row["ra"] + x / math.cos(math.radians(row["dec"])), row["dec"] + y))
if len(sys.argv) > 3:      # a list of tile centres (fields with a revisit, from the MAST observation list) replaces the grid
    tiles = [tuple(x) for x in pd.read_csv(sys.argv[3])[["ra", "dec"]].values]
print(name, len(tiles), "tiles, lim", round(lim, 2), flush=True)
S, D = [], []
cols = SUMCOLS + [c for b in COLOUR for c in (b, b + "_N")]
for k, (ra, dec) in enumerate(tiles):
    t = time.time()
    try:
        s = hsc.summary(ra, dec, 0.05, columns=cols, **{"A_F814W.lt": lim})
        d = hsc.visits(ra, dec, 0.05, "F814W", detector="ACS/WFC", mag_max=lim + 0.5) if len(s) else pd.DataFrame()
    except Exception as e:  # noqa: BLE001
        print(" tile", k, "failed", repr(e)[:100], flush=True); continue
    S.append(s); D.append(d)
    print(f" tile {k}: sum={len(s)} det={len(d)} [{time.time()-t:.0f}s]", flush=True)
    if k % 20 == 19 and any(len(x) for x in D):
        pd.concat([x for x in S if len(x)], ignore_index=True).drop_duplicates("MatchID").to_parquet(RUN / f"hsc/{name.replace(' ', '_')}_sum.partial.parquet")
        pd.concat([x for x in D if len(x)], ignore_index=True).drop_duplicates(["MatchID", "SourceID", "ImageID"]).to_parquet(RUN / f"hsc/{name.replace(' ', '_')}_det.partial.parquet")
key = name.replace(" ", "_")
S = pd.concat([x for x in S if len(x)], ignore_index=True).drop_duplicates("MatchID")
D = pd.concat([x for x in D if len(x)], ignore_index=True).drop_duplicates(["MatchID", "SourceID", "ImageID"])
S.to_parquet(RUN / f"hsc/{key}_sum.parquet"); D.to_parquet(RUN / f"hsc/{key}_det.parquet")
print(name, "sum", len(S), "det", len(D), "images", D.ImageID.nunique(), "span", round(D.StartMJD.max() - D.StartMJD.min()))
