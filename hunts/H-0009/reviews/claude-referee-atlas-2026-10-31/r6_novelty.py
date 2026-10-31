"""r6: novelty. Every failure is UNKNOWN, never 'nothing'.
 - local reference lists (hunts/H-0008/ext/reference_lenses.csv: OGLE EWS 2011-26, KMTNet 2016-22, Gaia DR3 ML, Gaia alerts,
   OGLE GVS, ZTF): nearest event of any year, nearest event peaking within 200 d of the NEOWISE visit, and the number of events
   of each survey within 30' (a proxy for the survey footprint);
 - Gaia alerts live list (gsaweb): within 60" at any time; nearest within 60' within 200 d;
 - TNS cone 60" (30 s pacing) for J174401, J180402, J172057;
 - SIMBAD (CfA mirror) 30" for all ten.
OGLE-IV was not observing from 2020 Mar 18 to 2022 Aug 12 (COVID-19)."""
import io
import os
import re
import sys
import time

import numpy as np
import pandas as pd
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA, H9, KEYS, mjd2date, targets  # noqa: E402

UA = {"User-Agent": "Mozilla/5.0 (oddsky referee)"}
T = targets()
ref = pd.read_csv(os.path.join(H9, "..", "H-0008", "ext", "reference_lenses.csv"))


def sep(ra, dec, ra0, dec0):
    return np.degrees(np.arccos(np.clip(np.sin(np.radians(dec)) * np.sin(np.radians(dec0)) + np.cos(np.radians(dec)) *
                                        np.cos(np.radians(dec0)) * np.cos(np.radians(ra - ra0)), -1, 1))) * 60


print("== local reference lists")
for k in KEYS:
    t = T[k]
    ref["sep"] = sep(ref.ra.values, ref.dec.values, t["ra"], t["dec"])
    n = ref.nsmallest(1, "sep").iloc[0]
    intime = ref[np.abs(ref.t0_mjd - t["tvis"]) < 200]
    m = intime.nsmallest(1, "sep").iloc[0] if len(intime) else None
    cnt = ref[ref.sep < 30].groupby("source").size().to_dict()
    print(f" {k} ({mjd2date(t['tvis'])}, l {t['l']:.2f} b {t['b']:+.2f}): nearest any year {n['name']} ({n.source}) {n.sep:.1f}'; nearest "
          f"within 200 d " + (f"{m['name']} ({m.source}, t0 {mjd2date(m.t0_mjd)}) {m.sep:.1f}'" if m is not None else "none") +
          f"; events within 30': {cnt}")

print("== Gaia alerts live list")
try:
    q = requests.get("https://gsaweb.ast.cam.ac.uk/alerts/alerts.csv", headers=UA, timeout=120)
    a = pd.read_csv(io.StringIO(q.text), skipinitialspace=True)
    a.columns = [c.strip("# ") for c in a.columns]
    a["t"] = pd.to_datetime(a.Date).map(lambda d: d.to_julian_date()) - 2400000.5
    print(f" HTTP {q.status_code}: {len(a)} alerts, latest {a.Date.max()}")
    for k in KEYS:
        t = T[k]
        s = sep(a.RaDeg.values, a.DecDeg.values, t["ra"], t["dec"])
        w = s < 1.0
        near = a[np.abs(a.t - t["tvis"]) < 200].assign(sep=s[np.abs(a.t - t["tvis"]) < 200]).nsmallest(1, "sep")
        print(f" {k}: within 60\": " + ("; ".join(f"{r.Name} {r.Date} {r.Class}" for r in a[w].itertuples()) or "none") +
              (f"; nearest within 200 d: {near.Name.iloc[0]} ({near.Date.iloc[0]}) {near.sep.iloc[0]:.1f}'" if len(near) else ""))
except Exception as e:  # noqa: BLE001
    print(" UNKNOWN", e)

print("== TNS 60\" cone")
for k in ("J174401", "J180402", "J172057"):
    t = T[k]
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
            d = pd.read_csv(io.StringIO(q.text)) if q.text.strip() else pd.DataFrame()
            res = ("UNKNOWN (no Name column)" if "Name" not in d else "none within 60\" (HTTP 200, valid CSV header)" if d.empty
                   else "; ".join(" | ".join(str(r[c]) for c in d.columns[:6]) for _, r in d.iterrows()))
            break
        except Exception as e:  # noqa: BLE001
            res = f"UNKNOWN ({str(e)[:80]})"
    print(f" {k}: {res}", flush=True)
    time.sleep(30)

print("== SIMBAD (CfA) 30\"")
for k in KEYS:
    t = T[k]
    try:
        q = requests.get("https://simbad.cfa.harvard.edu/simbad/sim-coo", params={"Coord": f"{t['ra']} {t['dec']}", "Radius": 30,
                         "Radius.unit": "arcsec", "output.format": "ASCII", "list.idsel": "off"}, headers=UA, timeout=60)
        if "No astronomical object found" in q.text:
            print(f" {k}: no object within 30\" (HTTP {q.status_code})")
        else:
            rows = [ln.strip() for ln in q.text.splitlines() if re.match(r"^\s*\d+\s*\|", ln)]
            if not rows:
                rows = [ln.strip() for ln in q.text.splitlines() if "Object" in ln or "Coordinates" in ln][:4]
            print(f" {k}: HTTP {q.status_code}, {len(rows)} rows")
            for ln in rows[:12]:
                print("    ", ln[:200])
    except Exception as e:  # noqa: BLE001
        print(f" {k}: UNKNOWN ({e})")
    time.sleep(2)
