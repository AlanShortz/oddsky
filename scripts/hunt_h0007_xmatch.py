"""H-0007: Gaia DR3 (brightest source within 3") for each star, via ESA TAP in batches of 15 cones.
VSX is a separate step (scripts/hunt_h0007_vsx.py, VizieR mirror): vsx.aavso.org rate-limits and serves a CAPTCHA that a JSON
parser reads as "no match".
usage: hunt_h0007_xmatch.py IN_CSV(with cntr, ra, dec) OUT_CSV"""

import sys
import time

import numpy as np
import pandas as pd

from oddsky.data.gaia import adql

a = pd.read_csv(sys.argv[1])
out = sys.argv[2]
rows = []
for i in range(0, len(a), 15):
    chunk = a.iloc[i : i + 15]
    ors = " OR ".join(
        f"CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',{r.ra},{r.dec},3/3600.))=1"
        for r in chunk.itertuples()
    )
    q = (
        "SELECT source_id, ra, dec, phot_g_mean_mag, bp_rp, parallax, parallax_over_error, ruwe, pmra, pmdec, "
        "phot_variable_flag, non_single_star, teff_gspphot, logg_gspphot, classprob_dsc_combmod_star, "
        f"phot_bp_rp_excess_factor FROM gaiadr3.gaia_source WHERE {ors}"
    )
    g = adql(q, timeout=300)
    for r in chunk.itertuples():
        if len(g):
            sep = 3600 * np.hypot((g.ra - r.ra) * np.cos(np.radians(r.dec)), g.dec - r.dec)
            m = g[sep < 3].assign(sep=sep[sep < 3]).sort_values("phot_g_mean_mag")
        else:
            m = g
        n = len(m)
        best = m.iloc[0].to_dict() if n else {}
        rows.append({"cntr": r.cntr, "n_gaia_3as": n, **{f"g_{k}": v for k, v in best.items()}})
    time.sleep(1)
x = pd.DataFrame(rows)
x = a.merge(x, on="cntr")
x.to_csv(out, index=False)
print(
    x[
        [
            "cntr",
            "designation",
            "n_gaia_3as",
            "g_phot_g_mean_mag",
            "g_bp_rp",
            "g_parallax",
            "g_parallax_over_error",
            "g_ruwe",
        ]
    ].to_string()
)
