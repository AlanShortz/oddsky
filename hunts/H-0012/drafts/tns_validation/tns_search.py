"""OS-0030 TNS pre-filing check: public TNS web searches near the NGC 3239 transient, paced >= 60 s apart.

HTTP 429 or any non-200 status is recorded as an ERROR (never as "nothing found"); a 200 with an empty CSV body
or a header-only CSV is recorded as an explicit empty result. Raw responses are written outside the repo, to
~/oddsky-runs/imaging/scratch/tns-validation-os0030/tns/.

    uv run python hunts/H-0012/drafts/tns_validation/tns_search.py
"""
import datetime as dt
import io
import json
import time
from pathlib import Path

import pandas as pd
import requests

OUT = Path.home() / "oddsky-runs/imaging/scratch/tns-validation-os0030/tns"
OUT.mkdir(parents=True, exist_ok=True)
URL = "https://www.wis-tns.org/search"
RA, DEC = 156.291224, 17.163778
UA = {"User-Agent": "Mozilla/5.0"}
BASE = {"format": "csv", "num_page": 500}

QUERIES = {
    "cone_60arcsec": {"ra": RA, "decl": DEC, "radius": 60, "coords_unit": "arcsec"},
    "cone_15arcmin": {"ra": RA, "decl": DEC, "radius": 15, "coords_unit": "arcmin"},
    "host_NGC3239": {"hostname": "NGC 3239"},
    "host_NGC3239_nospace": {"hostname": "NGC3239"},
    "internal_WTP": {"internal_name": "WTP"},
}

log = []
for i, (name, q) in enumerate(QUERIES.items()):
    if i:
        time.sleep(60)
    params = {**q, **BASE}
    t = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    try:
        r = requests.get(URL, params=params, headers=UA, timeout=90)
        status, text, url = r.status_code, r.text, r.url
    except Exception as e:  # noqa: BLE001
        status, text, url = f"EXC {e}", "", URL
    (OUT / f"{name}.csv").write_text(text)
    rec = {"query": name, "url": url, "utc": t, "status": status}
    if status != 200:
        rec["result"] = f"ERROR (HTTP {status}) - not a null result"
    elif not text.strip():
        rec["result"] = "EMPTY BODY (200)"
    elif text.lstrip().startswith("<"):
        rec["result"] = "ERROR: HTML returned instead of CSV (captcha/blocked?)"
    else:
        d = pd.read_csv(io.StringIO(text))
        rec["n"] = len(d)
        rec["rows"] = d[[c for c in ("Name", "RA", "DEC", "Obj. Type", "Host Name", "Reporting Group/s",
                                      "Discovery Data Source/s", "Disc. Internal Name", "Disc. Instrument/s",
                                      "Discovery Mag/Flux", "Discovery Filter", "Discovery Date (UT)", "Sender")
                         if c in d]].astype(str).to_dict("records")
    log.append(rec)
    print(json.dumps({k: v for k, v in rec.items() if k != "rows"}), flush=True)
    for row in rec.get("rows", [])[:60]:
        print("   ", row, flush=True)
(OUT / "tns_search_log.json").write_text(json.dumps(log, indent=1))
