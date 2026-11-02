"""Independent cross-matches for the H-0012a leads (wider radii than the pipeline's).

    uv run python hunts/H-0012/reviews/claude-referee-triage-2026-11-01/xmatch.py

Gaia DR3 (5", ESA TAP; source_id as string), AllWISE (6") and 2MASS PSC (4") via IRSA TAP, SIMBAD
(10", simbad.harvard.edu TAP), Milliquas v8 (VizieR VII/294 on vizier.idia.ac.za, 10"), NED (10",
objsearch cone). Writes xmatch.json.
"""
import json
from pathlib import Path

import httpx
import pyvo

HERE = Path(__file__).resolve().parent
LEADS = json.loads((HERE / "leads.json").read_text())
UA = {"User-Agent": "oddsky-referee/0.1"}


def tap(url, q, tries=3):
    import time
    err = "ERR"
    for urls in ([url] * tries):
        try:
            return pyvo.dal.TAPService(urls).run_sync(q).to_table().to_pandas().to_dict("records"), "ok"
        except Exception as e:  # noqa: BLE001
            err = f"ERR {type(e).__name__}: {str(e)[:150]}"
            time.sleep(5)
    return [], err


def gaia(ra, dec, r=5):
    q = f"""SELECT CAST(g.source_id AS VARCHAR(25)) AS sid, DISTANCE(POINT(g.ra,g.dec),POINT({ra},{dec}))*3600 AS sep,
    g.phot_g_mean_mag, g.bp_rp, g.parallax, g.parallax_over_error, g.pmra, g.pmdec, g.pm, g.ruwe,
    g.phot_variable_flag, g.astrometric_excess_noise, g.ipd_frac_multi_peak, a.classprob_dsc_combmod_quasar AS pq,
    a.classprob_dsc_combmod_galaxy AS pgal, a.classprob_dsc_combmod_star AS pstar, a.teff_gspphot
    FROM gaiadr3.gaia_source g LEFT JOIN gaiadr3.astrophysical_parameters a ON a.source_id=g.source_id
    WHERE 1=CONTAINS(POINT(g.ra,g.dec),CIRCLE({ra},{dec},{r/3600}))"""
    rows, st = tap("https://gea.esac.esa.int/tap-server/tap", q, tries=2)
    if st != "ok":  # ARI Heidelberg mirror
        rows, st = tap("https://gaia.ari.uni-heidelberg.de/tap", q.replace("gaiadr3.", "gaiadr3."), tries=2)
    return rows, st


def allwise(ra, dec, r=6):
    q = f"""SELECT designation, ra, dec, w1mpro, w1sigmpro, w2mpro, w2sigmpro, w3mpro, w3sigmpro, w4mpro, w4sigmpro,
    cc_flags, ext_flg, var_flg, nb, j_m_2mass, h_m_2mass, k_m_2mass FROM allwise_p3as_psd
    WHERE CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',{ra},{dec},{r/3600}))=1"""
    return tap("https://irsa.ipac.caltech.edu/TAP", q)


def simbad(ra, dec, r=10):
    q = f"""SELECT b.main_id, b.otype, b.ra, b.dec, b.nbref, b.rvz_redshift, b.sp_type,
    DISTANCE(POINT('ICRS',b.ra,b.dec),POINT('ICRS',{ra},{dec}))*3600 AS sep FROM basic b
    WHERE CONTAINS(POINT('ICRS',b.ra,b.dec),CIRCLE('ICRS',{ra},{dec},{r/3600}))=1"""
    return tap("https://simbad.harvard.edu/simbad/sim-tap", q)


def vizier(cat, ra, dec, r=10):
    url = "https://vizier.idia.ac.za/viz-bin/asu-tsv"
    p = {"-source": cat, "-c": f"{ra} {dec}", "-c.rs": r, "-out.all": "", "-out.max": 20}
    try:
        t = httpx.get(url, params=p, timeout=60, headers=UA).text
        rows = [ln for ln in t.splitlines() if ln and not ln.startswith("#")]
        return rows[:12], "ok"
    except Exception as e:  # noqa: BLE001
        return [], f"ERR {e}"


def ned(ra, dec, r=10):
    p = {"search_type": "Near Position Search", "in_csys": "Equatorial", "in_equinox": "J2000", "lon": f"{ra}d",
         "lat": f"{dec}d", "radius": r / 60, "of": "ascii_bar", "out_csys": "Equatorial", "out_equinox": "J2000"}
    try:
        t = httpx.get("https://ned.ipac.caltech.edu/cgi-bin/objsearch", params=p, timeout=90, headers=UA).text
        rows = [ln for ln in t.splitlines() if ln.count("|") > 8 and not ln.startswith("No.")]
        return rows[:15], "ok" if "|" in t or "No object" in t else "ERR unparsed"
    except Exception as e:  # noqa: BLE001
        return [], f"ERR {e}"


prev = json.loads((HERE / "xmatch.json").read_text()) if (HERE / "xmatch.json").exists() else {}
out = {}
for L in LEADS:
    ra, dec = L["ra"], L["dec"]
    rec = {}
    for name, fn in (("gaia", gaia), ("allwise", allwise), ("simbad", simbad), ("ned", ned)):
        old = prev.get(L["lead"], {}).get(name)
        if old and old["status"] == "ok":
            rec[name] = old
            continue
        rows, st = fn(ra, dec)
        rec[name] = dict(status=st, rows=rows)
    rows, st = vizier("VII/294", ra, dec)
    rec["milliquas"] = dict(status=st, rows=rows)
    out[L["lead"]] = rec
    print(L["lead"], {k: (v["status"], len(v["rows"])) for k, v in rec.items()}, flush=True)
(HERE / "xmatch.json").write_text(json.dumps(out, indent=1, default=str))
