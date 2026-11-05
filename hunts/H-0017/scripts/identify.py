"""H-0017: Gaia DR3 (star or not) and SIMBAD identities for image-confirmed nuclei. usage: identify.py IN_CSV OUT_CSV
IN_CSV is a nuclei_state.py output; only verdict == REAL rows are looked up. A lookup that failed is recorded as such."""
import io
import sys
import time

import numpy as np
import pandas as pd
import requests

x = pd.read_csv(sys.argv[1])
x = x[x.verdict == "REAL"].copy()
GCOLS = "source_id, phot_g_mean_mag, parallax_over_error, pmra, pmra_error, pmdec, pmdec_error, classprob_dsc_combmod_galaxy, classprob_dsc_combmod_quasar, classprob_dsc_combmod_star"
rows = []
for r in x.itertuples():
    rec = dict(cntr=r.cntr, gaia_status="failed", simbad_status="failed")
    cone = f"CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',{r.ra},{r.dec},0.000833))=1"
    for k in range(4):
        try:
            if k % 2 == 0:
                t = requests.post("https://gea.esac.esa.int/tap-server/tap/sync", data=dict(REQUEST="doQuery", LANG="ADQL", FORMAT="csv", QUERY=f"SELECT {GCOLS} FROM gaiadr3.gaia_source WHERE {cone}"), timeout=60).text.strip()
            else:
                t = requests.post("https://irsa.ipac.caltech.edu/TAP/sync", data={"QUERY": f"SELECT {GCOLS} FROM gaia_dr3_source WHERE {cone}", "FORMAT": "csv"}, timeout=120).text.strip()
            if not t.startswith("source_id"):
                raise RuntimeError("not a CSV answer")
            g = pd.read_csv(io.StringIO(t)) if "\n" in t else pd.DataFrame()
            rec["gaia_status"] = "ok"
            rec["n_gaia"] = len(g)
            if len(g):
                g = g.sort_values("phot_g_mean_mag").iloc[0]
                pm_sig = np.hypot(g.pmra / g.pmra_error, g.pmdec / g.pmdec_error) if pd.notna(g.pmra) else np.nan
                rec.update(G=g.phot_g_mean_mag, poe=g.parallax_over_error, pm_sig=pm_sig, p_gal=g.classprob_dsc_combmod_galaxy,
                           p_qso=g.classprob_dsc_combmod_quasar, p_star=g.classprob_dsc_combmod_star)
            break
        except Exception:  # noqa: BLE001
            time.sleep(5 * (k + 1))
    q = ("SELECT main_id, otype, sp_type, rvz_redshift FROM basic WHERE "
         f"CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',{r.ra},{r.dec},0.00139))=1")
    for k in range(3):
        try:
            t = requests.post("https://simbad.harvard.edu/simbad/sim-tap/sync", data=dict(REQUEST="doQuery", LANG="ADQL", FORMAT="csv", QUERY=q), timeout=60).text.strip()
            if not t.startswith("main_id"):
                raise RuntimeError("not a CSV answer")
            s = pd.read_csv(io.StringIO(t)) if "\n" in t else pd.DataFrame()
            rec["simbad_status"] = "ok"
            if len(s):
                rec.update(simbad=s.main_id.iloc[0], otype=s.otype.iloc[0], z=s.rvz_redshift.iloc[0])
            break
        except Exception:  # noqa: BLE001
            time.sleep(5 * (k + 1))
    rows.append(rec)
    print(r.designation, rec, flush=True)
o = x.merge(pd.DataFrame(rows), on="cntr", how="left")
o["star"] = (o.poe.abs() > 5) | (o.pm_sig > 5)
o.to_csv(sys.argv[2], index=False)
print("gaia failed:", int((o.gaia_status == "failed").sum()), " simbad failed:", int((o.simbad_status == "failed").sum()), " stars:", int(o.star.sum()))
