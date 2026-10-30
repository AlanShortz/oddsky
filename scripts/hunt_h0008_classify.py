"""H-0008 step 4: classify the clean one-night brightenings (after hunt_h0007_xmatch.py and hunt_h0007_vsx.py have added Gaia
and VSX columns).

Classes, in order: microlensing (known) if it matches a known lens (KMTNet, OGLE, Gaia DR3, Gaia alerts) or Gaia DR3
vari_microlensing lists the star or VSX types it Microlens; dwarf nova / CV,
young star or other variable from the VSX type; otherwise unclassified. For unclassified events after 2018.2 north of -30,
ZTF (IRSA DR, catflags = 0) is checked automatically: the r-band median within 10 days of the NEOWISE visit against the star's
median elsewhere (ztf_dr = negative if brighter), with the number of ZTF nights in that window.
usage: hunt_h0008_classify.py X_CSV OUT_CSV
"""

import io
import re
import sys
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
import requests

from oddsky.data.gaia import adql

x = pd.read_csv(sys.argv[1], dtype={"g_source_id": str})
ids = [s for s in x.g_source_id.dropna().unique() if s and s != "nan"]
ml = set()
for i in range(0, len(ids), 200):
    q = f"SELECT source_id FROM gaiadr3.vari_microlensing WHERE source_id IN ({','.join(ids[i:i + 200])})"
    res = adql(q)
    if "source_id" in res:
        ml |= {str(s) for s in res.source_id}
CV = re.compile(r"\b(UG|UGSU|UGSS|UGZ|UGWZ|NL|AM|DQ|NA|NB|NR|CV|ZAND|VY)\b")
YSO = re.compile(r"\b(YSO|INS|INSA|INSB|IN|INT|TTS|CTTS|WTTS|UXOR|FUOR|EXOR|ISA|ISB|IS|BY)\b")


def cls(r):
    vt = str(r.get("vsx") or "")
    vtype = vt.split("|")[2] if vt.count("|") >= 2 else ""
    if isinstance(r.get("known_lens"), str) and r["known_lens"] or r.get("g_source_id") in ml or "Microlens" in vtype:
        return "microlensing (known)"
    if CV.search(vtype.replace("+", " ").replace("/", " ")):
        return "dwarf nova / CV"
    if YSO.search(vtype.replace("+", " ").replace("/", " ")):
        return "young star"
    if vtype:
        return "other variable"
    return "unclassified"


x["class"] = x.apply(cls, axis=1)
x["ztf_dr"] = np.nan
x["ztf_n_window"] = 0


def ztf_check(r):
    try:
        t = requests.get(f"https://irsa.ipac.caltech.edu/cgi-bin/ZTF/nph_light_curves?POS=CIRCLE%20{r.ra}%20{r.dec}%200.0006"
                         "&FORMAT=csv", timeout=300).text
        z = pd.read_csv(io.StringIO(t))
        z = z[(z.catflags == 0) & (z.filtercode == "zr")]
    except Exception:  # noqa: BLE001
        return None
    w = z[(z.mjd - r.t).abs() < 10]
    o = z[(z.mjd - r.t).abs() > 120]
    if len(w) and len(o) > 10:
        return float(w.mag.median() - o.mag.median()), int(np.floor(w.mjd).nunique())
    return None


todo = x[(x["class"] == "unclassified") & (x.t > 58200) & (x.dec > -30)]
with ThreadPoolExecutor(8) as ex:
    for j, res in zip(todo.index, ex.map(ztf_check, [r for _, r in todo.iterrows()]), strict=True):
        if res:
            x.loc[j, "ztf_dr"], x.loc[j, "ztf_n_window"] = res
x.to_csv(sys.argv[2], index=False)
print(x["class"].value_counts().to_dict())
print("unclassified with a ZTF window:", int(x.ztf_dr.notna().sum()), "| of those brighter by > 0.1 mag in ZTF:",
      int((x.ztf_dr < -0.1).sum()))
