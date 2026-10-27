"""Hunt H-0002 deep vetting for finalists (tiers A-C): exposure-level checks against IRSA.

  centroid_shift   how far the IR position moves during the brightening (arcsec). A real afterglow on
                   the star stays put; a neighbour or a moving object drags the centroid.
  w2_neighbor_frac fraction of W2 flux within 15" that belongs to other AllWISE sources (red, faint-in-Gaia
                   neighbours are invisible to a G-band blend check).
  w3_snr           AllWISE W3 signal-to-noise: whether "dust before 2010" is measurable at all.
Writes hunts/H-0002/runs/<run>/deepvet.parquet and sheets/<cntr>.png.
"""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from astropy.io import ascii as aascii

from oddsky.data.http import request
from oddsky.data.neowise import quality_cuts
from oddsky.data.provenance import Provenance

GATOR = "https://irsa.ipac.caltech.edu/cgi-bin/Gator/nph-query"
run = sys.argv[1]
here = Path(f"hunts/H-0002/runs/{run}")
(here / "sheets").mkdir(exist_ok=True)
v = pd.read_parquet(here / "vetted.parquet")
fin = v[v.tier.str[0].isin(list(sys.argv[2] if len(sys.argv) > 2 else "ABC"))]
print(len(fin), "finalists", flush=True)


def gator(catalog, ra, dec, radius, cols):
    p = dict(catalog=catalog, spatial="cone", radius=radius, radunits="arcsec", objstr=f"{ra} {dec}", outfmt=1, selcols=cols)
    r = request("GET", GATOR, params=p, timeout=300)
    if "ERROR" in r.text[:500]:
        raise RuntimeError(r.text[:300])
    return aascii.read(r.text.splitlines(), format="ipac").to_pandas()


rows = []
for s in fin.itertuples():
    rec = {"allwise_cntr": s.allwise_cntr}
    try:
        ex = gator("neowiser_p1bs_psd", s.ra, s.dec, 3.0, "ra,dec,mjd,w1mpro,w1sigmpro,w2mpro,w2sigmpro,qual_frame,qi_fact,saa_sep,"
                   "moon_masked,cc_flags,ph_qual,nb,na,w1snr,w2snr,w1rchi2,w2rchi2,w1sat,w2sat")
        ex = quality_cuts(ex, "W2", Provenance(archive="x"))
        ex = ex.sort_values("mjd")
        vis = (ex.mjd.diff() > 30).cumsum()
        g = ex.groupby(vis)
        vt = pd.DataFrame({"t": g.mjd.median(), "w1": g.w1mpro.median(), "w2": g.w2mpro.median(),
                           "ra": g.ra.median(), "dec": g.dec.median(), "n": g.size()})
        vt = vt[vt.n >= 3]
        b = vt.iloc[:3]
        ra0, dec0 = b.ra.median(), b.dec.median()
        vt["off"] = np.hypot((vt.ra - ra0) * np.cos(np.radians(dec0)), vt.dec - dec0) * 3600
        bright = vt[vt.w2 < b.w2.median() - 0.15]
        rec["centroid_shift"] = float(bright.off.median()) if len(bright) else np.nan
        rec["centroid_scatter_base"] = float(vt.off.iloc[:3].median())
        nb = gator("allwise_p3as_psd", s.ra, s.dec, 15.0, "ra,dec,w1mpro,w2mpro,w3mpro,w3snr,w4mpro,w4snr,cc_flags,ext_flg")
        nb["sep"] = np.hypot((nb.ra - s.ra) * np.cos(np.radians(s.dec)), nb.dec - s.dec) * 3600
        tgt = nb.loc[nb.sep.idxmin()]
        f2 = 10 ** (-0.4 * nb.w2mpro.astype(float))
        rec["w2_neighbor_frac"] = float(f2[nb.index != tgt.name].sum() / f2.sum())
        rec["w3_snr"] = float(tgt.w3snr) if pd.notna(tgt.w3snr) else np.nan
        rec["w1_w3_allwise_meas"] = float(tgt.w1mpro - tgt.w3mpro) if pd.notna(tgt.w3snr) and tgt.w3snr >= 3 else np.nan
        rec["ext_flg"] = int(tgt.ext_flg) if pd.notna(tgt.ext_flg) else None
        # sheet
        fig, ax = plt.subplots(3, 1, figsize=(7, 7), sharex=True)
        ax[0].plot(vt.t, vt.w1, "o-", color="#c9832b", label="W1")
        ax[0].plot(vt.t, vt.w2, "s-", color="#b0303f", label="W2")
        ax[0].invert_yaxis()
        ax[0].legend(fontsize=7)
        ax[0].set_title(f"{s.allwise_cntr}  {s.tier}\nG={s.G:.2f} BP-RP={s.bp_rp:.2f} absG={s.absG:.2f} rise={s.w2_rise:.2f} mag", fontsize=8)
        ax[1].plot(vt.t, vt.w1 - vt.w2, "o-", color="#555")
        ax[1].set_ylabel("W1-W2")
        ax[2].plot(vt.t, vt.off, "o-", color="#3b6fd4")
        ax[2].set_ylabel('offset (")')
        fig.tight_layout()
        fig.savefig(here / "sheets" / f"{s.allwise_cntr}.png", dpi=80)
        plt.close(fig)
    except Exception as e:  # noqa: BLE001
        rec["error"] = str(e)[:200]
    rows.append(rec)
    print(rec, flush=True)
d = fin.merge(pd.DataFrame(rows), on="allwise_cntr", how="left")
d.to_parquet(here / "deepvet.parquet", index=False)
