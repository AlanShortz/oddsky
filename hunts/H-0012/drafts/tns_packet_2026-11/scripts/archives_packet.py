"""TNS packet 2026-11: catalogue, alert, archive and literature checks at the two candidates that pass the screen.

Every service failure is recorded as an ERROR string, never as an empty result. The ADS token is read from
~/.config/oddsky/ads-token and never printed. Queries are sequential with pauses.

  SIMBAD     TAP, CfA mirror (CDS times out from this machine), 15" cone
  VSX        VizieR B/vsx/vsx on vizier.idia.ac.za, 30"
  Gaia DR3   VizieR I/355/gaiadr3 (idia), 6"; AllWISE II/328/allwise (idia), 6"
  Spitzer    IRSA TAP SEIP source list (slphotdr4), 5"; IRSA SIA (spitzer_sha) IRAC mosaic count
  Gaia alerts / ASAS-SN  the copies fetched 2026-11-02 for the OS-0030 check (alerts.csv; transients.html)
  ALeRCE     ZTF alert objects within 60" (M81 only: NGC 4945 at -49 deg is outside ZTF)
  MAST       HST/JWST/Spitzer observations within 30" (astroquery.mast), with dates and release dates
  NED        object lookup (preferred redshift) and the redshift-independent distance table (nDistance)
  ADS        full text: position strings, host + transient terms, ATel / TNS bibstems

    uv run python hunts/H-0012/drafts/tns_packet_2026-11/scripts/archives_packet.py
Output: ~/oddsky-runs/imaging/scratch/tns-packet-2026-11/archives/archives.json
"""
import io
import json
import re
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

OUT = Path.home() / "oddsky-runs/imaging/scratch/tns-packet-2026-11/archives"
OUT.mkdir(parents=True, exist_ok=True)
DL = Path.home() / "oddsky-runs/imaging/scratch/tns-validation-os0030/brokers/dl"
VIZ = "https://vizier.idia.ac.za/viz-bin/asu-tsv"
UA = {"User-Agent": "oddsky-tns-packet/1.0 (alan@oddsky.ai)"}

SRC = {
    "NGC4945_obs3": dict(ra=196.469838, dec=-49.416317, host="NGC 4945", host_alias=["NGC4945", "ESO 219-24"],
                         pos_strings=['"13 05 52.7"', '"13:05:52.7"', '"130552.7"', '"130552.76"', '"J130552"',
                                      '"196.4698"'], ztf=False, ned="NGC 4945"),
    "M81_OS-0035": dict(ra=148.739074, dec=69.146874, host="M81", host_alias=["NGC 3031", "NGC3031", "Messier 81"],
                        pos_strings=['"09 54 57.3"', '"09:54:57.3"', '"095457.3"', '"095457.4"', '"J095457"',
                                     '"148.7391"'], ztf=True, ned="NGC 3031"),
}


def err(e):
    return f"ERROR {type(e).__name__}: {str(e)[:200]} (not a null result)"


def viz(cat, ra, dec, rs, out="**"):
    q = requests.get(VIZ, timeout=180, params={"-source": cat, "-c": f"{ra} {dec}", "-c.rs": rs, "-out": out,
                                              "-out.add": "_r", "-out.max": 500}, headers=UA)
    q.raise_for_status()
    lines = [ln for ln in q.text.splitlines() if ln and not ln.startswith("#")]
    if len(lines) < 3:
        return []
    d = pd.read_csv(io.StringIO("\n".join([lines[0]] + lines[3:])), sep="\t", dtype=str)
    return [{k: str(v).strip() for k, v in r.items()} for r in d.to_dict("records")]


def simbad(ra, dec, rs):
    adql = (f"SELECT b.main_id, b.otype, b.ra, b.dec, DISTANCE(POINT('ICRS', b.ra, b.dec), POINT('ICRS', {ra}, {dec}))*3600 AS sep "
            f"FROM basic AS b WHERE CONTAINS(POINT('ICRS', b.ra, b.dec), CIRCLE('ICRS', {ra}, {dec}, {rs / 3600})) = 1 ORDER BY sep")
    q = requests.get("https://simbad.cfa.harvard.edu/simbad/sim-tap/sync", timeout=120, headers=UA,
                     params={"request": "doQuery", "lang": "adql", "format": "csv", "query": adql})
    q.raise_for_status()
    return pd.read_csv(io.StringIO(q.text)).astype(str).to_dict("records")


def seip(ra, dec, rs):
    adql = (f"SELECT objid, ra, dec, i1_f_ap1, i1_df_ap1, i2_f_ap1, i2_df_ap1, i3_f_ap1, i4_f_ap1, m1_f_psf "
            f"FROM slphotdr4 WHERE CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', {ra}, {dec}, {rs / 3600})) = 1")
    q = requests.get("https://irsa.ipac.caltech.edu/TAP/sync", timeout=180, headers=UA,
                     params={"QUERY": adql, "FORMAT": "csv"})
    q.raise_for_status()
    d = pd.read_csv(io.StringIO(q.text))
    if len(d):
        d["sep"] = np.hypot((d.ra - ra) * np.cos(np.radians(dec)), d.dec - dec) * 3600
    return d.astype(str).to_dict("records")


def sha_count(ra, dec):
    q = requests.get("https://irsa.ipac.caltech.edu/SIA", timeout=180, headers=UA,
                     params={"COLLECTION": "spitzer_sha", "POS": f"circle {ra} {dec} 0.0005", "RESPONSEFORMAT": "CSV"})
    q.raise_for_status()
    d = pd.read_csv(io.StringIO(q.text))
    if not len(d):
        return {"n": 0}
    col = "t_min" if "t_min" in d else None
    keep = d[d.get("dataproduct_subtype", pd.Series(["science"] * len(d))).astype(str).str.contains("science", na=True)]
    names = keep["obs_title"].astype(str) if "obs_title" in keep else keep.iloc[:, 0].astype(str)
    irac = keep[names.str.contains("IRAC", case=False) | keep.astype(str).apply(lambda r: "IRAC" in " ".join(r), axis=1)]
    from astropy.time import Time
    yrs = sorted(set(np.round(Time(irac[col].astype(float), format="mjd").decimalyear, 2))) if col and len(irac) else []
    return {"n_rows": len(d), "n_irac": len(irac), "irac_epochs_decimalyear": yrs[:200]}


def gaia_alerts(ra, dec, rs):
    a = pd.read_csv(DL / "gaia.csv")
    a.columns = [c.strip().lstrip("#") for c in a.columns]
    rc, dc = "RaDeg", "DecDeg"
    sep = np.hypot((a[rc] - ra) * np.cos(np.radians(dec)), a[dc] - dec) * 3600
    return {"n_alerts_in_file": len(a), "within": a[sep < rs].astype(str).to_dict("records"),
            "nearest_arcsec": float(sep.min())}


def asassn(ra, dec, rs):
    from astropy.coordinates import SkyCoord
    import astropy.units as u
    html = (DL / "https___www.astronomy.ohio-state.edu_asassn_transients.html").read_text(errors="ignore")
    rows = re.findall(r"(\d{2}:\d{2}:\d{2}\.\d+)\s*</td>\s*<td[^>]*>\s*([+-]\d{2}:\d{2}:\d{2}\.\d+)", html)
    if not rows:
        return "ERROR: could not parse the cached ASAS-SN page (not a null result)"
    c = SkyCoord([r[0] for r in rows], [r[1] for r in rows], unit=(u.hourangle, u.deg))
    s = c.separation(SkyCoord(ra, dec, unit="deg")).arcsec
    return {"n_rows_parsed": len(rows), "within": int((s < rs).sum()), "nearest_arcsec": float(s.min())}


def alerce(ra, dec, rs):
    q = requests.get("https://api.alerce.online/ztf/v1/objects/", timeout=120, headers=UA,
                     params={"ra": ra, "dec": dec, "radius": rs, "page_size": 100})
    q.raise_for_status()
    items = q.json().get("items", [])
    out = []
    for it in items:
        s = float(np.hypot((it["meanra"] - ra) * np.cos(np.radians(dec)), it["meandec"] - dec) * 3600)
        out.append(dict(oid=it["oid"], sep=round(s, 1), ndet=it.get("ndet"), firstmjd=it.get("firstmjd"),
                        lastmjd=it.get("lastmjd")))
    return sorted(out, key=lambda x: x["sep"])


def mast(ra, dec, rs):
    from astropy.time import Time
    from astroquery.mast import Observations
    obs = Observations.query_region(f"{ra} {dec}", radius=f"{rs} arcsec").to_pandas()
    obs = obs[obs.obs_collection.isin(["HST", "JWST", "SPITZER_SHA"]) & (obs.dataproduct_type == "image")]
    if "intentType" in obs:
        obs = obs[obs.intentType == "science"]
    if not len(obs):
        return []
    obs["date"] = Time(obs.t_min.values, format="mjd").iso
    obs["year"] = Time(obs.t_min.values, format="mjd").decimalyear.round(2)
    obs["release"] = [Time(t, format="mjd").iso[:10] if np.isfinite(t) else "" for t in obs.t_obs_release]
    g = obs.groupby(["obs_collection", "instrument_name", "proposal_id", "proposal_pi"]).agg(
        n=("obs_id", "size"), first=("date", "min"), last=("date", "max"),
        filters=("filters", lambda s: ",".join(sorted(set(map(str, s)))[:12])),
        rights=("dataRights", lambda s: ",".join(sorted(set(map(str, s)))))).reset_index()
    return g.astype(str).to_dict("records")


def ned(name):
    q = requests.post("https://ned.ipac.caltech.edu/srs/ObjectLookup", timeout=120, headers=UA,
                      data={"json": json.dumps({"name": {"v": name}})})
    q.raise_for_status()
    j = q.json()
    pr = j.get("Preferred", {})
    rz = pr.get("Redshift", {})
    lookup = dict(status=j.get("ResultCode"), ned_name=pr.get("Name"), z=rz.get("Value"), z_unc=rz.get("Uncertainty"),
                  z_ref=rz.get("RefCode"), ra=pr.get("Position", {}).get("RA"), dec=pr.get("Position", {}).get("Dec"))
    time.sleep(3)
    h = requests.get("https://ned.ipac.caltech.edu/cgi-bin/nDistance", timeout=120, headers=UA,
                     params={"name": name})
    h.raise_for_status()
    try:
        t = pd.read_html(io.StringIO(h.text))
        big = max(t, key=len)
        cols = [c for c in big.columns if "Mpc" in str(c) or str(c).strip().lower() == "d (mpc)"]
        meth = [c for c in big.columns if "Method" in str(c)]
        vals = pd.to_numeric(big[cols[0]], errors="coerce").dropna() if cols else pd.Series(dtype=float)
        dist = dict(n=int(len(vals)), min=float(vals.min()) if len(vals) else None,
                    median=float(vals.median()) if len(vals) else None, max=float(vals.max()) if len(vals) else None,
                    methods=sorted(set(big[meth[0]].astype(str))) if meth else [])
        if len(vals):
            big[[cols[0]] + meth].to_csv(OUT / f"ned_distances_{name.replace(' ', '_')}.csv", index=False)
    except Exception as e:  # noqa: BLE001
        dist = err(e)
    return dict(lookup=lookup, distances=dist)


def ads(s):
    tok = (Path.home() / ".config/oddsky/ads-token").read_text().strip()
    api = "https://api.adsabs.harvard.edu/v1/search/query"
    hosts = " OR ".join(f'"{h}"' for h in [s["host"]] + s["host_alias"])
    Q = {
        "position_strings": f"full:({' OR '.join(s['pos_strings'])}) collection:astronomy",
        "atel_host": f"full:({hosts}) bibstem:ATel",
        "tns_bibstems_host": f"full:({hosts}) bibstem:(TNSTR OR TNSAN OR TNSCR)",
        "host_ir_transient_2019plus": f"full:({hosts}) full:(\"infrared transient\" OR \"mid-infrared\" OR NEOWISE OR \"infrared outburst\" OR SPIRITS) year:2019-2026",
        "host_recent_entries": f"full:({hosts}) entdate:[2026-10-01 TO *]",
    }
    res = {}
    for k, q in Q.items():
        time.sleep(1.5)
        try:
            r = requests.get(api, params={"q": q, "fl": "bibcode,title,year", "rows": 200, "sort": "date desc"},
                             headers={"Authorization": f"Bearer {tok}"}, timeout=60)
            if r.status_code != 200:
                res[k] = {"query": q, "error": f"HTTP {r.status_code} (not a null result)"}
                continue
            d = r.json()["response"]
            res[k] = {"query": q, "numFound": d["numFound"],
                      "docs": [{"bibcode": x["bibcode"], "title": (x.get("title") or [""])[0][:160]} for x in d["docs"]]}
        except Exception as e:  # noqa: BLE001
            res[k] = {"query": q, "error": err(e)}
    return res


CHECKS = [
    ("simbad_15arcsec", lambda s: simbad(s["ra"], s["dec"], 15)),
    ("vsx_30arcsec", lambda s: viz("B/vsx/vsx", s["ra"], s["dec"], 30)),
    ("gaia_dr3_6arcsec", lambda s: viz("I/355/gaiadr3", s["ra"], s["dec"], 6,
                                       "Source,RA_ICRS,DE_ICRS,Gmag,BP-RP,Plx,e_Plx,pmRA,pmDE,RUWE,VarFlag")),
    ("allwise_6arcsec", lambda s: viz("II/328/allwise", s["ra"], s["dec"], 6, "AllWISE,RAJ2000,DEJ2000,W1mag,W2mag,W3mag,W4mag,ccf,ex")),
    ("seip_5arcsec", lambda s: seip(s["ra"], s["dec"], 5)),
    ("spitzer_sha_irac", lambda s: sha_count(s["ra"], s["dec"])),
    ("gaia_alerts_60arcsec", lambda s: gaia_alerts(s["ra"], s["dec"], 60)),
    ("asassn_transients_60arcsec", lambda s: asassn(s["ra"], s["dec"], 60)),
    ("alerce_ztf_60arcsec", lambda s: alerce(s["ra"], s["dec"], 60) if s["ztf"] else "not applicable: outside the ZTF footprint (dec < -31)"),
    ("mast_30arcsec", lambda s: mast(s["ra"], s["dec"], 30)),
    ("ned_host", lambda s: ned(s["ned"])),
    ("ads", ads),
]

res = {}
for lab, s in SRC.items():
    res[lab] = {"position": [s["ra"], s["dec"]]}
    for name, fn in CHECKS:
        time.sleep(2)
        try:
            res[lab][name] = fn(s)
        except Exception as e:  # noqa: BLE001
            res[lab][name] = err(e)
        v = res[lab][name]
        short = json.dumps(v, default=str)
        print(lab, name, short[:900], flush=True)
    (OUT / "archives.json").write_text(json.dumps(res, indent=1, default=str))
