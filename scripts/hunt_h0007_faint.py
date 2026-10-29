"""H-0007 pass 3 analysis: one-visit achromatic events among the faint candidates (W1 13-15), from single exposures.

Per star: detections within 2.5" of the AllWISE position, standard single-exposure cuts per band (as in oddsky.sky.neowise_pixel),
visits split at gaps > 30 d, per-visit medians (>= 3 exposures in each band). An event is a run of 1-3 consecutive visits that is
brighter (or fainter) in both bands by >= max(0.3 mag, 6 sigma), achromatic (|dW1 - dW2| <= 0.1 + 0.15 |dW|), with every other
visit within max(0.15 mag, 4 sigma). Then the traps this hunt met, measured in the event visit against the others:
split detections (two sources within 2.5" in one frame), the reduced chi-square, the centroid offset, and the fraction of
frames with a W1/W2 artifact flag (cc_flags: D diffraction spike, P persistence, H halo, O ghost), which marks latents from bright stars.
usage: hunt_h0007_faint.py CANDS_POS_CSV EXP_DIR OUT_CSV
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

cands = pd.read_csv(sys.argv[1]).set_index("cntr")
exp_dir = Path(sys.argv[2])


def good(d, i):
    b = "w1" if i == 0 else "w2"
    return ((d.qual_frame > 0) & (d.qi_fact > 0) & (d.saa_sep > 0)
            & (d.moon_masked.astype(str).str.zfill(2).str[i] == "0")
            & (d.cc_flags.astype(str).str.zfill(4).str[i] == "0")
            & (d.ph_qual.astype(str).str[i].isin(["A", "B"])) & (d.nb == 1)
            & (d.sso_flg.fillna(0) == 0) & np.isfinite(d[f"{b}mpro"].astype(float)))


rows = []
for f in sorted(exp_dir.glob("*.parquet")):
    cntr = int(f.stem)
    d = pd.read_parquet(f)
    if d.empty or cntr not in cands.index:
        continue
    c = cands.loc[cntr]
    d["sep"] = 3600 * np.hypot((d.ra - c.ra) * np.cos(np.radians(c.dec)), d.dec - c.dec)
    d = d[d.sep < 2.5].sort_values("mjd").reset_index(drop=True)
    if len(d) < 20:
        continue
    d["frame"] = np.round(d.mjd, 5)
    d["split"] = d.groupby("frame").mjd.transform("size") > 1
    d["visit"] = np.r_[0, np.cumsum(np.diff(d.mjd.to_numpy()) > 30)]
    for i, b in enumerate(("w1", "w2")):
        d[f"{b}_ok"] = good(d, i)
    v = []
    for k, g in d.groupby("visit"):
        g1, g2 = g[g.w1_ok], g[g.w2_ok]
        if len(g1) < 3 or len(g2) < 3:
            continue
        v.append(dict(visit=k, t=g.mjd.median(), w1=g1.w1mpro.median(), w2=g2.w2mpro.median(),
                      e1=max(1.4826 * np.median(np.abs(g1.w1mpro - g1.w1mpro.median())), g1.w1sigmpro.median()) / np.sqrt(len(g1)),
                      e2=max(1.4826 * np.median(np.abs(g2.w2mpro - g2.w2mpro.median())), g2.w2sigmpro.median()) / np.sqrt(len(g2)),
                      n=len(g), split=int(g.split.sum()), rchi=g.w1rchi2.median(), off=g.sep.median(),
                      ccbad=float((g.cc_flags.astype(str).str.zfill(4).str[:2] != "00").mean())))
    v = pd.DataFrame(v)
    if len(v) < 10:
        continue
    for b in ("w1", "w2"):
        v[f"d{b}"] = v[b] - v[b].median()
        v[f"s{b}"] = np.maximum(1.4826 * np.median(np.abs(v[f"d{b}"])), 0.02)
    for sign, kind in ((-1, "brighten"), (1, "fade")):
        hit = ((sign * v.dw1 >= np.maximum(0.3, 6 * v.sw1)) & (sign * v.dw2 >= np.maximum(0.3, 6 * v.sw2))
               & ((v.dw1 - v.dw2).abs() <= 0.1 + 0.15 * v[["dw1", "dw2"]].abs().max(axis=1)))
        calm = (v.dw1.abs() <= np.maximum(0.15, 4 * v.sw1)) & (v.dw2.abs() <= np.maximum(0.15, 4 * v.sw2))
        k = np.flatnonzero(hit.to_numpy())
        if len(k) == 0 or len(k) > 3 or k[-1] - k[0] + 1 != len(k) or (hit | calm).sum() != len(v):
            continue
        e, o = v.iloc[k], v.drop(index=v.index[k])
        rows.append(dict(cntr=cntr, designation=c.designation, ra=c.ra, dec=c.dec, kind=kind, nhit=len(k),
                         edge=bool(k[0] == 0 or k[-1] == len(v) - 1), n_visits=len(v), t=float(e.t.iloc[0]),
                         year=float(1858.88 + e.t.iloc[0] / 365.25), dw1=float(e.dw1.iloc[0]), dw2=float(e.dw2.iloc[0]),
                         w1=float(v.w1.median()), w1w2=float((v.w1 - v.w2).median()), scatter_w1=float(v.sw1.iloc[0]),
                         split_event=int(e.split.sum()), split_other=int(o.split.sum()),
                         rchi_ratio=float(e.rchi.median() / o.rchi.median()), off_event=float(e.off.median()),
                         off_other=float(o.off.median()), ccbad_event=float(e.ccbad.max()),
                         ccbad_other=float(o.ccbad.median()), ext_flg=int(c.ext_flg)))
out = pd.DataFrame(rows)
out.to_csv(sys.argv[3], index=False)
print(f"stars analysed: {len(list(exp_dir.glob('*.parquet')))}; events: {len(out)}")
if len(out):
    print(out.groupby(["kind", "edge"]).size())
