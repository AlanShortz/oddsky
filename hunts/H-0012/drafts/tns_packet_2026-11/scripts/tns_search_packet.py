"""TNS packet 2026-11: public TNS web searches for every candidate (tns_validation/tns_search.py, generalised).

60" cones with unreal=all and no date limit at every candidate position, plus host-name searches for the hosts of the
candidates that pass the light-curve screen. Requests are paced >= 60 s apart (a 60 s wait also precedes the first,
so back-to-back invocations stay paced). HTTP 429, any non-200 status, an exception or an HTML body is recorded as an
ERROR, never as "nothing found"; a 200 header-only CSV is an explicit empty result.

    uv run python hunts/H-0012/drafts/tns_packet_2026-11/scripts/tns_search_packet.py
Outputs: ~/oddsky-runs/imaging/scratch/tns-packet-2026-11/tns/
"""
import datetime as dt
import io
import json
import time
from pathlib import Path

import pandas as pd
import requests

OUT = Path.home() / "oddsky-runs/imaging/scratch/tns-packet-2026-11/tns"
OUT.mkdir(parents=True, exist_ok=True)
URL = "https://www.wis-tns.org/search"
UA = {"User-Agent": "Mozilla/5.0"}
BASE = {"format": "csv", "num_page": 500}

POS = {  # rank in triage_h0012b -> (label, ra, dec); WISE centroids for the two that pass the screen
    3: ("NGC4945_obs3", 196.469723, -49.416201),
    8: ("M81_OS-0035", 148.739293, 69.146800),
    13: ("NGC55_obs13", 3.75579, -39.2033),
    23: ("IC342_obs23", 56.5658, 68.1491),
    17: ("HolmII_obs17", 124.80276, 70.71872),
    20: ("M101_obs20", 210.854, 54.5073),
    29: ("NGC1744_obs29", 74.9977, -26.0432),
    27: ("UGCA127_obs27", 95.2591, -8.4826),
    31: ("NGC300_obs31", 13.57636, -37.58393),
    32: ("NGC4214_obs32", 183.92217, 36.30241),
    33: ("NGC253_obs33", 11.9774, -25.2047),
    34: ("NGC4656_obs34", 190.896, 32.1797),
    35: ("NGC4656_obs35", 190.92204, 32.08198),
    36: ("KKR59_obs36", 315.85568, 57.29008),
    37: ("NGC925_obs37", 36.75536, 33.57473),
    39: ("ESO274-001_obs39", 228.52859, -46.82968),
}
QUERIES = {f"cone60_{lab}": {"ra": ra, "decl": dec, "radius": 60, "coords_unit": "arcsec", "unreal": "all"}
           for _, (lab, ra, dec) in POS.items()}
for h in ("NGC4945", "NGC 4945", "M81", "NGC3031", "NGC 3031", "M 81"):
    QUERIES[f"host_{h.replace(' ', '_')}"] = {"hostname": h, "unreal": "all"}

log = []
for name, q in QUERIES.items():
    time.sleep(61)
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
        rec["result"] = "ERROR: empty body (200) - not a null result"
    elif text.lstrip().startswith("<"):
        rec["result"] = "ERROR: HTML returned instead of CSV (captcha/blocked?) - not a null result"
    else:
        d = pd.read_csv(io.StringIO(text))
        rec["n"] = len(d)
        rec["result"] = "ok" if len(d) else "ok, 0 rows (header only)"
        rec["rows"] = d[[c for c in ("Name", "RA", "DEC", "Obj. Type", "Host Name", "Reporting Group/s",
                                      "Discovery Data Source/s", "Disc. Internal Name", "Disc. Instrument/s",
                                      "Discovery Mag/Flux", "Discovery Filter", "Discovery Date (UT)", "Sender")
                         if c in d]].astype(str).to_dict("records")
    log.append(rec)
    print(json.dumps({k: v for k, v in rec.items() if k != "rows"}), flush=True)
    for row in rec.get("rows", [])[:80]:
        print("   ", row, flush=True)
    (OUT / "tns_search_log.json").write_text(json.dumps(log, indent=1))
