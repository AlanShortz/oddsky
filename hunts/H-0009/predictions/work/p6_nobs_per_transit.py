"""p6: DR3 G CCD observations per matched transit (phot_g_n_obs / matched_transits) for each target vs DR3 stars within
2' and +-0.5 mag (ESA TAP, one query per target). If DR3 mean photometry rejected the CCD fluxes of strongly brightened
transits, the target shows a deficit. Weak evidence only: crowding/gating also change the count."""
import io
import os
import sys

import httpx
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from targets import HERE, T  # noqa: E402

TAP = "https://gea.esac.esa.int/tap-server/tap/sync"
rows = []
for k, t in T.items():
    adql = (f"SELECT source_id, phot_g_mean_mag, phot_g_n_obs, matched_transits, ruwe FROM gaiadr3.gaia_source WHERE "
            f"1=CONTAINS(POINT(ra,dec), CIRCLE({t['ra']},{t['dec']},{2 / 60})) AND phot_g_mean_mag BETWEEN {t['G'] - 0.5} AND {t['G'] + 0.5}")
    try:
        r = httpx.post(TAP, data=dict(REQUEST="doQuery", LANG="ADQL", FORMAT="csv", QUERY=adql), timeout=240)
        d = pd.read_csv(io.StringIO(r.text), dtype={"source_id": str})
    except Exception as e:  # noqa: BLE001
        print(k, "query failed:", e)
        continue
    d["cpt"] = d.phot_g_n_obs / d.matched_transits
    me = d[d.source_id == t["gaia"]]
    o = d[d.source_id != t["gaia"]]
    c0 = float(me.cpt.iloc[0])
    pct = 100 * (o.cpt < c0).mean()
    print(f"{k}: CCD obs per transit {c0:.2f} vs field median {o.cpt.median():.2f} (n {len(o)}, 10th pct {np.percentile(o.cpt, 10):.2f}); "
          f"percentile {pct:.1f}; implied missing transits-worth {me.matched_transits.iloc[0] - me.phot_g_n_obs.iloc[0] / o.cpt.median():.1f}",
          flush=True)
    rows.append(dict(k=k, cpt=c0, field_median=float(o.cpt.median()), pct=pct))
pd.DataFrame(rows).to_csv(os.path.join(HERE, "dr3_ccd_per_transit.csv"), index=False)
