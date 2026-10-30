"""r6: novelty re-check (outside the Oddsky tools). Every failure is recorded as UNKNOWN, never as 'nothing'.
 - local reference tables (KMT 2016-24, OGLE EWS, GVS, Gaia DR3 ML, Zhai+2024, TNS-reported) and the full Gaia alerts index
   (hunts/H-0005/alerts.csv, all classes, to the end of Gaia observations in Jan 2025);
 - TNS cone search 60" (one request per 30 s);
 - MOA 2022 and KMTNet 2022 public alert pages (fetched and parsed for coordinates);
 - ASAS-SN variable-star database cone."""
import io
import os
import re
import sys
import time

import astropy.units as u
import numpy as np
import pandas as pd
import requests
from astropy.coordinates import SkyCoord

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import H8, TARGETS  # noqa: E402

UA = {"User-Agent": "Mozilla/5.0 (oddsky referee; contact via github)"}
ROOT = os.path.abspath(os.path.join(H8, "..", ".."))
cs = {k: SkyCoord(T["ra"] * u.deg, T["dec"] * u.deg) for k, T in TARGETS.items()}

print("== local reference tables")
ref = pd.read_csv(os.path.join(H8, "ext", "reference_lenses.csv"))
rc = SkyCoord(ref.ra.values * u.deg, ref.dec.values * u.deg)
for k, c in cs.items():
    s = rc.separation(c).arcmin
    print(f" {k} (l, b = {c.galactic.l.deg:.2f}, {c.galactic.b.deg:+.2f})")
    for src in sorted(ref.source.unique()):
        m = (ref.source == src).values
        j = np.argmin(np.where(m, s, np.inf))
        m22 = m & (ref.t0_mjd > 59580) & (ref.t0_mjd < 59945)
        j22 = np.argmin(np.where(m22, s, np.inf)) if m22.any() else None
        txt = f"   {src:40s} nearest {ref.name.iloc[j]} at {s[j]:.1f}'"
        if j22 is not None:
            txt += f"; nearest 2022 event {ref.name.iloc[j22]} at {s[j22]:.1f}'"
        print(txt)

print("== Gaia Science Alerts index (all classes)")
a = pd.read_csv(os.path.join(ROOT, "hunts", "H-0005", "alerts.csv"), skipinitialspace=True)
a.columns = [c_.strip("# ") for c_ in a.columns]
ac = SkyCoord(a.RaDeg.values * u.deg, a.DecDeg.values * u.deg)
print(f" index: {len(a)} alerts, last {a.Date.max()}")
for k, c in cs.items():
    s = ac.separation(c).arcsec
    near = np.where(s < 60)[0]
    print(f" {k}: alerts within 60\": {len(near)}" + "".join(f"\n    {a.Name.iloc[j]} {s[j]:.1f}\" {a.Date.iloc[j]} {a.Class.iloc[j]} | {a.Comment.iloc[j]}" for j in near))
    o = np.argsort(s)[:6]
    print("   nearest alerts (any distance; used in r7 as Gaia scanning proxies):",
          [(a.Name.iloc[j], round(s[j] / 3600, 2), a.Date.iloc[j][:10]) for j in o])

print("== TNS cone 60\" (paced)")
for k, T in TARGETS.items():
    for attempt in range(3):
        try:
            r = requests.get("https://www.wis-tns.org/search", params={"ra": T["ra"], "decl": T["dec"], "radius": 60, "coords_unit": "arcsec",
                             "format": "csv"}, headers=UA, timeout=60)
            if r.status_code == 429:
                res = "UNKNOWN (HTTP 429 rate limit)"
                time.sleep(60)
                continue
            if r.status_code != 200:
                res = f"UNKNOWN (HTTP {r.status_code})"
                break
            d = pd.read_csv(io.StringIO(r.text)) if r.text.strip() else pd.DataFrame()
            if "Name" not in d.columns:
                res = f"UNKNOWN (no Name column; first bytes {r.text[:80]!r})"
            else:
                res = "none within 60\" (HTTP 200, valid CSV header)" if d.empty else "; ".join(f"{n} ({ty}, {dt})" for n, ty, dt in zip(d["Name"], d["Obj. Type"], d["Discovery Date (UT)"], strict=False))
            break
        except Exception as e:  # noqa: BLE001
            res = f"UNKNOWN ({str(e)[:80]})"
    print(f" {k}: {res}", flush=True)
    time.sleep(30)


def scrape_coords(url, label):
    """Fetch a public alert page; return list of (name, ra, dec) parsed from sexagesimal pairs."""
    try:
        r = requests.get(url, headers=UA, timeout=90)
    except Exception as e:  # noqa: BLE001
        print(f" {label}: UNKNOWN ({str(e)[:80]})")
        return None
    if r.status_code != 200:
        print(f" {label}: UNKNOWN (HTTP {r.status_code})")
        return None
    txt = re.sub(r"<[^>]+>", " ", r.text)
    pairs = re.findall(r"(\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+([+-]?\d{2}:\d{2}:\d{2}(?:\.\d+)?)", txt)
    print(f" {label}: HTTP 200, {len(pairs)} coordinate pairs parsed")
    return pairs


print("== MOA 2022 / KMTNet 2022 alert pages")
for label, url in [("MOA 2022", "https://moaprime.massey.ac.nz/alerts/index/moa/2022"),
                   ("MOA 2022 (old host)", "https://www.massey.ac.nz/~iabond/moa/alert2022/alert.php"),
                   ("KMTNet 2022", "https://kmtnet.kasi.re.kr/~ulens/event/2022/")]:
    pairs = scrape_coords(url, label)
    if pairs:
        pc = SkyCoord([p[0] for p in pairs], [p[1] for p in pairs], unit=(u.hourangle, u.deg))
        for k, c in cs.items():
            s = pc.separation(c).arcmin
            print(f"   {k}: nearest {label} event {s.min():.1f}' away ({len(pairs)} events)")
    time.sleep(3)

print("== ASAS-SN")
for k, T in TARGETS.items():
    for url in (f"https://asas-sn.osu.edu/variables.json?ra={T['ra']}&dec={T['dec']}&radius=0.5",
                f"https://asas-sn.osu.edu/sky-patrol/coordinate/{T['ra']}/{T['dec']}"):
        try:
            r = requests.get(url, headers=UA, timeout=60)
            print(f" {k} {url.split('.edu')[1][:40]}: HTTP {r.status_code}, {len(r.text)} bytes, starts {r.text[:120]!r}")
        except Exception as e:  # noqa: BLE001
            print(f" {k}: UNKNOWN ({str(e)[:80]})")
        time.sleep(2)
