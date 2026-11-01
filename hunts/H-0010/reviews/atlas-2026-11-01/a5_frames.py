"""a5: event nights frame by frame. Every frame of the nights that carry the event test (within 60 d of the Gaia t0, plus J184922's
2016 Oct nights) is listed with its detector position, PSF, depth, sky and chi/N, and compared with the K=25 nearest quiet frames in
PSF-shape space (maj, min, e cos 2phi, e sin 2phi) of the same unit and band (|dt| > 150 d from t0, all cut-passing frames, no chi/N
cut). The empirical tail probability p_emp is the share of quiet frames whose own kNN residual (leave-one-out, same metric) is at least
as large as the frame's, so non-Gaussian PSF systematics are accounted for. Also: the frame's distance to the detector edge, and
whether the residual repeats in every frame of the night.
Run: uv run python -I hunts/H-0010/reviews/atlas-2026-11-01/a5_frames.py"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import KEYS, atlas_raw, clean, mjd2date, targets  # noqa: E402

pd.set_option("display.width", 260)
pd.set_option("display.max_rows", 500)
T = targets()
KF = 25
EXTRA = {"J184922": (57660, 57700)}  # 2016 Oct 1 - Nov 10: the ATLAS o rise and c dips


def feats(d):
    e = d.maj - d["min"]
    return np.vstack([d.maj, d["min"], e * np.cos(2 * np.radians(d.phi)), e * np.sin(2 * np.radians(d.phi))]).T


for k in KEYS:
    t = T[k]
    t0 = t["t0"]
    r = clean(atlas_raw(k))
    r["dt"] = r.mjd - t0
    win = (np.abs(r.dt) <= 60)
    if k in EXTRA:
        win |= (r.mjd >= EXTRA[k][0]) & (r.mjd <= EXTRA[k][1])
    ev = r[win].sort_values("mjd")
    print("=" * 40, k, t["name"], f"t0 {mjd2date(t0)}; frames within 60 d: {len(ev)}")
    if len(ev) == 0:
        continue
    rows = []
    for (F, cam), d in r.groupby(["F", "cam"]):
        q = d[np.abs(d.dt) > 150]
        e = ev[(ev.F == F) & (ev.cam == cam)]
        if len(e) == 0 or len(q) < KF + 5:
            continue
        Xq = feats(q)
        # leave-one-out residuals of the quiet frames
        resq = np.empty(len(q))
        scq = np.empty(len(q))
        for i in range(len(q)):
            dist = np.sqrt(np.sum((Xq - Xq[i]) ** 2, axis=1))
            dist[i] = np.inf
            o = np.argsort(dist)[:KF]
            v = q.ujy.values[o]
            resq[i] = q.ujy.values[i] - np.median(v)
            scq[i] = 1.4826 * np.median(np.abs(v - np.median(v)))
        zq = resq / np.hypot(scq, q.dujy.values)
        Xe = feats(e)
        for j, row in enumerate(e.itertuples()):
            dist = np.sqrt(np.sum((Xq - Xe[j]) ** 2, axis=1))
            o = np.argsort(dist)[:KF]
            v = q.ujy.values[o]
            med = np.median(v)
            sc = 1.4826 * np.median(np.abs(v - med))
            res = row.ujy - med
            z = res / np.hypot(sc, row.dujy)
            p = float(np.mean(zq >= z)) if z > 0 else float(np.mean(zq <= z))
            edge = min(row.x, row.y, 10560 - row.x, 10560 - row.y)
            rows.append(dict(date=mjd2date(row.mjd), mjd=round(row.mjd, 4), dt=round(row.dt, 2), F=F, cam=cam, ujy=row.ujy, dujy=row.dujy,
                             knn_base=round(med, 1), knn_sc=round(sc, 1), kdist=round(float(dist[o].max()), 2), resid=round(res, 1),
                             z=round(z, 2), p_emp=round(p, 4), chi=row.chi_n, maj=row.maj, mn=e["min"].values[j], phi=row.phi, apfit=row.apfit,
                             m5=row.mag5sig, sky=row.sky, x=int(row.x), y=int(row.y), edge=int(edge), obs=row.obs))
        print(f"  {F} {cam}: quiet frames {len(q)}; quiet z robust std {1.4826 * np.median(np.abs(zq - np.median(zq))):.2f}; "
              f"share of quiet frames with z > 3: {np.mean(zq > 3):.3f}, z > 5: {np.mean(zq > 5):.4f}, z < -3: {np.mean(zq < -3):.3f}")
    if rows:
        R = pd.DataFrame(rows).sort_values("mjd")
        print(R.drop(columns=["mjd"]).to_string(index=False))
        R.to_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", f"a5_frames_{k}.csv"), index=False)
