"""r6: novelty / prior identifications for the seven stars. Every failure is UNKNOWN, never 'nothing'.
 - local reference tables (hunts/H-0008/ext/reference_lenses.csv: KMT 2016-24, OGLE EWS 2014-25, OGLE GVS, Gaia DR3 ML, Gaia
   alerts with ML class, Zhai/Medford/Rodriguez ZTF lists): nearest of any year and nearest within +-200 d of the event;
 - SIMBAD (CfA mirror) cone 10";
 - VizieR (vizier.idia.ac.za mirror): VSX (B/vsx/vsx), ASAS-SN variables (II/366), OGLE-IV collection of variables (J/ApJS/...
   via the generic 'OGLE' keyword is not reliable, so only VSX and ASAS-SN), Gaia DR3 vari_classifier (I/358/vclassre),
   2MASS PSC and AllWISE quality flags (II/246, II/328);
 - MOA / KMTNet / OGLE EWS online pages for the event year where a page exists.
"""
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
from lib import H8, mjd2date, targets  # noqa: E402

UA = {"User-Agent": "Mozilla/5.0 (oddsky referee)"}
T = targets()
TPK = {"J163539": 57980.0, "J075219": 58208.0, "J174440": 60010.0, "J191120": 59294.0, "J173150": 58311.0,
       "J185846": 57485.0, "J182120": 57472.0}
ref = pd.read_csv(os.path.join(H8, "ext", "reference_lenses.csv"))
rc = SkyCoord(ref.ra.values * u.deg, ref.dec.values * u.deg)

print("== local reference tables")
for k, t in T.items():
    c = SkyCoord(t["ra"] * u.deg, t["dec"] * u.deg)
    s = rc.separation(c).arcmin
    print(f" {k} (l {t['l']:.2f} b {t['b']:+.2f}, event {mjd2date(TPK[k])})")
    for src in sorted(ref.source.unique()):
        m = (ref.source == src).values
        j = int(np.argmin(np.where(m, s, np.inf)))
        mm = m & (np.abs(ref.t0_mjd.fillna(-1e9) - TPK[k]) < 200)
        txt = f"   {src:36s} nearest {ref.name.iloc[j]} {s[j]:.1f}'"
        if mm.any():
            jj = int(np.argmin(np.where(mm, s, np.inf)))
            txt += f"; nearest within 200 d of the event: {ref.name.iloc[jj]} {s[jj]:.1f}'"
        print(txt)


def vizier(cat, ra, dec, r_arcsec, cols="**"):
    for host in ("https://vizier.idia.ac.za", "https://vizier.cfa.harvard.edu"):
        try:
            q = requests.get(f"{host}/viz-bin/asu-tsv", params={"-source": cat, "-c": f"{ra} {dec}", "-c.rs": r_arcsec,
                             "-out": cols, "-out.add": "_r", "-sort": "_r", "-out.max": 20}, headers=UA, timeout=90)
            if q.status_code != 200:
                continue
            lines = [ln for ln in q.text.splitlines() if ln and not ln.startswith("#")]
            if not lines:
                return f"{host.split('//')[1]}: no rows (HTTP 200)"
            hdr = lines[0].split("\t")
            rows = [ln.split("\t") for ln in lines[3:]]
            if not rows:
                return f"{host.split('//')[1]}: none within {r_arcsec}\" (HTTP 200, header present)"
            return f"{host.split('//')[1]}: " + " || ".join("; ".join(f"{h.strip()}={v.strip()}" for h, v in zip(hdr, r, strict=False)
                                                                    if v.strip())[:400] for r in rows[:4])
        except Exception as e:  # noqa: BLE001
            err = str(e)[:80]
            continue
    return f"UNKNOWN ({err if 'err' in dir() else 'all hosts failed'})"


print("== VizieR / SIMBAD")
for k, t in T.items():
    ra, dec = t["ra"], t["dec"]
    print(f" {k}")
    for cat, r_, cols in (("B/vsx/vsx", 30, "**"), ("II/366/catalog", 30, "**"), ("I/358/vclassre", 5, "**"),
                          ("II/328/allwise", 3, "AllWISE,W1mag,e_W1mag,W2mag,e_W2mag,W3mag,e_W3mag,W4mag,e_W4mag,ccf,ex,qph,nb,na"),
                          ("II/246/out", 3, "2MASS,Jmag,Hmag,Kmag,Qflg,Cflg")):
        print(f"   {cat}: {vizier(cat, ra, dec, r_, cols)}")
        time.sleep(1)
    try:
        q = requests.get("https://simbad.cfa.harvard.edu/simbad/sim-coo", params={"Coord": f"{ra} {dec}", "Radius": 10,
                         "Radius.unit": "arcsec", "output.format": "ASCII"}, headers=UA, timeout=60)
        txt = q.text
        if "No astronomical object found" in txt:
            res = "no object within 10\" (HTTP %d)" % q.status_code
        else:
            names = re.findall(r"^\s*\d+\|\s*[\d.]+\|([^|]+)\|([^|]+)\|", txt, re.M)
            first = re.search(r"Object (.+?)  ---  (\S+)", txt)
            res = (f"HTTP {q.status_code}: " + (f"{first.group(1)} ({first.group(2)})" if first else "") +
                   ("; " + "; ".join(f"{a.strip()} ({b.strip()})" for a, b in names[:6]) if names else ""))
            if not first and not names:
                res += " unparsed: " + txt[:200].replace("\n", " ")
    except Exception as e:  # noqa: BLE001
        res = f"UNKNOWN ({str(e)[:80]})"
    print(f"   SIMBAD 10\": {res}")
    time.sleep(1)

print("== online alert pages for the event years")
pages = {"MOA 2017": "https://moaprime.massey.ac.nz/alerts/index/moa/2017",
         "MOA 2018": "https://moaprime.massey.ac.nz/alerts/index/moa/2018",
         "MOA 2023": "https://moaprime.massey.ac.nz/alerts/index/moa/2023",
         "OGLE EWS 2017": "https://ogle.astrouw.edu.pl/ogle4/ews/2017/ews.html",
         "OGLE EWS 2018": "https://ogle.astrouw.edu.pl/ogle4/ews/2018/ews.html",
         "OGLE EWS 2023": "https://ogle.astrouw.edu.pl/ogle4/ews/2023/ews.html",
         "KMTNet 2023": "https://kmtnet.kasi.re.kr/~ulens/event/2023/"}
for label, url in pages.items():
    try:
        q = requests.get(url, headers=UA, timeout=90)
        txt = re.sub(r"<[^>]+>", " ", q.text)
        pairs = re.findall(r"(\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+([+-]?\d{2}:\d{2}:\d{2}(?:\.\d+)?)", txt)
        line = f" {label}: HTTP {q.status_code}, {len(pairs)} coordinate pairs"
        if pairs:
            pc = SkyCoord([p[0] for p in pairs], [p[1] for p in pairs], unit=(u.hourangle, u.deg))
            for k, t in T.items():
                yr = label[-4:]
                if mjd2date(TPK[k])[:4] != yr:
                    continue
                s = pc.separation(SkyCoord(t["ra"] * u.deg, t["dec"] * u.deg)).arcmin
                line += f"; {k}: nearest {s.min():.1f}'"
        print(line, flush=True)
    except Exception as e:  # noqa: BLE001
        print(f" {label}: UNKNOWN ({str(e)[:80]})")
    time.sleep(2)
