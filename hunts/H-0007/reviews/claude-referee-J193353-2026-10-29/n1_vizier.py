"""Referee J193353: VizieR (IDIA mirror) cone searches for variable catalogues and Gaia DR3 neighbours, with a
positive control per catalogue (nearest entry within 1 deg, to show the query/table works).
uv run python hunts/H-0007/reviews/claude-referee-J193353-2026-10-29/n1_vizier.py ; raw output saved to /tmp/j1933nov/"""
from pathlib import Path
from urllib.parse import quote
from oddsky.data.http import request

RA, DEC = 293.471115, -21.3037472
BASE = "https://vizier.idia.ac.za/viz-bin/asu-tsv"
OUT = Path("/tmp/j1933nov"); OUT.mkdir(exist_ok=True)
Q = [("B/vsx/vsx", 120, ""), ("II/366", 30, ""), ("J/ApJS/249/18", 30, ""), ("I/358/vclassre", 30, ""),
     ("I/358", 30, ""), ("J/AJ/156/241", 30, ""), ("J/MNRAS/486/1907", 30, ""), ("I/350/gaiaedr3", 30, "&-out=Source,Gmag&-out.add=_r"),
     ("I/355/gaiadr3", 15, "&-out=Source,RA_ICRS,DE_ICRS,Gmag,BP-RP,Plx,pmRA,pmDE,RUWE,VarFlag&-out.add=_r")]


def run(src, rs, extra, nmax=200):
    url = f"{BASE}?-source={quote(src, safe='/')}&-c={RA}%20{DEC}&-c.rs={rs}&-out.max={nmax}&-sort=_r&-out.add=_r{extra}"
    try:
        txt = request("GET", url, timeout=120).text
    except Exception as e:
        txt = f"ERROR {e}"
    return url, txt


for src, rs, extra in Q:
    url, txt = run(src, rs, extra)
    (OUT / (src.replace("/", "_") + f"_r{rs}.tsv")).write_text(txt)
    rows = [ln for ln in txt.splitlines() if ln and not ln.startswith("#")]
    print(f"\n=== {src} r<{rs}\"  URL: {url}")
    print("\n".join(rows[:30]) if rows else "(no rows)")
    errs = [ln for ln in txt.splitlines() if ln.startswith("#INFO\tError") or ln.startswith("ERROR")]
    if errs: print("NOTE:", errs[:3])
    if not rows and src != "I/355/gaiadr3":
        url2, t2 = run(src, 3600, "", nmax=2)
        r2 = [ln for ln in t2.splitlines() if ln and not ln.startswith("#")]
        print(f"  control (r<1 deg, nearest): {url2}")
        print("  " + "\n  ".join(ln[:200] for ln in r2[:8]) if r2 else "  control: no rows within 1 deg")
