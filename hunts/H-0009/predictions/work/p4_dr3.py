"""p4: Gaia DR3 photometric stats for the six sources (one ESA TAP sync query, ~1 min) compared with the GOST transits
before the DR3 end (2017-05-28): matched_transits / GOST is the fraction of forecast transits that delivered photometry.
Neighbours within 6" (the WISE W1 beam) through VizieR I/355/gaiadr3 (vizier.idia.ac.za mirror)."""
import io
import os
import sys

import httpx
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gaialib import gost  # noqa: E402
from targets import HERE, T  # noqa: E402

TAP = "https://gea.esac.esa.int/tap-server/tap/sync"
ids = ",".join(t["gaia"] for t in T.values())
cols = ("source_id, phot_g_mean_mag, phot_g_n_obs, phot_g_mean_flux_over_error, phot_variable_flag, matched_transits, "
        "visibility_periods_used, ruwe, ipd_frac_multi_peak, bp_rp")
r = httpx.post(TAP, data=dict(REQUEST="doQuery", LANG="ADQL", FORMAT="csv",
                              QUERY=f"SELECT {cols} FROM gaiadr3.gaia_source WHERE source_id IN ({ids})"), timeout=180)
d = pd.read_csv(io.StringIO(r.text), dtype={"source_id": str})
# sigma of the mean G flux; per-CCD fractional rms = sqrt(n_obs)/(flux/err); per transit ~ that / sqrt(n_obs/transits)
d["rms_ccd"] = np.sqrt(d.phot_g_n_obs) / d.phot_g_mean_flux_over_error
d["rms_transit_est"] = 1.0857 * d.rms_ccd / np.sqrt(d.phot_g_n_obs / d.matched_transits)
d.to_csv(os.path.join(HERE, "dr3_stats.csv"), index=False)


def viz(ra, dec, rad=6):
    q = httpx.get("https://vizier.idia.ac.za/viz-bin/asu-tsv", params={"-source": "I/355/gaiadr3", "-c": f"{ra} {dec}",
                  "-c.rs": rad, "-out": "Source,Gmag,BP-RP", "-out.add": "_r", "-sort": "_r"}, timeout=180,
                  headers={"User-Agent": "oddsky/0.1"})
    lines = [ln for ln in q.text.splitlines() if ln and not ln.startswith("#")]
    df = pd.read_csv(io.StringIO("\n".join([lines[0]] + lines[3:])), sep="\t", dtype=str)
    df.columns = [c.strip() for c in df.columns]
    for c in ("_r", "Gmag", "BP-RP"):
        df[c] = pd.to_numeric(df[c].str.strip(), errors="coerce")
    df["sep"] = df["_r"] * (60 if df["_r"].max() < 1 else 1)
    return df


for k, t in T.items():
    x = d[d.source_id == t["gaia"]].iloc[0]
    tg = gost(k)
    n_gost = int((tg < 57901.0).sum())
    print(f"{k} {t['gaia']}: G {x.phot_g_mean_mag:.3f} BP-RP {x.bp_rp:.2f} n_obs(CCD) {x.phot_g_n_obs} matched_transits "
          f"{x.matched_transits} (GOST forecast to 2017-05-28: {n_gost}; delivered {x.matched_transits / n_gost:.0%}) "
          f"vis_periods {x.visibility_periods_used} var_flag {x.phot_variable_flag} RUWE {x.ruwe:.2f} ipd_multi {x.ipd_frac_multi_peak}"
          f"\n    per-transit G rms estimate {x.rms_transit_est:.4f} mag (an upper bound if the star varied in 2014-17)")
    nb = viz(t["ra"], t["dec"])
    f = 10 ** (-0.4 * nb.Gmag)
    me = nb.Source.str.strip() == t["gaia"]
    print(f"    DR3 within 6\": {len(nb)}; target share of G flux {float(f[me].sum() / f.sum()):.2f}; others: "
          + "; ".join(f"G {g:.2f} at {s:.1f}\"" for g, s, m in zip(nb.Gmag, nb.sep, me, strict=True) if not m))
