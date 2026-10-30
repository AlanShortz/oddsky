"""H-0008: queue ATLAS forced photometry (reduced images, full history) for the strongest lens-like unclassified events that
ZTF cannot check (south of ZTF, or before 2018), and write the task URLs to work/atlas/queue.csv. Selection: the 66 strong
events (work/sky3_strong.csv), class unclassified, no ZTF window, Gaia G < 19.5, ranked by |dW1|, ten picked by hand for ATLAS
coverage at their epoch (Hawaii units from 2015.5 reach dec ~ -45; Chile and South Africa from 2022).
usage: hunt_h0008_atlas_queue.py   (then wait with ~/oddsky-runs/h0007/atlas_wait.py URL OUT)"""

import os

import pandas as pd

from oddsky.data import atlas

PICK = ["J163539.69-355208.3", "J075219.97-325515.6", "J185846.27+033028.5", "J174440.98-365619.1", "J182120.84-143232.7",
        "J173150.73-444549.3", "J191120.59+134303.3", "J075928.63-221055.1", "J175634.35-205556.9", "J174744.42-374630.7"]
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hunts", "H-0008", "work", "atlas", "queue.csv")
s = pd.read_csv(os.path.join(os.path.dirname(OUT), "..", "sky3_strong.csv"), dtype={"g_source_id": str})
rows = []
for d in PICK:
    r = s[s.designation == d].iloc[0]
    url = atlas.submit(float(r.ra), float(r.dec))
    print(d, url, flush=True)
    rows.append({"designation": d, "ra": r.ra, "dec": r.dec, "t_neowise": r.t, "dw1": r.dw1, "task": url})
pd.DataFrame(rows).to_csv(OUT, index=False)
