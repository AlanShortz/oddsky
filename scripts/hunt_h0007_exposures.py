"""H-0007: exposure-level check of a single-visit NEOWISE event (IRSA neowiser_p1bs_psd, 90" cone).

For the target (within 2" of the AllWISE position): every exposure in the event visit, with its offset from
the star and W1/W2. For every other source in the cone (the controls): its W1/W2 change at the event visit
relative to its own median, so a frame-calibration error shows up as all stars moving together.
usage: hunt_h0007_exposures.py RA DEC EVENT_MJD [label]
"""

import sys

import numpy as np
from astropy.io import ascii as aascii

from oddsky.data.http import request

GATOR = "https://irsa.ipac.caltech.edu/cgi-bin/Gator/nph-query"
ra, dec, tev = float(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3])
label = sys.argv[4] if len(sys.argv) > 4 else f"{ra:.4f}_{dec:.4f}"
cols = (
    "ra,dec,mjd,w1mpro,w1sigmpro,w2mpro,w2sigmpro,qual_frame,qi_fact,saa_sep,moon_masked,cc_flags,ph_qual,nb,na,"
    "w1rchi2,w2rchi2,allwise_cntr,r_allwise,source_id,scan_id,frame_num,sso_flg"
)
p = dict(
    catalog="neowiser_p1bs_psd",
    spatial="cone",
    radius=90,
    radunits="arcsec",
    objstr=f"{ra} {dec}",
    outfmt=1,
    selcols=cols,
)
r = request("GET", GATOR, params=p, timeout=600)
ex = aascii.read(r.text.splitlines(), format="ipac").to_pandas()
ex.to_parquet(f"hunts/H-0007/work/exp_{label}.parquet")
ex["sep"] = 3600 * np.hypot((ex.ra - ra) * np.cos(np.radians(dec)), ex.dec - dec)
ex["visit"] = np.round((ex.mjd - 55000) / 182.6).astype(
    int
)  # NEOWISE revisits each position every ~6 months
vev = int(np.round((tev - 55000) / 182.6))
ok = (ex.qual_frame > 0) & (ex.qi_fact > 0) & (ex.saa_sep > 0) & (ex.nb == 1)
t = ex[(ex.sep < 2.5)].sort_values("mjd")
print(f"target exposures: {len(t)}; event visit {vev}")
e = t[t.visit == vev]
print(
    e[
        [
            "mjd",
            "w1mpro",
            "w1sigmpro",
            "w2mpro",
            "w2sigmpro",
            "sep",
            "cc_flags",
            "ph_qual",
            "qual_frame",
            "w1rchi2",
            "w2rchi2",
            "nb",
            "na",
            "scan_id",
        ]
    ].to_string()
)
summ = (
    t[ok.loc[t.index]]
    .groupby("visit")
    .agg(
        t=("mjd", "median"),
        n=("mjd", "size"),
        w1=("w1mpro", "median"),
        w2=("w2mpro", "median"),
        sep=("sep", "median"),
        r1=("w1rchi2", "median"),
    )
)
print(summ.to_string())
# controls: other AllWISE-associated sources in the cone
c = ex[ok & (ex.sep > 5) & ex.allwise_cntr.notna() & (ex.r_allwise < 2)].copy()
c["dw1"] = c.w1mpro - c.groupby("allwise_cntr").w1mpro.transform("median")
c["dw2"] = c.w2mpro - c.groupby("allwise_cntr").w2mpro.transform("median")
cv = (
    c[c.visit == vev]
    .groupby("allwise_cntr")
    .agg(
        n=("mjd", "size"),
        w1=("w1mpro", "median"),
        dw1=("dw1", "median"),
        dw2=("dw2", "median"),
        sep=("sep", "first"),
    )
)
print(
    f"\ncontrols at event visit: {len(cv)} sources; median dW1 {cv.dw1.median():+.3f}, dW2 {cv.dw2.median():+.3f}; "
    f"|dW1|>0.3: {(cv.dw1.abs() > 0.3).sum()}"
)
print(cv.sort_values("sep").head(12).to_string())
# new sources near the target in the event visit that are not AllWISE-associated
n = ex[(ex.visit == vev) & (ex.sep < 20) & (ex.sep > 2.5)]
print(
    f'\nother detections within 20" in the event visit: {len(n)}; outside it per visit: '
    f"{len(ex[(ex.visit != vev) & (ex.sep < 20) & (ex.sep > 2.5)]) / max(1, ex.visit.nunique() - 1):.1f}"
)
