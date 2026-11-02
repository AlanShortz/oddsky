"""H-0013 archive checks for the top candidates: Gaia DR3, SIMBAD, AllWISE, Spitzer SEIP, HST/JWST coverage (MAST),
TNS (cached galaxy cones from H-0012; fetched politely if missing) and ADS full text.

    uv run python hunts/H-0013/scripts/archives.py [--top 10] [--uids UID ...]

Polite: one service at a time, a pause between requests. Every failure is recorded as "ERR ...", never as "none".
The ADS token is read from ~/.config/oddsky/ads-token and never printed. Writes work/archives_h0013.json.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import time
from pathlib import Path

import httpx
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import h0013  # noqa: E402

IRSA = "https://irsa.ipac.caltech.edu/TAP/sync"
GAIA = "https://gea.esac.esa.int/tap-server/tap/sync"
SIMBAD = "https://simbad.cfa.harvard.edu/simbad/sim-tap/sync"
ADS = "https://api.adsabs.harvard.edu/v1/search/query"
OUT = h0013.WORK / "archives_h0013.json"
PAUSE = 2.0


def tap(url, q):
    try:
        r = httpx.get(url, params=dict(REQUEST="doQuery", LANG="ADQL", FORMAT="csv", QUERY=" ".join(q.split())), timeout=180,
                      follow_redirects=True)
        r.raise_for_status()
        return "ok", pd.read_csv(io.StringIO(r.text), dtype={"sid": str}).to_dict("records")
    except Exception as e:  # noqa: BLE001
        return f"ERR {type(e).__name__}: {e}"[:200], []


def cone(ra, dec, r_arcsec):
    return f"CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',{ra},{dec},{r_arcsec / 3600}))=1"


def sexa(ra, dec):
    from astropy.coordinates import SkyCoord

    c = SkyCoord(ra, dec, unit="deg")
    h = c.ra.hms
    d = c.dec.dms
    sgn = "-" if dec < 0 else "+"
    ra_s = f"{int(h.h):02d}:{int(h.m):02d}:{h.s:04.1f}"
    de_s = f"{sgn}{abs(int(d.d)):02d}:{abs(int(d.m)):02d}:{abs(d.s):02.0f}"
    return ra_s, de_s


def ads(query, token, rows=30):
    for attempt in range(4):
        try:
            r = httpx.get(ADS, headers={"Authorization": f"Bearer {token}"}, params={"q": query, "rows": rows, "fl": "bibcode,title,year"},
                          timeout=60)
        except Exception as e:  # noqa: BLE001
            err = f"ERR {type(e).__name__}"
            time.sleep(5 * (attempt + 1))
            continue
        if r.status_code == 200:
            d = r.json()["response"]
            return {"n": d["numFound"], "docs": [{"bibcode": x["bibcode"], "year": x.get("year"),
                                                  "title": (x.get("title") or [""])[0][:140]} for x in d["docs"]]}
        err = f"ERR HTTP {r.status_code}"
        time.sleep(5 * (attempt + 1))
    return {"error": err}


def tns_near(galaxy, ra, dec, r_arcsec=30.0):
    """From the H-0012 TNS galaxy cones (cached; fetched at the H-0012 pace if missing)."""
    sys.path.insert(0, str(h0013.HERE.parent / "H-0012" / "scripts"))
    import merge_triage as mt

    try:
        targets = mt.load_targets()
        tns = mt.tns_for_galaxies([galaxy], targets, fetch=False)
        df, st = tns.get(galaxy, (pd.DataFrame(), "ERR no cone"))
        if str(st) != "ok":
            tns = mt.tns_for_galaxies([galaxy], targets, fetch=True)
            df, st = tns.get(galaxy, (pd.DataFrame(), "ERR no cone"))
    except Exception as e:  # noqa: BLE001
        return f"ERR {type(e).__name__}: {e}"[:200], []
    if df is None or not len(df):
        return str(st), []
    s = np.hypot((df.ra - ra) * np.cos(np.radians(dec)), df.dec - dec) * 3600
    near = df[s < r_arcsec].assign(sep=s[s < r_arcsec])
    return str(st), near[[c for c in ("Name", "Obj. Type", "Discovery Date (UT)", "sep") if c in near]].to_dict("records")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--uids", nargs="*", default=[])
    a = ap.parse_args()
    token = (Path.home() / ".config/oddsky/ads-token").read_text().strip()
    cands = pd.read_csv(h0013.WORK / "candidates_h0013.csv")
    sel = cands[cands.verdict.isin(["candidate", "flagged"])].head(a.top)
    extra = cands[cands.uid.isin(a.uids)]
    sel = pd.concat([sel, extra]).drop_duplicates("uid")
    out = json.loads(OUT.read_text()) if OUT.exists() else {}
    from astropy.coordinates import SkyCoord
    from astroquery.mast import Observations

    for _, c in sel.iterrows():
        if c.uid in out and not any(str(v.get("status", "ok")).startswith("ERR") for v in out[c.uid].values() if isinstance(v, dict)):
            continue
        ra, dec = float(c.ra), float(c.dec)
        o = dict(galaxy=c.galaxy, ra=ra, dec=dec)
        st, rows = tap(GAIA, f"""SELECT CAST(source_id AS VARCHAR(20)) AS sid, ra, dec, phot_g_mean_mag, bp_rp, parallax_over_error,
            pm, ruwe, phot_variable_flag, classprob_dsc_combmod_quasar FROM gaiadr3.gaia_source WHERE {cone(ra, dec, 3)}""")
        o["gaia_3as"] = dict(status=st, rows=rows)
        time.sleep(PAUSE)
        st, rows = tap(SIMBAD, f"""SELECT main_id, otype, ra, dec, DISTANCE(POINT('ICRS',ra,dec), POINT('ICRS',{ra},{dec}))*3600 AS sep
            FROM basic WHERE {cone(ra, dec, 10)} ORDER BY sep""")
        o["simbad_10as"] = dict(status=st, rows=rows)
        time.sleep(PAUSE)
        st, rows = tap(IRSA, f"""SELECT designation, ra, dec, w1mpro, w2mpro, w3mpro, w4mpro, cc_flags, ext_flg
            FROM allwise_p3as_psd WHERE {cone(ra, dec, 6)}""")
        o["allwise_6as"] = dict(status=st, rows=rows)
        time.sleep(PAUSE)
        st, rows = tap(IRSA, f"""SELECT ra, dec, i1_f_ap1, i2_f_ap1, i3_f_ap1, i4_f_ap1, m1_f_psf FROM slphotdr4 WHERE {cone(ra, dec, 4)}""")
        o["seip_4as"] = dict(status=st, rows=rows)
        time.sleep(PAUSE)
        try:
            t = Observations.query_region(SkyCoord(ra, dec, unit="deg"), radius="0.0003 deg")
            t = t[(t["dataproduct_type"] == "image") & (t["intentType"] == "science")]
            obs = sorted({(str(r["obs_collection"]), str(r["instrument_name"]), str(r["filters"]), round(float(r["t_min"]), 1))
                          for r in t if str(r["obs_collection"]) in ("HST", "JWST")}, key=lambda x: x[3])
            o["mast_1as"] = dict(status="ok", n=len(obs), obs=obs[:60])
        except Exception as e:  # noqa: BLE001
            o["mast_1as"] = dict(status=f"ERR {type(e).__name__}: {e}"[:200])
        time.sleep(PAUSE)
        st, rows = tns_near(c.galaxy, ra, dec)
        o["tns_30as"] = dict(status=st, rows=rows)
        ra_s, de_s = sexa(ra, dec)
        res = {}
        for qq in (f'full:"{ra_s}"', f'full:"{ra_s.replace(":", "")}"', f'full:"{ra_s.replace(":", " ")}"', f'full:"{ra:.3f}" full:"{dec:.3f}"'):
            res[qq] = ads(qq, token)
            time.sleep(1.2)
        gname = str(c.galaxy).replace("MESSIER0", "M").replace("MESSIER", "M")
        for qq in (f'full:"{gname}" full:("colliding wind" OR "dust-forming" OR "WC binary" OR "episodic dust" OR "periodic dust")',
                   f'full:"{gname}" full:("infrared variable" OR "mid-infrared variable" OR SPIRITS) full:(periodic OR "long-period")'):
            res[qq] = ads(qq, token)
            time.sleep(1.2)
        o["ads"] = res
        o["sexagesimal"] = f"{ra_s} {de_s}"
        out[c.uid] = o
        OUT.write_text(json.dumps(out, indent=1, default=str))
        print(c.uid, "Gaia", len(o["gaia_3as"]["rows"]), o["gaia_3as"]["status"][:12], "| SIMBAD",
              [(r["main_id"], r["otype"], round(r["sep"], 1)) for r in o["simbad_10as"]["rows"][:3]], "| HST/JWST",
              o["mast_1as"].get("n"), "| TNS", o["tns_30as"]["status"][:20], len(o["tns_30as"]["rows"]), "| ADS coords",
              [v.get("n", v.get("error")) for k, v in res.items()][:4], flush=True)


if __name__ == "__main__":
    main()
