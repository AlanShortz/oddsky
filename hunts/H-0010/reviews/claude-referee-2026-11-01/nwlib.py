"""Exposure-level NEOWISE helpers (referee's own code). Input: data/frames/<sid>.csv (all detections within 8" of the Gaia position).
visit_table: per visit, (a) the detection nearest the Gaia star within 3" (what an association-by-position light curve uses),
(b) every detection within 8" summed per frame (blend total), (c) the number of detections per frame, (d) the centroid offsets of
the detection nearest the star, (e) flag shares. Frames of a visit are grouped by gaps > 30 d."""
import numpy as np
import pandas as pd


def load(path, ra0, de0):
    d = pd.read_csv(path, dtype={"cc_flags": str, "ph_qual": str, "moon_masked": str, "scan_id": str})
    d = d[np.isfinite(d.w1mpro) | np.isfinite(d.w2mpro)].copy()
    d["dx"] = (d.ra - ra0) * np.cos(np.radians(de0)) * 3600
    d["dy"] = (d.dec - de0) * 3600
    d["r"] = np.hypot(d.dx, d.dy)
    o = np.argsort(d.mjd.values)
    v = np.zeros(len(d), int)
    v[o] = np.r_[0, np.cumsum(np.diff(d.mjd.values[o]) > 30)]
    d["vis"] = v
    d["fk"] = d.scan_id.astype(str) + "_" + d.frame_num.astype(str)
    d["cc"] = d.cc_flags.astype(str).str.zfill(4)
    d["clean"] = (d.cc.str[0] == "0") & (d.cc.str[1] == "0") & (d.nb == 1) & (d.w1sat.fillna(0) < 0.05)
    return d


def f(m):
    return 10 ** (-0.4 * np.asarray(m, float))


def m(fl):
    return -2.5 * np.log10(np.asarray(fl, float))


def visit_table(d, rnear=3.0):
    rows = []
    for v, g in d.groupby("vis"):
        nfr = g.fk.nunique()
        tot1 = g.groupby("fk").w1mpro.apply(lambda x: f(x[np.isfinite(x)]).sum())
        tot2 = g.groupby("fk").w2mpro.apply(lambda x: f(x[np.isfinite(x)]).sum())
        near = g[g.r < rnear].sort_values("r").drop_duplicates("fk")
        rows.append(dict(vis=v, mjd=g.mjd.median(), n_frames=nfr, n_det=len(g), det_per_frame=g.groupby("fk").size().median(),
                         n_near=len(near), W1_near=near.w1mpro.median(), W2_near=near.w2mpro.median(), r_near=near.r.median(),
                         dx_near=near.dx.median(), dy_near=near.dy.median(), clean_near=near.clean.mean() if len(near) else np.nan,
                         nb_near=near.nb.median(), W1_tot=m(tot1.median()), W2_tot=m(tot2.median()),
                         W1_near_clean=near[near.clean].w1mpro.median(), n_near_clean=int(near.clean.sum())))
    return pd.DataFrame(rows)
