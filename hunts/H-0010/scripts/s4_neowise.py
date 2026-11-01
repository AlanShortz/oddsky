"""s4: NEOWISE at each of the 67 positions.

  * AllWISE source within 3" (IRSA Gator allwise_p3as_psd): cntr, W1-W4, cc_flags, ext_flg, nb.
  * NEOWISE-R single exposures within 3" (IRSA Gator neowiser_p1bs_psd), matched to that AllWISE cntr when there is one,
    else the nearest detection per frame. Visit medians with H-0009's "long" cuts (keep nb <= 3, saturated frames and
    lowercase h/d flags; drop latents/ghosts p, o, uppercase flags, qual_frame 0, SAA, moon) and with the strict cuts of
    oddsky.data.neowise (cc_flags 0, nb 1, ph_qual A/B).
  * Did H-0008 or H-0009 flag an event on this AllWISE source? (sky3/sky4 brighten tables by cntr; sky4long pixel light
    curve if so.)

Run from the repo root: uv run python -I hunts/H-0010/scripts/s4_neowise.py
Writes hunts/H-0010/data/neowise/<source_id>_exp.csv, <source_id>_visits.csv and data/allwise.csv, data/neowise_events.csv."""
import os
import sys
import time

import numpy as np
import pandas as pd
from astropy.io import ascii as aascii

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA, NW, targets  # noqa: E402

from oddsky.data.http import request  # noqa: E402

GATOR = "https://irsa.ipac.caltech.edu/cgi-bin/Gator/nph-query"
COLS = ("ra,dec,mjd,w1mpro,w1sigmpro,w2mpro,w2sigmpro,qual_frame,qi_fact,saa_sep,moon_masked,cc_flags,ph_qual,w1sat,w2sat,"
        "nb,na,w1snr,w2snr,w1rchi2,w2rchi2,allwise_cntr,source_id")
AW_COLS = "cntr,designation,ra,dec,w1mpro,w1sigmpro,w2mpro,w2sigmpro,w3mpro,w4mpro,cc_flags,ext_flg,nb,na,ph_qual,j_m_2mass,k_m_2mass"
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
os.makedirs(NW, exist_ok=True)


def gator(catalog, ra, dec, radius, cols):
    params = dict(catalog=catalog, spatial="cone", radius=radius, radunits="arcsec", objstr=f"{ra} {dec}", outfmt=1,
                  selcols=cols)
    for k in range(4):
        r = request("GET", GATOR, params=params, timeout=300)
        if "[struct stat=\"ERROR\"" in r.text:
            print("  gator error:", r.text.strip().splitlines()[-1][:200])
            time.sleep(20)
            continue
        tbl = aascii.read(r.text.splitlines(), format="ipac")
        df = tbl.to_pandas()
        return df
    raise RuntimeError("gator failed")


def visit_medians(df, mode):
    rows = []
    if df.empty:
        return pd.DataFrame()
    cc = df.cc_flags.astype(str).str.ljust(4, "0")
    base = (df.qual_frame > 0) & (df.qi_fact > 0) & (df.saa_sep > 0) & (df.moon_masked.astype(str).str.zfill(2) == "00")
    t = df.mjd.values
    grp = np.concatenate([[0], np.cumsum(np.diff(t) > 30)])
    for b, idx in (("w1", 0), ("w2", 1)):
        c = cc.str[idx]
        m = df[f"{b}mpro"].astype(float)
        if mode == "strict":
            ok = base & (c == "0") & (df.nb == 1) & df.ph_qual.astype(str).str[idx].isin(["A", "B"]) & (df[f"{b}snr"] >= 4)
        else:
            ok = base & c.isin(["0", "h", "d"]) & (df.nb <= 3) & (df[f"{b}snr"] >= 3)
        ok &= np.isfinite(m)
        for gval in np.unique(grp):
            sel = ok.values & (grp == gval)
            if sel.sum() == 0:
                continue
            mm = m.values[sel]
            med = np.median(mm)
            mad = 1.4826 * np.median(np.abs(mm - med)) if sel.sum() > 2 else np.nan
            if np.isfinite(mad) and mad > 0:
                k = np.abs(mm - med) < 4 * mad
                mm = mm[k]
            ee = df[f"{b}sigmpro"].astype(float).values[sel]
            sc = 1.4826 * np.median(np.abs(mm - np.median(mm))) if len(mm) > 2 else np.nanmedian(ee)
            rows.append(dict(visit=int(gval), t=float(np.median(t[sel])), band=b.upper(), mag=float(np.median(mm)), n=len(mm),
                             err=float(max(sc / np.sqrt(len(mm)), np.nanmedian(ee) / np.sqrt(len(mm)), 0.005)),
                             satfrac=float((df[f"{b}sat"].values[sel] > 0.05).mean()),
                             hdfrac=float(c.values[sel].__ne__("0").mean()), nbfrac=float((df.nb.values[sel] > 1).mean())))
    return pd.DataFrame(rows)


def main():
    T = targets()
    aw_rows, ev_rows = [], []
    b3 = pd.read_csv(os.path.join(REPO, "hunts/H-0008/work/sky3_brighten.csv"), dtype={"allwise_cntr": str})
    b4 = pd.read_csv(os.path.join(REPO, "hunts/H-0009/work/sky4_brighten.csv"), dtype={"allwise_cntr": str})
    for r in T.itertuples():
        sid = r.source_id
        aw = gator("allwise_p3as_psd", r.ra, r.dec, 3.0, AW_COLS)
        if len(aw):
            aw["sep"] = np.hypot((aw.ra - r.ra) * np.cos(np.radians(r.dec)), aw.dec - r.dec) * 3600
            aw = aw.sort_values("sep")
            a0 = aw.iloc[0]
            cntr = str(int(a0.cntr))
            aw_rows.append(dict(source_id=sid, n_allwise_3as=len(aw), allwise_cntr=cntr, allwise=a0.designation,
                                aw_sep=round(float(a0.sep), 2), W1=a0.w1mpro, W2=a0.w2mpro, W3=a0.w3mpro, W4=a0.w4mpro,
                                aw_cc=a0.cc_flags, aw_ext=a0.ext_flg, aw_nb=a0.nb, J=a0.j_m_2mass, K=a0.k_m_2mass))
        else:
            cntr = None
            aw_rows.append(dict(source_id=sid, n_allwise_3as=0))
        path = os.path.join(NW, f"{sid}_exp.csv")
        if os.path.exists(path):
            ex = pd.read_csv(path, dtype={"allwise_cntr": str, "source_id": str})
        else:
            ex = gator("neowiser_p1bs_psd", r.ra, r.dec, 3.0, COLS)
            ex["allwise_cntr"] = ex.allwise_cntr.astype("Int64").astype(str)
            ex.to_csv(path, index=False)
        ex["sep"] = np.hypot((ex.ra - r.ra) * np.cos(np.radians(r.dec)), ex.dec - r.dec) * 3600
        if cntr and (ex.allwise_cntr == cntr).sum() > 10:
            use = ex[ex.allwise_cntr == cntr]
            how = "allwise_cntr"
        else:
            use = ex.sort_values("sep").drop_duplicates("mjd")
            how = "nearest"
        use = use.sort_values("mjd").reset_index(drop=True)
        vis = []
        for mode in ("long", "strict"):
            v = visit_medians(use, mode)
            if len(v):
                v["mode"] = mode
                vis.append(v)
        vis = pd.concat(vis, ignore_index=True) if vis else pd.DataFrame()
        vis.to_csv(os.path.join(NW, f"{sid}_visits.csv"), index=False)
        e3 = b3[b3.allwise_cntr == cntr] if cntr else b3.iloc[:0]
        e4 = b4[b4.allwise_cntr == cntr] if cntr else b4.iloc[:0]
        ev_rows.append(dict(source_id=sid, match=how, n_exp=len(use), n_exp_3as=len(ex),
                            n_visits_long=int((vis["mode"] == "long").sum() / 2) if len(vis) else 0,
                            h0008_events=";".join(f"{x.t:.1f}:{x.dw1:+.2f}:{x.kind}" for x in e3.itertuples()),
                            h0009_events=";".join(f"{x.t:.1f}:{x.dw1:+.2f}:{x.kind}:clean={x.clean}" for x in e4.itertuples())))
        print(sid, how, len(use), "exposures;", ev_rows[-1]["h0008_events"], ev_rows[-1]["h0009_events"], flush=True)
    pd.DataFrame(aw_rows).to_csv(os.path.join(DATA, "allwise.csv"), index=False)
    pd.DataFrame(ev_rows).to_csv(os.path.join(DATA, "neowise_events.csv"), index=False)


if __name__ == "__main__":
    main()
