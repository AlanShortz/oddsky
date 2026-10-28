"""Hunt H-0005, step 1: fading Gaia Science Alerts on bright sources that were never classified, with Gaia DR3 context.

Input: hunts/H-0005/alerts.csv (the final alert list, http://gsaweb.ast.cam.ac.uk/alerts/alerts.csv, 27,076 alerts).
Keeps fades of > 0.5 mag from a historic G < 16.5 with class "unknown", and attaches the brightest Gaia DR3 source within
2" of each. Writes hunts/H-0005/candidates.csv.
"""
import io
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
import requests

GAIA_TAP = "https://gea.esac.esa.int/tap-server/tap/sync"

alerts = pd.read_csv("hunts/H-0005/alerts.csv", skipinitialspace=True)
alerts.columns = [c.strip("#").strip() for c in alerts.columns]
alerts["dm"] = alerts.AlertMag - alerts.HistoricMag
fading = alerts[(alerts.dm > 0.5) & (alerts.HistoricMag < 16.5) & (alerts.Class.str.strip() == "unknown")].copy()


def gaia_context(row) -> pd.DataFrame:
    q = (f"SELECT TOP 3 source_id, phot_g_mean_mag AS g, bp_rp, parallax, parallax_over_error AS poe, ruwe, "
         f"teff_gspphot AS teff, logg_gspphot AS logg, ag_gspphot AS ag, phot_variable_flag AS vf, l, b, "
         f"DISTANCE(POINT({row.RaDeg},{row.DecDeg}),POINT(ra,dec))*3600 AS sep FROM gaiadr3.gaia_source "
         f"WHERE 1=CONTAINS(POINT(ra,dec),CIRCLE({row.RaDeg},{row.DecDeg},{2 / 3600})) ORDER BY phot_g_mean_mag")
    for _ in range(4):
        try:
            r = requests.post(GAIA_TAP, data={"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": q},
                              timeout=90)
            if r.ok:
                d = pd.read_csv(io.StringIO(r.text), dtype={"source_id": str})
                d["Name"] = row.Name
                return d.head(1)
        except requests.RequestException:
            pass
        time.sleep(3)
    return pd.DataFrame({"Name": [row.Name]})


with ThreadPoolExecutor(4) as ex:
    ctx = pd.concat(ex.map(gaia_context, fading.itertuples()))
out = fading.merge(ctx, on="Name", how="left")
out["absg"] = out.g + 5 * np.log10(out.parallax.clip(lower=1e-3) / 100)
out.to_csv("hunts/H-0005/candidates.csv", index=False)
print(len(out), "fading unclassified alerts;", out.source_id.notna().sum(), "with a Gaia DR3 match")
