"""Queue ATLAS forced photometry (difference images) for six H-0012a leads; record the task URLs.

    set -a; . ~/.config/oddsky/atlas.env; set +a
    uv run python hunts/H-0012/reviews/claude-referee-triage-2026-11-01/atlas_submit.py
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from oddsky.data import atlas

HERE = Path(__file__).resolve().parent
TASKS = [
    ("NGC4945 obs#3", 196.4697, -49.4162),
    ("M81 obs#9", 148.7390, 69.1468),
    ("NGC55 obs#14", 3.75575, -39.2033),
    ("NGC3239 obs#33", 156.2910, 17.1639),
    ("UGCA127 obs#30", 95.2591, -8.4826),
    ("IC342 obs#26", 56.5658, 68.1491),
]
out = []
for lab, ra, dec in TASKS:
    url = atlas.submit(ra, dec, mjd_min=57200.0, use_reduced=False)
    out.append(dict(lead=lab, ra=ra, dec=dec, use_reduced=False, mjd_min=57200.0, task_url=url,
                    submitted=datetime.now(timezone.utc).isoformat(timespec="seconds")))
    print(lab, url, flush=True)
(HERE / "atlas_tasks.json").write_text(json.dumps(out, indent=1))
