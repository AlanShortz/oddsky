"""H-0011 pilot, step 7: queue ATLAS forced photometry (reduced images, 2015-) for at most 5 top candidates.

Submits only; does not wait (one task takes minutes to hours on the shared queue). Task URLs go to
work/atlas_tasks.json; fetch later with oddsky.data.atlas.status / download / parse.
Needs ATLAS credentials:  set -a; . ~/.config/oddsky/atlas.env; set +a

usage: 07_atlas_submit.py "<main_id>" ["<main_id>" ...]   (looked up in work/stats_mc.csv, stats_gal.csv)
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
from oddsky.data import atlas  # noqa: E402
from oddsky.data.provenance import now_iso  # noqa: E402

WORK = Path(__file__).resolve().parents[1] / "work"
MAX_TASKS = 5


def main(names: list[str]):
    if len(names) > MAX_TASKS:
        raise SystemExit(f"at most {MAX_TASKS} ATLAS tasks in this pilot")
    st = pd.concat([pd.read_csv(WORK / "stats_mc.csv"), pd.read_csv(WORK / "stats_gal.csv")], ignore_index=True)
    out_path = WORK / "atlas_tasks.json"
    tasks = json.loads(out_path.read_text()) if out_path.exists() else []
    done = {t["main_id"] for t in tasks}
    if not atlas.available():
        raise SystemExit("no ATLAS credentials in the environment")
    for n in names:
        if n in done:
            print("already queued", n)
            continue
        r = st[st.main_id == n].iloc[0]
        url = atlas.submit(float(r.ra), float(r.dec))
        tasks.append(dict(main_id=n, ra=float(r.ra), dec=float(r.dec), task_url=url, submitted=now_iso(),
                          mjd_min=atlas.MJD_MIN_DEFAULT, use_reduced=True))
        print(n, url, flush=True)
        out_path.write_text(json.dumps(tasks, indent=1))


if __name__ == "__main__":
    main(sys.argv[1:])
