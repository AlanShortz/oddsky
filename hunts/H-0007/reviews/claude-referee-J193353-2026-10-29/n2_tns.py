"""Referee J193353: TNS cone search (public web csv). uv run python .../n2_tns.py ; raw to /tmp/j1933nov/"""
from pathlib import Path
from oddsky.data.http import request

OUT = Path("/tmp/j1933nov")
for rad in (60, 900, 3600):
    url = (f"https://www.wis-tns.org/search?ra=293.471115&decl=-21.3037472&radius={rad}&coords_unit=arcsec"
           f"&format=csv&num_page=500")
    try:
        r = request("GET", url, timeout=120, retries=2)
        txt = r.text; st = r.status_code
    except Exception as e:
        txt = f"ERROR {e}"; st = None
    (OUT / f"tns_r{rad}.csv").write_text(txt)
    lines = txt.strip().splitlines()
    print(f"\n=== radius {rad}\" status {st} lines {len(lines)}  URL: {url}")
    for ln in lines[:40]:
        print(ln[:400])
