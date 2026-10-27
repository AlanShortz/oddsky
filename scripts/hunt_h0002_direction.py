"""Centroid-direction test: during the brightening, does the WISE centroid move toward the star's Gaia
position (the star brightened) or away from it (a neighbour or a moving object)?

For each finalist: Gaia DR3 position propagated to each NEOWISE visit with its proper motion; per-visit
WISE centroid; distance to the star before (first 3 visits) and during the rise.
Real event on the star: d_rise <= d_before (+ noise). Impostor: d_rise > d_before.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from astropy.io import ascii as aascii

from oddsky.data.gaia import adql
from oddsky.data.http import request
from oddsky.data.neowise import quality_cuts
from oddsky.data.provenance import Provenance

here = Path(f"hunts/H-0002/runs/{sys.argv[1]}")
d = pd.read_parquet(here / "deepvet.parquet")
ids = sys.argv[2:] or [str(x) for x in d.allwise_cntr]
d = d[d.allwise_cntr.astype(str).isin(ids)]
out = []
for s in d.itertuples():
    # Match by position: 19-digit Gaia ids do not survive a float column.
    g = adql(f"SELECT TOP 1 ra, dec, pmra, pmdec, ref_epoch FROM gaiadr3.gaia_source WHERE 1=CONTAINS(POINT(ra,dec), "
             f"CIRCLE({s.ra},{s.dec},{2 / 3600})) ORDER BY phot_g_mean_mag").iloc[0]
    p = dict(catalog="neowiser_p1bs_psd", spatial="cone", radius=3.0, radunits="arcsec", objstr=f"{s.ra} {s.dec}", outfmt=1,
             selcols="ra,dec,mjd,w1mpro,w1sigmpro,w2mpro,w2sigmpro,qual_frame,qi_fact,saa_sep,moon_masked,cc_flags,ph_qual,nb,na,w1snr,w2snr,w1rchi2,w2rchi2,w1sat,w2sat")
    ex = aascii.read(request("GET", "https://irsa.ipac.caltech.edu/cgi-bin/Gator/nph-query", params=p, timeout=300).text.splitlines(), format="ipac").to_pandas()
    ex = quality_cuts(ex, "W2", Provenance(archive="x")).sort_values("mjd")
    vis = (ex.mjd.diff() > 30).cumsum()
    gv = ex.groupby(vis)
    vt = pd.DataFrame({"t": gv.mjd.median(), "w2": gv.w2mpro.median(), "ra": gv.ra.median(), "dec": gv.dec.median(), "n": gv.size()})
    vt = vt[vt.n >= 3].reset_index(drop=True)
    yr = 2016.0 + (vt.t - 57388.5) / 365.25 - (g.ref_epoch - 2016.0)
    pmra = 0 if pd.isna(g.pmra) else g.pmra
    pmdec = 0 if pd.isna(g.pmdec) else g.pmdec
    sra = g.ra + pmra / 3.6e6 / np.cos(np.radians(g.dec)) * (yr - 2016.0)
    sdec = g.dec + pmdec / 3.6e6 * (yr - 2016.0)
    vt["d_star"] = np.hypot((vt.ra - sra) * np.cos(np.radians(g.dec)), vt.dec - sdec) * 3600
    base = vt.iloc[:3]
    bright = vt[vt.w2 < base.w2.median() - 0.15]
    rec = {"allwise_cntr": s.allwise_cntr, "pm_mas_yr": float(np.hypot(pmra, pmdec)),
           "d_before": float(base.d_star.median()), "d_rise": float(bright.d_star.median()) if len(bright) else np.nan,
           "n_bright_visits": int(len(bright)), "noise": float(max(base.d_star.std(), 0.03))}
    rec["toward_star"] = bool(rec["d_rise"] <= rec["d_before"] + 2 * rec["noise"]) if len(bright) else None
    out.append(rec)
    print(rec, flush=True)
pd.DataFrame(out).to_parquet(here / "direction.parquet", index=False)
