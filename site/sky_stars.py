#!/usr/bin/env python3
"""Pack the background sky: Hipparcos (new reduction, van Leeuwen 2007) stars brighter than Hp 9.3,
fetched from the ESA Gaia archive's copy, into web/data/sky/stars.bin.

    python3 site/sky_stars.py

Record (6 bytes, little-endian, brightest first): uint16 RA (0-360 deg), int16 Dec (±90 deg),
uint8 magnitude ((Hp + 2) × 20), int8 B−V (× 50). 90,020 stars, 540 kB (~380 kB over the wire).
"""

import csv
import io
import struct
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "web/data/sky/stars.bin"
TAP = "https://gea.esac.esa.int/tap-server/tap/sync"


def fetch() -> list[dict]:
    rows = []
    for lo, hi in [(-90, -30), (-30, 0), (0, 30), (30, 91)]:  # the archive caps a synchronous query at 50,000 rows
        q = f"SELECT ra, dec, hp_mag, b_v FROM public.hipparcos_newreduction WHERE hp_mag < 9.3 AND dec >= {lo} AND dec < {hi}"
        data = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": q}).encode()
        rows += list(csv.DictReader(io.StringIO(urllib.request.urlopen(TAP, data=data, timeout=170).read().decode())))
    return rows


def pack(rows) -> bytes:
    rows = sorted(rows, key=lambda r: float(r["hp_mag"]))
    out = bytearray()
    for r in rows:
        ra, dec, m = float(r["ra"]), float(r["dec"]), float(r["hp_mag"])
        bv = float(r["b_v"]) if r["b_v"] not in ("", None) else 0.6
        out += struct.pack("<HhBb", round(ra / 360 * 65535) % 65536, round(dec / 90 * 32767),
                           max(0, min(255, round((m + 2) * 20))), max(-127, min(127, round(bv * 50))))
    return bytes(out)


if __name__ == "__main__":
    rows = fetch()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(pack(rows))
    print(f"{len(rows)} stars → {OUT} ({OUT.stat().st_size // 1024} kB)")
