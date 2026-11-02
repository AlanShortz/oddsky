"""Archive context at the key h0012b leads: Spitzer SEIP (2004-09 cryogenic), AllWISE, Gaia DR3 (all sources within
6"), SIMBAD (CfA mirror, 10"), and HST/JWST/Spitzer image coverage from MAST and IRSA. Polite: one service at a
time, a pause between requests.

    uv run python hunts/H-0012/reviews/h0012b-referee/archives.py
Writes archives.json next to this script.
"""
import json
import time
from pathlib import Path

import io

import pandas as pd
import requests
from astropy.coordinates import SkyCoord
from astroquery.mast import Observations

HERE = Path(__file__).resolve().parent
L = {d["lead"]: d for d in json.loads((HERE / "leads.json").read_text())}
SEL = ["NGC55_fsn7", "NGC55_fsn13", "NGC55_obs184", "NGC55_obs299", "M81_fsn24", "NGC925_obs37", "NGC2403_obs50",
       "NGC2903_obs75", "NGC5128_obs22_AT2020nqq", "Circinus_fsn72"]
irsa = "https://irsa.ipac.caltech.edu/TAP/sync"
gaia = "https://gea.esac.esa.int/tap-server/tap/sync"
simbad = "https://simbad.cfa.harvard.edu/simbad/sim-tap/sync"


def run(url, q):
    """Synchronous TAP query, CSV, with a hard timeout (pyvo had hung)."""
    try:
        r = requests.get(url, params=dict(REQUEST="doQuery", LANG="ADQL", FORMAT="csv", QUERY=" ".join(q.split())),
                         timeout=180)
        r.raise_for_status()
        return "ok", pd.read_csv(io.StringIO(r.text), dtype={"sid": str})
    except Exception as e:  # noqa: BLE001
        return f"ERR {e}"[:200], None


def cone(ra, dec, r_arcsec):
    return f"CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',{ra},{dec},{r_arcsec / 3600}))=1"


OUT = HERE / "archives.json"
out = json.loads(OUT.read_text()) if OUT.exists() else {}
for lab in SEL:
    if lab in out and all(str(out[lab][k].get("status", "ok")) == "ok" for k in ("seip", "allwise", "gaia", "simbad")) \
            and "error" not in out[lab]["mast"]:
        continue
    d = L[lab]
    ra, dec = d["ra"], d["dec"]
    o = {}
    st, t = run(irsa, f"""SELECT ra, dec, i1_f_ap1, i1_df_ap1, i2_f_ap1, i2_df_ap1, i3_f_ap1, i3_df_ap1, i4_f_ap1, i4_df_ap1,
        m1_f_psf, m1_df_psf FROM slphotdr4 WHERE {cone(ra, dec, 4)}""")
    o["seip"] = dict(status=st, rows=t.to_dict("records") if t is not None else [])
    time.sleep(2)
    st, t = run(irsa, f"""SELECT designation, ra, dec, w1mpro, w1sigmpro, w2mpro, w2sigmpro, w3mpro, w4mpro, cc_flags, ext_flg, nb
        FROM allwise_p3as_psd WHERE {cone(ra, dec, 6)}""")
    o["allwise"] = dict(status=st, rows=t.to_dict("records") if t is not None else [])
    time.sleep(2)
    st, t = run(gaia, f"""SELECT CAST(source_id AS VARCHAR(20)) AS sid, ra, dec, phot_g_mean_mag, bp_rp, parallax_over_error,
        pmra, pmdec, pm, astrometric_params_solved, ruwe, phot_variable_flag, classprob_dsc_combmod_quasar,
        classprob_dsc_combmod_galaxy, phot_bp_rp_excess_factor
        FROM gaiadr3.gaia_source WHERE {cone(ra, dec, 6)}""")
    o["gaia"] = dict(status=st, rows=t.to_dict("records") if t is not None else [])
    time.sleep(2)
    st, t = run(simbad, f"""SELECT main_id, otype, ra, dec, DISTANCE(POINT('ICRS',ra,dec), POINT('ICRS',{ra},{dec}))*3600 AS sep
        FROM basic WHERE {cone(ra, dec, 10)} ORDER BY sep""")
    o["simbad"] = dict(status=st, rows=t.to_dict("records") if t is not None else [])
    time.sleep(2)
    print(lab, "catalogues done; MAST", flush=True)
    try:
        t = Observations.query_region(SkyCoord(ra, dec, unit="deg"), radius="0.0003 deg")
        t = t[(t["dataproduct_type"] == "image") & (t["intentType"] == "science")]
        rows = sorted({(str(r["obs_collection"]), str(r["instrument_name"]), str(r["filters"]), round(float(r["t_min"]), 1),
                        str(r["proposal_id"])) for r in t if str(r["obs_collection"]) in ("HST", "JWST", "SPITZER_SHA")},
                      key=lambda x: x[3])
        o["mast"] = dict(n=len(rows), obs=rows)
    except Exception as e:  # noqa: BLE001
        o["mast"] = dict(error=str(e)[:200])
    time.sleep(2)
    out[lab] = o
    print(lab, "SEIP", o["seip"]["status"], len(o["seip"]["rows"]), "AllWISE", len(o["allwise"]["rows"]), "Gaia",
          o["gaia"]["status"][:20], len(o["gaia"]["rows"]), "SIMBAD", o["simbad"]["status"][:20], len(o["simbad"]["rows"]),
          "MAST", o["mast"].get("n"), o["mast"].get("error", ""), flush=True)
    OUT.write_text(json.dumps(out, indent=1, default=str))  # after every lead
