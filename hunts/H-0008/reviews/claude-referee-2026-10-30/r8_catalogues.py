"""r8: catalogue context for the five targets: Gaia DR3 cone 6" (all sources = the WISE beam), vari_summary /
vari_classifier_result / vari_microlensing for the brightest-matching source; AllWISE ph_qual / cc_flags / var_flg
(IRSA TAP); VSX (VizieR B/vsx/vsx on vizier.idia.ac.za, 30"); SIMBAD (simbad.cfa.harvard.edu TAP, 10")."""
import io, os, sys, time
import numpy as np, pandas as pd, requests
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from targets import TARGETS
from oddsky.data.gaia import adql
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
for k, (name, ra, dec, t, pix) in TARGETS.items():
    print("=" * 20, name)
    g = adql(f"""SELECT source_id, ra, dec, phot_g_mean_mag, bp_rp, parallax, parallax_over_error, ruwe, phot_variable_flag,
      non_single_star, teff_gspphot, logg_gspphot, distance_gspphot, ag_gspphot, classprob_dsc_combmod_star, classprob_dsc_combmod_quasar,
      phot_g_n_obs, phot_g_mean_flux_over_error, ipd_frac_multi_peak, has_epoch_photometry,
      DISTANCE(POINT(ra, dec), POINT({ra}, {dec}))*3600 AS sep
      FROM gaiadr3.gaia_source WHERE 1=CONTAINS(POINT(ra, dec), CIRCLE({ra}, {dec}, {6/3600}))""")
    g = g.sort_values("sep")
    print(g.round(3).to_string(index=False))
    sid = int(g.source_id.iloc[0])
    for tab in ("vari_summary", "vari_classifier_result", "vari_microlensing"):
        try:
            v = adql(f"SELECT * FROM gaiadr3.{tab} WHERE source_id = {sid}")
            print(f"  {tab}:", "none" if len(v) == 0 else v.iloc[0].dropna().to_dict())
        except Exception as e:
            print(f"  {tab}: ERR {e}")
    flux_scatter = adql(f"SELECT source_id, phot_g_mean_flux_error*SQRT(phot_g_n_obs)/phot_g_mean_flux AS g_rel_scatter, phot_g_n_obs FROM gaiadr3.gaia_source WHERE source_id={sid}")
    print("  G relative flux scatter (proxy for variability):", flux_scatter.round(4).to_dict("records"))
    q = (f"SELECT designation, ph_qual, cc_flags, var_flg, ext_flg, w1mpro, w1sigmpro, w2mpro, w3mpro, w3sigmpro, w3snr, w4mpro, w4snr, w1rchi2, w3rchi2, nb, na "
         f"FROM allwise_p3as_psd WHERE CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', {ra}, {dec}, {1/3600}))=1")
    r = requests.post("https://irsa.ipac.caltech.edu/TAP/sync", data={"QUERY": q, "FORMAT": "csv"}, timeout=300)
    print("  AllWISE:", pd.read_csv(io.StringIO(r.text)).to_dict("records"))
    try:
        r = requests.get("https://vizier.idia.ac.za/viz-bin/asu-tsv", params={"-source": "B/vsx/vsx", "-c": f"{ra} {dec}", "-c.rs": 30,
                         "-out": "Name,Type,max,min,Period,_r"}, timeout=120)
        lines = [l for l in r.text.splitlines() if l and not l.startswith("#")]
        print("  VSX (30\"):", lines[3:] if len(lines) > 3 else "none", f"[HTTP {r.status_code}]")
    except Exception as e:
        print("  VSX: UNKNOWN", e)
    try:
        q = (f"SELECT main_id, otype, sp_type, DISTANCE(POINT('ICRS', ra, dec), POINT('ICRS', {ra}, {dec}))*3600 AS sep FROM basic "
             f"WHERE CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', {ra}, {dec}, {10/3600}))=1")
        r = requests.post("https://simbad.cfa.harvard.edu/simbad/sim-tap/sync", data={"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": q}, timeout=120)
        d = pd.read_csv(io.StringIO(r.text))
        print("  SIMBAD (10\"):", d.to_dict("records") if len(d) else "none", f"[HTTP {r.status_code}]")
        for mid in d.main_id[:3]:
            r2 = requests.post("https://simbad.cfa.harvard.edu/simbad/sim-tap/sync", data={"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv",
                 "QUERY": f"SELECT b.bibcode FROM has_ref h JOIN ref b ON h.oidbibref=b.oidbib JOIN basic s ON s.oid=h.oidref WHERE s.main_id='{mid}'"}, timeout=120)
            print(f"    refs for {mid}:", r2.text.strip().splitlines()[1:])
    except Exception as e:
        print("  SIMBAD: UNKNOWN", e)
    time.sleep(1)
