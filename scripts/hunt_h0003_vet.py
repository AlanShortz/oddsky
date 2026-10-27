"""Hunt H-0003, step 4: vet R CrB-like candidates (AllWISE colours, VSX, SIMBAD, RCB catalogues)."""
from pathlib import Path

import httpx
import pandas as pd

from oddsky.data.gaia import adql
from oddsky.data.http import request

here = Path("hunts/H-0003")
sc = pd.read_csv(here / "scored.csv")
pick = sc[sc.rcb_like].copy()
ids = ",".join(str(s) for s in pick.source_id)
wise = adql("SELECT x.source_id, a.w1mpro, a.w2mpro, a.w3mpro, a.w4mpro, a.ph_qual FROM gaiadr3.allwise_best_neighbour AS x "
            f"JOIN gaiadr1.allwise_original_valid AS a ON a.allwise_oid = x.allwise_oid WHERE x.source_id IN ({ids})")
pick = pick.merge(wise, on="source_id", how="left")
cls = adql(f"SELECT source_id, best_class_name, best_class_score FROM gaiadr3.vari_classifier_result WHERE source_id IN ({ids})")
pick = pick.merge(cls, on="source_id", how="left")


def vizier_rcb_known(ra, dec):
    hits = []
    for tab in ("J/A+A/667/A84/objects", "J/A+A/635/A14/list", "J/AJ/156/148/table1", "J/ApJ/747/102/stars"):
        q = (f'SELECT TOP 1 * FROM "{tab}" WHERE 1=CONTAINS(POINT(\'ICRS\', RAJ2000, DEJ2000), '
             f"CIRCLE('ICRS', {ra}, {dec}, {10 / 3600}))")
        try:
            r = httpx.post("https://tapvizier.cds.unistra.fr/TAPVizieR/tap/sync", timeout=60,
                           data=dict(REQUEST="doQuery", LANG="ADQL", FORMAT="csv", QUERY=q))
            if r.status_code == 200 and len(r.text.strip().splitlines()) > 1:
                hits.append(tab)
        except Exception:  # noqa: BLE001
            pass
    return hits


def vsx(ra, dec):
    r = request("GET", "https://www.aavso.org/vsx/index.php", timeout=60,
                params={"view": "api.list", "ra": ra, "dec": dec, "radius": 10 / 3600, "format": "json"})
    try:
        objs = r.json().get("VSXObjects", {}).get("VSXObject", [])
    except ValueError:
        return []
    objs = objs if isinstance(objs, list) else [objs]
    return [f"{o.get('Name')} [{o.get('VariabilityType')}]" for o in objs]


def simbad(ra, dec):
    from astroquery.simbad import Simbad
    q = ("SELECT TOP 3 main_id, otype FROM basic WHERE CONTAINS(POINT('ICRS', ra, dec), "
         f"CIRCLE('ICRS', {ra}, {dec}, {5 / 3600})) = 1")
    try:
        return [f"{r['main_id']} ({r['otype']})" for r in Simbad.query_tap(q)]
    except Exception as e:  # noqa: BLE001
        return [f"error {str(e)[:60]}"]


out = []
for _, s in pick.iterrows():
    rec = {"source_id": int(s.source_id), "vsx": vsx(s.ra, s.dec), "simbad": simbad(s.ra, s.dec),
           "rcb_catalogues": vizier_rcb_known(s.ra, s.dec)}
    out.append(rec)
    print(s.source_id, rec, flush=True)
pick = pick.merge(pd.DataFrame(out), on="source_id")
pick.to_json(here / "vetted.json", orient="records", indent=1)
print("done", len(pick))
