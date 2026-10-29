"""Referee J193353: parse the KMTNet 2020 event page (saved at /tmp/j1933nov/kmt2020.html from
https://kmtnet.kasi.re.kr/~ulens/event/2020/) and report the RA/Dec envelope and the event nearest the target.
uv run python -I .../n5_kmt2020.py /tmp/j1933nov/kmt2020.html"""
import re, sys
import numpy as np

RA, DEC = 293.471115, -21.3037472
html = open(sys.argv[1], encoding="utf-8", errors="replace").read()
rows = re.findall(r"(KMT-2020-BLG-\d+).*?(\d{2}:\d{2}:\d{2}\.\d+)\D+?(-?\d{2}:\d{2}:\d{2}\.\d+)", html, flags=re.S)
seen = {}
for name, ra, dec in rows:
    if name in seen: continue
    h, m, s = map(float, ra.split(":")); sg = -1 if dec.startswith("-") else 1
    d, dm, ds = map(float, dec.lstrip("-").split(":"))
    seen[name] = (15 * (h + m / 60 + s / 3600), sg * (d + dm / 60 + ds / 3600))
n = np.array(list(seen)); ra = np.array([v[0] for v in seen.values()]); de = np.array([v[1] for v in seen.values()])
print(f"{len(n)} KMT-2020 events parsed; RA {ra.min():.2f}..{ra.max():.2f} deg, Dec {de.min():.2f}..{de.max():.2f}")
r1, d1, r2, d2 = map(np.radians, (RA, DEC, ra, de))
sep = np.degrees(2 * np.arcsin(np.sqrt(np.sin((d2 - d1) / 2) ** 2 + np.cos(d1) * np.cos(d2) * np.sin((r2 - r1) / 2) ** 2)))
for i in np.argsort(sep)[:3]:
    print(f"  {n[i]} RA {ra[i]:.4f} Dec {de[i]:.4f} sep {sep[i]:.2f} deg")
