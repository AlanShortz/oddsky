"""OS-0030 TNS pre-filing check: fetch public TNS pages (docs, search-form option lists, object pages), one request
every >= 60 s (including a 60 s wait before the first, so back-to-back invocations stay paced). Saves raw HTML/CSV outside the repo and prints status lines; non-200 is printed as an ERROR.

    uv run python hunts/H-0012/drafts/tns_validation/tns_pages.py URL [URL ...]
Output: ~/oddsky-runs/imaging/scratch/tns-validation-os0030/tns/pages/
"""
import datetime as dt
import re
import sys
import time
from pathlib import Path

import requests

OUT = Path.home() / "oddsky-runs/imaging/scratch/tns-validation-os0030/tns/pages"
OUT.mkdir(parents=True, exist_ok=True)
for url in sys.argv[1:]:
    time.sleep(60)  # also before the first request: successive invocations must stay >= 60 s apart
    t = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=90)
        status, text, raw = r.status_code, r.text, r.content
    except Exception as e:  # noqa: BLE001
        status, text, raw = f"EXC {e}", "", b""
    name = re.sub(r"[^A-Za-z0-9]+", "_", url.split("://", 1)[-1])[:150]
    ext = ".pdf" if raw[:4] == b"%PDF" else ".html"
    (OUT / f"{name}{ext}").write_bytes(raw)
    flag = "" if status == 200 else "  <-- ERROR, not a null result"
    print(f"{t} {status} {len(text)} bytes {url} -> {name}{ext}{flag}", flush=True)
