"""r4: TNS cone 60" for the seven stars (one request per 30 s; HTTP 429 or any error = UNKNOWN, never 'none'), then the
object pages of every hit (classification, reporting groups, comments, classification reports)."""
import html
import io
import os
import re
import sys
import time

import pandas as pd
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA, targets  # noqa: E402

H = {"User-Agent": "Mozilla/5.0 (oddsky referee)"}
T = targets()
hits = set()
for k, t in T.items():
    res = "UNKNOWN"
    for attempt in range(3):
        try:
            q = requests.get("https://www.wis-tns.org/search", params={"ra": t["ra"], "decl": t["dec"], "radius": 60,
                             "coords_unit": "arcsec", "format": "csv"}, headers=H, timeout=60)
            if q.status_code == 429:
                res = "UNKNOWN (HTTP 429 rate limit)"
                time.sleep(90)
                continue
            if q.status_code != 200:
                res = f"UNKNOWN (HTTP {q.status_code})"
                break
            d = pd.read_csv(io.StringIO(q.text)) if q.text.strip() else pd.DataFrame()
            if "Name" not in d:
                res = "UNKNOWN (no Name column: " + q.text[:60].replace("\n", " ") + ")"
            elif d.empty:
                res = "none within 60\" (HTTP 200, valid CSV header)"
            else:
                cols = [c for c in ("Name", "Obj. Type", "Discovery Date (UT)", "Discovery Mag/Flux", "Disc. Internal Name",
                                    "Reporting Group", "RA", "DEC") if c in d]
                res = "; ".join(" | ".join(str(r[c]) for c in cols) for _, r in d.iterrows())
                hits.update(n.replace("AT ", "").replace("SN ", "").strip() for n in d["Name"])
            break
        except Exception as e:  # noqa: BLE001
            res = f"UNKNOWN ({str(e)[:80]})"
    print(f"{k}: {res}", flush=True)
    time.sleep(30)

for o in sorted(hits):
    try:
        p = requests.get(f"https://www.wis-tns.org/object/{o}", headers=H, timeout=60)
        open(os.path.join(DATA, f"tns_{o}.html"), "w").write(p.text)
        txt = html.unescape(re.sub(r"<[^>]+>", " | ", re.sub(r"<script.*?</script>", "", p.text, flags=re.S)))
        txt = re.sub(r"(\s*\|\s*)+", " | ", txt)
        print(f"--- {o}: HTTP {p.status_code}")
        for key in ("Type |", "Classification", "Comments", "Remarks", "Internal Names", "Discovery date", "Reporting Group"):
            for m in re.finditer(re.escape(key), txt):
                print(f"   [{key}] {txt[m.start():m.start() + 260]}")
                break
    except Exception as e:  # noqa: BLE001
        print(f"--- {o}: UNKNOWN {e}")
    time.sleep(30)
