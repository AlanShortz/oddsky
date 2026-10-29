"""Referee J193353: SIMBAD cone search (CfA mirror, CDS fallback), 30" and 120". uv run python .../n4_simbad.py"""
from pathlib import Path
from oddsky.data.http import request

OUT = Path("/tmp/j1933nov")
for host in ("https://simbad.cfa.harvard.edu", "https://simbad.cds.unistra.fr"):
    for rad in (30, 120):
        url = (f"{host}/simbad/sim-coo?Coord=293.471115+-21.3037472&Radius={rad}&Radius.unit=arcsec"
               f"&output.format=ASCII&list.idsel=on&list.otypesel=on&list.coo=on")
        try:
            txt = request("GET", url, timeout=90, retries=2).text
        except Exception as e:
            txt = f"ERROR {e}"
        (OUT / f"simbad_{host.split('//')[1].split('.')[1]}_r{rad}.txt").write_text(txt)
        print(f"\n=== {url}\n" + txt[:3000])
