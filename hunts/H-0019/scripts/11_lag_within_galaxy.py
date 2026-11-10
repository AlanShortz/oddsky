"""Exploratory: does the excess grow with the time between visits inside one galaxy? Uses every clean pair of visits of
each star in M33 and NGC 300 (one randomly chosen pair per star per lag bin), boxes as in 04_measure. Writes work/lag_within.csv."""
import pathlib
import numpy as np, pandas as pd
from oddsky.data import hsc

RUN = pathlib.Path.home() / "oddsky-runs/h0019"; HERE = pathlib.Path(__file__).resolve().parents[1]
rng = np.random.default_rng(11); rows = []
BINS = [(0, 10), (10, 100), (100, 400), (400, 1000), (1000, 2500), (2500, 6000)]
for key in ("MESSIER033", "NGC0300"):
    det = pd.read_parquet(RUN / f"hsc/{key}_det.parquet")
    det = det[(det.Flags == 0) & det.CI.between(0.85, 1.30)]
    box = pd.read_parquet(HERE / f"work/pairs/{key}.parquet")[["MatchID", "box", "rel"]].drop_duplicates("MatchID")
    det = det[det.MatchID.isin(box[box.box.isin(["agb", "rgb"])].MatchID)]
    p = hsc.pairs(det); p = p[p.nsplit == 1]
    grp = p.groupby(["img1", "img2"]).dmag
    p = p.assign(d=p.dmag - grp.transform("median"), nimg=grp.transform("size")); p = p[p.nimg >= 30].merge(box, on="MatchID")
    for lo, hi in BINS:
        s = p[(p.lag >= lo) & (p.lag < hi)]
        s = s.iloc[rng.permutation(len(s))].drop_duplicates("MatchID")
        a, r = s[s.box == "agb"], s[s.box == "rgb"]
        if len(a) < 100 or len(r) < 100:
            continue
        f1, f2 = (a.d.abs() > 0.3).mean(), (r.d.abs() > 0.3).mean()
        rows.append(dict(gal=key, lag_lo=lo, lag_hi=hi, n_agb=len(a), n_rgb=len(r), f_agb=round(f1, 4), f_rgb=round(f2, 4), E03=round(f1 - f2, 4),
                         se=round(float(np.sqrt(f1 * (1 - f1) / len(a) + f2 * (1 - f2) / len(r))), 4), n_image_pairs=s.groupby(["img1", "img2"]).ngroups))
df = pd.DataFrame(rows); df.to_csv(HERE / "work/lag_within.csv", index=False); print(df.to_string(index=False))
