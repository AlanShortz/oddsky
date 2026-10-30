"""r19b: redo r19's raw-event lookup without the float64 upcast (r19 concatenated empty per-pixel tables, the very bug
hunt_h0008_events.py warns about; its 'not in raw event table' result is void). Which of the bright missed Zhai events are in
the raw sky3lens event table at all?"""
import glob, os
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
want = {2724024301351007698: "ZTF19abagvae", 2775018201351043648: "ZTF21abmnkml", 2749006101351043120: "ZTF21abrgqfr",
        2615021301351002491: "ZTF21aawqeqn", 2864009101351065887: "ZTF21acqomnw", 2761007601351043279: "ZTF18absrimp",
        2711018201351020504: "ZTF22abcfjfp (recovered)", 2813101501351057452: "ZTF22aaajzoi (recovered)"}
hits = []
for f in glob.glob(os.path.expanduser("~/oddsky-runs/h0008/events/*.parquet")):
    d = pd.read_parquet(f)
    if "allwise_cntr" not in d:
        continue
    if len(d):
        d = d[d.allwise_cntr.astype("int64").isin(want)][["allwise_cntr", "kind", "edge", "t", "dw1", "dw2", "n_visits"]]
        if len(d):
            hits.append(d.assign(file=os.path.basename(f)))
h = pd.concat(hits) if hits else pd.DataFrame()
print(h.assign(name=h.allwise_cntr.map(want)).to_string(index=False) if len(h) else "none")
print("not in the raw event table:", [v for k, v in want.items() if len(h) == 0 or k not in set(h.allwise_cntr)])
