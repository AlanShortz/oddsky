"""H-0009: queue ATLAS forced photometry (reduced images, full history) for ten strong unexplained events (work/sky4_strong.csv)
that ATLAS can cover: Gaia G <= 19, event after 2015.6 (ATLAS start), dec > -45 before 2022 (Hawaii units only), no Gaia alert,
not already followed up (H-0008's queue, OS-0016/17/18/19), not saturated in ATLAS; ranked by |dW1| with a bonus for multi-visit
events. Writes work/atlas/queue.csv. Wait with ~/oddsky-runs/h0007/atlas_wait.py URL OUT.
usage: hunt_h0009_atlas_queue.py"""

import os

import pandas as pd

from oddsky.data import atlas

PICK = ["J172057.02-414201.2", "J185035.91-014014.4", "J025145.03+602012.5", "J170153.51-425620.0", "J182621.38-175812.7",
        "J180402.28-181847.5", "J184240.11-052241.7", "J174401.99-382512.2", "J173349.59-264330.5", "J064439.73+011503.3"]
W = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hunts", "H-0009", "work")
s = pd.read_csv(os.path.join(W, "sky4_strong.csv"), dtype={"g_source_id": str})
rows = []
for d in PICK:
    r = s[s.designation == d].iloc[0]
    url = atlas.submit(float(r.ra), float(r.dec))
    print(d, url, flush=True)
    rows.append({"designation": d, "ra": r.ra, "dec": r.dec, "t_neowise": r.t, "dw1": r.dw1, "nblock": r.nblock, "task": url})
pd.DataFrame(rows).to_csv(os.path.join(W, "atlas", "queue.csv"), index=False)
