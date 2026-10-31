"""r5: online novelty checks. Every failure is UNKNOWN, never 'nothing'.
 - TNS cone 60" (one request per 30 s; HTTP 429 = UNKNOWN (rate limit));
 - SIMBAD (CfA mirror) cone 30";
 - OGLE EWS 2022 page (season start; nearest event), KMTNet 2022 event page, MOA 2022 alert page: nearest coordinates;
 - Gaia alerts: the live alerts.csv (to check events after the local index ends 2025-01-15)."""
import io
import os
import re
import sys
import time

import astropy.units as u
import pandas as pd
import requests
from astropy.coordinates import SkyCoord

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA, targets  # noqa: E402

UA = {"User-Agent": "Mozilla/5.0 (oddsky referee)"}
T = targets()

print("== TNS 60\" cone")
for k, t in T.items():
    res = "UNKNOWN"
    for attempt in range(3):
        try:
            q = requests.get("https://www.wis-tns.org/search", params={"ra": t["ra"], "decl": t["dec"], "radius": 60,
                             "coords_unit": "arcsec", "format": "csv"}, headers=UA, timeout=60)
            if q.status_code == 429:
                res = "UNKNOWN (HTTP 429 rate limit)"
                time.sleep(90)
                continue
            if q.status_code != 200:
                res = f"UNKNOWN (HTTP {q.status_code})"
                break
            open(os.path.join(DATA, f"tns_{k}.csv"), "w").write(q.text)
            d = pd.read_csv(io.StringIO(q.text)) if q.text.strip() else pd.DataFrame()
            if "Name" not in d:
                res = "UNKNOWN (no Name column: " + q.text[:80].replace("\n", " ") + ")"
            elif d.empty:
                res = "none within 60\" (HTTP 200, valid CSV header)"
            else:
                res = "; ".join(" | ".join(str(r[c]) for c in d.columns[:8]) for _, r in d.iterrows())
            break
        except Exception as e:  # noqa: BLE001
            res = f"UNKNOWN ({str(e)[:80]})"
    print(f" {k}: {res}", flush=True)
    time.sleep(30)

print("== SIMBAD (CfA) 30\"")
for k, t in T.items():
    try:
        q = requests.get("https://simbad.cfa.harvard.edu/simbad/sim-coo", params={"Coord": f"{t['ra']} {t['dec']}", "Radius": 30,
                         "Radius.unit": "arcsec", "output.format": "ASCII", "list.idsel": "off"}, headers=UA, timeout=60)
        open(os.path.join(DATA, f"simbad_{k}.txt"), "w").write(q.text)
        if "No astronomical object found" in q.text:
            print(f" {k}: no object within 30\" (HTTP {q.status_code})")
        else:
            rows = [ln for ln in q.text.splitlines() if re.match(r"^\s*\d+\s*\|", ln)]
            first = re.search(r"Object (.+?)\s+---\s+(\S+)", q.text)
            print(f" {k}: HTTP {q.status_code}; " + (f"single object {first.group(1)} ({first.group(2)})" if first else "") +
                  ("\n   " + "\n   ".join(r[:160] for r in rows[:15]) if rows else ""))
            if not rows and not first:
                print("   unparsed:", q.text[:300].replace("\n", " "))
    except Exception as e:  # noqa: BLE001
        print(f" {k}: UNKNOWN ({str(e)[:80]})")
    time.sleep(2)

print("== alert pages, 2022")
pages = {"OGLE EWS 2022": "https://ogle.astrouw.edu.pl/ogle4/ews/2022/ews.html",
         "KMTNet 2022": "https://kmtnet.kasi.re.kr/~ulens/event/2022/",
         "MOA 2022 (moaprime)": "https://moaprime.massey.ac.nz/alerts/index/moa/2022",
         "MOA 2022 (iabond)": "https://www.massey.ac.nz/~iabond/moa/alert2022/alert.php"}
for label, url in pages.items():
    try:
        q = requests.get(url, headers=UA, timeout=90)
        open(os.path.join(DATA, "page_" + re.sub(r"\W+", "_", label) + ".html"), "w").write(q.text)
        txt = re.sub(r"<[^>]+>", " ", q.text)
        pairs = re.findall(r"(\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+([+-]?\d{2}:\d{2}:\d{2}(?:\.\d+)?)", txt)
        line = f" {label}: HTTP {q.status_code}, {len(q.text)} bytes, {len(pairs)} coordinate pairs"
        if pairs:
            pc = SkyCoord([p[0] for p in pairs], [p[1] for p in pairs], unit=(u.hourangle, u.deg))
            for k, t in T.items():
                s = pc.separation(SkyCoord(t["ra"] * u.deg, t["dec"] * u.deg)).arcmin
                line += f"; {k}: nearest {s.min():.1f}' (n within 30': {(s < 30).sum()})"
        print(line, flush=True)
    except Exception as e:  # noqa: BLE001
        print(f" {label}: UNKNOWN ({str(e)[:80]})")
    time.sleep(2)

print("== Gaia alerts live list")
try:
    q = requests.get("https://gsaweb.ast.cam.ac.uk/alerts/alerts.csv", headers=UA, timeout=120)
    a = pd.read_csv(io.StringIO(q.text), skipinitialspace=True)
    a.columns = [c.strip("# ") for c in a.columns]
    ac = SkyCoord(a.RaDeg.values * u.deg, a.DecDeg.values * u.deg)
    print(f" HTTP {q.status_code}: {len(a)} alerts, latest {a.Date.max()}")
    for k, t in T.items():
        s = ac.separation(SkyCoord(t["ra"] * u.deg, t["dec"] * u.deg)).arcsec
        j = s.argsort()[:2]
        print(f" {k}: within 60\": {(s < 60).sum()}; nearest " + "; ".join(f"{a.Name.iloc[i]} {s[i] / 60:.1f}' {a.Date.iloc[i][:10]}" for i in j))
except Exception as e:  # noqa: BLE001
    print(f" UNKNOWN ({str(e)[:80]})")
