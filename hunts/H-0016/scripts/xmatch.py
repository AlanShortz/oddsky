"""H-0016: cross-match a table (cntr, ra, dec) with Gaia DR3 (brightest within 3", plus neighbour count within 6"),
SIMBAD (nearest within 5", via the CfA mirror) and VSX (within 6", VizieR mirror).
usage: xmatch.py IN_CSV OUT_CSV [--skip-vsx]"""
import io
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
import requests

SIMBAD = "https://simbad.harvard.edu/simbad/sim-tap/sync"
VSX_MIRRORS = ["https://vizier.idia.ac.za/viz-bin/asu-tsv", "https://vizier.cds.unistra.fr/viz-bin/asu-tsv"]
a = pd.read_csv(sys.argv[1])
out = sys.argv[2]
a["cntr"] = a["cntr"].astype("int64")

GCOLS = ("source_id, ra, dec, phot_g_mean_mag, bp_rp, parallax, parallax_over_error, ruwe, pmra, pmdec, phot_variable_flag, "
         "non_single_star, teff_gspphot, logg_gspphot, classprob_dsc_combmod_star, classprob_dsc_combmod_galaxy, classprob_dsc_combmod_quasar, "
         "phot_bp_rp_excess_factor")

def gaia_one(r):
    """Gaia DR3 via IRSA's copy (gaia_dr3_source; one cone per query, IRSA rejects OR'd cones). ESA's archive hung on 2026-11-02/03."""
    q = f"SELECT {GCOLS} FROM gaia_dr3_source WHERE CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',{r.ra},{r.dec},0.001667))=1"
    g = pd.DataFrame()
    for k in range(5):
        try:
            rr = requests.post("https://irsa.ipac.caltech.edu/TAP/sync", data={"QUERY": q, "FORMAT": "csv"}, timeout=300)
            rr.raise_for_status()
            txt = rr.text.strip()
            g = pd.read_csv(io.StringIO(txt)) if "\n" in txt else pd.DataFrame(columns=GCOLS.replace(" ", "").split(","))
            break
        except Exception as ex:  # noqa: BLE001
            print("gaia retry", k, str(ex)[:100], file=sys.stderr)
            time.sleep(10 * (k + 1))
    rec = {"cntr": r.cntr, "n_gaia_3as": 0, "n_gaia_6as": 0}
    if len(g):
        sep = 3600 * np.hypot((g.ra - r.ra) * np.cos(np.radians(r.dec)), g.dec - r.dec)
        m6 = g[sep < 6].assign(sep=sep[sep < 6])
        m3 = m6[m6.sep < 3].sort_values("phot_g_mean_mag")
        rec["n_gaia_6as"], rec["n_gaia_3as"] = len(m6), len(m3)
        if len(m3):
            best = m3.iloc[0].to_dict()
            best["source_id"] = str(int(best["source_id"]))
            rec.update({f"g_{k}": v for k, v in best.items()})
            others = m6[(m6.source_id != m3.source_id.iloc[0]) & m6.phot_g_mean_mag.notna()]
            if len(others):
                rec["g_nb_dg"] = float(others.phot_g_mean_mag.min() - best["phot_g_mean_mag"])
                rec["g_nb_sep"] = float(others.loc[others.phot_g_mean_mag.idxmin(), "sep"])
    return rec

with ThreadPoolExecutor(4) as ex:
    rows = list(ex.map(gaia_one, a.itertuples()))
print("gaia done", len(rows), flush=True)
x = a.merge(pd.DataFrame(rows), on="cntr", how="left")

def simbad_batch(chunk):
    ors = " OR ".join(f"CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',{r.ra},{r.dec},5/3600.))=1" for r in chunk.itertuples())
    q = f"SELECT main_id, otype, sp_type, ra, dec, nbref FROM basic WHERE {ors}"
    data = urllib.parse.urlencode(dict(request="doQuery", lang="adql", format="csv", query=q)).encode()
    for k in range(4):
        try:
            txt = urllib.request.urlopen(urllib.request.Request(SIMBAD, data=data), timeout=300).read().decode()
            return pd.read_csv(io.StringIO(txt))
        except Exception as e:  # noqa: BLE001
            print("simbad retry", k, str(e)[:100], file=sys.stderr)
            time.sleep(10)
    return pd.DataFrame()

x["simbad_id"], x["simbad_otype"], x["simbad_sp"], x["simbad_sep"], x["simbad_nref"] = "", "", "", np.nan, np.nan
for i in range(0, len(x), 40):
    chunk = x.iloc[i:i + 40]
    s = simbad_batch(chunk)
    if not len(s):
        continue
    for j, r in chunk.iterrows():
        sep = 3600 * np.hypot((s.ra - r.ra) * np.cos(np.radians(r.dec)), s.dec - r.dec)
        m = s[sep < 5].assign(sep=sep[sep < 5]).sort_values("sep")
        if len(m):
            x.loc[j, ["simbad_id", "simbad_otype", "simbad_sp", "simbad_sep", "simbad_nref"]] = [
                m.main_id.iloc[0], m.otype.iloc[0], m.sp_type.iloc[0] if isinstance(m.sp_type.iloc[0], str) else "", float(m.sep.iloc[0]), float(m.nbref.iloc[0])]
    time.sleep(0.5)
print("simbad matched", int((x.simbad_id != "").sum()), flush=True)

def vsx(r):
    for m in VSX_MIRRORS:
        try:
            t = requests.get(m, params={"-source": "B/vsx/vsx", "-c": f"{r.ra} {r.dec}", "-c.rs": 6, "-out": "_r Name Type Period max min", "-sort": "_r"}, timeout=60).text
            rows = [ln for ln in t.splitlines() if ln and not ln.startswith("#")]
            return "; ".join("|".join(v.strip() for v in ln.split("\t")) for ln in rows[3:]) if len(rows) > 3 else ""
        except Exception:  # noqa: BLE001
            continue
    return "ERR"

if "--skip-vsx" not in sys.argv:
    with ThreadPoolExecutor(4) as ex:
        x["vsx"] = list(ex.map(vsx, x.itertuples()))
    print("vsx matched", int((x.vsx.fillna("") != "").sum() - (x.vsx == "ERR").sum()), "errors", int((x.vsx == "ERR").sum()))
x.to_csv(out, index=False)
