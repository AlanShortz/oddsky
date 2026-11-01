"""r7a: TNS cone search (60") for the 21 candidates, 50 s between requests. A result counts as 'none' only if the HTTP
status is 200 and the body is a CSV whose header has a 'Name' column; HTTP 429 or anything else is recorded as ERROR.
Writes data/tns.csv. Run: uv run python -I hunts/H-0010/reviews/claude-referee-2026-11-01/r7a_tns.py"""
import io, os, time
import pandas as pd, requests

HERE = os.path.dirname(os.path.abspath(__file__))
C = pd.read_csv(os.path.join(HERE, "data", "candidates21.csv"), dtype={"source_id": str})
out = []
for c in C.itertuples():
    res = "ERROR not tried"
    for attempt in range(3):
        try:
            r = requests.get("https://www.wis-tns.org/search", params={"ra": c.ra, "decl": c.dec, "radius": 60, "coords_unit": "arcsec",
                             "format": "csv"}, headers={"User-Agent": "Mozilla/5.0 (oddsky referee)"}, timeout=60)
        except Exception as e:  # noqa: BLE001
            res = f"ERROR {str(e)[:60]}"; time.sleep(60); continue
        if r.status_code == 429:
            res = "ERROR HTTP 429"; time.sleep(float(r.headers.get("Retry-After", 150))); continue
        if r.status_code != 200:
            res = f"ERROR HTTP {r.status_code}"; break
        first = r.text.strip().splitlines()[0] if r.text.strip() else ""
        if '"Name"' not in first and "Name" not in first.split(","):
            res = f"ERROR unexpected body: {r.text[:80]!r}"; break
        d = pd.read_csv(io.StringIO(r.text))
        res = "none (valid CSV, 0 rows)" if d.empty else "; ".join(f"{a} ({b}, {e})" for a, b, e in zip(d["Name"], d["Obj. Type"], d["Discovery Date (UT)"]))
        break
    out.append((c.name, c.source_id, res))
    print(c.name, res, flush=True)
    pd.DataFrame(out, columns=["name", "source_id", "tns"]).to_csv(os.path.join(HERE, "data", "tns.csv"), index=False)
    time.sleep(50)
